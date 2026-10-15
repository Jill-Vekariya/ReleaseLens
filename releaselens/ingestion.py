import hashlib
import json
import re

from sqlalchemy import select

from releaselens.models import Answer, Change, Dependency, Document, Passage, Revision
from releaselens.schemas import IngestRequest
from releaselens.security import Forbidden, injection_marker


class RevisionConflict(Exception):
    pass


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize(value: str) -> str:
    """Conservative: line endings/trailing spaces/blank runs; preserve code indentation."""
    value = "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").split("\n"))
    return re.sub(r"\n{3,}", "\n\n", value).strip("\n")


def ingest(session, principal, request: IngestRequest, embedder):
    if principal.role != "admin":
        raise Forbidden("Ingestion requires an administrator")
    document = session.scalar(
        select(Document)
        .where(
            Document.project == request.project,
            Document.release == request.release,
            Document.key == request.document_key,
        )
        .with_for_update()
    )
    if document and document.classification != request.classification:
        raise RevisionConflict("Document classification is immutable; create a new document")
    raw = json.dumps([s.model_dump() for s in request.sections], sort_keys=True)
    normalized = {
        s.key: {
            "title": s.title,
            "text": normalize(s.text),
            "fact_key": s.fact_key,
            "fact_value": s.fact_value,
        }
        for s in request.sections
    }
    norm_hash = digest(json.dumps(normalized, sort_keys=True))
    old = session.get(Revision, document.current_revision) if document else None
    if old:
        identity = (
            old.source_type,
            old.upstream_commit,
            old.source_url,
            old.license,
            old.attribution,
            old.published_at,
        )
        incoming = (
            request.source_type,
            request.upstream_commit,
            str(request.source_url),
            request.license,
            request.attribution,
            request.published_at,
        )
        if old.raw_hash == digest(raw) and identity == incoming:
            models = set(
                session.scalars(
                    select(Passage.embedding_model).where(Passage.revision_id == old.id)
                )
            )
            if models != {embedder.name}:
                raise RevisionConflict(
                    "Encoder changed: use a fresh corpus database or an explicit reindex migration"
                )
            return {
                "document_id": document.id,
                "revision_id": old.id,
                "kind": "identical",
                "affected_answer_ids": [],
            }
        if request.expected_revision != old.id:
            raise RevisionConflict("Send the current expected_revision to update a document")
        if old.source_type != request.source_type:
            raise RevisionConflict("Cannot relabel synthetic evidence as upstream")
    if not document:
        document = Document(
            project=request.project,
            release=request.release,
            key=request.document_key,
            classification=request.classification,
        )
        session.add(document)
        session.flush()
    revision = Revision(
        document_id=document.id,
        sequence=(old.sequence + 1 if old else 1),
        raw_hash=digest(raw),
        raw_content=raw,
        normalized_hash=norm_hash,
        source_url=str(request.source_url),
        license=request.license,
        attribution=request.attribution,
        source_type=request.source_type,
        upstream_commit=request.upstream_commit,
        published_at=request.published_at,
    )
    session.add(revision)
    session.flush()
    old_passages = (
        list(session.scalars(select(Passage).where(Passage.revision_id == old.id))) if old else []
    )
    new_passages = []
    for section in request.sections:
        passage = Passage(
            revision_id=revision.id,
            document_id=document.id,
            logical_key=section.key,
            section=section.title,
            text=section.text,
            normalized_hash=digest(normalize(section.text)),
            embedding=embedder.encode(section.title + " " + section.text),
            embedding_model=embedder.name,
            fact_key=section.fact_key,
            fact_value=section.fact_value,
            quarantined=injection_marker(section.text),
        )
        session.add(passage)
        new_passages.append(passage)
    document.current_revision = revision.id
    session.flush()
    if session.bind.dialect.name == "postgresql":
        from sqlalchemy import text

        for passage in new_passages:
            session.execute(
                text("UPDATE passages SET dense_vector=CAST(:v AS vector) WHERE id=:id"),
                {"v": str(passage.embedding), "id": passage.id},
            )
    kind, affected = "created", []
    if old:
        kind = "formatting_only" if old.normalized_hash == norm_hash else "technical_review_needed"
        mapping = {p.logical_key: p for p in new_passages}
        changed = [
            p
            for p in old_passages
            if p.logical_key not in mapping
            or (p.normalized_hash, p.fact_key, p.fact_value, p.section)
            != (
                mapping[p.logical_key].normalized_hash,
                mapping[p.logical_key].fact_key,
                mapping[p.logical_key].fact_value,
                mapping[p.logical_key].section,
            )
        ]
        # Follow ALL historical citations for this logical document, including citations
        # predating a formatting-only revision. Otherwise the second update is missed.
        historical = list(
            session.scalars(select(Passage).where(Passage.document_id == document.id))
        )
        changed_keys = {p.logical_key for p in changed}
        # Revisit historical citations only for logical sections changed by this event.
        # A formatting-only update must not requeue an already reviewed stale answer.
        changed_ids = [
            p.id
            for p in historical
            if p.revision_id != revision.id and p.logical_key in changed_keys
        ]
        if changed_ids:
            dependent = list(
                session.scalars(
                    select(Answer).where(
                        Answer.id.in_(
                            select(Dependency.answer_id).where(
                                Dependency.passage_id.in_(changed_ids)
                            )
                        )
                    )
                )
            )
            for answer in dependent:
                answer.status = "revalidation_pending"
                if answer.owner == principal.user:
                    affected.append(answer.id)
        before = {p.logical_key: p.text for p in old_passages}
        after = {p.logical_key: p.text for p in new_passages}
        session.add(
            Change(
                document_id=document.id,
                old_revision=old.id,
                new_revision=revision.id,
                kind=kind,
                delta={
                    "before": before,
                    "after": after,
                    "changed_keys": sorted(changed_keys),
                    "added_keys": sorted(set(after) - set(before)),
                    "removed_keys": sorted(set(before) - set(after)),
                },
            )
        )
    return {
        "document_id": document.id,
        "revision_id": revision.id,
        "kind": kind,
        "affected_answer_ids": affected,
        "quarantined_passages": sum(p.quarantined for p in new_passages),
    }
