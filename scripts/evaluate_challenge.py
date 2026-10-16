"""Diagnostic challenge evaluation; heldout questions are intentionally unsupported.

python -m scripts.evaluate_challenge --split dev validation --output <new.json>
Add --learned in the cached Windows CPU environment for the five-way comparison.
No threshold search, model training, human accuracy or production adoption.
"""

import argparse
import json
import os
import platform
from datetime import datetime, timezone
from statistics import mean
from time import perf_counter

from releaselens.challenge import MANIFEST, load_challenge, select_cases
from releaselens.db import create_local_schema, database
from releaselens.evaluate import percentile
from releaselens.models import Passage
from releaselens.retrieval import HashEmbedder, rank
from releaselens.review_dataset import ROOT, file_hash
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask
from releaselens.sources import ingest_snapshot
from scripts.evaluate_v3 import evaluate, selective_metrics
from scripts.supplement_v3 import measures


def run(splits, learned=False):
    manifest, cases = load_challenge()
    selected = select_cases(cases, splits)
    frozen_names = [
        "benchmark-v3.jsonl",
        "answerability-policy-v3.json",
        "v3-calibrate.json",
        "v3-test.json",
    ]
    original_hashes = {name: file_hash(ROOT / "evaluation" / name) for name in frozen_names}
    policy = json.loads((ROOT / "evaluation/answerability-policy-v3.json").read_text())
    start = perf_counter()
    scorer = None
    if learned:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        import torch

        from releaselens.relevance import RelevanceScorer
        from releaselens.retrieval import SentenceEmbedder

        torch.set_num_threads(2)
        encoder = SentenceEmbedder(
            "sentence-transformers/all-MiniLM-L6-v2", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
        )
        scorer = RelevanceScorer()
        assert policy["embedding"] == encoder.name and policy["model"] == scorer.name
    else:
        encoder = HashEmbedder()
    loading_ms = (perf_counter() - start) * 1000
    engine, factory = database("sqlite:///:memory:")
    hash_engine, hash_factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    create_local_schema(hash_engine)
    try:
        with factory.begin() as session, hash_factory.begin() as hash_session:
            start = perf_counter()
            for source in manifest["sources"]:
                ingest_snapshot(session, ROOT / source["manifest"], encoder)
                if learned:
                    ingest_snapshot(hash_session, ROOT / source["manifest"], HashEmbedder())
            indexing_ms = (perf_counter() - start) * 1000
            passages = session.query(Passage).count()
            probe = selected[0]
            warm = rank(
                session,
                Principal("warmup", probe["role"]),
                probe["project"],
                probe["release"],
                probe["question"],
                encoder,
                "hybrid",
                4,
            )
            if learned:
                scorer.score(probe["question"], [p for p, _, _ in warm])
                records, probes = evaluate(
                    selected, session, encoder, scorer, hash_session, policy["threshold"]
                )
            else:
                records, probes = [], []
                for case in selected:
                    principal = Principal("challenge", case["role"])
                    for mode, base in [("bm25", "lexical"), ("feature-hash-reference", "hybrid")]:
                        start = perf_counter()
                        hits = rank(
                            session,
                            principal,
                            case["project"],
                            case["release"],
                            case["question"],
                            encoder,
                            base,
                            10,
                        )
                        elapsed = (perf_counter() - start) * 1000
                        if any(
                            d.project != case["project"]
                            or d.release != case["release"]
                            or d.classification not in principal.classifications
                            for _, d, _ in hits
                        ):
                            raise RuntimeError("Scope violation")
                        records.append(
                            {
                                "case_id": case["id"],
                                "family_id": case["family_id"],
                                "split": case["split"],
                                "mode": mode,
                                "latency_ms": elapsed,
                                "wrong_release_hits": 0,
                                "unauthorized_hits": 0,
                                "retrieved": [
                                    {"document_key": d.key, "logical_key": p.logical_key}
                                    for p, d, _ in hits
                                ],
                                "metrics": None,
                            }
                        )
                    answer = ask(
                        session,
                        principal,
                        AskRequest(
                            project=case["project"],
                            release=case["release"],
                            question=case["question"],
                            save=False,
                        ),
                        encoder,
                    )
                    probes.append(
                        {
                            "case_id": case["id"],
                            "split": case["split"],
                            "expected_abstention": case["expected_abstention"],
                            "baseline_answered": not bool(answer.abstention_reason),
                        }
                    )
    finally:
        engine.dispose()
        hash_engine.dispose()
    case_map = {c["id"]: c for c in selected}
    for row in records:
        identities = [(p["document_key"], p["logical_key"]) for p in row["retrieved"]]
        row["metrics"] = measures(identities, case_map[row["case_id"]]["relevance"])
    summaries = {}
    for split in splits:
        rows = [r for r in records if r["split"] == split]
        reports = []
        for mode in sorted({r["mode"] for r in rows}):
            group = [r for r in rows if r["mode"] == mode]
            positive = [r for r in group if r["metrics"] is not None]
            reports.append(
                {
                    "mode": mode,
                    "questions": len(group),
                    "supported": len(positive),
                    **{
                        key: mean(r["metrics"][key] for r in positive) if positive else None
                        for key in (
                            "recall_at_5",
                            "proposal_precision_at_5",
                            "mrr_at_10",
                            "ndcg_at_10",
                        )
                    },
                    "latency_p50_ms": percentile([r["latency_ms"] for r in group], 0.5),
                    "latency_p95_ms": percentile([r["latency_ms"] for r in group], 0.95),
                }
            )
        answers = [r for r in probes if r["split"] == split]
        summary = {
            "retrieval": reports,
            "baseline_answerability": selective_metrics(
                [{**r, "answered": r["baseline_answered"]} for r in answers]
            ),
        }
        if learned:
            summary["transferred_gate_answerability"] = selective_metrics(answers)
        summaries[split] = summary
    if original_hashes != {name: file_hash(ROOT / "evaluation" / name) for name in frozen_names}:
        raise RuntimeError("Original frozen v3 data/policy/predictions changed")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": manifest["dataset_sha256"],
        "manifest_sha256": file_hash(ROOT / "evaluation" / MANIFEST),
        "splits_scored": list(splits),
        "test_questions_scored": 0,
        "selected_case_ids": [c["id"] for c in selected],
        "labels": "AI-authored/source-inspected proposals; human reviewed0; not independent accuracy",
        "encoder": encoder.name,
        "scorer": scorer.name if scorer else None,
        "transferred_policy": {
            "threshold": policy["threshold"],
            "policy_sha256": original_hashes["answerability-policy-v3.json"],
            "interpretation": "Fixed v3 threshold, transferred without tuning to different corpus/questions; not calibrated on this challenge or approved for production",
        }
        if learned
        else None,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_cpus": os.cpu_count(),
            "backend": "SQLite in-memory, exact vectors/BM25",
            "corpus_snapshots": len(manifest["sources"]),
            "corpus_passages": passages,
            "model_loading_ms": loading_ms,
            "indexing_ms": indexing_ms,
            "torch_threads": 2 if learned else None,
            "warmup": "First selected development query; excluded from timings",
        },
        "parameters": {
            "recall_k": 5,
            "ndcg_k": 10,
            "rerank_candidates": 20,
            "rrf_constant": 60,
            "gate_k": 4,
        },
        "code_sha256": {
            p: file_hash(ROOT / p)
            for p in (
                "scripts/evaluate_challenge.py",
                "releaselens/challenge.py",
                "scripts/evaluate_v3.py",
                "releaselens/relevance.py",
                "releaselens/retrieval.py",
            )
        },
        "original_v3_sha256": original_hashes,
        "summaries": summaries,
        "records": records,
        "answer_probes": probes,
        "human_correctness": None,
        "human_support": None,
        "provider_api_cost_usd": 0,
        "electricity_network_cost_usd": None,
        "limits": [
            "Sparse labels and four realistic missing-information negatives; no population or significance claim.",
            "All19 source snapshots are indexed, including reserved-family text; holdout is unscored questions/families, not an unseen corpus.",
            "Public pretraining contamination and related concepts unaudited; prior v3 test remains consumed.",
            "Binary unsupported-answer errors omit wrong answers to answerable questions; semantic error unmeasured.",
            "No threshold/model change; weak or failed results are retained.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", nargs="+", choices=("dev", "validation"), default=["dev"])
    parser.add_argument("--learned", action="store_true")
    parser.add_argument("--output", type=__import__("pathlib").Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite evidence; choose a new output path")
    result = run(tuple(args.split), args.learned)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("records", "answer_probes")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
