"""Verify the actual Compose deployment and retain evidence without printing secrets."""

import json
import platform
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run():
    commands = [
        ["docker", "compose", "up", "--build", "--wait"],
        ["docker", "compose", "exec", "-T", "backend", "python", "scripts/ingest_sources.py"],
        ["docker", "compose", "exec", "-T", "backend", "python", "scripts/docker_smoke.py"],
        [
            "docker",
            "compose",
            "run",
            "--rm",
            "--no-deps",
            "-v",
            f"{(ROOT / 'tests').as_posix()}:/app/tests:ro",
            "backend",
            "python",
            "-m",
            "pytest",
            "tests/test_postgres.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        ["docker", "compose", "ps", "--format", "json"],
    ]
    checks = []
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        checks.append(
            {
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
        print(f"{'PASS' if completed.returncode == 0 else 'FAIL'}: {' '.join(command)}", flush=True)
        if completed.returncode:
            break
    passed = all(c["exit_code"] == 0 for c in checks) and len(checks) == len(commands)
    health = None
    if passed:
        with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=10) as response:
            health = json.load(response)
        passed = (
            health["status"] == "ok" and health["database"] == "postgresql" and not health["demo"]
        )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "checks": checks,
        "nginx_health": health,
        "runtime": platform.platform(),
    }
    (ROOT / "evaluation" / "docker-verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": result["status"], "nginx_health": health}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
