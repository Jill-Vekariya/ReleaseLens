"""Checksum-verified snapshots and deterministic paragraph chunking."""

import hashlib
import json
import re

from releaselens.ingestion import ingest
from releaselens.schemas import IngestRequest
from releaselens.security import Principal


def chunks(raw):
    """Bounded paragraph packing; ordinal keys conservatively require review on movement."""
    result, block = [], ""
    for paragraph in raw.split("\n\n"):
        if len(block) + len(paragraph) > 1300 and block:
            result.append(block)
            block = ""
        for offset in range(0, len(paragraph), 1300):
            fragment = paragraph[offset : offset + 1300]
            if block and len(block) + len(fragment) > 1300:
                result.append(block)
                block = ""
            block += fragment + "\n\n"
    if block:
        result.append(block)
    return result


def ingest_snapshot(session, manifest_path, embedder):
    meta = json.loads(manifest_path.read_text())
    directory = manifest_path.parent
    raw = (directory / "source.txt").read_bytes()
    license_bytes = (directory / "LICENSE").read_bytes()
    if not meta.get("verified") or not re.fullmatch(r"[a-f0-9]{40}", meta["commit"]):
        raise ValueError("Unverified source manifest")
    if hashlib.sha256(raw).hexdigest() != meta["raw_sha256"]:
        raise ValueError("Source checksum mismatch")
    if hashlib.sha256(license_bytes).hexdigest() != meta["license_sha256"]:
        raise ValueError("License checksum mismatch")
    sections = [
        {"key": f"{meta['path']}#block-{i:04}", "title": meta["path"], "text": t}
        for i, t in enumerate(chunks(raw.decode()))
    ]
    body = IngestRequest(
        project=meta["project"],
        release=meta["release"],
        document_key=meta["path"],
        source_type="upstream",
        source_url=meta["canonical_url"],
        upstream_commit=meta["commit"],
        published_at=meta["published_at"],
        license=meta["license"],
        attribution=meta["attribution"],
        sections=sections,
    )
    return ingest(session, Principal("source-curator", "admin"), body, embedder)
