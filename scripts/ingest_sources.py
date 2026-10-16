"""Ingest verified local snapshots without HTTP or arbitrary URL fetching by the API."""

import argparse
from pathlib import Path

from releaselens.db import create_local_schema, database
from releaselens.retrieval import configured_embedder
from releaselens.sources import chunks, ingest_snapshot  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expanded",
        action="store_true",
        help="Include the ten additional pinned pages; maintenance window required",
    )
    args = parser.parse_args()
    engine, factory = database()
    if engine.dialect.name == "sqlite":
        create_local_schema(engine)
    embedder = configured_embedder()
    manifests = sorted(
        (ROOT / "data" / "upstream").glob(
            "**/manifest.json" if args.expanded else "*/*/manifest.json"
        )
    )
    if not manifests:
        raise SystemExit("No verified snapshots. Run python scripts/fetch_sources.py first.")
    with factory.begin() as session:
        for manifest in manifests:
            print(ingest_snapshot(session, manifest, embedder))
