"""Review evidence sufficiency separately from exact-extract citation validity.

These reviews are offline annotations, never authorization or serving policy.
An attestation is not technical proof of reviewer identity or independence.
"""

import hashlib
import json


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def packet(case, payload):
    body = {
        "case_id": case["id"],
        "author": "ai-assisted-stage4",
        "annotation_status": "UNREVIEWED",
        "exposure": "development-exposed",
        "required_aspects": case["required_aspects"],
        "payload": payload.model_dump(),
        "review_question": "Do these authorized extracts jointly answer every required aspect, without adding assumptions?",
    }
    return {**body, "packet_sha256": digest(body)}


def validate_review(item, review):
    body = {k: v for k, v in item.items() if k != "packet_sha256"}
    if digest(body) != item["packet_sha256"]:
        raise ValueError("Packet integrity mismatch")
    if review["case_id"] != item["case_id"] or review["packet_sha256"] != item["packet_sha256"]:
        raise ValueError("Review is for different question/evidence/answer bytes")
    if (
        review.get("reviewer_kind") != "human"
        or review.get("independent_of_author") is not True
        or not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
        or review["reviewer"] == item["author"]
    ):
        raise ValueError("Named independent human-review attestation required")
    if review.get("decision") not in ("sufficient", "partial", "unsupported", "conflicting"):
        raise ValueError("Explicit sufficiency decision required")
    aspects = review.get("aspects", {})
    if set(aspects) != set(item["required_aspects"]):
        raise ValueError("Review every required aspect")
    passages = {p["passage_id"]: p["quote"] for p in item["payload"]["passages"]}
    supported = []
    for assessment in aspects.values():
        if assessment.get("status") not in ("supported", "missing", "contradicted"):
            raise ValueError("Explicit aspect status required")
        if not isinstance(assessment.get("rationale"), str) or not assessment["rationale"].strip():
            raise ValueError("Aspect rationale required")
        evidence = assessment.get("evidence", [])
        if assessment["status"] in ("supported", "contradicted") and not evidence:
            raise ValueError("Support or contradiction must cite review-packet evidence")
        for cited in evidence:
            quote = cited.get("quote")
            if (
                not isinstance(quote, str)
                or not quote.strip()
                or quote not in passages.get(cited.get("passage_id"), "")
            ):
                raise ValueError("Review evidence outside authorized packet")
        supported.append(assessment["status"] == "supported")
    decision = review["decision"]
    if (
        (decision == "sufficient") != all(supported)
        or (decision == "partial" and not (any(supported) and not all(supported)))
        or (decision == "unsupported" and any(supported))
        or (
            decision == "conflicting"
            and not any(a["status"] == "contradicted" for a in aspects.values())
        )
    ):
        raise ValueError("Decision conflicts with aspect assessments")
    return review


def summarize(packets, reviews):
    known = {p["case_id"]: p for p in packets}
    if len(known) != len(packets):
        raise ValueError("Duplicate packet case")
    accepted = {}
    for review in reviews:
        case_id = review["case_id"]
        if case_id not in known or case_id in accepted:
            raise ValueError("Unknown case or duplicate review; adjudicate separately")
        accepted[case_id] = validate_review(known[case_id], review)
    unsupported_answered = sufficient_abstained = 0
    for case_id, review in accepted.items():
        answered = not bool(known[case_id]["payload"]["abstention_reason"])
        unsupported_answered += answered and review["decision"] != "sufficient"
        sufficient_abstained += not answered and review["decision"] == "sufficient"
    return {
        "planned_cases": len(packets),
        "reviewed_cases": len(accepted),
        "unreviewed_cases": len(packets) - len(accepted),
        "review_status": "BLOCKED" if len(accepted) < len(packets) else "PARTIALLY VERIFIED",
        "answered_without_sufficient_evidence": unsupported_answered if accepted else None,
        "abstained_despite_sufficient_evidence": sufficient_abstained if accepted else None,
        "denominator": "Reviewed cases only; all unreviewed cases reported separately",
        "identity_limit": "Human identity and independence are self-attested, not technically verified",
        "semantic_quality_claim": "UNVERIFIED"
        if not accepted
        else "Self-attested offline review only",
    }
