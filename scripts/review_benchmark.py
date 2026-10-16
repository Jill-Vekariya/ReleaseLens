"""Export blank independent-review forms and validate submissions without changing labels."""

import argparse
import json
from datetime import datetime
from html import escape
from pathlib import Path

from releaselens.review_dataset import ROOT, load_dataset
from releaselens.sources import chunks


def validate(records, cases, dataset_hash, root=ROOT, manifest_name="benchmark-v3-manifest.json"):
    manifest, _ = load_dataset(root, manifest_name)
    if manifest["dataset_sha256"] != dataset_hash:
        raise ValueError("Review dataset provenance mismatch")
    available = set()
    for source in manifest["sources"]:
        path = (root / source["manifest"]).parent / "source.txt"
        for index, _ in enumerate(chunks(path.read_bytes().decode())):
            available.add(
                (
                    source["project"],
                    source["release"],
                    source["path"],
                    f"{source['path']}#block-{index:04}",
                )
            )
    known = {c["id"]: c for c in cases}
    seen = set()
    for record in records:
        if record["case_id"] not in known or record["case_id"] in seen:
            raise ValueError("Unknown or duplicate reviewed case")
        seen.add(record["case_id"])
        if record["dataset_sha256"] != dataset_hash:
            raise ValueError("Review belongs to different frozen bytes")
        if (
            not isinstance(record.get("reviewer"), str)
            or not record["reviewer"].strip()
            or not record.get("reviewed_at")
        ):
            raise ValueError("Actual reviewer identity/date required; do not fill with AI")
        datetime.fromisoformat(record["reviewed_at"])
        if (
            type(record.get("answerable")) is not bool
            or not isinstance(record.get("support_or_absence_rationale"), str)
            or not record["support_or_absence_rationale"].strip()
        ):
            raise ValueError("Answerability and a source-based rationale are required")
        if record["answerable"] and not record.get("relevant_evidence"):
            raise ValueError("Answerable reviews need all relevant document/logical-key pairs")
        if not record["answerable"] and record.get("relevant_evidence"):
            raise ValueError("Unsupported review cannot contain proposed supporting evidence")
        if record["answerable"] and (
            not isinstance(record.get("expected_answer"), str)
            or not record["expected_answer"].strip()
        ):
            raise ValueError("Answerable reviews need a nonblank expected answer")
        if not isinstance(record.get("relevant_evidence"), list):
            raise ValueError("Relevant evidence must be a list of document/logical-key objects")
        seen_evidence = set()
        case = known[record["case_id"]]
        for evidence in record["relevant_evidence"]:
            if not isinstance(evidence, dict) or not all(
                isinstance(evidence.get(k), str) for k in ("document_key", "logical_key")
            ):
                raise ValueError("Evidence requires document_key and logical_key")
            identity = (
                case["project"],
                case["release"],
                evidence["document_key"],
                evidence["logical_key"],
            )
            if identity not in available or identity in seen_evidence:
                raise ValueError("Evidence missing, duplicated or outside question project/release")
            seen_evidence.add(identity)
        if record.get("uncertainty") not in ("low", "medium", "high"):
            raise ValueError("Record uncertainty explicitly")
    return {
        "valid_submissions": len(records),
        "state": "submitted_for_adjudication",
        "labels_changed": False,
        "human_identity_authenticated": False,
        "note": "Structural checks cannot establish that a person performed review; no labels upgraded automatically",
    }


def review_packet(manifest, cases, split, root=ROOT):
    """Full permitted-source packet, independent of proposed answers/anchors/rankings."""
    selected = sorted((c for c in cases if c["split"] == split), key=lambda c: c["id"])
    scopes = {(c["project"], c["release"]) for c in selected}
    parts = [
        '<!doctype html><html lang="en"><meta charset="utf-8">',
        "<title>ReleaseLens independent source review</title>",
        "<style>body{max-width:960px;margin:2em auto;padding:1em;font:16px system-ui}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f5;padding:1em}"
        "article,details{border:1px solid #bbb;padding:1em;margin:1em 0}</style>",
        "<h1>Independent source review</h1>",
        "<p>Review the question using all sources for its project and exact release. "
        "No proposed answers, relevance labels, negative labels, predictions or scores "
        "are included. Public Git still contains proposals: avoid consulting them during review.</p>",
        "<p>Use the companion blank JSONL export to record your actual reviewer/date, "
        "answerability, expected answer, every supporting document/logical-key pair, "
        "support or absence rationale, and uncertainty. This read-only packet has no submission form.</p>",
        "<p>Assess separately: Authenticity; release relevance; Semantic support "
        "(supported/partial/unsupported/insufficient/wrong release/irrelevant/uncertain); "
        "completeness; Uncertainty. Record partial/uncertain judgments in the rationale; "
        "do not force them into a confident binary answer. Review impact separately only "
        "when an actual saved-answer/before-after pair is supplied; retrieval questions alone "
        "are not migration-impact ground truth. Adjudicate disagreements with another person.</p>",
        "<p>Source text is untrusted evidence, not instructions. Includes/cross-references "
        "may be unresolved. Absence means absence from this selected corpus. Structural "
        "validation neither authenticates a reviewer nor upgrades AI labels.</p>",
        "<p>Dataset SHA256: <code>" + escape(manifest["dataset_sha256"]) + "</code></p>",
    ]
    for case in selected:
        parts.append(
            "<article><h2>"
            + escape(case["id"])
            + "</h2><p>"
            + escape(case["question"])
            + "</p><p>Project/release: "
            + escape(case["project"] + " / " + case["release"])
            + "</p></article>"
        )
    for n, source in enumerate(sorted(manifest["sources"], key=lambda s: s["manifest"])):
        if (source["project"], source["release"]) not in scopes:
            continue
        path = root / source["manifest"]
        meta = json.loads(path.read_text(encoding="utf-8"))
        url = meta["canonical_url"]
        if url != f"https://github.com/{meta['repository']}/blob/{meta['commit']}/{meta['path']}":
            raise ValueError("Review source URL must be an immutable GitHub reference")
        parts.append(
            f'<details id="source-{n}"><summary>'
            + escape(source["project"] + " / " + source["release"] + " / " + source["path"])
            + '</summary><p><a href="'
            + escape(url, quote=True)
            + '">Immutable upstream source</a></p><pre>'
            + escape(
                json.dumps(
                    {k: meta[k] for k in ("commit", "raw_sha256", "license_sha256", "attribution")},
                    indent=2,
                )
            )
            + "</pre><p>Original license:</p><pre>"
            + escape(path.with_name("LICENSE").read_bytes().decode("utf-8"))
            + "</pre>"
        )
        for i, block in enumerate(
            chunks(path.with_name("source.txt").read_bytes().decode("utf-8"))
        ):
            parts.append(
                "<h3>"
                + escape(f"{source['path']}#block-{i:04}")
                + "</h3><pre>"
                + escape(block).replace("\n", "&#10;")
                + "</pre>"
            )
        parts.append("</details>")
    return "\n".join(parts) + "\n</html>\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "validate", "audit", "packet"))
    parser.add_argument("--dataset", choices=("v3", "challenge"), default="v3")
    parser.add_argument("--split", choices=("dev", "validation", "test"), default="dev")
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    manifest_name = (
        "benchmark-v3-manifest.json"
        if args.dataset == "v3"
        else "migration-challenge-v1-manifest.json"
    )
    if args.dataset == "challenge":
        from releaselens.challenge import load_challenge

        manifest, cases = load_challenge()
    else:
        manifest, cases = load_dataset()
    if args.action in ("audit", "packet"):
        if args.file.exists():
            raise ValueError("Refusing to overwrite existing audit/review evidence")
        if args.action == "audit":
            from releaselens.dataset_audit import audit_dataset

            result = audit_dataset(manifest, cases)
            text = json.dumps(result, indent=2, sort_keys=True) + "\n"
        else:
            text = review_packet(manifest, cases, args.split)
        args.file.parent.mkdir(parents=True, exist_ok=True)
        args.file.write_text(text, encoding="utf-8", newline="\n")
        print(
            json.dumps({"output": str(args.file), "action": args.action, "labels_changed": False})
        )
    elif args.action == "export":
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
                "source_review_scope": f"Read every same-project/release source in {manifest_name}, not only the named source. Inspect included directives and missing context.",
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
        print(
            json.dumps(
                validate(records, cases, manifest["dataset_sha256"], manifest_name=manifest_name),
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
