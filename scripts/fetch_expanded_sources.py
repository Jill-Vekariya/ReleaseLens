"""Fetch additional MIT-licensed pages at the four already verified release commits.

The original four snapshots are read for pin/license verification and never written.
Existing expansion directories are verified and preserved; drift fails closed.
Run: python scripts/fetch_expanded_sources.py
"""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    ("pydantic", "1.10.15"): "5476a758c8ac59887dbfa3aa1c3481d0a0e20837",
    ("pydantic", "2.10.4"): "5bd3a6507b749fcd4833173fba88b3690ff77170",
    ("sqlalchemy", "1.4.54"): "dfe401fd471323638ad3e1b1027d89e01fcbeef5",
    ("sqlalchemy", "2.0.36"): "66e31814644bad95c8cda853f03088f59be0053d",
}
PAGES = [
    ("pydantic", "1.10.15", "models", "dev", "docs/usage/models.md"),
    ("pydantic", "2.10.4", "models", "dev", "docs/concepts/models.md"),
    ("pydantic", "1.10.15", "validators", "validation", "docs/usage/validators.md"),
    ("pydantic", "2.10.4", "validators", "validation", "docs/concepts/validators.md"),
    ("pydantic", "1.10.15", "serialization", "test", "docs/usage/exporting_models.md"),
    ("pydantic", "2.10.4", "serialization", "test", "docs/concepts/serialization.md"),
    ("sqlalchemy", "1.4.54", "engines", "validation", "doc/build/core/engines.rst"),
    ("sqlalchemy", "2.0.36", "engines", "validation", "doc/build/core/engines.rst"),
    ("sqlalchemy", "1.4.54", "select", "test", "doc/build/tutorial/data_select.rst"),
    ("sqlalchemy", "2.0.36", "select", "test", "doc/build/tutorial/data_select.rst"),
]


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ReleaseLens/portfolio-v3"})
    with urllib.request.urlopen(request, timeout=45) as response:
        content = response.read(2_000_001)
    if len(content) > 2_000_000:
        raise ValueError("Source exceeds bounded public documentation size")
    content.decode("utf-8")
    return content


def fetch_page(item):
    project, release, family, split, path = item
    parent = ROOT / "data/upstream" / project / release
    original = json.loads((parent / "manifest.json").read_text())
    commit = PINS[(project, release)]
    if original["commit"] != commit or not original["verified"]:
        raise ValueError("Original release pin is not verified")
    directory = parent / family
    if directory.exists():
        manifest = json.loads((directory / "manifest.json").read_text())
        for field, expected in {
            "commit": commit,
            "path": path,
            "document_family_id": f"{project}:{family}",
            "split": split,
        }.items():
            if manifest[field] != expected:
                raise ValueError(f"Existing expansion metadata drift: {directory}")
        for filename, field in (("source.txt", "raw_sha256"), ("LICENSE", "license_sha256")):
            if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != manifest[field]:
                raise ValueError(f"Existing expansion content drift: {directory}")
        return manifest
    repository = original["repository"]
    base = f"https://raw.githubusercontent.com/{repository}/{commit}/"
    raw = download(base + path)
    license_bytes = download(base + "LICENSE")
    license_hash = hashlib.sha256(license_bytes).hexdigest()
    if license_hash != original["license_sha256"]:
        raise ValueError("Pinned repository license differs from preserved original")
    if "Permission is hereby granted" not in license_bytes.decode():
        raise ValueError("Expected MIT permission text missing")
    manifest = {
        **{
            key: original[key]
            for key in (
                "project",
                "repository",
                "release",
                "tag",
                "commit",
                "published_at",
                "date_semantics",
                "license",
                "attribution",
            )
        },
        "path": path,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "license_sha256": license_hash,
        "canonical_url": f"https://github.com/{repository}/blob/{commit}/{path}",
        "raw_url": base + path,
        "license_url": base + "LICENSE",
        "document_family_id": f"{project}:{family}",
        "split": split,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "verification_basis": "Pinned immutable raw source bytes; license hash matches original release snapshot",
        "verified": True,
    }
    directory.mkdir()
    (directory / "source.txt").write_bytes(raw)
    (directory / "LICENSE").write_bytes(license_bytes)
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    for page in PAGES:
        result = fetch_page(page)
        print(
            json.dumps({key: result[key] for key in ("project", "release", "path", "raw_sha256")})
        )
