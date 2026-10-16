"""Conservative new-public-prose review candidates, without contradiction verdicts.

Only already public current passages in the same project/release participate.
A lexical overlap rule can miss paraphrases and can flag agreeing text. It never
confirms staleness. Historical evidence and original answers remain immutable.
"""

import re

from sqlalchemy import select

from releaselens.models import Answer, Dependency, Document, Passage, Revision
from releaselens.security import Forbidden

POLICY = "public-upstream-prose-overlap-v1"
STOP = set(
    "the and for from with this that does which what how can are was were will would should into when why use using model models pydantic sqlalchemy release documentation document".split()
)


def terms(text):
    return {
        t for t in re.findall(r"[a-z][a-z0-9_]+", text.lower()) if len(t) >= 3 and t not in STOP
    }


def _supported_origins(session, answer):
    payload = answer.payload
    if payload.get("abstention_reason") or not payload.get("claims"):
        return set(), set()
    rows = session.execute(
        select(Passage, Revision)
        .join(Dependency, Dependency.passage_id == Passage.id)
        .join(Revision, Revision.id == Passage.revision_id)
        .where(
            Dependency.answer_id == answer.id,
            Revision.source_type == "upstream",
            Passage.quarantined.is_(False),
        )
    ).all()
    by_id = {p.id: p for p, _ in rows}
    origins, supported = set(), set()
    for claim in payload["claims"]:
        cited = [by_id.get(pid) for pid in claim.get("citation_ids", [])]
        text = claim.get("text")
        if not text or not cited or any(p is None or text not in p.text for p in cited):
            continue
        origins.update((p.document_id, p.logical_key) for p in cited)
        supported |= terms(text)
    return origins, supported


def current_public_prose_candidates(session, answer, *, only_ids=None):
    """Recompute public candidates for an owner-authorized answer's review fingerprint.

    Scope before text comparison; first-seen normalized content must postdate answer.
    Exclude cited logical sections, which already have dependency change detection.
    No candidate truncation: supported only for the documented small corpus.
    """
    if not session.info.get("prose_review_candidates", False):
        return []
    origins, supported = _supported_origins(session, answer)
    query = terms(answer.question)
    if not origins or len(query) < 2:
        return []
    scope = (
        Document.project == answer.project,
        Document.release == answer.release,
        Document.classification == "public",
        Passage.quarantined.is_(False),
        Revision.source_type == "upstream",
    )
    statement = (
        select(Passage, Document, Revision)
        .join(Document, Document.id == Passage.document_id)
        .join(Revision, Revision.id == Passage.revision_id)
        .where(
            *scope,
            Passage.revision_id == Document.current_revision,
            Revision.created_at > answer.created_at,
        )
    )
    if only_ids is not None:
        if not only_ids:
            return []
        statement = statement.where(Passage.id.in_(only_ids))
    rows = session.execute(statement).all()
    if not rows:
        return []
    prior = set(
        session.execute(
            select(Passage.document_id, Passage.logical_key, Passage.normalized_hash)
            .join(Document, Document.id == Passage.document_id)
            .join(Revision, Revision.id == Passage.revision_id)
            .where(*scope, Revision.created_at <= answer.created_at)
        ).all()
    )
    result = []
    for p, doc, revision in rows:
        if (doc.id, p.logical_key) in origins or (
            doc.id,
            p.logical_key,
            p.normalized_hash,
        ) in prior:
            continue
        passage_terms = terms(p.text)
        matched_query, matched_claim = query & passage_terms, supported & passage_terms
        if (
            len(matched_query) >= 2
            and len(matched_query) / len(query) >= 0.5
            and len(matched_claim) >= 3
        ):
            result.append(
                {
                    "result": "new_public_related_prose_requires_review",
                    "policy": POLICY,
                    "document_id": doc.id,
                    "revision_id": p.revision_id,
                    "passage_id": p.id,
                    "quote": p.text,
                    "source_url": revision.source_url,
                    "release": doc.release,
                    "normalized_hash": p.normalized_hash,
                    "matched_question_terms": sorted(matched_query),
                    "matched_claim_terms": sorted(matched_claim),
                    "verdict": "candidate_only; agreement_or_contradiction_not_determined",
                }
            )
    return sorted(result, key=lambda r: r["passage_id"])


def queue_new_public_prose(session, principal, document, old_passages, new_passages):
    if principal.role != "admin":
        raise Forbidden("Impact updates require an administrator")
    if not session.info.get("prose_review_candidates", False):
        return []
    revision = session.get(Revision, document.current_revision)
    if document.classification != "public" or revision.source_type != "upstream":
        return []
    old = {(p.logical_key, p.normalized_hash) for p in old_passages if not p.quarantined}
    introduced = {
        p.id
        for p in new_passages
        if not p.quarantined and (p.logical_key, p.normalized_hash) not in old
    }
    if not introduced:
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
        if current_public_prose_candidates(session, answer, only_ids=introduced):
            answer.status = "revalidation_pending"
            if answer.owner == principal.user:
                affected.append(answer.id)
    return affected
