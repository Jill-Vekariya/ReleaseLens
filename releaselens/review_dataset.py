"""Versioned benchmark integrity and family leakage checks, independent of ranking."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from releaselens.sources import chunks

ROOT = Path(__file__).resolve().parents[1]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_dataset(root=ROOT):
    manifest_path = root / "evaluation/benchmark-v3-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dataset = root / manifest["dataset"]
    if file_hash(dataset) != manifest["dataset_sha256"]:
        raise ValueError("Frozen dataset hash mismatch")
    records = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines()]
    if len(records) != manifest["records"] or len({r["id"] for r in records}) != len(records):
        raise ValueError("Record IDs/count mismatch")
    sources, families, groups, evidence_splits = {}, {}, {}, {}
    for source in manifest["sources"]:
        path = root / source["manifest"]
        meta = json.loads(path.read_text())
        for field in ("project", "release", "path", "commit", "raw_sha256", "license_sha256"):
            if source[field] != meta[field]:
                raise ValueError("Source metadata drift")
        if not meta["verified"] or not re.fullmatch("[a-f0-9]{40}", meta["commit"]):
            raise ValueError("Unverified source")
        for filename, field in (("source.txt", "raw_sha256"), ("LICENSE", "license_sha256")):
            if file_hash(path.parent / filename) != source[field]:
                raise ValueError("Source/license byte drift")
        blocks = chunks((path.parent / "source.txt").read_bytes().decode())
        if len(blocks) != source["passages"]:
            raise ValueError("Chunking drift")
        identity = (source["project"], source["release"], source["path"])
        sources[identity] = (source, blocks)
    questions = defaultdict(set)
    for record in records:
        split = record["split"]
        if split not in ("dev", "validation", "test"):
            raise ValueError("Unknown split")
        if families.setdefault(record["family_id"], split) != split:
            raise ValueError("Document family crosses splits")
        if groups.setdefault(record["dedup_group"], split) != split:
            raise ValueError("Version variants or near duplicates cross splits")
        question = record["question"].split(", ", 1)[-1]
        normalized = tuple(re.findall(r"[a-z0-9_]+", question.casefold()))
        questions[normalized].add(split)
        if len(questions[normalized]) > 1:
            raise ValueError("Normalized question crosses splits")
        if bool(record["relevance"]) == record["expected_abstention"]:
            raise ValueError("Answerability/relevance mismatch")
        if record["review_status"] != "ai_reviewed_proposal" or record["human_review"] is not None:
            raise ValueError("V3 is frozen AI-proposal data; create a reviewed successor version")
        meta = json.loads((root / record["source_manifest"]).read_text())
        source, blocks = sources[(record["project"], record["release"], meta["path"])]
        if record["family_id"] != source["family_id"] or split != source["split"]:
            raise ValueError("Question differs from source family assignment")
        if source["commit"] != record["source_commit"]:
            raise ValueError("Case source revision mismatch")
        for label in record["relevance"]:
            index = int(label["logical_key"].rsplit("#block-", 1)[1])
            block = blocks[index]
            if (
                label["document_key"] != source["path"]
                or label["logical_key"] != f"{source['path']}#block-{index:04}"
            ):
                raise ValueError("Evidence identity mismatch")
            if (
                label["anchor"] not in block
                or hashlib.sha256(block.encode()).hexdigest() != label["passage_sha256"]
            ):
                raise ValueError("Evidence anchor/hash drift")
            if evidence_splits.setdefault(label["passage_sha256"], split) != split:
                raise ValueError("Duplicate labeled passage crosses splits")
    if families != manifest["family_splits"]:
        raise ValueError("Family freeze mismatch")
    return manifest, records
