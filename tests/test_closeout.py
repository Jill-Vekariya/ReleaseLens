"""Regression cases for mechanically invalid benchmark labels and review submissions."""

import copy
import hashlib
import json
import shutil
from types import SimpleNamespace

import pytest

from releaselens.review_dataset import ROOT, load_dataset
from scripts.evaluate_reranker import order_reranked
from scripts.review_benchmark import validate


@pytest.fixture
def mutable_dataset(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    (tmp_path / "evaluation").mkdir()
    for name in ("benchmark-v3.jsonl", "benchmark-v3-manifest.json"):
        shutil.copyfile(ROOT / "evaluation" / name, tmp_path / "evaluation" / name)
    return tmp_path


def rewrite_dataset(root, change):
    path = root / "evaluation/benchmark-v3.jsonl"
    cases = [json.loads(line) for line in path.read_text().splitlines()]
    change(cases)
    path.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    manifest_path = root / "evaluation/benchmark-v3-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["dataset_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


@pytest.mark.parametrize("grade", [0, 4, True, 1.5])
def test_dataset_rejects_invalid_relevance_grade(mutable_dataset, grade):
    rewrite_dataset(mutable_dataset, lambda cases: cases[0]["relevance"][0].update(grade=grade))
    with pytest.raises(ValueError, match="grade"):
        load_dataset(mutable_dataset)


def test_dataset_rejects_duplicate_label(mutable_dataset):
    rewrite_dataset(mutable_dataset, lambda c: c[0]["relevance"].append(c[0]["relevance"][0]))
    with pytest.raises(ValueError, match="Duplicate evidence"):
        load_dataset(mutable_dataset)


def test_dataset_rejects_duplicate_question_within_release(mutable_dataset):
    rewrite_dataset(mutable_dataset, lambda c: c[1].update(question=c[0]["question"]))
    with pytest.raises(ValueError, match="Duplicate normalized question"):
        load_dataset(mutable_dataset)


def test_dataset_rejects_nonboolean_answerability(mutable_dataset):
    rewrite_dataset(mutable_dataset, lambda c: c[0].update(expected_abstention="false"))
    with pytest.raises(ValueError, match="boolean"):
        load_dataset(mutable_dataset)


def test_dataset_rejects_incorrect_split_counts(mutable_dataset):
    path = mutable_dataset / "evaluation/benchmark-v3-manifest.json"
    data = json.loads(path.read_text())
    data["splits"]["test"] += 1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Split count"):
        load_dataset(mutable_dataset)


def submission():
    manifest, cases = load_dataset()
    case = cases[0]
    record = {
        "case_id": case["id"],
        "dataset_sha256": manifest["dataset_sha256"],
        "reviewer": "fictional-test-fixture-not-a-human-review",
        "reviewed_at": "2026-10-16T09:30:00+00:00",
        "answerable": True,
        "expected_answer": "An inner Config class.",
        "relevant_evidence": [
            {k: case["relevance"][0][k] for k in ("document_key", "logical_key")}
        ],
        "support_or_absence_rationale": "Synthetic validator fixture; no human review performed.",
        "uncertainty": "medium",
    }
    return manifest, cases, record


@pytest.mark.parametrize(
    "mutation",
    ["unknown", "wrong_release", "duplicate", "empty_answer", "blank_reviewer", "blank_rationale"],
)
def test_review_rejects_mechanically_invalid_evidence(mutation):
    manifest, cases, record = submission()
    if mutation == "unknown":
        record["relevant_evidence"][0]["logical_key"] += "-missing"
    elif mutation == "wrong_release":
        other = next(
            c
            for c in cases
            if c["project"] == "pydantic" and c["release"] == "2.10.4" and c["relevance"]
        )
        record["relevant_evidence"] = [
            {k: other["relevance"][0][k] for k in ("document_key", "logical_key")}
        ]
    elif mutation == "duplicate":
        record["relevant_evidence"] *= 2
    elif mutation == "empty_answer":
        record["expected_answer"] = " "
    elif mutation == "blank_reviewer":
        record["reviewer"] = " "
    else:
        record["support_or_absence_rationale"] = " "
    with pytest.raises(ValueError):
        validate([record], cases, manifest["dataset_sha256"])


def test_review_accepts_valid_identity_without_upgrading_human_status():
    manifest, cases, record = submission()
    before = copy.deepcopy(cases)
    result = validate([record], cases, manifest["dataset_sha256"])
    assert result["valid_submissions"] == 1
    assert result["labels_changed"] is result["human_identity_authenticated"] is False
    assert cases == before


@pytest.mark.parametrize("score", [float("nan"), float("inf"), float("-inf")])
def test_legacy_reranker_rejects_nonfinite_score(score):
    with pytest.raises(ValueError, match="finite"):
        order_reranked(["already-authorized"], [score])


def test_relevance_empty_pairs_skip_model_and_unavailable_model_is_explicit(monkeypatch):
    import sys

    from releaselens.relevance import RelevanceScorer

    def unavailable(*args, **kwargs):
        raise OSError("fixture: requested revision not in offline cache")

    monkeypatch.setitem(
        sys.modules, "sentence_transformers", SimpleNamespace(CrossEncoder=unavailable)
    )
    monkeypatch.setitem(sys.modules, "torch.nn", SimpleNamespace(Identity=lambda: object()))
    with pytest.raises(OSError, match="offline cache"):
        RelevanceScorer()
    assert object.__new__(RelevanceScorer).score("question", []) == []


def test_supplemental_metrics_keep_fixed_denominator_and_rank_cutoff():
    from scripts.supplement_v3 import measures

    labels = [{"document_key": "a", "logical_key": "x", "grade": 3}]
    value = measures([("a", "x")], labels)
    assert value == {
        "recall_at_5": 1,
        "proposal_precision_at_5": 0.2,
        "mrr_at_10": 1,
        "ndcg_at_10": 1,
    }
    assert measures([], labels)["mrr_at_10"] == 0
    assert measures([], []) is None
    rank6 = measures([("a", str(i)) for i in range(5)] + [("a", "x")], labels)
    assert rank6["recall_at_5"] == 0 and rank6["mrr_at_10"] == 1 / 6


def test_supplement_recomputes_frozen_predictions_without_changing_inputs():
    from releaselens.review_dataset import file_hash
    from scripts.supplement_v3 import supplement

    paths = [
        ROOT / "evaluation" / p for p in ("v3-calibrate.json", "v3-test.json", "benchmark-v3.jsonl")
    ]
    before = [file_hash(p) for p in paths]
    result = supplement()
    assert len(result["records"]) == 70 * 5
    assert len(result["summaries"]) == 15
    assert before == [file_hash(p) for p in paths]
    assert result["original_reranking_only_latency_ms"] is None


@pytest.mark.parametrize("mutation", ["missing_prediction", "evidence_hash"])
def test_supplement_rejects_incomplete_or_tampered_predictions(mutable_dataset, mutation):
    from scripts.supplement_v3 import supplement

    for name in ("v3-calibrate.json", "v3-test.json"):
        shutil.copyfile(ROOT / "evaluation" / name, mutable_dataset / "evaluation" / name)
    path = mutable_dataset / "evaluation/v3-test.json"
    data = json.loads(path.read_text())
    if mutation == "missing_prediction":
        data["records"].pop()
    else:
        data["records"][0]["retrieved"][0]["passage_sha256"] = "0" * 64
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        supplement(mutable_dataset)


def test_profile_blocks_nondev_and_scope_violations_before_model(monkeypatch):
    import releaselens.retrieval as retrieval
    from scripts.supplement_v3 import profile_query

    case = {"split": "test"}
    with pytest.raises(ValueError, match="development-only"):
        profile_query(None, case, None, None)
    _, cases = load_dataset()
    embedder = SimpleNamespace(name="test")
    private = (
        SimpleNamespace(),
        SimpleNamespace(project="other", release="2.0", classification="restricted"),
        1,
    )
    monkeypatch.setattr(retrieval, "rank", lambda *a, **k: [private])
    with pytest.raises(RuntimeError, match="before cross-encoder"):
        profile_query(None, cases[0], embedder, None)
