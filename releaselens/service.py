"""Extractive demo answers and conservative, auditable revalidation."""

from time import perf_counter

from sqlalchemy import select

from releaselens.generation import ExtractiveGenerator, GenerationFailure
from releaselens.impact import current_public_counterevidence, review_fingerprint
from releaselens.ingestion import normalize
from releaselens.models import Answer, Dependency, Document, Passage, Review, Revision
from releaselens.retrieval import rank
from releaselens.schemas import AnswerPayload, AskRequest, Citation, Claim
from releaselens.security import NotFound, authorized_document


def citation(session, passage, document):
    revision = session.get(Revision, passage.revision_id)
    return Citation(
        passage_id=passage.id,
        document_id=document.id,
        revision_id=revision.id,
        section=passage.section,
        release=document.release,
        quote=passage.text,
        source_url=revision.source_url,
        source_type=revision.source_type,
        normalized_hash=passage.normalized_hash,
    )


def validate_citations(session, principal, payload: AnswerPayload):
    """Verify membership, authorization, release, exact quotation and claim containment.

    This proves extractive grounding; it does not establish entailment for arbitrary prose.
    """
    evidence = {}
    for cited in payload.passages:
        passage = session.get(Passage, cited.passage_id)
        if passage is None:
            raise ValueError("Unknown citation")
        doc = authorized_document(session, passage.document_id, principal)
        expected = citation(session, passage, doc)
        if expected.model_dump() != cited.model_dump() or passage.quarantined:
            raise ValueError("Citation does not match immutable evidence")
        if doc.project != payload.project or doc.release != payload.release:
            raise ValueError("Wrong project/release citation")
        evidence[passage.id] = passage
    for claim in payload.claims:
        if not claim.citation_ids:
            raise ValueError("Uncited claim")
        for passage_id in claim.citation_ids:
            passage = evidence.get(passage_id)
            if not passage or claim.text not in passage.text:
                raise ValueError("Claim is not an exact evidence extract")
            expected_fact = (
                (passage.fact_key, passage.fact_value)
                if claim.text == passage.text
                else (None, None)
            )
            if (claim.fact_key, claim.fact_value) != expected_fact:
                raise ValueError("Fact metadata differs from source")
    if payload.answer != "\n\n".join(c.text for c in payload.claims):
        raise ValueError("Answer contains uncited prose")


def ask(session, principal, request: AskRequest, embedder):
    start = perf_counter()
    rows = rank(
        session,
        principal,
        request.project,
        request.release,
        request.question,
        embedder,
        request.mode,
        request.k,
    )
    reason = None
    if rows and any(doc.release != request.release for _, doc, _ in rows):
        rows = []
        reason = "Baseline retrieved another release; citation validation blocks generation."
    if not rows and reason is None:
        reason = "No authorized, non-quarantined evidence with query overlap in this release."
    conflicts = []
    facts = {}
    for passage, _, _ in rows:
        if passage.fact_key:
            facts.setdefault(passage.fact_key, set()).add(passage.fact_value)
    for key, values in facts.items():
        if len(values) > 1:
            conflicts.append({"fact_key": key, "values": sorted(values)})
    if conflicts:
        reason = "Retrieved synthetic fact assertions conflict; manual review required."
    gate_metadata = None
    gate = session.info.get("relevance_gate")
    if gate is not None and not reason:
        if request.mode != "version" or request.k != 4:
            raise ValueError("Experimental answerability policy requires version mode and k=4")
        rows, gate_metadata = gate.filter(request.question, rows)
        if not rows:
            reason = "Experimental relevance policy found insufficient evidence; review required."
    generator = session.info.get("generator") or ExtractiveGenerator()
    claims, generation_metadata = [], {"provider_cost_usd": 0}
    if not reason:
        generation_metadata = {"provider_cost_usd": None, "usage": None}
        try:
            selected, generation_metadata = generator.select(
                request.question, [p for p, _, _ in rows]
            )
            allowed = {p.id: p for p, _, _ in rows}
            for item in selected:
                passage = allowed.get(item["passage_id"])
                if passage is None or item["text"] not in passage.text:
                    raise GenerationFailure(
                        "Provider selected a fabricated ID or unsupported extract"
                    )
                claims.append(
                    Claim(
                        text=item["text"],
                        citation_ids=[passage.id],
                        fact_key=passage.fact_key if item["text"] == passage.text else None,
                        fact_value=passage.fact_value if item["text"] == passage.text else None,
                    )
                )
            if not claims:
                reason = "Extract selector found insufficient evidence."
        except GenerationFailure as exc:
            if exc.metadata is not None:
                generation_metadata = exc.metadata
            claims = []
            reason = "Generation failed deterministic evidence validation or provider invocation."
    if claims:
        used = {pid for claim in claims for pid in claim.citation_ids}
        rows = [(p, d, score) for p, d, score in rows if p.id in used]
    payload = AnswerPayload(
        question=request.question,
        project=request.project,
        release=request.release,
        answer="\n\n".join(c.text for c in claims),
        claims=claims,
        passages=[citation(session, p, d) for p, d, _ in rows],
        conflicts=conflicts,
        abstention_reason=reason,
        metadata={
            "answerability": gate_metadata,
            "generation": generator.name,
            "embedding": embedder.name,
            "mode": request.mode,
            "k": request.k,
            "reranker": "section-overlap heuristic" if request.mode == "rerank" else None,
            "latency_ms": round((perf_counter() - start) * 1000, 3),
            **generation_metadata,
            "quality_caveat": "Overlap is not proof of relevance or completeness",
        },
    )
    validate_citations(session, principal, payload)
    if request.save:
        answer = Answer(
            owner=principal.user,
            project=request.project,
            release=request.release,
            question=request.question,
            payload={},
        )
        session.add(answer)
        session.flush()
        payload.saved_answer_id = answer.id
        answer.payload = payload.model_dump()
        for cited in payload.passages:
            session.add(Dependency(answer_id=answer.id, passage_id=cited.passage_id))
    return payload


def owned_answer(session, principal, answer_id):
    answer = session.scalar(
        select(Answer).where(Answer.id == answer_id, Answer.owner == principal.user)
    )
    if answer is None:
        raise NotFound("Resource unavailable")
    dependencies = list(
        session.scalars(select(Passage).join(Dependency).where(Dependency.answer_id == answer.id))
    )
    for passage in dependencies:
        authorized_document(session, passage.document_id, principal)
    return answer, dependencies


def revalidate(session, principal, answer_id):
    answer, dependencies = owned_answer(session, principal, answer_id)
    heads = sorted(
        (p.id, session.get(Document, p.document_id).current_revision) for p in dependencies
    )
    counterevidence = current_public_counterevidence(session, answer)
    fingerprint = review_fingerprint(heads, counterevidence)
    existing = session.scalar(
        select(Review).where(
            Review.answer_id == answer_id, Review.evidence_fingerprint == fingerprint
        )
    )
    if existing:
        answer.status = existing.status
        return {
            "review_id": existing.id,
            "answer_id": answer.id,
            "status": existing.status,
            "assessment": existing.assessment,
        }
    substantive = bool(answer.payload.get("claims")) and not answer.payload.get("abstention_reason")
    reasons, changed, missing, uncertain, updated = list(counterevidence), False, False, False, []
    for prior in dependencies if substantive else []:
        doc = authorized_document(session, prior.document_id, principal)
        current = session.scalar(
            select(Passage).where(
                Passage.revision_id == doc.current_revision,
                Passage.logical_key == prior.logical_key,
            )
        )
        if current is None or current.quarantined:
            missing = True
            reasons.append({"old_passage": prior.id, "result": "missing_or_quarantined"})
            continue
        updated.append(citation(session, current, doc).model_dump())
        prior_revision = session.get(Revision, prior.revision_id)
        current_revision = session.get(Revision, current.revision_id)
        structured_support = (
            prior_revision.source_type == current_revision.source_type == "synthetic"
        ) and any(
            c.get("fact_key") == prior.fact_key
            and prior.fact_key is not None
            and c.get("fact_value") == prior.fact_value
            and c.get("text") == prior.text
            and prior.id in c.get("citation_ids", [])
            for c in answer.payload["claims"]
        )
        if structured_support and current.fact_key == prior.fact_key:
            # Only synthetic, explicit, exclusive fact assertions permit deterministic staleness.
            if current.fact_value != prior.fact_value:
                changed = True
                reasons.append(
                    {
                        "old_passage": prior.id,
                        "new_passage": current.id,
                        "result": "synthetic_fact_changed",
                        "old_value": prior.fact_value,
                        "new_value": current.fact_value,
                    }
                )
            else:
                reasons.append(
                    {
                        "old_passage": prior.id,
                        "new_passage": current.id,
                        "result": "synthetic_fact_unchanged",
                    }
                )
        elif (prior.fact_key, prior.fact_value) != (current.fact_key, current.fact_value):
            uncertain = True
            reasons.append(
                {
                    "old_passage": prior.id,
                    "new_passage": current.id,
                    "result": "fact_assertion_metadata_changed_requires_review",
                }
            )
        elif normalize(prior.text) == normalize(current.text):
            reasons.append(
                {
                    "old_passage": prior.id,
                    "new_passage": current.id,
                    "result": "exact_extract_still_present",
                }
            )
        else:
            uncertain = True
            reasons.append(
                {
                    "old_passage": prior.id,
                    "new_passage": current.id,
                    "result": "changed_text_requires_human_entailment_review",
                }
            )
    if not substantive:
        status = (
            "manual_review_required" if answer.payload.get("conflicts") else "insufficient_evidence"
        )
        reasons.append(
            {"result": "original_answer_was_abstention; no substantive claim classified incorrect"}
        )
    elif changed:
        status = "confirmed_stale"
    elif missing or not dependencies:
        status = "insufficient_evidence"
    elif uncertain or counterevidence:
        status = "manual_review_required"
    else:
        status = "reviewed_still_valid"
    corrected = None
    if changed:
        corrected = ask(
            session,
            principal,
            AskRequest(
                project=answer.project,
                release=answer.release,
                question=answer.question,
                save=True,
                k=answer.payload.get("metadata", {}).get("k", 4),
            ),
            session.info["embedder"],
        )
    assessment = {
        "reasons": reasons,
        "updated_evidence": updated,
        "public_counterevidence": counterevidence,
        "corrected_answer_id": corrected.saved_answer_id if corrected else None,
        "original_answer_preserved": True,
    }
    answer.status = status
    review = Review(
        answer_id=answer.id,
        actor=principal.user,
        status=status,
        assessment=assessment,
        evidence_fingerprint=fingerprint,
    )
    session.add(review)
    session.flush()
    return {
        "review_id": review.id,
        "answer_id": answer.id,
        "status": status,
        "assessment": assessment,
    }
