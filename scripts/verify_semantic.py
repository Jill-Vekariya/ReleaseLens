"""Verify a pinned CPU encoder against real snapshots and controlled diagnostics."""

import importlib.metadata
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from releaselens.db import create_local_schema, database
from releaselens.evaluate import run as evaluate
from releaselens.retrieval import HashEmbedder, configured_embedder
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask

ROOT = Path(__file__).resolve().parents[1]


def run():
    embedder = configured_embedder()
    if isinstance(embedder, HashEmbedder):
        raise RuntimeError("Set the model name and immutable revision before semantic verification")
    engine, factory = database("sqlite:///:memory:")
    create_local_schema(engine)
    spec = importlib.util.spec_from_file_location(
        "source_ingestion", ROOT / "scripts" / "ingest_sources.py"
    )
    ingestion = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ingestion)
    with factory.begin() as session:
        for manifest in sorted((ROOT / "data" / "upstream").glob("*/*/manifest.json")):
            ingestion.ingest_snapshot(session, manifest, embedder)
        current = ask(
            session,
            Principal("semantic-evaluator", "reader"),
            AskRequest(
                project="pydantic", release="2.10.4", question="str_max_length", k=2, save=False
            ),
            embedder,
        )
        assert current.claims and all(
            p.release == "2.10.4" and p.source_type == "upstream" for p in current.passages
        )
        historical = ask(
            session,
            Principal("semantic-evaluator", "reader"),
            AskRequest(
                project="pydantic",
                release="1.10.15",
                question="model configuration",
                k=2,
                save=False,
            ),
            embedder,
        )
        assert historical.passages and all(p.release == "1.10.15" for p in historical.passages)
    evaluate(ROOT / "evaluation" / "semantic-results.json", embedder)
    version = importlib.metadata.version("sentence-transformers")
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "encoder": embedder.name,
        "dimensions": 384,
        "sentence_transformers_version": version,
        "torch_version": importlib.metadata.version("torch"),
        "model_license": "Apache-2.0 (upstream model card)",
        "model_card": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
        "checks": [
            "four pinned upstream snapshots embedded and ingested",
            "current-release exact citations",
            "historical-release isolation",
            "24-case controlled retrieval diagnostic",
        ],
        "limitations": "Execution verified; independent human relevance/accuracy review and held-out generalization remain pending. The corpus is small and lexical overlap remains a conservative gate in hybrid/version modes.",
    }
    (ROOT / "evaluation" / "semantic-verification.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, indent=2))
    engine.dispose()


if __name__ == "__main__":
    run()
