import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from releaselens.models import Document, Passage

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "source_ingestion", ROOT / "scripts" / "ingest_sources.py"
)
source_ingestion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_ingestion)


def test_verified_upstream_snapshots_ingest_idempotently(client):
    manifests = sorted((ROOT / "data" / "upstream").glob("*/*/manifest.json"))
    assert len(manifests) == 4
    with client.app.state.factory.begin() as session:
        for manifest in manifests:
            result = source_ingestion.ingest_snapshot(session, manifest, client.app.state.embedder)
            assert result["kind"] == "created"
            result = source_ingestion.ingest_snapshot(session, manifest, client.app.state.embedder)
            assert result["kind"] == "identical"
        assert session.scalar(select(func.count()).select_from(Passage)) > 100


def test_checksum_tampering_is_rejected(client, tmp_path):
    manifest_path = next((ROOT / "data" / "upstream").glob("*/*/manifest.json"))
    manifest = json.loads(manifest_path.read_text())
    (tmp_path / "source.txt").write_text("Tampered documentation")
    (tmp_path / "LICENSE").write_bytes((manifest_path.parent / "LICENSE").read_bytes())
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with client.app.state.factory.begin() as session:
        with pytest.raises(ValueError, match="checksum mismatch"):
            source_ingestion.ingest_snapshot(
                session, tmp_path / "manifest.json", client.app.state.embedder
            )


def test_restart_does_not_overwrite_updated_fixture(client, admin):
    from test_lifecycle import update

    from releaselens.fixtures import seed

    update(client, admin, "60")
    with client.app.state.factory.begin() as session:
        doc = session.scalar(select(Document).where(Document.key == "timeout-policy"))
        head = doc.current_revision
        seed(session, client.app.state.embedder)
        assert doc.current_revision == head
