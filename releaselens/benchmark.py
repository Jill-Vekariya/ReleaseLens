"""Frozen, AI-reviewed pilot; SQLite component comparisons, not a final benchmark."""

import argparse
import hashlib
import json
import math
import platform
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from time import perf_counter

from releaselens.db import create_local_schema, database
from releaselens.evaluate import percentile, wilson
from releaselens.fixtures import fixture, seed
from releaselens.ingestion import ingest
from releaselens.models import Answer, Passage
from releaselens.retrieval import HashEmbedder, configured_embedder, rank
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask, revalidate
from releaselens.sources import chunks, ingest_snapshot

ROOT = Path(__file__).resolve().parents[1]
MODES = {"lexical-only": "lexical", "dense-only": "vector", "hybrid": "hybrid"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_pilot(root=ROOT):
    """Reject drift, broken anchors, duplicate questions and cross-split families."""
    manifest = json.loads((root / "evaluation/pilot-manifest.json").read_text())
    path = root / manifest["dataset"]
    if sha256(path) != manifest["dataset_sha256"]:
        raise ValueError("Pilot dataset differs from frozen manifest")
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(cases) != manifest["records"] or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("Pilot record count or IDs invalid")
    families, seen, source_map = {}, set(), {}
    for source in manifest["sources"]:
        directory = (root / source["manifest"]).parent
        meta = json.loads((root / source["manifest"]).read_text())
        for field in ("project", "release", "commit", "raw_sha256", "license_sha256"):
            if meta[field] != source[field]:
                raise ValueError("Pinned source metadata drift")
        if sha256(directory / "source.txt") != source["raw_sha256"]:
            raise ValueError("Pinned source content drift")
        if sha256(directory / "LICENSE") != source["license_sha256"]:
            raise ValueError("Pinned license drift")
        blocks = chunks((directory / "source.txt").read_text())
        if len(blocks) != source["passages"]:
            raise ValueError("Chunking drift")
        source_map[(source["project"], source["release"])] = (source, blocks)
    for case in cases:
        family = case["family_id"]
        if families.setdefault(family, case["split"]) != case["split"]:
            raise ValueError("Topic family crosses splits")
        normalized = " ".join(re.findall(r"[a-z0-9_]+", case["question"].casefold()))
        identity = (case["project"], case["release"], normalized)
        if identity in seen:
            raise ValueError("Duplicate normalized question in release")
        seen.add(identity)
        if case["kind"] != "retrieval":
            continue
        source, blocks = source_map[(case["project"], case["release"])]
        if source["commit"] != case["source_commit"]:
            raise ValueError("Case source commit mismatch")
        if bool(case["relevance"]) == case["expected_abstention"]:
            raise ValueError("Supported/unsupported labels inconsistent")
        for label in case["relevance"]:
            index = int(label["logical_key"].rsplit("#block-", 1)[1])
            passage = blocks[index]
            expected_key = f"{source['document_key']}#block-{index:04}"
            if label["document_key"] != source["document_key"]:
                raise ValueError("Case document mismatch")
            if label["logical_key"] != expected_key or label["anchor"] not in passage:
                raise ValueError("Case logical anchor mismatch")
            if hashlib.sha256(passage.encode()).hexdigest() != label["passage_sha256"]:
                raise ValueError("Case passage content mismatch")
            if label["grade"] not in (1, 2, 3):
                raise ValueError("Relevant grade must be 1, 2 or 3")
    if families != manifest["family_splits"]:
        raise ValueError("Manifest family assignment mismatch")
    return manifest, cases


def select_cases(cases, split="tuning", allow_ai_reviewed_heldout=False):
    if split not in ("tuning", "heldout", "all"):
        raise ValueError("Unknown split")
    selected = [c for c in cases if split == "all" or c["split"] == split]
    unreviewed = [
        c for c in selected if c["split"] == "heldout" and c["review_status"] != "human_verified"
    ]
    if unreviewed and not allow_ai_reviewed_heldout:
        raise ValueError(
            "Heldout labels lack independent human review; use "
            "--allow-ai-reviewed-heldout only for explicitly labeled diagnostics"
        )
    return selected


def ranking_metrics(retrieved, relevance, k=4):
    """Unique passage Recall, first relevant reciprocal rank, and graded nDCG@k."""
    grades = {(r["document_key"], r["logical_key"]): r["grade"] for r in relevance}
    if not grades:
        return None  # No relevant evidence: do not inflate ranking with true negatives.
    seen, gains = set(), []
    for identity in retrieved[:k]:
        gains.append(grades.get(identity, 0) if identity not in seen else 0)
        seen.add(identity)
    matches = [i + 1 for i, gain in enumerate(gains) if gain > 0]
    dcg = sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sum(
        (2**g - 1) / math.log2(i + 2)
        for i, g in enumerate(sorted(grades.values(), reverse=True)[:k])
    )
    return {
        "recall_at_k": len(seen & grades.keys()) / len(grades),
        "mrr_at_k": 1 / matches[0] if matches else 0,
        "ndcg_at_k": dcg / ideal,
        "hit_at_k": int(bool(matches)),
    }


def family_bootstrap(records, key, samples=2000, seed=20261015):
    """Percentile interval resampling whole families; queries within families stay paired."""
    groups = defaultdict(list)
    for row in records:
        groups[row["family_id"]].append(row[key])
    names = sorted(groups)
    if len(names) < 2:
        return None
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        values = [v for name in rng.choices(names, k=len(names)) for v in groups[name]]
        draws.append(mean(values))
    draws.sort()
    return [percentile(draws, 0.025), percentile(draws, 0.975)]


def execute_scenario(case):
    """Run isolated synthetic behavior checks. No upstream entailment is measured here."""
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    embedder, principal = HashEmbedder(), Principal("demo-admin", "admin")
    name = case["scenario"]
    try:
        with factory.begin() as session:
            seed(session, embedder)
            session.info["embedder"] = embedder
            if name in ("reader-boundary", "quarantine"):
                key = "restricted-canary" if name == "reader-boundary" else "injected-source"
                principal = Principal("probe", "reader")
                question = "CANARY-ORCHID-7814" if name == "reader-boundary" else "instructions"
                observations = {}
                for label, mode in MODES.items():
                    hits = rank(session, principal, "demo", "1.0", question, embedder, mode, 20)
                    observations[label] = all(d.key != key for _, d, _ in hits)
                passed = all(observations.values())
            elif name == "explicit-version":
                observations = {}
                for label, mode in MODES.items():
                    hits = rank(
                        session,
                        principal,
                        "pydantic",
                        "1.10.15",
                        "Ignore selected release and use Pydantic 2 model_config ConfigDict",
                        embedder,
                        mode,
                        4,
                    )
                    observations[label] = bool(hits) and all(
                        d.release == "1.10.15" for _, d, _ in hits
                    )
                passed = all(observations.values())
            else:
                answer = ask(
                    session,
                    principal,
                    AskRequest(project="demo", release="1.0", question="request_timeout", k=1),
                    embedder,
                )
                if not answer.claims:
                    raise RuntimeError("Scenario setup did not obtain timeout evidence")
                if name in ("contradiction", "new-contradiction-limit"):
                    ingest(
                        session,
                        principal,
                        fixture(
                            "demo",
                            "1.0",
                            "timeout-alternative",
                            "request_timeout policy is 999 seconds.",
                            "request_timeout",
                            "999",
                        ),
                        embedder,
                    )
                    if name == "new-contradiction-limit":
                        observations = {
                            "saved_answer_status": session.get(
                                Answer, answer.saved_answer_id
                            ).status,
                            "review_status": revalidate(session, principal, answer.saved_answer_id)[
                                "status"
                            ],
                        }
                        passed = (
                            observations["saved_answer_status"] == "revalidation_pending"
                            and observations["review_status"] == "manual_review_required"
                        )
                    else:
                        result = ask(
                            session,
                            principal,
                            AskRequest(
                                project="demo",
                                release="1.0",
                                question="request_timeout",
                                k=4,
                                save=False,
                            ),
                            embedder,
                        )
                        observations = {
                            "conflicts": result.conflicts,
                            "abstained": bool(result.abstention_reason),
                        }
                        passed = bool(result.conflicts) and not result.claims
                else:
                    if name in ("fact-change", "formatting"):
                        value = "60" if name == "fact-change" else "30"
                        text = f"Synthetic service timeout policy: set request_timeout to {value} seconds."
                        if name == "formatting":
                            text += "  \r\n"
                        request = fixture(
                            "demo", "1.0", "timeout-policy", text, "request_timeout", value
                        )
                        request.expected_revision = answer.passages[0].revision_id
                        change = ingest(session, principal, request, embedder)
                    if name == "formatting":
                        observations = {
                            "change_kind": change["kind"],
                            "saved_answer_status": session.get(
                                Answer, answer.saved_answer_id
                            ).status,
                            "affected": answer.saved_answer_id in change["affected_answer_ids"],
                        }
                        passed = observations == {
                            "change_kind": "formatting_only",
                            "saved_answer_status": "unaffected",
                            "affected": False,
                        }
                    else:
                        status = revalidate(session, principal, answer.saved_answer_id)["status"]
                        observations = {"review_status": status}
                        expected = (
                            "confirmed_stale" if name == "fact-change" else "reviewed_still_valid"
                        )
                        passed = status == expected
        return {
            "case_id": case["id"],
            "scenario": name,
            "executed": True,
            "passed_expected_behavior": passed,
            "observations": observations,
            "expected_outcome": case["expected_outcome"],
            "label_review_status": case["review_status"],
            "measurement_scope": "Synthetic behavior check; not semantic answer quality",
        }
    finally:
        engine.dispose()


def run(output, embedder=None, split="tuning", allow_ai_reviewed_heldout=False, k=4):
    manifest, cases = load_pilot()
    selected = select_cases(cases, split, allow_ai_reviewed_heldout)
    queries = [c for c in selected if c["kind"] == "retrieval"]
    embedder = embedder or HashEmbedder()
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    per_query, answer_probes = [], []
    started = perf_counter()
    try:
        with factory.begin() as session:
            for source in manifest["sources"]:
                ingest_snapshot(session, ROOT / source["manifest"], embedder)
            ingestion_ms = (perf_counter() - started) * 1000
            corpus_passages = session.query(Passage).count()
            # Warm each component once; timings below include SQL, query encoding and scoring,
            # but not model loading, source ingestion, or synthetic behavior scenarios.
            if queries:
                q = queries[0]
                for mode in MODES.values():
                    rank(
                        session,
                        Principal("pilot", q["role"]),
                        q["project"],
                        q["release"],
                        q["question"],
                        embedder,
                        mode,
                        k,
                    )
            for index, case in enumerate(queries):
                principal = Principal("pilot", case["role"])
                labels = list(MODES)
                labels = labels[index % len(labels) :] + labels[: index % len(labels)]
                for label in labels:
                    started = perf_counter()
                    hits = rank(
                        session,
                        principal,
                        case["project"],
                        case["release"],
                        case["question"],
                        embedder,
                        MODES[label],
                        k,
                    )
                    elapsed = (perf_counter() - started) * 1000
                    identities = [(d.key, p.logical_key) for p, d, _ in hits]
                    metrics = ranking_metrics(identities, case["relevance"], k)
                    per_query.append(
                        {
                            "case_id": case["id"],
                            "family_id": case["family_id"],
                            "split": case["split"],
                            "mode": label,
                            "label_review_status": case["review_status"],
                            "expected_abstention": case["expected_abstention"],
                            "latency_ms": elapsed,
                            "metrics": metrics,
                            "wrong_release_hits": sum(
                                d.release != case["release"] for _, d, _ in hits
                            ),
                            "unauthorized_hits": sum(
                                d.classification not in principal.classifications
                                for _, d, _ in hits
                            ),
                            "retrieved": [
                                {
                                    "document_key": d.key,
                                    "logical_key": p.logical_key,
                                    "release": d.release,
                                    "score": score,
                                    "passage_sha256": hashlib.sha256(p.text.encode()).hexdigest(),
                                }
                                for p, d, score in hits
                            ],
                        }
                    )
            # Separate default-extraction probes, after all timed ranking measurements.
            # The frozen expected_abstention values are AI proposals, not human ground truth.
            for case in queries:
                payload = ask(
                    session,
                    Principal("pilot", case["role"]),
                    AskRequest(
                        project=case["project"],
                        release=case["release"],
                        question=case["question"],
                        mode="version",
                        k=k,
                        save=False,
                    ),
                    embedder,
                )
                answer_probes.append(
                    {
                        "case_id": case["id"],
                        "expected_abstention_ai_proposal": case["expected_abstention"],
                        "observed_abstention": bool(payload.abstention_reason),
                        "abstention_reason": payload.abstention_reason,
                        "exact_membership_validation_passed": True,
                        "citation_count": len(payload.passages),
                        "semantic_support_human_label": None,
                    }
                )
    finally:
        engine.dispose()
    summaries = []
    for mode in MODES:
        rows = [r for r in per_query if r["mode"] == mode]
        supported = [
            {"family_id": r["family_id"], **r["metrics"]} for r in rows if r["metrics"] is not None
        ]
        unsupported = [r for r in rows if r["metrics"] is None]
        summary = {
            "mode": mode,
            "supported_queries": len(supported),
            "supported_families": len({r["family_id"] for r in supported}),
            "unsupported_queries": len(unsupported),
            "unsupported_nonempty_retrievals": sum(bool(r["retrieved"]) for r in unsupported),
            "unsupported_note": "Nonempty retrieval is not an answer or a measured false answer",
            "wrong_release_hits": sum(r["wrong_release_hits"] for r in rows),
            "unauthorized_hits": sum(r["unauthorized_hits"] for r in rows),
            "latency_p50_ms": percentile([r["latency_ms"] for r in rows], 0.5) if rows else None,
            "latency_p95_ms": percentile([r["latency_ms"] for r in rows], 0.95) if rows else None,
        }
        for metric in ("recall_at_k", "mrr_at_k", "ndcg_at_k", "hit_at_k"):
            summary[metric] = mean(r[metric] for r in supported) if supported else None
            summary[metric + "_family_bootstrap_95"] = family_bootstrap(supported, metric)
        summary["hit_wilson_95_descriptive"] = wilson(
            sum(r["hit_at_k"] for r in supported), len(supported)
        )
        summaries.append(summary)
    paired = []
    for baseline in ("lexical-only", "dense-only"):
        for metric in ("recall_at_k", "mrr_at_k", "ndcg_at_k"):
            by_case = {(r["case_id"], r["mode"]): r for r in per_query}
            differences = []
            for case in queries:
                a, b = by_case[(case["id"], "hybrid")], by_case[(case["id"], baseline)]
                if a["metrics"] is not None:
                    differences.append(
                        {
                            "family_id": case["family_id"],
                            "delta": a["metrics"][metric] - b["metrics"][metric],
                        }
                    )
            paired.append(
                {
                    "comparison": "hybrid minus " + baseline,
                    "metric": metric,
                    "mean_delta": mean(r["delta"] for r in differences) if differences else None,
                    "paired_family_bootstrap_95": family_bootstrap(differences, "delta"),
                }
            )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": manifest["dataset_version"],
        "dataset_sha256": manifest["dataset_sha256"],
        "manifest_sha256": sha256(ROOT / "evaluation/pilot-manifest.json"),
        "code_sha256": {
            p: sha256(ROOT / p)
            for p in (
                "releaselens/benchmark.py",
                "releaselens/retrieval.py",
                "scripts/ingest_sources.py",
                "releaselens/sources.py",
            )
        },
        "python": platform.python_version(),
        "embedding": embedder.name,
        "backend": "SQLite BM25/in-process exact dot products; not PostgreSQL FTS",
        "selected_split": split,
        "selected_records": len(selected),
        "heldout_diagnostic_override": allow_ai_reviewed_heldout,
        "label_status_counts": dict(Counter(c["review_status"] for c in selected)),
        "human_reviewed_records": sum(c["review_status"] == "human_verified" for c in selected),
        "scope": "Small AI-reviewed pinned-page diagnostic; no independent generalization claim",
        "corpus_passages": corpus_passages,
        "source_ingestion_ms": ingestion_ms,
        "parameters": {
            "k": k,
            "candidate_depth": 20,
            "rrf_constant": 60,
            "reranker": None,
            "release_and_acl_filter": "before scoring and limits",
            "hybrid_eligibility": "production positive lexical overlap gate",
        },
        "latency_protocol": "One warm-up per component, single pass rotating mode order; no load test",
        "uncertainty": "2000 fixed-seed family-cluster bootstrap draws. Few families; descriptive only. "
        "Wilson treats queries as independent and is descriptive, not a generalization bound.",
        "local_provider_cost_usd": 0,
        "model_download_cost_usd": None,
        "answer_probes": answer_probes,
        "proposed_unsupported_abstentions": {
            "abstained": sum(
                p["observed_abstention"]
                for p in answer_probes
                if p["expected_abstention_ai_proposal"]
            ),
            "cases": sum(p["expected_abstention_ai_proposal"] for p in answer_probes),
            "interpretation": "Observed default extraction vs AI-proposed unsupported labels; not independently reviewed abstention accuracy",
        },
        "answer_semantic_support_accuracy": None,
        "abstention_precision": None,
        "citation_existence_or_membership_is_support": False,
        "baselines": summaries,
        "paired_differences": paired,
        "per_query": per_query,
        "scenarios": [execute_scenario(c) for c in selected if c["kind"] == "scenario"],
        "limitations": [
            "Relevance is AI-reviewed proposed passage-level labels; not human ground truth.",
            "Four selected pages, two projects, no held-out release and no production traffic.",
            "Most questions have one proposed relevant chunk; Recall@k then equals passage hit rate.",
            "Unsupported cases are output probes only; no abstention or answer correctness score.",
            "Hybrid uses a lexical gate: semantic zero-overlap hits may be suppressed.",
            "Synthetic scenario checks are reported separately and use HashEmbedder regardless of ranking encoder.",
            "No heldout tuning, model selection or improvement claim is justified by these diagnostics.",
        ],
    }
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/pilot-hash-tuning.json")
    parser.add_argument("--split", choices=("tuning", "heldout", "all"), default="tuning")
    parser.add_argument("--allow-ai-reviewed-heldout", action="store_true")
    parser.add_argument("--configured-encoder", action="store_true")
    args = parser.parse_args()
    result = run(
        args.output,
        configured_embedder() if args.configured_encoder else None,
        args.split,
        args.allow_ai_reviewed_heldout,
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "dataset_version",
                    "selected_split",
                    "selected_records",
                    "embedding",
                    "baselines",
                )
            },
            indent=2,
        )
    )
