"""Bounded loopback HTTP responsiveness diagnostic, not a capacity benchmark."""

import argparse
import asyncio
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from releaselens.evaluate import percentile

ROOT = Path(__file__).resolve().parents[1]


async def run(base_url, count, concurrency):
    if base_url not in ("http://127.0.0.1:8000", "http://localhost:8000"):
        raise ValueError(
            "This no-credential demo load diagnostic is restricted to loopback port 8000"
        )
    semaphore = asyncio.Semaphore(concurrency)
    elapsed, failures, wrong_release = [], [], []
    cases = [
        ("pydantic", "1.10.15", "model configuration"),
        ("pydantic", "2.10.4", "model_config ConfigDict"),
        ("sqlalchemy", "1.4.54", "Connection.execute transactions"),
        ("sqlalchemy", "2.0.36", "autocommit transactions"),
    ]
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:

        async def query(index):
            project, release, question = cases[index % len(cases)]
            async with semaphore:
                start = time.perf_counter()
                try:
                    response = await client.post(
                        "/api/ask",
                        json={
                            "project": project,
                            "release": release,
                            "question": question,
                            "save": False,
                            "k": 2,
                        },
                    )
                    elapsed.append((time.perf_counter() - start) * 1000)
                    if response.status_code != 200:
                        failures.append({"index": index, "status": response.status_code})
                    else:
                        payload = response.json()
                        if any(p["release"] != release for p in payload["passages"]):
                            wrong_release.append(index)
                except httpx.HTTPError as error:
                    failures.append({"index": index, "error_type": type(error).__name__})

        start = time.perf_counter()
        await asyncio.gather(*(query(i) for i in range(count)))
        total = time.perf_counter() - start
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requests": count,
        "concurrency": concurrency,
        "elapsed_seconds": total,
        "observed_requests_per_second": count / total,
        "p50_ms": percentile(elapsed, 0.5) if elapsed else None,
        "p95_ms": percentile(elapsed, 0.95) if elapsed else None,
        "http_failures": failures,
        "wrong_release_responses": wrong_release,
        "status": "passed" if not failures and not wrong_release else "failed",
        "environment": {
            "os": platform.system(),
            "python": platform.python_version(),
            "logical_cpus": os.cpu_count(),
        },
        "scope": "100-request small-corpus loopback responsiveness check; no serving capacity or production-scale claim",
        "provider_cost_usd": 0,
        "cost_note": "No model-provider call in default extractive mode; compute/electricity unmeasured",
    }
    (ROOT / "evaluation" / "load-verification.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.base_url, 100, 8)))
