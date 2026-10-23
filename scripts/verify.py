"""Run actual local checks and retain their outputs; failures remain failures."""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(output_dir=None):
    output_dir = (
        Path(output_dir)
        if output_dir
        else ROOT / "evaluation" / "local" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    junit = output_dir / "test-results.xml"
    commands = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}"],
        ["node", "--check", "web/app.js"],
        [sys.executable, "-m", "compileall", "-q", "releaselens", "scripts", "alembic"],
    ]
    checks = []
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        checks.append(
            {
                "command": ["python" if x == sys.executable else x for x in command],
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    summary = {}
    if junit.exists():
        try:
            suite = ET.parse(junit).getroot().find("testsuite")
            summary = dict(suite.attrib) if suite is not None else {"error": "No test suite"}
        except ET.ParseError:
            summary = {"error": "Test runner produced invalid XML"}
    else:
        summary = {"error": "Test runner did not produce XML; inspect command output"}
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "test_summary": summary,
        "all_local_checks_passed": all(c["exit_code"] == 0 for c in checks),
        "not_covered_by_this_command": [
            "Docker startup",
            "PostgreSQL service provisioning (run the separate CI postgres job)",
            "Browser interaction/layout",
            "Learned encoder quality",
            "Live provider inference",
            "Human-reviewed benchmark",
            "GitHub CI execution",
            "Hosted deployment",
            "Requested Astra final review",
        ],
        "additional_evidence": [
            "docker-verification.json",
            "browser-verification.json",
            "semantic-verification.json",
        ],
        "attribution": "AI-assisted implementation; no independent human code review recorded",
    }
    (output_dir / "verification.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "all_local_checks_passed": record["all_local_checks_passed"],
                "test_summary": record["test_summary"],
            },
            indent=2,
        )
    )
    return 0 if record["all_local_checks_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="New directory for this verification run")
    raise SystemExit(verify(parser.parse_args().output_dir))
