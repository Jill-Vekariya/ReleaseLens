"""Run actual local checks and retain their outputs; failures remain failures."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify():
    commands = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "-m", "pytest", "-q", "--junitxml=evaluation/test-results.xml"],
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
    tree = ET.parse(ROOT / "evaluation" / "test-results.xml")
    suite = tree.getroot().find("testsuite")
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "test_summary": dict(suite.attrib),
        "all_local_checks_passed": all(c["exit_code"] == 0 for c in checks),
        "not_covered_by_this_command": [
            "Docker startup",
            "PostgreSQL integration (skipped)",
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
    (ROOT / "evaluation" / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
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
    raise SystemExit(verify())
