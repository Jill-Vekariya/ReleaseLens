"""Export blank independent-review forms and validate submissions without changing labels."""

import argparse
import json
from datetime import datetime
from pathlib import Path

from releaselens.review_dataset import load_dataset


def validate(records, cases, dataset_hash):
    known = {c["id"]: c for c in cases}
    seen = set()
    for record in records:
        if record["case_id"] not in known or record["case_id"] in seen:
            raise ValueError("Unknown or duplicate reviewed case")
        seen.add(record["case_id"])
        if record["dataset_sha256"] != dataset_hash:
            raise ValueError("Review belongs to different frozen bytes")
        if not record.get("reviewer") or not record.get("reviewed_at"):
            raise ValueError("Actual reviewer identity/date required; do not fill with AI")
        datetime.fromisoformat(record["reviewed_at"])
        if type(record.get("answerable")) is not bool or not record.get(
            "support_or_absence_rationale"
        ):
            raise ValueError("Answerability and a source-based rationale are required")
        if record["answerable"] and not record.get("relevant_evidence"):
            raise ValueError("Answerable reviews need all relevant document/logical-key pairs")
        if not record["answerable"] and record.get("relevant_evidence"):
            raise ValueError("Unsupported review cannot contain proposed supporting evidence")
        if record.get("uncertainty") not in ("low", "medium", "high"):
            raise ValueError("Record uncertainty explicitly")
    return {
        "valid_submissions": len(records),
        "state": "submitted_for_adjudication",
        "labels_changed": False,
        "human_identity_authenticated": False,
        "note": "Structural checks cannot establish that a person performed review; no labels upgraded automatically",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "validate"))
    parser.add_argument("--split", choices=("dev", "validation", "test"), default="dev")
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    manifest, cases = load_dataset()
    if args.action == "export":
        if args.file.exists():
            raise ValueError("Refusing to overwrite an existing review")
        # Proposal answers and labels are deliberately absent to reduce anchoring bias.
        forms = [
            {
                "case_id": c["id"],
                "dataset_sha256": manifest["dataset_sha256"],
                "question": c["question"],
                "project": c["project"],
                "release": c["release"],
                "source_manifest": c["source_manifest"],
                "source_review_scope": "Read every same-project/release source in benchmark-v3-manifest, not only the named source. Inspect included directives and missing context.",
                "reviewer": None,
                "reviewed_at": None,
                "answerable": None,
                "expected_answer": None,
                "relevant_evidence": [],
                "support_or_absence_rationale": None,
                "uncertainty": None,
                "independent_reviewer": None,
                "adjudication": None,
            }
            for c in cases
            if c["split"] == args.split
        ]
        args.file.parent.mkdir(parents=True, exist_ok=True)
        args.file.write_text("".join(json.dumps(r) + "\n" for r in forms), encoding="utf-8")
        print(
            json.dumps(
                {
                    "blank_forms": len(forms),
                    "proposal_labels_visible": False,
                    "labels_changed": False,
                }
            )
        )
    else:
        records = [json.loads(line) for line in args.file.read_text(encoding="utf-8").splitlines()]
        print(json.dumps(validate(records, cases, manifest["dataset_sha256"]), indent=2))


if __name__ == "__main__":
    main()
