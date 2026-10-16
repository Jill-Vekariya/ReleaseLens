"""Matched expanded-corpus retrieval, validation-only gate calibration, frozen test.

All quality labels are AI proposals. Exact-evidence validation is a separate measure.
No human correctness, semantic support, classifier training or production result.
"""

import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from statistics import mean
from time import perf_counter

from releaselens.benchmark import family_bootstrap, ranking_metrics
from releaselens.db import create_local_schema, database
from releaselens.evaluate import percentile
from releaselens.models import Passage
from releaselens.relevance import RelevanceGate, RelevanceScorer
from releaselens.retrieval import HashEmbedder, configured_embedder, rank
from releaselens.review_dataset import ROOT, file_hash, load_dataset
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask, validate_citations
from releaselens.sources import ingest_snapshot

MODES = ("bm25", "dense", "hybrid", "hybrid-cross-encoder", "feature-hash-reference")
GRID = (-12.0, -8.0, -4.0, 0.0, 2.0, 4.0, 6.0, 8.0, 12.0)


def selective_metrics(rows):
    """Binary answerability vs AI proposals; does NOT score semantic correctness."""
    tp = sum(r["answered"] and not r["expected_abstention"] for r in rows)
    fp = sum(r["answered"] and r["expected_abstention"] for r in rows)
    fn = sum(not r["answered"] and not r["expected_abstention"] for r in rows)
    tn = sum(not r["answered"] and r["expected_abstention"] for r in rows)
    answered = tp + fp
    return {
        "cases": len(rows),
        "answered": answered,
        "coverage": answered / len(rows) if rows else None,
        "unsupported_answer_false_positives": fp,
        "supported_abstention_false_negatives": fn,
        "supported_answers": tp,
        "unsupported_abstentions": tn,
        "unsupported_error_among_answered": fp / answered if answered else None,
        "answerability_precision": tp / answered if answered else None,
        "answerability_recall": tp / (tp + fn) if tp + fn else None,
        "abstention_precision": tn / (tn + fn) if tn + fn else None,
        "abstention_recall": tn / (tn + fp) if tn + fp else None,
        "semantic_answer_error_rate": None,
        "interpretation": "AI-proposed binary answerability only; answerable questions may still receive irrelevant or incorrect extracts",
    }


def choose_threshold(rows):
    """Preregistered utility: unsupported answer costs 3; missed supported answer costs 1.

    Ties prefer fewer false positives, then a higher threshold. No test rows allowed.
    """
    if not rows or any(r["split"] != "validation" for r in rows):
        raise ValueError("Threshold calibration requires validation rows only")
    trials = []
    for threshold in GRID:
        assessed = [
            {**r, "answered": r["top_score"] is not None and r["top_score"] >= threshold}
            for r in rows
        ]
        metrics = selective_metrics(assessed)
        loss = (
            3 * metrics["unsupported_answer_false_positives"]
            + metrics["supported_abstention_false_negatives"]
        )
        trials.append({"threshold": threshold, "weighted_errors": loss, **metrics})
    best = min(
        trials,
        key=lambda t: (
            t["weighted_errors"],
            t["unsupported_answer_false_positives"],
            -t["threshold"],
        ),
    )
    return best["threshold"], trials


def summarize(records):
    summaries = []
    for mode in MODES:
        subset = [r for r in records if r["mode"] == mode]
        positives = [r for r in subset if r["metrics"] is not None]
        item = {
            "mode": mode,
            "questions": len(subset),
            "supported": len(positives),
            "latency_p50_ms": percentile([r["latency_ms"] for r in subset], 0.5),
            "latency_p95_ms": percentile([r["latency_ms"] for r in subset], 0.95),
            "wrong_release_hits": sum(r["wrong_release_hits"] for r in subset),
            "unauthorized_hits": sum(r["unauthorized_hits"] for r in subset),
        }
        for metric in ("recall_at_5", "ndcg_at_10"):
            values = [
                {"family_id": r["family_id"], metric: r["metrics"][metric]} for r in positives
            ]
            item[metric] = mean(r[metric] for r in values) if values else None
            item[metric + "_family_bootstrap_95_descriptive"] = family_bootstrap(values, metric)
        summaries.append(item)
    return summaries


def evaluate(cases, session, embedder, scorer, hash_session, threshold=None):
    records, probes = [], []
    for n, case in enumerate(cases):
        principal = Principal("v3-evaluation", case["role"])
        modes = MODES[n % len(MODES) :] + MODES[: n % len(MODES)]
        for mode in modes:
            start = perf_counter()
            base = {"bm25": "lexical", "dense": "vector"}.get(mode, "hybrid")
            hits = rank(
                hash_session if mode == "feature-hash-reference" else session,
                principal,
                case["project"],
                case["release"],
                case["question"],
                HashEmbedder() if mode == "feature-hash-reference" else embedder,
                base,
                20 if mode == "hybrid-cross-encoder" else 10,
            )
            if mode == "hybrid-cross-encoder" and hits:
                scores = scorer.score(case["question"], [p for p, _, _ in hits])
                hits = [hits[i] for i in sorted(range(len(hits)), key=lambda i: (-scores[i], i))]
            hits = hits[:10]
            elapsed = (perf_counter() - start) * 1000
            identities = [(d.key, p.logical_key) for p, d, _ in hits]
            m5, m10 = (
                ranking_metrics(identities, case["relevance"], 5),
                ranking_metrics(identities, case["relevance"], 10),
            )
            wrong = sum(
                d.release != case["release"] or d.project != case["project"] for _, d, _ in hits
            )
            private = sum(d.classification not in principal.classifications for _, d, _ in hits)
            if wrong or private:
                raise RuntimeError("Scope violation")
            records.append(
                {
                    "case_id": case["id"],
                    "family_id": case["family_id"],
                    "split": case["split"],
                    "mode": mode,
                    "metrics": {"recall_at_5": m5["recall_at_k"], "ndcg_at_10": m10["ndcg_at_k"]}
                    if m5 is not None
                    else None,
                    "latency_ms": elapsed,
                    "wrong_release_hits": wrong,
                    "unauthorized_hits": private,
                    "retrieved": [
                        {
                            "document_key": d.key,
                            "logical_key": p.logical_key,
                            "passage_sha256": hashlib.sha256(p.text.encode()).hexdigest(),
                        }
                        for p, d, _ in hits
                    ],
                }
            )
        # Same production ask route, top4, including exact citation validation. No persistence.
        request = AskRequest(
            project=case["project"], release=case["release"], question=case["question"], save=False
        )
        session.info.pop("relevance_gate", None)
        start = perf_counter()
        original = ask(session, principal, request, embedder)
        baseline_ms = (perf_counter() - start) * 1000
        rows = rank(
            session,
            principal,
            case["project"],
            case["release"],
            case["question"],
            embedder,
            "version",
            4,
        )
        values = scorer.score(case["question"], [p for p, _, _ in rows])
        best = max(range(len(values)), key=lambda i: values[i]) if values else None
        proposed = {(r["document_key"], r["logical_key"]) for r in case["relevance"]}
        probe = {
            "case_id": case["id"],
            "family_id": case["family_id"],
            "split": case["split"],
            "expected_abstention": case["expected_abstention"],
            "baseline_answered": not bool(original.abstention_reason),
            "baseline_end_to_end_ms": baseline_ms,
            "top_score": max(values) if values else None,
            "top_passage_proposed_relevant": (rows[best][1].key, rows[best][0].logical_key)
            in proposed
            if best is not None
            else False,
            "human_correctness": None,
            "human_relevance": None,
            "human_semantic_support": None,
        }
        if threshold is not None:
            session.info["relevance_gate"] = RelevanceGate(scorer, threshold, "v3-validation-only")
            start = perf_counter()
            answer = ask(session, principal, request, embedder)
            probe["gated_end_to_end_ms"] = (perf_counter() - start) * 1000
            validate_citations(session, principal, answer)
            probe.update(
                {
                    "answered": not bool(answer.abstention_reason),
                    "exact_citation_validation_passed": True,
                    "selected_passage_count": len(answer.passages),
                    "abstention_reason": answer.abstention_reason,
                }
            )
            session.info.pop("relevance_gate", None)
        probes.append(probe)
    return records, probes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("calibrate", "test"), default="calibrate")
    parser.add_argument("--allow-ai-test-diagnostic", action="store_true")
    args = parser.parse_args()
    if args.stage == "test" and not args.allow_ai_test_diagnostic:
        parser.error(
            "Test requires explicit --allow-ai-test-diagnostic; all labels are AI proposals"
        )
    manifest, cases = load_dataset()
    policy_path = ROOT / "evaluation/answerability-policy-v3.json"
    if args.stage == "test" and not policy_path.exists():
        parser.error("Freeze a validation policy before test")
    selected = [c for c in cases if (c["split"] == "test") == (args.stage == "test")]
    policy = json.loads(policy_path.read_text()) if args.stage == "test" else None
    if policy is not None and (
        policy["dataset_sha256"] != manifest["dataset_sha256"]
        or policy["scorer_code_sha256"] != file_hash(ROOT / "releaselens/relevance.py")
    ):
        raise ValueError("Frozen policy provenance mismatch")
    import torch

    torch.set_num_threads(2)
    start = perf_counter()
    encoder, scorer = configured_embedder(), RelevanceScorer()
    if isinstance(encoder, HashEmbedder):
        raise ValueError("Set the pinned learned encoder explicitly; hash reference is separate")
    load_ms = (perf_counter() - start) * 1000
    engine, factory = database("sqlite:///:memory:")
    hash_engine, hash_factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    create_local_schema(hash_engine)
    try:
        with factory.begin() as session, hash_factory.begin() as hash_session:
            start = perf_counter()
            for source in manifest["sources"]:
                ingest_snapshot(session, ROOT / source["manifest"], encoder)
                ingest_snapshot(hash_session, ROOT / source["manifest"], HashEmbedder())
            indexing_ms = (perf_counter() - start) * 1000
            count = session.query(Passage).count()
            # Warm inference/ranking on a fixed dev probe, never a test label.
            probe = next(c for c in cases if c["split"] == "dev")
            hits = rank(
                session,
                Principal("warmup", "reader"),
                probe["project"],
                probe["release"],
                probe["question"],
                encoder,
                "hybrid",
                4,
            )
            scorer.score(probe["question"], [p for p, _, _ in hits])
            records, probes = evaluate(
                selected,
                session,
                encoder,
                scorer,
                hash_session,
                policy["threshold"] if policy else None,
            )
            trials = None
            if args.stage == "calibrate":
                threshold, trials = choose_threshold(
                    [r for r in probes if r["split"] == "validation"]
                )
                policy = {
                    "policy_id": "v3-validation-only",
                    "threshold": threshold,
                    "model": scorer.name,
                    "retrieval_mode": "version",
                    "k": 4,
                    "dataset_sha256": manifest["dataset_sha256"],
                    "scorer_code_sha256": file_hash(ROOT / "releaselens/relevance.py"),
                    "criterion": "Fixed grid; minimize 3*unsupported answers + supported abstentions; tie fewer unsupported then higher threshold",
                    "calibration_split": "validation",
                    "human_reviewed": 0,
                    "production_default": False,
                    "embedding": encoder.name,
                    "backend": "sqlite",
                    "selected_validation_ids": [
                        r["case_id"] for r in probes if r["split"] == "validation"
                    ],
                }
                if policy_path.exists():
                    raise ValueError(
                        "Policy already frozen; preserve it and version any new experiment"
                    )
                policy_path.write_text(json.dumps(policy, indent=2) + "\n")
                # Actual answer path at frozen threshold, reuse already measured rankings only for diagnostics.
                for case, row in zip(selected, probes, strict=True):
                    session.info["relevance_gate"] = RelevanceGate(
                        scorer, threshold, policy["policy_id"]
                    )
                    start = perf_counter()
                    answer = ask(
                        session,
                        Principal("v3-evaluation", case["role"]),
                        AskRequest(
                            project=case["project"],
                            release=case["release"],
                            question=case["question"],
                            save=False,
                        ),
                        encoder,
                    )
                    row.update(
                        {
                            "answered": not bool(answer.abstention_reason),
                            "gated_end_to_end_ms": (perf_counter() - start) * 1000,
                            "exact_citation_validation_passed": True,
                            "selected_passage_count": len(answer.passages),
                            "abstention_reason": answer.abstention_reason,
                        }
                    )
                session.info.pop("relevance_gate", None)
    finally:
        engine.dispose()
        hash_engine.dispose()
    summaries = {}
    for split in sorted({r["split"] for r in probes}):
        rows = [r for r in probes if r["split"] == split]
        summaries[split] = {
            "retrieval": summarize([r for r in records if r["split"] == split]),
            "baseline_answerability": selective_metrics(
                [{**r, "answered": r["baseline_answered"]} for r in rows]
            ),
            "gated_answerability": selective_metrics(rows),
            "answered_top_passage_label_hit_rate": mean(
                r["top_passage_proposed_relevant"] for r in rows if r["answered"]
            )
            if any(r["answered"] for r in rows)
            else None,
            "gated_end_to_end_p50_ms": percentile([r["gated_end_to_end_ms"] for r in rows], 0.5),
            "gated_end_to_end_p95_ms": percentile([r["gated_end_to_end_ms"] for r in rows], 0.95),
        }
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage": args.stage,
        "dataset_sha256": manifest["dataset_sha256"],
        "manifest_sha256": file_hash(ROOT / "evaluation/benchmark-v3-manifest.json"),
        "policy_sha256": file_hash(policy_path),
        "policy": policy,
        "label_status": "AI authored and source-inspected proposals; human-reviewed 0; not independent accuracy",
        "models": {
            "encoder": encoder.name,
            "dimensions": 384,
            "encoder_token_limit": encoder.model.max_seq_length,
            "reranker": scorer.name,
            "reranker_token_limit": 256,
            "activation": "Identity; raw logits; not confidence",
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_cpus": os.cpu_count(),
            "torch_threads": torch.get_num_threads(),
            "torch": torch.__version__,
            "backend": "SQLite BM25 and in-process exact normalized dot products",
            "model_load_ms": load_ms,
            "indexing_ms": indexing_ms,
            "corpus_passages": count,
            "snapshots": len(manifest["sources"]),
        },
        "parameters": {
            "recall_k": 5,
            "ndcg_k": 10,
            "rerank_candidates": 20,
            "rrf_depth": 20,
            "rrf_constant": 60,
            "gate_candidates": 4,
            "gate_selected_extracts": 1,
            "lexical_gate": True,
        },
        "code_sha256": {
            p: file_hash(ROOT / p)
            for p in (
                "scripts/evaluate_v3.py",
                "releaselens/retrieval.py",
                "releaselens/service.py",
                "releaselens/relevance.py",
                "releaselens/sources.py",
            )
        },
        "summaries": summaries,
        "threshold_trials_validation_only": trials,
        "records": records,
        "answer_probes": probes,
        "provider_requests": 0,
        "provider_api_cost_usd": 0,
        "electricity_network_cost_usd": None,
        "answer_correctness": None,
        "semantic_support": None,
        "limits": [
            "Only six document families; bootstrap descriptive, not population bounds.",
            "Labels are sparse proposals and anchor existence is not independent relevance review.",
            "Public docs/pretraining contamination unaudited; topic holdout is procedural and not secret.",
            "Some unsupported questions contain conspicuous impossible guarantees; realistic hard negatives remain needed.",
            "Model input truncation can lose passage tails; no exhaustive relevance judgments.",
            "Gate only limits relevance and selects one extract; completeness and truth remain unmeasured.",
            "One sequential warmed pass per question, rotating mode order; no SLA or capacity inference.",
            "Frozen test is consumed after this run; do not tune on its failures.",
        ],
    }
    output = ROOT / f"evaluation/v3-{args.stage}.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "stage": args.stage,
                "runtime": result["runtime"],
                "policy": policy,
                "summaries": summaries,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
