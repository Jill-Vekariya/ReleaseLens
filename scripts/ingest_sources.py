"""Ingest verified local snapshots without HTTP or arbitrary URL fetching by the API."""

import argparse
from pathlib import Path

from releaselens.db import create_local_schema, database
from releaselens.retrieval import configured_embedder
from releaselens.sources import chunks, ingest_snapshot  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def selected_manifests(root=ROOT, *, expanded=False, challenge=False):
    """Corpus selection is explicit; adding snapshots cannot change the frozen v3 demo."""
    if expanded and challenge:
        raise ValueError("Choose either expanded v3 or challenge sources")
    if challenge:
        from releaselens.challenge import load_challenge

        manifest, _ = load_challenge(root)
    elif expanded:
        from releaselens.review_dataset import load_dataset

        manifest, _ = load_dataset(root)
    else:
        return sorted((root / "data/upstream").glob("*/*/manifest.json"))
    return sorted(root / source["manifest"] for source in manifest["sources"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--expanded",
        action="store_true",
        help="Include the ten additional pinned pages; maintenance window required",
    )
    group.add_argument(
        "--challenge",
        action="store_true",
        help="Include the 19 challenge snapshots in a fresh DB or maintenance window",
    )
    args = parser.parse_args()
    engine, factory = database()
    if engine.dialect.name == "sqlite":
        create_local_schema(engine)
    embedder = configured_embedder()
    manifests = selected_manifests(expanded=args.expanded, challenge=args.challenge)
    if not manifests:
        raise SystemExit("No verified snapshots. Run python scripts/fetch_sources.py first.")
    with factory.begin() as session:
        for manifest in manifests:
            print(ingest_snapshot(session, manifest, embedder))
