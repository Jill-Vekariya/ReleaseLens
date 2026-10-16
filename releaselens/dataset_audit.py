"""Deterministic, model-free overlap diagnostics; no retrieval or answer predictions."""

import hashlib
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from releaselens.review_dataset import ROOT, file_hash
from releaselens.sources import chunks


def audit_dataset(manifest, cases, root=ROOT):
    def overlaps(rows):
        groups = defaultdict(set)
        for key, split in rows:
            groups[key].add(split)
        return [
            {"identity": key, "splits": sorted(splits)}
            for key, splits in sorted(groups.items())
            if len(splits) > 1
        ]

    def tokens(case):
        # Match the loader's release-prefix removal; no learned similarity or tuning.
        return set(re.findall(r"[a-z0-9_]+", case["question"].split(", ", 1)[-1].casefold()))

    near = []
    for left, right in combinations(sorted(cases, key=lambda c: c["id"]), 2):
        if left["split"] == right["split"]:
            continue
        a, b = tokens(left), tokens(right)
        similarity = len(a & b) / len(a | b) if a | b else 0
        if similarity >= 0.8:
            near.append(
                {
                    "case_ids": [left["id"], right["id"]],
                    "token_jaccard": similarity,
                    "needs_semantic_review": True,
                }
            )
    passages = defaultdict(list)
    for source in sorted(manifest["sources"], key=lambda s: s["manifest"]):
        path = (root / source["manifest"]).with_name("source.txt")
        for i, block in enumerate(chunks(path.read_bytes().decode("utf-8"))):
            digest = hashlib.sha256(block.encode()).hexdigest()
            passages[digest].append(
                {
                    "manifest": source["manifest"],
                    "split": source["split"],
                    "logical_key": f"{source['path']}#block-{i:04}",
                }
            )
    duplicates = [
        {"passage_sha256": digest, "occurrences": rows}
        for digest, rows in sorted(passages.items())
        if len({r["split"] for r in rows}) > 1
    ]
    return {
        "dataset_version": manifest["dataset_version"],
        "dataset_sha256": manifest["dataset_sha256"],
        "audit_code_sha256": file_hash(Path(__file__)),
        "validator_code_sha256": file_hash(root / "releaselens/review_dataset.py"),
        "cases": len(cases),
        "split_counts": dict(sorted(Counter(c["split"] for c in cases).items())),
        "family_counts": dict(sorted(Counter(c["family_id"] for c in cases).items())),
        "category_counts": dict(sorted(Counter(c["category"] for c in cases).items())),
        "human_reviewed_records": manifest["human_reviewed_records"],
        "cross_split_family_overlap": overlaps((c["family_id"], c["split"]) for c in cases),
        "cross_split_intent_overlap": overlaps((c["dedup_group"], c["split"]) for c in cases),
        "cross_split_source_page_overlap": overlaps(
            (c["source_manifest"], c["split"]) for c in cases
        ),
        "cross_split_near_duplicate_questions": near,
        "near_duplicate_method": "Fixed token-set Jaccard >=0.8 after release-prefix removal; review flag, not semantic equivalence",
        "shared_cross_split_passages": duplicates,
        "cross_split_labeled_evidence": overlaps(
            (label["passage_sha256"], c["split"]) for c in cases for label in c["relevance"]
        ),
        "shared_upstream_revisions": overlaps(
            (f"{s['project']}:{s['release']}:{s['commit']}", s["split"])
            for s in manifest["sources"]
        ),
        "model_calls": 0,
        "questions_scored": 0,
        "limits": [
            "Shared library commits across different pages are reported, not automatically label leakage.",
            "All source text is indexed, including reserved families; public proposal labels are in Git.",
            "Token similarity misses paraphrases and can flag distinct questions; humans must assess meaning.",
            "Duplicate raw passage text can be boilerplate; this report does not establish complete conceptual independence.",
            "No thresholds, models, splits, labels or benchmark predictions are changed by this audit.",
        ],
    }
