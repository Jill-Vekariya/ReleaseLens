"""Real pinned prose excerpt replays; review candidates, not stale-answer truth labels."""

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from releaselens.db import create_local_schema, database
from releaselens.fixtures import fixture
from releaselens.ingestion import ingest
from releaselens.models import Answer
from releaselens.retrieval import HashEmbedder
from releaselens.review_dataset import ROOT, load_dataset
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask, revalidate

SPECS = [
    (
        "pydantic/2.10.4/models",
        "Pydantic may cast input data",
        "does not do any validation",
        "Does model validation validate input data?",
        True,
    ),
    (
        "pydantic/2.10.4/validators",
        "run after Pydantic",
        "terminate validation immediately",
        "Do validators perform internal validation after returning?",
        True,
    ),
    (
        "sqlalchemy/2.0.36",
        "Engine.begin",
        "DBAPI-level autocommit",
        "Does a connection commit a transaction automatically?",
        True,
    ),
]


def paragraph(raw, anchor):
    matches = [p for p in raw.split("\n\n") if anchor.casefold() in p.casefold()]
    if not matches:
        raise ValueError("Missing source anchor: " + anchor)
    return matches[0]


def run(output=None):
    output = (
        Path(output)
        if output
        else ROOT
        / "evaluation"
        / "local"
        / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-prose-impact.json")
    )
    if output.exists():
        raise FileExistsError(f"Evidence already exists: {output}. Choose a new output path.")
    output.parent.mkdir(parents=True, exist_ok=True)
    load_dataset()  # verify all source and license hashes before using excerpts
    outputs = []
    for identity, old_anchor, new_anchor, question, _ in SPECS:
        folder = ROOT / "data/upstream" / identity
        meta = json.loads((folder / "manifest.json").read_text())
        raw = (folder / "source.txt").read_bytes().decode()
        old, new = paragraph(raw, old_anchor), paragraph(raw, new_anchor)
        # These replays change ingestion order, not upstream history; no real stale claim.
        for variant in ("related_addition", "agreeing_duplicate", "unrelated", "restricted"):
            engine, factory = database("sqlite:///:memory:")
            create_local_schema(engine)
            try:
                with factory.begin() as session:
                    encoder, admin = HashEmbedder(), Principal("replay-admin", "admin")
                    session.info["embedder"] = encoder
                    session.info["prose_review_candidates"] = True

                    def request(key, text, classification="public", meta=meta):
                        req = fixture(
                            meta["project"],
                            meta["release"],
                            key,
                            text,
                            classification=classification,
                        )
                        req.source_type, req.upstream_commit = "upstream", meta["commit"]
                        req.source_url, req.license, req.attribution = (
                            meta["canonical_url"],
                            meta["license"],
                            meta["attribution"],
                        )
                        return req

                    ingest(session, admin, request("excerpt-original", old), encoder)
                    payload = ask(
                        session,
                        admin,
                        AskRequest(
                            project=meta["project"], release=meta["release"], question=question, k=1
                        ),
                        encoder,
                    )
                    assert not payload.abstention_reason
                    original = copy.deepcopy(payload.model_dump())
                    before = revalidate(session, admin, payload.saved_answer_id)
                    text = (
                        old
                        if variant == "agreeing_duplicate"
                        else "A connection pool retains database network sockets."
                        if variant == "unrelated"
                        else new
                    )
                    ingest(
                        session,
                        admin,
                        request(
                            "excerpt-added",
                            text,
                            "restricted" if variant == "restricted" else "public",
                        ),
                        encoder,
                    )
                    observed = (
                        session.get(Answer, payload.saved_answer_id).status
                        == "revalidation_pending"
                    )
                    review = revalidate(session, admin, payload.saved_answer_id)
                    assert session.get(Answer, payload.saved_answer_id).payload == original
                    assert review["status"] != "confirmed_stale"
                    outputs.append(
                        {
                            "case_id": f"prose-{len(outputs) + 1:02}",
                            "source_manifest": str((folder / "manifest.json").relative_to(ROOT)),
                            "release": meta["release"],
                            "question": question,
                            "variant": variant,
                            "original_quote": old,
                            "added_quote": text,
                            "original_quote_sha256": hashlib.sha256(old.encode()).hexdigest(),
                            "added_quote_sha256": hashlib.sha256(text.encode()).hexdigest(),
                            "expected_review_candidate_ai_proposal": variant == "related_addition",
                            "observed_review_candidate": observed,
                            "review_status": review["status"],
                            "review_fingerprint_changed": review["review_id"]
                            != before["review_id"],
                            "original_preserved": True,
                            "confirmed_stale": False,
                            "label_status": "ai_source_inspected_proposal",
                            "human_reviewed": False,
                        }
                    )
            finally:
                engine.dispose()
    tp = sum(
        r["observed_review_candidate"] and r["expected_review_candidate_ai_proposal"]
        for r in outputs
    )
    fp = sum(
        r["observed_review_candidate"] and not r["expected_review_candidate_ai_proposal"]
        for r in outputs
    )
    fn = sum(
        not r["observed_review_candidate"] and r["expected_review_candidate_ai_proposal"]
        for r in outputs
    )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": len(outputs),
        "source_families": 3,
        "human_reviewed": 0,
        "review_candidate_precision_ai_proposal": tp / (tp + fp) if tp + fp else None,
        "review_candidate_recall_ai_proposal": tp / (tp + fn) if tp + fn else None,
        "true_positives": tp,
        "false_alarms": fp,
        "missed_review_candidates": fn,
        "confirmed_stale_precision": None,
        "confirmed_stale_recall": None,
        "scope": "Offline ingestion-order replay of exact licensed same-release prose excerpts, not historical upstream change accuracy; agreeing duplicate labeled no review to expose false alarms",
        "limits": [
            "Only three source families; hand-picked AI proposals, not independent evaluation.",
            "New prose can be compatible contextual nuance rather than a contradiction.",
            "Lexical rule misses paraphrases and flags agreements; no semantic stale classification.",
        ],
        "records": outputs,
    }
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New output path; existing files are refused")
    run(parser.parse_args().output)
