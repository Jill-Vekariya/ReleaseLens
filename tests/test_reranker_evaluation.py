"""Contract tests for isolated, permission-preserving cross-encoder evaluation."""

import pytest

from scripts.evaluate_reranker import MODES, measure, order_reranked, summarize


def test_reranker_only_reorders_existing_candidates():
    original = [("public-a", 1), ("public-b", 2), ("public-c", 3)]
    ranked = order_reranked(original, [0.2, 0.7, -0.1])
    assert ranked == [original[1], original[0], original[2]]
    assert set(ranked) == set(original)


def test_equal_scores_preserve_initial_rank():
    assert order_reranked(["a", "b", "c"], [1, 1, 1]) == ["a", "b", "c"]


def test_reranker_score_mismatch_rejected():
    with pytest.raises(ValueError):
        order_reranked(["a", "b"], [0.5])


def test_matched_recall_and_ndcg_with_ai_proposals():
    labels = [{"document_key": "a", "logical_key": "x", "grade": 3}]
    case = {"relevance": labels}
    from types import SimpleNamespace

    hit_a = (SimpleNamespace(logical_key="x"), SimpleNamespace(key="a"), 1.0)
    hit_b = (SimpleNamespace(logical_key="y"), SimpleNamespace(key="b"), 1.0)
    assert measure([hit_a], case)["recall_at_5"] == 1
    assert measure([hit_a], case)["ndcg_at_10"] == 1
    assert measure([hit_b], case)["recall_at_5"] == 0
    assert measure([], {"relevance": []}) is None


def test_summary_marks_unsupported_without_inflating_recall():
    rows = []
    for mode in MODES:
        rows.extend(
            [
                {
                    "mode": mode,
                    "family_id": "supported",
                    "metrics": {"recall_at_5": 1, "ndcg_at_10": 1, "mrr_at_5": 1},
                    "latency_ms": 1,
                    "wrong_release_hits": 0,
                    "unauthorized_hits": 0,
                },
                {
                    "mode": mode,
                    "family_id": "unsupported",
                    "metrics": None,
                    "latency_ms": 2,
                    "wrong_release_hits": 0,
                    "unauthorized_hits": 0,
                },
            ]
        )
    for result in summarize(rows):
        assert result["supported_ai_proposals"] == 1
        assert result["unsupported_ai_proposals"] == 1
        assert result["recall_at_5"] == 1
