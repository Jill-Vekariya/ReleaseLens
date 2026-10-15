import json
import shutil

import pytest

from releaselens.benchmark import (
    ROOT,
    execute_scenario,
    family_bootstrap,
    load_pilot,
    ranking_metrics,
    run,
    select_cases,
)


def test_frozen_pilot_has_disjoint_families_and_real_passage_anchors():
    manifest, cases = load_pilot()
    assert len(cases) == 40
    assert sum(c["kind"] == "retrieval" for c in cases) == 32
    assert sum(c["kind"] == "scenario" for c in cases) == 8
    assert manifest["human_reviewed_records"] == 0
    tuning = {c["family_id"] for c in cases if c["split"] == "tuning"}
    heldout = {c["family_id"] for c in cases if c["split"] == "heldout"}
    assert not tuning & heldout
    assert all(c["review_status"] == "ai_reviewed_proposal" for c in cases)


def test_heldout_labels_need_human_review_or_explicit_diagnostic_override():
    _, cases = load_pilot()
    assert all(c["split"] == "tuning" for c in select_cases(cases))
    for split in ("heldout", "all"):
        with pytest.raises(ValueError, match="independent human review"):
            select_cases(cases, split)
    selected = select_cases(cases, "heldout", allow_ai_reviewed_heldout=True)
    assert selected
    assert all(c["review_status"] == "ai_reviewed_proposal" for c in selected)


def test_freeze_rejects_dataset_and_source_drift(tmp_path):
    shutil.copytree(ROOT / "evaluation", tmp_path / "evaluation")
    shutil.copytree(ROOT / "data/upstream", tmp_path / "data/upstream")
    dataset = tmp_path / "evaluation/pilot-v2.jsonl"
    original = dataset.read_bytes()
    dataset.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="frozen manifest"):
        load_pilot(tmp_path)
    dataset.write_bytes(original)
    source = tmp_path / "data/upstream/pydantic/1.10.15/source.txt"
    source.write_text(source.read_text() + " altered")
    with pytest.raises(ValueError, match="source content drift"):
        load_pilot(tmp_path)


def test_ranking_metrics_score_passages_and_do_not_count_unsupported_as_correct():
    relevance = [
        {"document_key": "d", "logical_key": "a", "grade": 2},
        {"document_key": "d", "logical_key": "b", "grade": 1},
    ]
    perfect = ranking_metrics([("d", "a"), ("d", "b")], relevance)
    assert perfect == {"recall_at_k": 1, "mrr_at_k": 1, "ndcg_at_k": 1, "hit_at_k": 1}
    missed = ranking_metrics([("d", "irrelevant")], relevance)
    assert missed["recall_at_k"] == missed["mrr_at_k"] == missed["ndcg_at_k"] == 0
    duplicate = ranking_metrics([("d", "a"), ("d", "a")], relevance)
    assert duplicate["recall_at_k"] == 0.5
    assert duplicate["ndcg_at_k"] < 1
    assert ranking_metrics([], []) is None
    assert ranking_metrics([("d", "a")], []) is None


def test_family_bootstrap_is_reproducible_and_preserves_paired_delta_sign():
    rows = [
        {"family_id": "a", "delta": -1},
        {"family_id": "a", "delta": -0.5},
        {"family_id": "b", "delta": 0},
    ]
    bounds = family_bootstrap(rows, "delta", samples=100)
    assert bounds == family_bootstrap(rows, "delta", samples=100)
    assert -1 <= bounds[0] <= bounds[1] <= 0
    assert family_bootstrap(rows[:1], "delta") is None


@pytest.mark.parametrize(
    "case", [c for c in load_pilot()[1] if c["kind"] == "scenario"], ids=lambda c: c["scenario"]
)
def test_synthetic_scenarios_execute_separately_from_retrieval_metrics(case):
    result = execute_scenario(case)
    assert result["executed"]
    assert result["passed_expected_behavior"], result
    assert "metrics" not in result
    assert result["label_review_status"] == "ai_reviewed_proposal"


def test_hash_pilot_runs_offline_without_answer_quality_claims(tmp_path):
    output = tmp_path / "pilot.json"
    result = run(output)
    assert json.loads(output.read_text())["dataset_sha256"] == result["dataset_sha256"]
    assert result["selected_split"] == "tuning"
    assert result["human_reviewed_records"] == 0
    assert result["answer_semantic_support_accuracy"] is None
    assert result["abstention_precision"] is None
    assert {r["mode"] for r in result["baselines"]} == {
        "lexical-only",
        "dense-only",
        "hybrid",
    }
    assert all(r["supported_queries"] == 16 for r in result["baselines"])
    assert all(r["unsupported_queries"] == 6 for r in result["baselines"])
    assert not any(r["wrong_release_hits"] or r["unauthorized_hits"] for r in result["baselines"])
    assert all(r["passed_expected_behavior"] for r in result["scenarios"])
    assert all(r["split"] == "tuning" for r in result["per_query"])
