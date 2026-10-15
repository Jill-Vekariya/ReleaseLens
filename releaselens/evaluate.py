"""Deterministic development diagnostics. No human-reviewed benchmark claims."""

import argparse
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter

from releaselens.db import create_local_schema, database
from releaselens.fixtures import fixture, seed
from releaselens.ingestion import ingest
from releaselens.retrieval import HashEmbedder, configured_embedder, rank
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask, revalidate

ROOT = Path(__file__).resolve().parents[1]


def percentile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def wilson(successes, n):
    if not n:
        return None
    p, z = successes / n, 1.96
    denominator = 1 + z * z / n
    midpoint = (p + z * z / (2 * n)) / denominator
    halfwidth = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(max(0, midpoint - halfwidth), 4), round(min(1, midpoint + halfwidth), 4)]


def cases():
    result = []
    families = [
        (
            "pydantic",
            "model-configuration",
            [
                "model configuration",
                "configure ConfigDict model_config",
                "inner Config class configuration",
            ],
        ),
        (
            "pydantic",
            "serialization",
            [
                "serialize dictionary model",
                "model_dump dict serialization",
                "dictionary serialization method",
            ],
        ),
        (
            "sqlalchemy",
            "execution",
            [
                "Engine.execute Connection.execute",
                "legacy engine execution",
                "execute engine statement",
            ],
        ),
        (
            "sqlalchemy",
            "transactions",
            [
                "library autocommit transactions",
                "explicit transaction boundaries",
                "autocommit library support",
            ],
        ),
    ]
    for project, key, questions in families:
        releases = ["1.10.15", "2.10.4"] if project == "pydantic" else ["1.4.54", "2.0.36"]
        for release in releases:
            for question in questions:
                result.append(
                    {
                        "id": f"dev-{len(result) + 1:03}",
                        "project": project,
                        "release": release,
                        "question": question,
                        "expected_document": key,
                        "split": "development",
                        "review_status": "AI-authored; not human-reviewed",
                        "label_origin": "synthetic fixture identity; not an LLM judge",
                    }
                )
    return result


def lifecycle_diagnostics():
    results = []
    scenarios = [
        ("unchanged", None, "30", "reviewed_still_valid"),
        (
            "formatting",
            "Synthetic service timeout policy: set request_timeout to 30 seconds.  \r\n",
            "30",
            "reviewed_still_valid",
        ),
        (
            "clarification",
            "Synthetic timeout clarification: request_timeout is 30 seconds.",
            "30",
            "reviewed_still_valid",
        ),
        ("value-60", None, "60", "confirmed_stale"),
        ("value-90", None, "90", "confirmed_stale"),
        ("value-120", None, "120", "confirmed_stale"),
    ]
    for name, changed_text, value, expected in scenarios:
        engine, factory = database("sqlite:///:memory:")
        create_local_schema(engine)
        embedder = HashEmbedder()
        principal = Principal("demo-admin", "admin")
        with factory.begin() as session:
            seed(session, embedder)
            session.info["embedder"] = embedder
            answer = ask(
                session,
                principal,
                AskRequest(project="demo", release="1.0", question="request_timeout", k=1),
                embedder,
            )
            if name != "unchanged":
                passage = answer.passages[0]
                request = fixture(
                    "demo",
                    "1.0",
                    "timeout-policy",
                    changed_text
                    or f"Synthetic service timeout policy: set request_timeout to {value} seconds.",
                    "request_timeout",
                    value,
                )
                request.expected_revision = passage.revision_id
                ingest(session, principal, request, embedder)
            actual = revalidate(session, principal, answer.saved_answer_id)["status"]
            results.append(
                {
                    "scenario": name,
                    "expected": expected,
                    "actual": actual,
                    "correct": expected == actual,
                }
            )
        engine.dispose()
    positives = [r for r in results if r["actual"] == "confirmed_stale"]
    true_positives = sum(r["correct"] for r in positives)
    expected_positives = sum(r["expected"] == "confirmed_stale" for r in results)
    return {
        "cases": results,
        "precision": true_positives / len(positives),
        "recall": true_positives / expected_positives,
        "precision_wilson_95": wilson(true_positives, len(positives)),
        "caveat": "Six curated synthetic cases, not a general staleness benchmark.",
    }


def run(output, embedder=None):
    questions = cases()
    corpus_path = ROOT / "evaluation" / "development.jsonl"
    corpus_path.write_text("\n".join(json.dumps(q) for q in questions) + "\n")
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    embedder, principal = embedder or HashEmbedder(), Principal("evaluator", "reader")
    rows, details = [], []
    with factory.begin() as session:
        seed(session, embedder)
        for mode in ("vector", "hybrid", "rerank", "version"):
            recall, reciprocal, times, wrong = [], [], [], 0
            for case in questions:
                start = perf_counter()
                hits = rank(
                    session,
                    principal,
                    case["project"],
                    case["release"],
                    case["question"],
                    embedder,
                    mode,
                    4,
                    enforce_release=(mode == "version"),
                )
                times.append((perf_counter() - start) * 1000)
                relevant = [
                    i + 1
                    for i, (_, d, _) in enumerate(hits)
                    if d.release == case["release"] and d.key == case["expected_document"]
                ]
                recall.append(bool(relevant))
                reciprocal.append(1 / min(relevant) if relevant else 0)
                wrong += any(d.release != case["release"] for _, d, _ in hits)
                details.append(
                    {
                        "case_id": case["id"],
                        "mode": mode,
                        "relevant_rank": min(relevant) if relevant else None,
                        "retrieved": [{"key": d.key, "release": d.release} for _, d, _ in hits],
                    }
                )
            rows.append(
                {
                    "mode": mode,
                    "queries": len(questions),
                    "k": 4,
                    "recall_at_4": mean(recall),
                    "recall_wilson_95": wilson(sum(recall), len(recall)),
                    "mrr": mean(reciprocal),
                    "wrong_release_queries": wrong,
                    "p50_ms": percentile(times, 0.5),
                    "p95_ms": percentile(times, 0.95),
                }
            )
        security_trials = []
        for role in ("reader", "engineer"):
            for mode in ("vector", "hybrid", "rerank", "version"):
                hits = rank(
                    session,
                    Principal("probe", role),
                    "demo",
                    "1.0",
                    "CANARY-ORCHID-7814",
                    embedder,
                    mode,
                    10,
                )
                security_trials.append(any(d.classification == "restricted" for _, d, _ in hits))
        payloads = [
            ask(
                session,
                principal,
                AskRequest(
                    project=q["project"],
                    release=q["release"],
                    question=q["question"],
                    k=1,
                    save=False,
                ),
                embedder,
            )
            for q in questions
        ]
        unanswerable = ["zyzzyva teleportation qubits", "neutrino superconductivity"]
        abstentions = [
            ask(
                session,
                principal,
                AskRequest(project="pydantic", release="1.10.15", question=q, save=False),
                embedder,
            ).abstention_reason
            is not None
            for q in unanswerable
        ]
    engine.dispose()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "scope": "24 synthetic development questions; no held-out test evaluation. Encoder: "
        + embedder.name,
        "dataset_review_status": "NOT HUMAN-REVIEWED",
        "embedding": embedder.name,
        "generator": "deterministic exact extracts",
        "provider_cost_usd": 0,
        "dataset_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "baselines": rows,
        "citation_exact_membership_rate": sum(bool(p.claims) for p in payloads) / len(payloads),
        "citation_support_semantics": "Exact membership only; semantic relevance/completeness unmeasured",
        "answer_coverage": sum(not p.abstention_reason for p in payloads) / len(payloads),
        "accuracy_conditional_on_answering": None,
        "version_correct_answer_rate": None,
        "answer_accuracy_status": "Pending independent human review",
        "unanswerable_cases": len(unanswerable),
        "unanswerable_abstentions": sum(abstentions),
        "abstention_precision": None,
        "abstention_note": "Two trivial vocabulary probes do not establish precision",
        "unauthorized_retrieval_trials": len(security_trials),
        "unauthorized_retrieval_rate": sum(security_trials) / len(security_trials),
        "unauthorized_retrieval_wilson_95": wilson(sum(security_trials), len(security_trials)),
        "change_intelligence": lifecycle_diagnostics(),
        "limitations": "Tiny AI-authored synthetic suite, no LLM or human relevance review. Small differences and timings are diagnostic only. Lifecycle diagnostics use the deterministic hash encoder independently of the retrieval encoder. No component-benefit claim is justified.",
        "per_query": details,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "per_query"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--configured-encoder",
        action="store_true",
        help="Use the pinned encoder configured in environment",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation" / "results.json")
    args = parser.parse_args()
    run(args.output, configured_embedder() if args.configured_encoder else None)
