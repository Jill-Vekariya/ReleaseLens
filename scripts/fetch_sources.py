"""Resolve release tags to commits; download licensed snapshots, never current docs.

Run from the repository root: python scripts/fetch_sources.py
Network failures remain failures and are recorded, never replaced with synthetic data.
"""

import hashlib
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

SOURCES = [
    ("pydantic", "pydantic/pydantic", "1.10.15", "v1.10.15", "docs/usage/model_config.md"),
    ("pydantic", "pydantic/pydantic", "2.10.4", "v2.10.4", "docs/concepts/config.md"),
    (
        "sqlalchemy",
        "sqlalchemy/sqlalchemy",
        "1.4.54",
        "rel_1_4_54",
        "doc/build/core/connections.rst",
    ),
    (
        "sqlalchemy",
        "sqlalchemy/sqlalchemy",
        "2.0.36",
        "rel_2_0_36",
        "doc/build/core/connections.rst",
    ),
]
ROOT = Path(__file__).resolve().parents[1]


def get(url):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ReleaseLens/0.1"})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(2_000_001)
                if len(data) > 2_000_000:
                    raise ValueError("Source too large")
                return data
        except Exception:
            if attempt == 2:
                raise
            time.sleep(0.2)


def fetch(item):
    project, repo, release, tag, path = item
    directory = ROOT / "data" / "upstream" / project / release
    directory.mkdir(parents=True, exist_ok=True)
    try:
        metadata = json.loads(get(f"https://api.github.com/repos/{repo}/commits/{tag}"))
        commit = metadata["sha"]
        if not re.fullmatch(r"[a-f0-9]{40}", commit):
            raise ValueError("Invalid upstream commit")
        base = f"https://raw.githubusercontent.com/{repo}/{commit}/"
        raw = get(base + path)
        license_bytes = get(base + "LICENSE")
        raw.decode("utf-8")
        if "Permission is hereby granted" not in license_bytes.decode():
            raise ValueError("Unexpected license: manual assessment required")
        (directory / "source.txt").write_bytes(raw)
        (directory / "LICENSE").write_bytes(license_bytes)
        record = {
            "project": project,
            "repository": repo,
            "release": release,
            "tag": tag,
            "commit": commit,
            "path": path,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "license_sha256": hashlib.sha256(license_bytes).hexdigest(),
            "canonical_url": f"https://github.com/{repo}/blob/{commit}/{path}",
            "published_at": metadata["commit"]["committer"]["date"],
            "date_semantics": "commit time; not necessarily release publication date",
            "license": "MIT",
            "attribution": f"{repo} authors; see adjacent LICENSE",
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "verified": True,
        }
        (directory / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
        return record
    except Exception as exc:
        return {
            "project": project,
            "release": release,
            "verified": False,
            "error": type(exc).__name__ + ": " + str(exc)[:150],
        }


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(fetch, SOURCES))
    path = ROOT / "data" / "source-status.json"
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if all(r["verified"] for r in results) else 1)
