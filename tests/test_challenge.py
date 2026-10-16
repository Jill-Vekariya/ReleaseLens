"""Challenge leakage, source identities, holdout refusal and review contracts."""

import copy
import hashlib
import json
import shutil

import pytest

from releaselens.challenge import MANIFEST, load_challenge, select_cases
from releaselens.review_dataset import ROOT, file_hash
from scripts.build_challenge import freeze
from scripts.evaluate_challenge import run
from scripts.review_benchmark import validate


@pytest.fixture
def challenge_copy(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    (tmp_path / "evaluation").mkdir()
    for name in (MANIFEST, "migration-challenge-v1.jsonl", "benchmark-v3-manifest.json"):
        shutil.copyfile(ROOT / "evaluation" / name, tmp_path / "evaluation" / name)
    return tmp_path


def mutate(root, change):
    path = root / "evaluation/migration-challenge-v1.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    change(cases)
    path.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    path = root / "evaluation" / MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    data["dataset_sha256"] = file_hash(root / "evaluation/migration-challenge-v1.jsonl")
    path.write_text(json.dumps(data), encoding="utf-8")


def test_challenge_freeze_counts_and_new_heldout_sources():
    manifest, cases = load_challenge()
    assert len(cases) == 24 and manifest["splits"] == {"dev": 12, "validation": 4, "test": 8}
    assert sum(c["expected_abstention"] for c in cases) == 4
    assert sum(s["passages"] for s in manifest["sources"]) == 707
    old = json.loads((ROOT / "evaluation/benchmark-v3-manifest.json").read_text(encoding="utf-8"))
    assert not set(manifest["new_holdout_sources"]) & {s["manifest"] for s in old["sources"]}
    for c in cases:
        assert c["review_status"] == "ai_reviewed_proposal" and c["human_review"] is None
        assert bool(c["proposed_hard_negatives"]) == c["expected_abstention"]


@pytest.mark.parametrize("splits", [("test",), ("dev", "test"), (), ("dev", "dev")])
def test_challenge_refuses_heldout_and_invalid_selection(splits):
    _, cases = load_challenge()
    with pytest.raises(ValueError, match="heldout"):
        select_cases(cases, splits)


def test_loader_rejects_old_source_reused_as_new_holdout(challenge_copy):
    path = challenge_copy / "evaluation" / MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    data["new_holdout_sources"].append(data["sources"][0]["manifest"])
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="absent from v3"):
        load_challenge(challenge_copy)


def test_rejects_tampered_same_release_hard_negative(challenge_copy):
    def change(cases):
        case = next(c for c in cases if c["proposed_hard_negatives"])
        case["proposed_hard_negatives"][0]["passage_sha256"] = "0" * 64

    mutate(challenge_copy, change)
    with pytest.raises(ValueError, match="Hard-negative anchor/hash"):
        load_challenge(challenge_copy)


def test_rejects_leaking_intent_group_across_splits(challenge_copy):
    def change(cases):
        test = next(c for c in cases if c["split"] == "test")
        test["dedup_group"] = cases[0]["dedup_group"]

    mutate(challenge_copy, change)
    with pytest.raises(ValueError, match="Version variants or near duplicates"):
        load_challenge(challenge_copy)


def test_freeze_refuses_to_overwrite_existing_proposals():
    path = ROOT / "evaluation/migration-challenge-v1.jsonl"
    before = file_hash(path)
    with pytest.raises(ValueError, match="already frozen"):
        freeze()
    assert file_hash(path) == before


def test_blank_review_packet_contains_no_proposed_answers_or_judgments():
    rows = [
        json.loads(line)
        for line in (ROOT / "docs/review/challenge-dev-blank.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(rows) == 12
    for row in rows:
        assert (
            row["reviewer"]
            is row["reviewed_at"]
            is row["answerable"]
            is row["expected_answer"]
            is None
        )
        assert row["relevant_evidence"] == []
        assert "proposed_hard_negatives" not in row and "relevance" not in row


def test_challenge_review_validation_never_promotes_personhood():
    manifest, cases = load_challenge()
    case = cases[0]
    record = {
        "case_id": case["id"],
        "dataset_sha256": manifest["dataset_sha256"],
        "reviewer": "fictional-regression-fixture-not-a-human-review",
        "reviewed_at": "2026-10-16T10:00:00+00:00",
        "answerable": True,
        "expected_answer": "Fixture for structural validation only.",
        "support_or_absence_rationale": "Synthetic test record, not a real review.",
        "relevant_evidence": [
            {k: case["relevance"][0][k] for k in ("document_key", "logical_key")}
        ],
        "uncertainty": "high",
    }
    before = copy.deepcopy(cases)
    result = validate([record], cases, manifest["dataset_sha256"], manifest_name=MANIFEST)
    assert result["labels_changed"] is result["human_identity_authenticated"] is False
    assert before == cases


def test_hash_diagnostic_never_scores_holdout_or_changes_v3():
    paths = [
        ROOT / "evaluation" / p
        for p in ("v3-test.json", "answerability-policy-v3.json", "benchmark-v3.jsonl")
    ]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    result = run(("dev",))
    assert result["test_questions_scored"] == 0
    assert len(result["selected_case_ids"]) == 12
    assert {r["split"] for r in result["records"]} == {"dev"}
    assert result["human_correctness"] is result["human_support"] is None
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    with pytest.raises(ValueError, match="heldout"):
        run(("test",), learned=True)


def test_expanded_ingestion_keeps_frozen14_as_repository_grows(tmp_path):
    import os
    import sqlite3
    import subprocess
    import sys

    db = tmp_path / "expanded.db"
    env = os.environ.copy()
    for name in ("EMBEDDING_MODEL", "EMBEDDING_REVISION", "ANSWERABILITY_POLICY"):
        env.pop(name, None)
    env["DATABASE_URL"] = "sqlite:///" + db.as_posix()
    result = subprocess.run(
        [sys.executable, "scripts/ingest_sources.py", "--expanded"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM documents").fetchone()[0] == 14
        assert connection.execute("SELECT count(*) FROM passages").fetchone()[0] == 534


def test_ingestion_source_profiles_are_explicit():
    from scripts.ingest_sources import selected_manifests

    assert len(selected_manifests()) == 4
    assert len(selected_manifests(expanded=True)) == 14
    assert len(selected_manifests(challenge=True)) == 19
    with pytest.raises(ValueError, match="either"):
        selected_manifests(expanded=True, challenge=True)
