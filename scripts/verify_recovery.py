"""Back up real PG, restore to a disposable DB, test migrations there and restart API.

Keeps backups under ignored .backups/. Never restores over the live database.
"""

import hashlib
import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def command(args):
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "Recovery check failed: " + " ".join(args[:6]) + ": " + result.stderr[-1200:]
        )
    return result.stdout.strip()


def signature(database):
    result = {}
    for table in (
        "documents",
        "revisions",
        "passages",
        "answers",
        "dependencies",
        "changes",
        "reviews",
    ):
        sql = f"SELECT count(*), md5(coalesce(string_agg(row_to_json(t)::text, '|' ORDER BY row_to_json(t)::text),'')) FROM {table} t"
        result[table] = command(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "releaselens",
                "-d",
                database,
                "-At",
                "-c",
                sql,
            ]
        )
    return result


def run():
    suffix = uuid4().hex[:12]
    clone = "releaselens_verify_" + suffix
    assert re.fullmatch(r"releaselens_verify_[a-f0-9]{12}", clone)
    directory = ROOT / ".backups"
    directory.mkdir(exist_ok=True)
    backup = directory / ("releaselens-" + suffix + ".dump")
    before = signature("releaselens")
    command(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "pg_dump",
            "-U",
            "releaselens",
            "-d",
            "releaselens",
            "-Fc",
            "-f",
            "/tmp/releaselens-verification.dump",
        ]
    )
    command(["docker", "compose", "cp", "db:/tmp/releaselens-verification.dump", str(backup)])
    command(["docker", "compose", "exec", "-T", "db", "createdb", "-U", "releaselens", clone])
    try:
        command(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "db",
                "pg_restore",
                "-U",
                "releaselens",
                "--exit-on-error",
                "--no-owner",
                "-d",
                clone,
                "/tmp/releaselens-verification.dump",
            ]
        )
        restored = signature(clone)
        assert restored == before, "Restored data does not match captured source signatures"
        migration_code = (
            "import os,subprocess;from sqlalchemy.engine import make_url;"
            f"u=make_url(os.environ['DATABASE_URL']).set(database='{clone}');"
            "env=dict(os.environ,DATABASE_URL=u.render_as_string(hide_password=False));"
            "subprocess.run(['python','-m','alembic','downgrade','base'],env=env,check=True);"
            "subprocess.run(['python','-m','alembic','upgrade','head'],env=env,check=True)"
        )
        command(["docker", "compose", "exec", "-T", "backend", "python", "-c", migration_code])
        migrated = signature(clone)
        assert all(value.startswith("0|") for value in migrated.values())
        assert signature("releaselens") == before, "Live database changed during clone verification"
    finally:
        command(["docker", "compose", "exec", "-T", "db", "dropdb", "-U", "releaselens", clone])
    command(["docker", "compose", "restart", "backend"])
    healthy = False
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2) as response:
                health = json.load(response)
            healthy = health.get("database") == "postgresql" and health.get("status") == "ok"
            if healthy:
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    assert healthy, "Backend did not recover after restart"
    assert signature("releaselens") == before, "Persistent records changed across restart"
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "checks": [
            "binary custom-format backup",
            "restore into isolated disposable database",
            "all table data signatures preserved",
            "PG downgrade/upgrade on disposable clone",
            "live data unchanged",
            "backend restart health recovery",
            "records persist after restart",
        ],
        "backup_filename": backup.name,
        "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "backup_bytes": backup.stat().st_size,
        "source_signatures": before,
        "safety": "Live DB was never a restore or downgrade target; only the generated clone was dropped",
    }
    (ROOT / "evaluation" / "recovery-verification.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    run()
