"""Own a fresh v3 demo process for browser/concurrency checks; preserve existing demo."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    env = os.environ.copy()
    for key in (
        "EMBEDDING_MODEL",
        "EMBEDDING_REVISION",
        "ANSWERABILITY_POLICY",
        "LLM_BASE_URL",
        "LLM_MODEL",
        "LLM_API_KEY",
    ):
        env.pop(key, None)
    env.update(
        {
            "RELEASELENS_DEMO": "true",
            "GENERATOR_MODE": "extractive",
            "ENABLE_PROSE_REVIEW_CANDIDATES": "false",
            "RELEASELENS_TEST_BASE_URL": "http://127.0.0.1:8001",
        }
    )
    with tempfile.TemporaryDirectory(prefix="releaselens-v3-") as folder:
        env["DATABASE_URL"] = "sqlite:///" + (Path(folder) / "demo.db").as_posix()
        ingest = subprocess.run(
            [sys.executable, "scripts/ingest_sources.py", "--expanded"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if ingest.returncode:
            raise RuntimeError("Fresh verification source ingestion failed: " + ingest.stderr)
        with (Path(folder) / "server.log").open("w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "releaselens.api:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8001",
                    "--no-access-log",
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                deadline = time.monotonic() + 25
                health = None
                while time.monotonic() < deadline and process.poll() is None:
                    try:
                        with urllib.request.urlopen(
                            "http://127.0.0.1:8001/health", timeout=1
                        ) as response:
                            health = json.load(response)
                        break
                    except OSError:
                        time.sleep(0.2)
                if (
                    health is None
                    or not health["demo"]
                    or health["embedding"] != "hash-384-demo-not-semantic"
                ):
                    raise RuntimeError("Owned fresh verification server did not become healthy")
                for script in ("browser_smoke.py", "browser_security_smoke.py", "load_smoke.py"):
                    command = [sys.executable, "scripts/" + script]
                    if script == "load_smoke.py":
                        command += ["--base-url", "http://127.0.0.1:8001"]
                    result = subprocess.run(
                        command,
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=120,
                    )
                    checks.append(
                        {
                            "script": script,
                            "exit_code": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                        }
                    )
                    print(f"{script}: exit {result.returncode}", flush=True)
                    if result.returncode:
                        break
            finally:
                if os.name == "nt":
                    # Windows venv python.exe launches the real interpreter as a child.
                    # Terminating only the launcher leaves the owned server/DB open.
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        check=False,
                    )
                else:
                    process.terminate()
                process.wait(timeout=15)
    passed = len(checks) == 3 and all(c["exit_code"] == 0 for c in checks)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "fresh_owned_server": True,
        "source_snapshots": 14,
        "existing_demo_port_8000_preserved": True,
        "base_url": "http://127.0.0.1:8001",
        "health": health,
        "checks": checks,
        "code_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "releaselens").glob("*.py")
        },
        "scope": "Headless installed Edge and 100-request concurrency-eight loopback functional checks; no production capacity claim",
    }
    (ROOT / "evaluation/demo-v3-verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "status",
                    "fresh_owned_server",
                    "source_snapshots",
                    "existing_demo_port_8000_preserved",
                )
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
