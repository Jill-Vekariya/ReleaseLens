"""Bounded impact detection for trusted, explicit synthetic fact assertions.

This detects a reason to review an answer, never a proof that the answer is wrong.
Only public counterevidence participates: a shared answer status or review fingerprint
must not reveal the existence of internal/restricted sources after a role downgrade.
"""

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import select

from releaselens.models import Answer, Dependency, Document, Passage, Revision
from releaselens.security import Forbidden

POLICY_VERSION = "public-synthetic-counterevidence-v1"


@dataclass(frozen=True)
class _Fact:
    key: str
    value: str
    origins: frozenset[tuple[str, str]]


def _saved_facts(session, answer):
    """Use actual supported claims, not every retrieved or abstention citation."""
    payload = answer.payload
    if not isinstance(payload, dict) or payload.get("abstention_reason"):
        return []
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        return []
    rows = session.execute(
        select(Passage, Document, Revision)
        .join(Dependency, Dependency.passage_id == Passage.id)
        .join(Document, Document.id == Passage.document_id)
        .join(Revision, Revision.id == Passage.revision_id)
        .where(
            Dependency.answer_id == answer.id,
            Document.project == answer.project,
            Document.release == answer.release,
            Revision.document_id == Document.id,
            Revision.source_type == "synthetic",
            Passage.quarantined.is_(False),
        )
    ).all()
    cited = {p.id: p for p, _, _ in rows}
    facts = {}
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        key, value = claim.get("fact_key"), claim.get("fact_value")
        ids, text = claim.get("citation_ids"), claim.get("text")
        if (
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            or not isinstance(text, str)
            or not text
            or not isinstance(ids, list)
            or not ids
            or not all(isinstance(pid, str) for pid in ids)
        ):
            continue
        sources = [cited.get(pid) for pid in ids]
        # A substring can omit the asserted fact while inheriting passage metadata.
        # Until fixtures have fact spans, only complete asserted passages qualify.
        if any(
            p is None or (p.fact_key, p.fact_value) != (key, value) or text != p.text
            for p in sources
        ):
            continue
        facts.setdefault((key, value), set()).update(
            (p.document_id, p.logical_key) for p in sources
        )
    return [_Fact(key, value, frozenset(origins)) for (key, value), origins in facts.items()]


def _current_public_rows(session, project, release, keys):
    if not keys:
        return []
    return session.execute(
        select(Passage, Document)
        .join(Document, Document.id == Passage.document_id)
        .join(Revision, Revision.id == Passage.revision_id)
        .where(
            Document.project == project,
            Document.release == release,
            Document.classification == "public",
            Passage.revision_id == Document.current_revision,
            Revision.document_id == Document.id,
            Revision.source_type == "synthetic",
            Passage.quarantined.is_(False),
            Passage.fact_key.in_(keys),
            Passage.fact_value.is_not(None),
        )
        .order_by(Passage.id)
    ).all()


def _conflicts(facts, rows):
    conflicts = {}
    for fact in facts:
        for passage, doc in rows:
            if (
                passage.fact_key != fact.key
                or passage.fact_value == fact.value
                or (doc.id, passage.logical_key) in fact.origins
            ):
                continue
            key = (fact.key, fact.value, passage.id)
            conflicts[key] = {
                "result": "public_synthetic_counterevidence_requires_review",
                "fact_key": fact.key,
                "saved_value": fact.value,
                "counter_value": passage.fact_value,
                "document_id": doc.id,
                "revision_id": passage.revision_id,
                "passage_id": passage.id,
            }
    return [conflicts[key] for key in sorted(conflicts)]


def current_public_counterevidence(session, answer):
    """Return deterministic current counterevidence for an already authorized answer.

    The caller must check answer ownership and dependency ACLs first. The cited logical
    sources are excluded: replacing those sources belongs to dependency revalidation.
    No candidate cap is applied; this is intentionally a small-corpus implementation.
    """
    facts = _saved_facts(session, answer)
    rows = _current_public_rows(
        session, answer.project, answer.release, {fact.key for fact in facts}
    )
    return _conflicts(facts, rows)


def review_fingerprint(heads, counterevidence):
    """Fingerprint exactly the evidence used for review, including an explicit policy."""
    value = {
        "policy": POLICY_VERSION,
        "cited_heads": sorted(heads),
        "public_counterevidence": sorted(
            counterevidence,
            key=lambda item: (item["fact_key"], item["saved_value"], item["passage_id"]),
        ),
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def queue_new_public_counterevidence(session, principal, document, old_passages, new_passages):
    """Queue potentially affected answers in the existing ingestion transaction.

    Call once after the new document head and passages have been flushed, and after the
    ingestion identical-content early return. Never replay this hook as an event worker:
    there is no event ledger. Return IDs only for the caller's own answers, while updating
    other owners' statuses internally. Classification is immutable in the current schema.
    """
    if principal.role != "admin":
        raise Forbidden("Impact updates require an administrator")
    if document.classification != "public":
        return []
    revision = session.get(Revision, document.current_revision)
    if revision is None or revision.source_type != "synthetic":
        return []
    old = {
        (p.logical_key, p.fact_key, p.fact_value)
        for p in old_passages
        if p.document_id == document.id
        and p.fact_key
        and p.fact_value is not None
        and not p.quarantined
    }
    introduced = {
        p.id
        for p in new_passages
        if p.document_id == document.id
        and p.revision_id == document.current_revision
        and p.fact_key
        and p.fact_value is not None
        and not p.quarantined
        and (p.logical_key, p.fact_key, p.fact_value) not in old
    }
    if not introduced:
        return []
    keys = {p.fact_key for p in new_passages if p.id in introduced}
    rows = [
        (p, doc)
        for p, doc in _current_public_rows(session, document.project, document.release, keys)
        if p.id in introduced
    ]
    if not rows:
        return []
    affected = []
    answers = session.scalars(
        select(Answer)
        .where(Answer.project == document.project, Answer.release == document.release)
        .order_by(Answer.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    for answer in answers:
        if _conflicts(_saved_facts(session, answer), rows):
            answer.status = "revalidation_pending"
            if answer.owner == principal.user:
                affected.append(answer.id)
    return affected
