from copy import deepcopy

import pytest

from releaselens.schemas import AnswerPayload
from releaselens.sufficiency import digest, packet, summarize
from scripts.evaluate_sufficiency import run


def test_citation_validity_does_not_promote_semantic_labels(tmp_path):
    result = run(tmp_path / "probe")
    assert all(c["citation_valid"] for c in result["mechanical_checks"])
    review = result["semantic_review"]
    assert review["reviewed_cases"] == 0 and review["unreviewed_cases"] == 6
    assert review["answered_without_sufficient_evidence"] is None
    assert review["review_status"] == "BLOCKED"
    by_id = {c["case_id"]: c for c in result["mechanical_checks"]}
    assert not by_id["access-boundary"]["answered"]
    assert not by_id["unsupported"]["answered"]
    # Retained negative behavior: lexical overlap can answer a missing measurement.
    assert by_id["missing-measurement"]["answered"]


def make_packet():
    value = packet(
        {"id": "case", "required_aspects": ["export", "memory"]},
        AnswerPayload(
            question="Export and memory?",
            project="fixture",
            release="1",
            answer="",
            claims=[],
            passages=[],
            conflicts=[],
            abstention_reason="missing",
            metadata={},
        ),
    )
    review = {
        "case_id": "case",
        "packet_sha256": value["packet_sha256"],
        "reviewer_kind": "human",
        "reviewer": "test-fixture-only",
        "independent_of_author": True,
        "decision": "unsupported",
        "aspects": {
            k: {"status": "missing", "rationale": "No extract covers this aspect", "evidence": []}
            for k in ("export", "memory")
        },
    }
    return value, review


def test_review_binding_and_independence_are_required():
    item, review = make_packet()
    assert summarize([item], [review])["reviewed_cases"] == 1
    changed = deepcopy(item)
    changed["payload"]["question"] = "Changed action?"
    with pytest.raises(ValueError, match="integrity"):
        summarize([changed], [review])
    changed["packet_sha256"] = digest({k: v for k, v in changed.items() if k != "packet_sha256"})
    with pytest.raises(ValueError, match="different"):
        summarize([changed], [review])
    review["independent_of_author"] = False
    with pytest.raises(ValueError, match="independent"):
        summarize([item], [review])


def test_cannot_assert_support_without_authorized_evidence():
    item, review = make_packet()
    review["aspects"]["memory"] = {
        "status": "supported",
        "rationale": "fixture",
        "evidence": [{"passage_id": "restricted", "quote": "secret"}],
    }
    with pytest.raises(ValueError, match="authorized"):
        summarize([item], [review])
    review["aspects"].pop("memory")
    with pytest.raises(ValueError, match="every required"):
        summarize([item], [review])
