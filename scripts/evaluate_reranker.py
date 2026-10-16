"""Exploratory pretrained cross-encoder comparison on frozen, AI-labeled tuning cases.

Offline only. Rerank already authorized, exact-release candidates; never use a
reranker to establish permission, model confidence, or confirmed answer support.
"""

import argparse
import hashlib
import json
import math
import os
import platform
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter

from releaselens.benchmark import ROOT, family_bootstrap, load_pilot, ranking_metrics, select_cases
from releaselens.db import create_local_schema, database
from releaselens.evaluate import percentile
from releaselens.models import Passage
from releaselens.retrieval import configured_embedder, rank
from releaselens.security import Principal
from releaselens.sources import ingest_snapshot

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
MODES = ("bm25", "dense", "hybrid", "hybrid-cross-encoder")


def order_reranked(candidates, values):
    """Stable post-scope rerank. No passage is ever added to candidates."""
    if len(candidates) != len(values):
        raise ValueError("One cross-encoder score required for each candidate")
    if any(not math.isfinite(float(value)) for value in values):
        raise ValueError("Cross-encoder scores must be finite")
    return [
        candidates[i] for i in sorted(range(len(candidates)), key=lambda i: (-float(values[i]), i))
    ]


def identities(hits):
    return [(doc.key, passage.logical_key) for passage, doc, _ in hits]


def measure(hits, case):
    values5 = ranking_metrics(identities(hits), case["relevance"], 5)
    values10 = ranking_metrics(identities(hits), case["relevance"], 10)
    if values5 is None:
        return None
    return {
        "recall_at_5": values5["recall_at_k"],
        "ndcg_at_10": values10["ndcg_at_k"],
        "mrr_at_5": values5["mrr_at_k"],
    }


def summarize(rows):
    output = []
    for mode in MODES:
        subset = [r for r in rows if r["mode"] == mode]
        supported = [r for r in subset if r["metrics"] is not None]
        entry = {
            "mode": mode,
            "questions": len(subset),
            "supported_ai_proposals": len(supported),
            "unsupported_ai_proposals": len(subset) - len(supported),
            "retrieval_latency_p50_ms": percentile([r["latency_ms"] for r in subset], 0.5),
            "retrieval_latency_p95_ms": percentile([r["latency_ms"] for r in subset], 0.95),
            "wrong_release_hits": sum(r["wrong_release_hits"] for r in subset),
            "unauthorized_hits": sum(r["unauthorized_hits"] for r in subset),
        }
        for metric in ("recall_at_5", "ndcg_at_10", "mrr_at_5"):
            values = [
                {"family_id": r["family_id"], metric: r["metrics"][metric]} for r in supported
            ]
            entry[metric] = mean(v[metric] for v in values) if values else None
            entry[metric + "_family_bootstrap_95"] = family_bootstrap(values, metric)
        output.append(entry)
    return output


def run(output: Path, reranker, embedder, split="tuning"):
    manifest, cases = load_pilot()
    selected = select_cases(cases, split)
    queries = [case for case in selected if case["kind"] == "retrieval"]
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    records = []
    model_pairs = 0
    try:
        with factory.begin() as session:
            for source in manifest["sources"]:
                ingest_snapshot(session, ROOT / source["manifest"], embedder)
            passages = session.query(Passage).count()
            if queries:
                probe = queries[0]
                rank(
                    session,
                    Principal("pilot", probe["role"]),
                    probe["project"],
                    probe["release"],
                    probe["question"],
                    embedder,
                    "hybrid",
                    20,
                )
                if reranker is not None:
                    reranker.predict(
                        [(probe["question"], "Warmup evidence")], show_progress_bar=False
                    )
            for case in queries:
                principal = Principal("pilot", case["role"])
                for mode in MODES:
                    started = perf_counter()
                    base_mode = {"bm25": "lexical", "dense": "vector"}.get(mode, "hybrid")
                    candidate_count = 20 if mode == "hybrid-cross-encoder" else 10
                    hits = rank(
                        session,
                        principal,
                        case["project"],
                        case["release"],
                        case["question"],
                        embedder,
                        base_mode,
                        candidate_count,
                    )
                    max_score = None
                    if mode == "hybrid-cross-encoder":
                        if reranker is None:
                            raise ValueError("Cross-encoder model required")
                        scores = (
                            reranker.predict(
                                [(case["question"], p.section + "\n" + p.text) for p, _, _ in hits],
                                batch_size=16,
                                show_progress_bar=False,
                            ).tolist()
                            if hits
                            else []
                        )
                        model_pairs += len(hits)
                        hits = order_reranked(hits, scores)
                        max_score = max(scores, default=None)
                    hits = hits[:10]
                    elapsed = (perf_counter() - started) * 1000
                    wrong_release = sum(doc.release != case["release"] for _, doc, _ in hits)
                    unauthorized = sum(
                        doc.classification not in principal.classifications for _, doc, _ in hits
                    )
                    if wrong_release or unauthorized:
                        raise RuntimeError("Retrieved result escaped scoped release/authorization")
                    records.append(
                        {
                            "case_id": case["id"],
                            "family_id": case["family_id"],
                            "split": case["split"],
                            "mode": mode,
                            "ai_proposed_abstention": case["expected_abstention"],
                            "metrics": measure(hits, case),
                            "retrieved": [
                                {"document_key": d.key, "logical_key": p.logical_key}
                                for p, d, _ in hits
                            ],
                            "wrong_release_hits": wrong_release,
                            "unauthorized_hits": unauthorized,
                            "latency_ms": elapsed,
                            "top_cross_encoder_logit": max_score,
                        }
                    )
    finally:
        engine.dispose()
    summary = summarize(records)
    differences = []
    by_case = {(r["case_id"], r["mode"]): r for r in records}
    for baseline in ("bm25", "dense", "hybrid"):
        for key in ("recall_at_5", "ndcg_at_10"):
            diffs = [
                {
                    "family_id": case["family_id"],
                    "difference": by_case[(case["id"], "hybrid-cross-encoder")]["metrics"][key]
                    - by_case[(case["id"], baseline)]["metrics"][key],
                }
                for case in queries
                if case["relevance"]
            ]
            differences.append(
                {
                    "comparison": "hybrid-cross-encoder minus " + baseline,
                    "metric": key,
                    "mean_delta": mean(d["difference"] for d in diffs),
                    "paired_family_bootstrap_95": family_bootstrap(diffs, "difference"),
                }
            )
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": manifest["dataset_sha256"],
        "dataset_version": manifest["dataset_version"],
        "split": split,
        "annotation_status": dict(Counter(c["review_status"] for c in queries)),
        "human_reviewed": sum(c["review_status"] == "human_verified" for c in queries),
        "embedding_model": embedder.name,
        "cross_encoder": f"{RERANK_MODEL}@{RERANK_REVISION}",
        "cross_encoder_model_license": "Apache-2.0 (model card; review upstream)",
        "cross_encoder_pairs_scored": model_pairs,
        "backend": "SQLite, in-process exact dense, scoped BM25; not PostgreSQL FTS",
        "scope": "Tuning-only, AI-proposed relevance; no independent generalization",
        "source_passages": passages,
        "python": platform.python_version(),
        "os": platform.platform(),
        "logical_cpus": os.cpu_count(),
        "parameters": {
            "candidate_depth": 20,
            "rrf_constant": 60,
            "k_recall": 5,
            "k_ndcg": 10,
            "batch_size": 16,
            "positive_lexical_gate": True,
        },
        "latency_scope": "Warmed single-query sequential timings including query embedding, SQL ranking and reranker (where applicable), excluding loading and ingestion",
        "results": summary,
        "paired_differences": differences,
        "records": records,
        "provider_api_cost_usd": 0,
        "electricity_network_cost_usd": None,
        "answer_support_accuracy": None,
        "revalidation_precision_recall": None,
        "limitations": [
            "Labels are AI-authored proposals, not human judgments.",
            "Heldout families have not been used for model selection.",
            "Cross-encoder logits are not calibrated answerability probabilities.",
            "Not a production enabled mode; no claims about PostgreSQL quality.",
            "Passage chunks may exceed the model token budget; cross-encoder truncation occurs.",
            "Reranking only the lexically eligible hybrid candidates cannot recover excluded evidence.",
            "Sequential latency is not load-test p95 or an SLA.",
        ],
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "evaluation/pretrained-reranker-tuning.json"
    )
    parser.add_argument(
        "--split",
        choices=("tuning",),
        default="tuning",
        help="Heldout intentionally unavailable before independent review",
    )
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    from sentence_transformers import CrossEncoder

    model = CrossEncoder(
        RERANK_MODEL,
        revision=RERANK_REVISION,
        trust_remote_code=False,
        device="cpu",
        max_length=256,
    )
    result = run(args.output, model, configured_embedder(), split=args.split)
    print(
        json.dumps(
            {
                "split": result["split"],
                "questions": len(set(x["case_id"] for x in result["records"])),
                "results": result["results"],
                "paired_differences": result["paired_differences"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
