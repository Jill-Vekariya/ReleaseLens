"""Add descriptive metrics from frozen predictions, or profile dev-only cached models.

Never selects a model/threshold, changes labels or reruns the consumed v3 test.
Sparse proposal-label Precision is not human relevance precision.
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

from releaselens.benchmark import family_bootstrap, ranking_metrics
from releaselens.evaluate import percentile
from releaselens.review_dataset import ROOT, file_hash, load_dataset
from releaselens.sources import chunks
from scripts.evaluate_reranker import order_reranked
from scripts.evaluate_v3 import MODES


def measures(identities, relevance):
    at5 = ranking_metrics(identities, relevance, 5)
    at10 = ranking_metrics(identities, relevance, 10)
    if at5 is None:
        return None
    relevant = {(r["document_key"], r["logical_key"]) for r in relevance}
    return {
        "recall_at_5": at5["recall_at_k"],
        "proposal_precision_at_5": len(set(identities[:5]) & relevant) / 5,
        "mrr_at_10": at10["mrr_at_k"],
        "ndcg_at_10": at10["ndcg_at_k"],
    }


def supplement(root=ROOT):
    manifest, cases = load_dataset(root)
    known = {c["id"]: c for c in cases}
    available = {}
    for source in manifest["sources"]:
        path = (root / source["manifest"]).parent / "source.txt"
        for index, block in enumerate(chunks(path.read_bytes().decode())):
            identity = (
                source["project"],
                source["release"],
                source["path"],
                f"{source['path']}#block-{index:04}",
            )
            available[identity] = hashlib.sha256(block.encode()).hexdigest()
    records, inputs = [], {}
    for name, allowed in [
        ("v3-calibrate.json", ("dev", "validation")),
        ("v3-test.json", ("test",)),
    ]:
        path = root / "evaluation" / name
        original = json.loads(path.read_text(encoding="utf-8"))
        inputs[name] = file_hash(path)
        if original["dataset_sha256"] != manifest["dataset_sha256"]:
            raise ValueError("Prediction dataset hash mismatch")
        seen = set()
        for row in original["records"]:
            if row["case_id"] not in known or row["mode"] not in MODES:
                raise ValueError("Unknown prediction case/mode")
            case = known[row["case_id"]]
            identity = (case["id"], row["mode"])
            if identity in seen or row["split"] != case["split"] or case["split"] not in allowed:
                raise ValueError("Duplicate or incorrectly split prediction")
            seen.add(identity)
            if (
                row["family_id"] != case["family_id"]
                or row["wrong_release_hits"]
                or row["unauthorized_hits"]
            ):
                raise ValueError("Invalid prediction provenance/scope counters")
            hits = row["retrieved"]
            ids = [(h["document_key"], h["logical_key"]) for h in hits]
            if len(ids) > 10 or len(set(ids)) != len(ids):
                raise ValueError("Duplicate or excessive ranked passages")
            for h in hits:
                scope = (case["project"], case["release"], h["document_key"], h["logical_key"])
                if available.get(scope) != h["passage_sha256"]:
                    raise ValueError("Prediction evidence hash/identity outside case corpus")
            computed = measures(ids, case["relevance"])
            for key in ("recall_at_5", "ndcg_at_10"):
                if (computed is None) != (row["metrics"] is None) or (
                    computed is not None
                    and not math.isclose(computed[key], row["metrics"][key], abs_tol=1e-12)
                ):
                    raise ValueError("Stored ranking metric differs from frozen predictions")
            records.append(
                {
                    "case_id": case["id"],
                    "family_id": case["family_id"],
                    "split": case["split"],
                    "mode": row["mode"],
                    "metrics": computed,
                }
            )
        expected = {(c["id"], mode) for c in cases if c["split"] in allowed for mode in MODES}
        if seen != expected:
            raise ValueError("Incomplete prediction matrix")
    summaries = []
    for split in ("dev", "validation", "test"):
        for mode in MODES:
            rows = [r for r in records if r["split"] == split and r["mode"] == mode]
            positive = [r for r in rows if r["metrics"] is not None]
            result = {
                "split": split,
                "mode": mode,
                "questions": len(rows),
                "supported": len(positive),
            }
            for metric in ("recall_at_5", "proposal_precision_at_5", "mrr_at_10", "ndcg_at_10"):
                values = [
                    {"family_id": r["family_id"], metric: r["metrics"][metric]} for r in positive
                ]
                result[metric] = mean(v[metric] for v in values) if values else None
                result[metric + "_family_bootstrap_95_descriptive"] = family_bootstrap(
                    values, metric
                )
            summaries.append(result)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": manifest["dataset_sha256"],
        "input_sha256": inputs,
        "method": "Post-hoc descriptive metrics from preserved rankings; no new test inference or selection",
        "labels": "AI proposals; human-reviewed 0; unjudged passages are not known irrelevant",
        "precision_definition": "Unique proposed relevant hits in first five divided by five; fewer than five returned pads missing ranks with zero",
        "mrr_definition": "Reciprocal rank of first proposed relevant passage at cutoff ten; zero if absent",
        "cutoffs": "Recall/Precision at 5 for short evidence lists; MRR/nDCG at 10 for ordering diagnostics, not selected after a cutoff search",
        "original_pre_rerank_candidate_coverage": None,
        "original_reranking_only_latency_ms": None,
        "timing_note": "Original outputs stored only final top ten and combined latency; missing stages cannot be reconstructed by subtraction",
        "confidence_note": "Only two supported families per split; family bootstrap is descriptive and may degenerate",
        "summaries": summaries,
        "records": records,
    }


def profile_query(session, case, embedder, scorer):
    from releaselens.retrieval import rank
    from releaselens.security import Principal

    if case["split"] != "dev":
        raise ValueError("New profiling is development-only; do not rerun consumed test")
    principal = Principal("dev-profile", case["role"])
    start = perf_counter()
    candidates = rank(
        session,
        principal,
        case["project"],
        case["release"],
        case["question"],
        embedder,
        "hybrid",
        20,
    )
    retrieval_ms = (perf_counter() - start) * 1000
    # Fail before model invocation on a scope error; never score an unauthorized candidate.
    if any(
        d.project != case["project"]
        or d.release != case["release"]
        or d.classification not in principal.classifications
        or p.revision_id != d.current_revision
        or p.quarantined
        or p.embedding_model != embedder.name
        for p, d, _ in candidates
    ):
        raise RuntimeError("Candidate scope violation before cross-encoder")
    start = perf_counter()
    scores = scorer.score(case["question"], [p for p, _, _ in candidates])
    hits = order_reranked(candidates, scores)
    reranking_ms = (perf_counter() - start) * 1000
    candidate_ids = [(d.key, p.logical_key) for p, d, _ in candidates]
    coverage = ranking_metrics(candidate_ids, case["relevance"], 20)
    return {
        "case_id": case["id"],
        "family_id": case["family_id"],
        "split": case["split"],
        "candidates": len(candidates),
        "retrieval_ms": retrieval_ms,
        "reranking_ms": reranking_ms,
        "ranking_total_ms": retrieval_ms + reranking_ms,
        "pre_rerank_recall_at_20": coverage["recall_at_k"] if coverage else None,
        "post_rerank": measures(
            [(d.key, p.logical_key) for p, d, _ in hits[:10]], case["relevance"]
        ),
        "scope_checked_before_scoring": True,
    }


def peak_memory():
    if platform.system() != "Windows":
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
            1 if platform.system() == "Darwin" else 1024
        )
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    data = Counters()
    data.cb = ctypes.sizeof(data)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(Counters),
        wintypes.DWORD,
    ]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(data), data.cb):
        return None
    return data.PeakWorkingSetSize


def profile_dev(root=ROOT):
    # Must precede optional Hugging Face/ML imports. No network fallback or model substitution.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch

    from releaselens.db import create_local_schema, database
    from releaselens.models import Passage
    from releaselens.relevance import RelevanceScorer
    from releaselens.retrieval import SentenceEmbedder
    from releaselens.sources import ingest_snapshot

    manifest, cases = load_dataset(root)
    torch.set_num_threads(2)
    encoder_id = "sentence-transformers/all-MiniLM-L6-v2"
    encoder_revision = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    start = perf_counter()
    embedder, scorer = SentenceEmbedder(encoder_id, encoder_revision), RelevanceScorer()
    loading_ms = (perf_counter() - start) * 1000
    # Deliberately absent revision; exception must propagate instead of silent hash fallback.
    try:
        SentenceEmbedder(encoder_id, "0" * 40)
    except (OSError, ValueError) as exc:
        unavailable = {
            "revision": "0" * 40,
            "failed_explicitly": True,
            "error_type": type(exc).__name__,
        }
    else:
        raise RuntimeError("Expected absent offline revision to fail")
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    try:
        with factory.begin() as session:
            start = perf_counter()
            for source in manifest["sources"]:
                ingest_snapshot(session, root / source["manifest"], embedder)
            indexing_ms = (perf_counter() - start) * 1000
            count = session.query(Passage).count()
            dev = [c for c in cases if c["split"] == "dev"]
            profile_query(session, dev[0], embedder, scorer)  # Fixed dev warmup, not included.
            records = [profile_query(session, c, embedder, scorer) for c in dev]
    finally:
        engine.dispose()
    positive = [r for r in records if r["pre_rerank_recall_at_20"] is not None]
    timing = {
        key: {
            "p50": percentile([r[key] for r in records], 0.5),
            "p95": percentile([r[key] for r in records], 0.95),
        }
        for key in ("retrieval_ms", "reranking_ms", "ranking_total_ms")
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split": "dev",
        "dataset_sha256": manifest["dataset_sha256"],
        "questions": len(records),
        "supported": len(positive),
        "encoder": embedder.name,
        "reranker": scorer.name,
        "parameters": {
            "dimensions": 384,
            "pair_tokens": 256,
            "batch_size": 8,
            "candidate_depth": 20,
            "threads": 2,
            "offline": True,
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
            "torch": torch.__version__,
            "backend": "SQLite in-memory",
            "model_loading_ms": loading_ms,
            "indexing_ms": indexing_ms,
            "corpus_passages": count,
            "peak_process_resident_bytes": peak_memory(),
        },
        "memory_scope": "Process lifetime high-water RSS/working set including imports, both models, index and unavailable-revision probe; not isolated reranker or production memory",
        "offline_missing_revision": unavailable,
        "timing_ms": timing,
        "pre_rerank_recall_at_20": mean(r["pre_rerank_recall_at_20"] for r in positive),
        "families": dict(Counter(c["family_id"] for c in dev)),
        "cross_encoder_pairs_scored_excluding_warmup": sum(r["candidates"] for r in records),
        "limits": "AI-proposed sparse labels, one warmed sequential pass, development-only profile; not comparable heldout accuracy or a production SLA; no threshold/model changes",
        "provider_api_cost_usd": 0,
        "electricity_network_cost_usd": None,
        "code_sha256": {
            p: file_hash(root / p)
            for p in (
                "scripts/supplement_v3.py",
                "releaselens/retrieval.py",
                "releaselens/relevance.py",
                "scripts/evaluate_reranker.py",
            )
        },
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dev", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / "evaluation" / (
        "reranker-profile-dev-v3.json" if args.profile_dev else "retrieval-supplement-v3.json"
    )
    if output.exists():
        parser.error("Refusing to overwrite evidence; use --output with a new path")
    result = profile_dev() if args.profile_dev else supplement()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps({k: v for k, v in result.items() if k not in ("records", "summaries")}, indent=2)
    )


if __name__ == "__main__":
    main()
