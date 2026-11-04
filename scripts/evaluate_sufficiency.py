"""Bounded offline sufficiency review packet. No LLM, downloads or label promotion."""

import argparse
import json
from pathlib import Path

from releaselens.db import create_local_schema, database
from releaselens.fixtures import fixture
from releaselens.ingestion import ingest
from releaselens.retrieval import HashEmbedder
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask, validate_citations
from releaselens.sufficiency import packet, summarize

CASES = [
    {
        "id": "direct",
        "question": "Which function exports a dictionary?",
        "release": "1",
        "required_aspects": ["dictionary export function"],
    },
    {
        "id": "missing-measurement",
        "question": "What is the dictionary export latency at 1000 requests per second?",
        "release": "1",
        "required_aspects": ["measured latency", "1000 requests per second workload"],
    },
    {
        "id": "partial",
        "question": "Which function exports a dictionary and how much memory does it require?",
        "release": "1",
        "required_aspects": ["dictionary export function", "measured memory requirement"],
    },
    {
        "id": "wrong-release",
        "question": "What does the parallel_export function do?",
        "release": "1",
        "required_aspects": ["parallel_export in release 1"],
    },
    {
        "id": "access-boundary",
        "question": "What is the secret_internal_export quota?",
        "release": "1",
        "required_aspects": ["authorized secret_internal_export quota"],
    },
    {
        "id": "unsupported",
        "question": "What is the Martian gravity constant?",
        "release": "1",
        "required_aspects": ["Martian gravity measurement"],
    },
]


def run(output, reviews=None):
    output.mkdir(parents=True, exist_ok=False)
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    embedder = HashEmbedder()
    packets, checks = [], []
    try:
        with factory.begin() as session:
            for record in [
                fixture(
                    "fixture", "1", "export", "The dictionary export function is export_dict()."
                ),
                fixture(
                    "fixture",
                    "2",
                    "parallel",
                    "parallel_export performs concurrent dictionary export.",
                ),
                fixture(
                    "fixture",
                    "1",
                    "private",
                    "secret_internal_export quota is 700.",
                    classification="restricted",
                ),
            ]:
                ingest(session, Principal("fixture-author", "admin"), record, embedder)
            for case in CASES:
                principal = Principal("offline-reader", "reader")
                payload = ask(
                    session,
                    principal,
                    AskRequest(
                        project="fixture",
                        release=case["release"],
                        question=case["question"],
                        save=False,
                    ),
                    embedder,
                )
                validate_citations(session, principal, payload)
                assert all(c.release == case["release"] for c in payload.passages)
                assert not any(
                    "secret_internal_export quota is 700" in c.quote for c in payload.passages
                )
                packets.append(packet(case, payload))
                checks.append(
                    {
                        "case_id": case["id"],
                        "citation_valid": True,
                        "answered": not bool(payload.abstention_reason),
                        "abstention_reason": payload.abstention_reason,
                        "reviewed_sufficiency": "UNVERIFIED",
                    }
                )
    finally:
        engine.dispose()
    result = {
        "mechanical_checks": checks,
        "semantic_review": summarize(packets, reviews or []),
        "protocol": {
            "dataset": "six AI-authored development-exposed synthetic cases",
            "sample_size": "Bounded mechanism check, not general model-quality estimation",
            "selection": "Cases predefined in source; no successful-case filtering",
            "live_provider_calls": 0,
            "limitations": "Exact citations prove extractive grounding, not completeness.",
        },
    }
    (output / "review-packet.json").write_text(json.dumps(packets, indent=2))
    (output / "results.json").write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument(
        "--packet", type=Path, help="Existing packet to which human reviews are bound"
    )
    args = parser.parse_args()
    if args.reviews:
        if not args.packet:
            parser.error(
                "--reviews requires the original --packet; regenerating changes evidence IDs"
            )
        result = summarize(
            json.loads(args.packet.read_text()), json.loads(args.reviews.read_text())
        )
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "review-results.json").write_text(json.dumps(result, indent=2))
    else:
        result = run(args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
