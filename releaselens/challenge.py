"""Small migration challenge integrity and an explicit untouched-query boundary."""

import hashlib
import json

from releaselens.review_dataset import ROOT, load_dataset
from releaselens.sources import chunks

MANIFEST = "migration-challenge-v1-manifest.json"


def load_challenge(root=ROOT):
    manifest, cases = load_dataset(root, MANIFEST)
    previous = json.loads((root / "evaluation/benchmark-v3-manifest.json").read_text())
    if manifest["parent_v3_sha256"] != previous["dataset_sha256"]:
        raise ValueError("Challenge parent dataset drift")
    old_paths = {s["manifest"] for s in previous["sources"]}
    holdout = set(manifest["new_holdout_sources"])
    if holdout & old_paths or holdout != {
        s["manifest"] for s in manifest["sources"] if s["split"] == "test"
    }:
        raise ValueError("New holdout must use source files absent from v3")
    if any(c["source_manifest"] not in holdout for c in cases if c["split"] == "test"):
        raise ValueError("Test case is not in a newly reserved family")
    source_by_path = {s["manifest"]: s for s in manifest["sources"]}
    for case in cases:
        source = source_by_path[case["source_manifest"]]
        texts = chunks(
            (root / case["source_manifest"]).with_name("source.txt").read_bytes().decode()
        )
        seen = set()
        for label in case["proposed_hard_negatives"]:
            identity = (label["document_key"], label["logical_key"])
            if (
                identity in seen
                or label["document_key"] != source["path"]
                or label["release"] != case["release"]
            ):
                raise ValueError("Hard negative must be unique and in the permitted release")
            seen.add(identity)
            index = int(label["logical_key"].rsplit("#block-", 1)[1])
            if (
                index < 0
                or index >= len(texts)
                or label["logical_key"] != f"{source['path']}#block-{index:04}"
            ):
                raise ValueError("Hard-negative passage identity mismatch")
            if (
                label["anchor"] not in texts[index]
                or hashlib.sha256(texts[index].encode()).hexdigest() != label["passage_sha256"]
            ):
                raise ValueError("Hard-negative anchor/hash drift")
            if not label.get("rationale", "").strip() or not case["expected_abstention"]:
                raise ValueError(
                    "Proposed insufficient evidence needs rationale and unsupported status"
                )
    return manifest, cases


def select_cases(cases, splits=("dev",)):
    if not splits or len(set(splits)) != len(splits) or set(splits) - {"dev", "validation"}:
        raise ValueError("Only dev/validation diagnostics; heldout questions must remain unscored")
    return [c for c in cases if c["split"] in splits]
