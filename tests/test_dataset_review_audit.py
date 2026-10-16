"""Reject schema drift and audit leakage without ranking held-out questions."""

import copy
import hashlib
import json
import shutil

import pytest

from releaselens.review_dataset import ROOT, load_dataset


@pytest.fixture
def dataset_copy(tmp_path):
    shutil.copytree(ROOT / "data", tmp_path / "data")
    (tmp_path / "evaluation").mkdir()
    for name in ("benchmark-v3.jsonl", "benchmark-v3-manifest.json"):
        shutil.copyfile(ROOT / "evaluation" / name, tmp_path / "evaluation" / name)
    return tmp_path


@pytest.mark.parametrize(
    "change,match",
    [
        ("version", "version"),
        ("unknown_field", "fields"),
        ("category", "category"),
        ("origin", "annotation"),
    ],
)
def test_rejects_unrecognized_contract_metadata(dataset_copy, change, match):
    mp = dataset_copy / "evaluation/benchmark-v3-manifest.json"
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    dp = dataset_copy / "evaluation/benchmark-v3.jsonl"
    cases = [json.loads(line) for line in dp.read_text(encoding="utf-8").splitlines()]
    if change == "version":
        manifest["dataset_version"] = "unrecognized-future-schema"
    elif change == "unknown_field":
        cases[0]["expected_anwser"] = "silently ignored typo"
    elif change == "category":
        cases[0]["category"] = "human_confirmed_truth"
    else:
        cases[0]["question_origin"] = "human_authored"
    dp.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    manifest["dataset_sha256"] = hashlib.sha256(dp.read_bytes()).hexdigest()
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_dataset(dataset_copy)


def test_split_audit_exposes_similar_questions_without_scores():
    from releaselens.dataset_audit import audit_dataset

    manifest, cases = load_dataset()
    rows = copy.deepcopy(cases[:2])
    rows[1].update(split="test", question=rows[0]["question"] + " please")
    result = audit_dataset(manifest, rows)
    assert result["cross_split_near_duplicate_questions"]
    assert result["cross_split_family_overlap"]
    assert result["model_calls"] == result["questions_scored"] == 0
    assert "question" not in result["cross_split_near_duplicate_questions"][0]
    assert "expected_answer" not in json.dumps(result)


def test_review_packet_escapes_content_and_omits_proposals():
    from scripts.review_benchmark import review_packet

    manifest, cases = load_dataset()
    rows = copy.deepcopy(cases)
    rows[0]["question"] = '<script>alert("review")</script>'
    rows[0]["expected_answer"] = "AI_PROPOSAL_MUST_NOT_RENDER"
    html = review_packet(manifest, rows, "dev")
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert "AI_PROPOSAL_MUST_NOT_RENDER" not in html
    assert 'id="source-0"' in html
    assert "#block-0000" in html and "license_sha256" in html
    assert "Uncertainty" in html and "Semantic support" in html
    assert "test" not in {c["split"] for c in rows if c["id"] in html}


def test_review_packet_renders_entire_permitted_sources_not_ai_anchors():
    from scripts.review_benchmark import review_packet

    manifest, cases = load_dataset()
    rows = copy.deepcopy([c for c in cases if c["split"] == "dev"])
    for c in rows:
        c["relevance"] = []
        c["expected_answer"] = "SECRET_PROPOSAL"
    assert review_packet(manifest, rows, "dev") == review_packet(manifest, cases, "dev")

    # Rendering must preserve exact source whitespace, including trailing spaces and newlines.
    from html.parser import HTMLParser

    from releaselens.sources import chunks

    class PreText(HTMLParser):
        def __init__(self):
            super().__init__()
            self.inside = False
            self.current = []
            self.blocks = []

        def handle_starttag(self, tag, attrs):
            if tag == "pre":
                self.inside = True
                self.current = []

        def handle_data(self, data):
            if self.inside:
                self.current.append(data)

        def handle_endtag(self, tag):
            if tag == "pre":
                self.blocks.append("".join(self.current))
                self.inside = False

    manifest, cases = load_dataset()
    packet = review_packet(manifest, cases, "dev")
    parser = PreText()
    parser.feed(packet)
    block = chunks(
        (ROOT / "data/upstream/pydantic/1.10.15/models/source.txt").read_bytes().decode()
    )[0]
    assert block in parser.blocks


@pytest.mark.parametrize("action", ["audit", "packet"])
def test_review_cli_preserves_existing_output(tmp_path, action):
    import subprocess
    import sys

    output = tmp_path / "do-not-overwrite.txt"
    output.write_text("retained reviewer work", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.review_benchmark",
            action,
            "--dataset",
            "challenge",
            "--file",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "Refusing to overwrite" in result.stderr
    assert output.read_text(encoding="utf-8") == "retained reviewer work"
