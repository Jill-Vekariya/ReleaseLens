# Local private operations

This runbook targets the repository's three-service Compose deployment on Windows Docker Desktop with Linux containers. The private source repository is [Jill-Vekariya/ReleaseLens](https://github.com/Jill-Vekariya/ReleaseLens). Keep both the repository and runtime private. These instructions do not provision a public endpoint or a paid service. A documented command is not evidence it has passed: consult dated files in `evaluation/` and [STATUS.md](STATUS.md) for actual execution results.

## Start and access

From the repository root, with Docker Desktop running and Python 3.12 available:

```powershell
python scripts/configure.py
docker compose up --build --wait
docker compose ps
Invoke-RestMethod http://127.0.0.1:8080/health
```

Run configuration only on first setup; it refuses to overwrite `.env`. Open **http://127.0.0.1:8080**. The host binding is `127.0.0.1:8080:80`; neither PostgreSQL nor the backend publishes a host port. Keep this binding. Do not publish a tunnel, change it to `0.0.0.0`, or enable demo mode in Compose. Loopback HTTP is the current local access boundary; remote access needs a separately reviewed identity, transport, and network design.

The backend startup runs `alembic upgrade head` before starting one Uvicorn process. `pgdata` persists PostgreSQL data. `docker compose stop` pauses services; `docker compose down` removes containers and the network while retaining the named volume. **Do not run `docker compose down -v` for routine shutdown:** it deletes the database volume. A named volume is persistence, not a backup.

To ingest the bundled hash-verified snapshots, first pause UI/API writes and ensure no other ingestion process is running:

```powershell
docker compose exec -T backend python scripts/ingest_sources.py
```

The CLI writes directly to the database, bypassing the HTTP process's lock. Use a quiet maintenance window; do not run it concurrently with API writes or another CLI. The API's administrator role is a trusted curator, and API provenance assertions are not independently fetched or attested.

## Credentials and identities

`scripts/configure.py` generates a random database password and separate random reader, engineer, and administrator bearer tokens in `.env`. Inspect it locally in a private editor and copy only the token needed into the UI's **API token** control. The UI keeps the bearer token in page memory; a page reload clears it. Synthetic role selection does not authenticate Compose requests. Saved answers belong to the configured `user` string, including for administrators.

- Keep `.env` out of source control, screenshots, transcripts, and shared terminals. Do not paste `docker compose config`, `docker inspect`, or environment dumps into reports: they can reveal resolved secrets.
- Restrict `.env` and backup directories to the Windows user operating Docker. The script requests Unix mode `0600`; that is not a Windows ACL guarantee. Check the file's Security properties on Windows. Store a private copy of configuration separately from database backups.
- To rotate an API token, replace its JSON key in `RELEASELENS_TOKENS` with a newly generated high-entropy token, retain the intended `user`/`role`, then run `docker compose up -d --no-deps --force-recreate backend` and `docker compose restart frontend`. Re-enter the new token in the UI. There is no token expiry, identity provider, or per-token revocation service; removal from configuration plus backend recreation performs revocation.
- Changing `DB_PASSWORD` in `.env` alone does **not** change an existing PostgreSQL role's password: the image initializes credentials only for an empty volume. Coordinate an actual database password change and backend recreation during maintenance. Do not delete the volume to reset credentials.

Default inference makes no provider requests. The optional compatible extract selector can send authorized retrieved evidence to its configured endpoint; enabling it requires an explicit privacy and cost decision. The default Dockerfile and Compose configuration do not install or wire the optional learned encoder. See [SCALE.md](SCALE.md) before changing embedding models.

## Health, logs, and verification

```powershell
docker compose ps
docker compose logs --tail 100 db backend frontend
docker compose exec -T db pg_isready -U releaselens -d releaselens
docker compose exec -T backend python -m alembic current
Invoke-RestMethod http://127.0.0.1:8080/health
```

The health response should report `status: ok`, `database: postgresql`, and `demo: false`, plus the configured embedding and generator names. It checks `SELECT 1`; it does not prove corpus completeness, retrieval quality, authorization correctness, recovery readiness, or provider availability. The database and backend have Compose health checks; the frontend has no separate health check, so check the proxied health URL yourself. Long requests can delay health because database-backed HTTP requests share one process lock.

Request responses carry `X-Request-ID` and `Server-Timing`. Application middleware prepares structured INFO records containing request ID, route template, status, and latency; whether they appear depends on logger configuration. Questions, evidence, bearer headers, and raw URLs are excluded by that middleware. Nginx and other components have their own logs; inspect and redact before sharing. Logs have no configured centralized retention, alerts, or durable export.

The prepared Compose verification helper builds/starts services, ingests snapshots, runs the authenticated lifecycle and PostgreSQL tests, then records its results:

```powershell
python scripts/verify_docker.py
```

It is a write-capable verification workflow, not a read-only production probe. Use approved test data and a quiet local deployment. It writes `evaluation/docker-verification.json`; inspect its timestamp, commands, exit codes, and final status. Do not infer a fresh pass from a historical artifact.

For a 409, reload the current document head and review the intended change before retrying with `expected_revision`; do not blindly replay an obsolete update. For 401, check the active token and backend configuration. A 404 can mean absent **or unauthorized** evidence/answer; do not bypass the ACL to diagnose it for another user. For unhealthy startup, inspect database readiness, Alembic errors, and backend logs before restarting repeatedly.

## Backup without binary corruption

Use a maintenance window with no API/CLI writes when you need table-signature comparisons or a consistent operational checkpoint. PostgreSQL `pg_dump` itself uses a consistent database snapshot. Stop both UI and backend to prevent new application requests; the database stays running:

```powershell
docker compose stop frontend backend
New-Item -ItemType Directory -Force .backups
$backupStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupPath = ".backups/releaselens-$backupStamp.dump"
docker compose exec -T db pg_dump -U releaselens -d releaselens -Fc -f /tmp/releaselens-ops.dump
# Continue only if the preceding command succeeded.
docker compose cp db:/tmp/releaselens-ops.dump $backupPath
Get-FileHash -Algorithm SHA256 $backupPath
docker compose exec -T db pg_restore --list /tmp/releaselens-ops.dump
docker compose up -d --wait
```

Check every native command's exit code (`$LASTEXITCODE` in PowerShell); stop on failure. The archive is written **inside** the container and copied as a file. Do not use PowerShell `>` or text pipelines to capture `pg_dump -Fc` stdout: shell/version-dependent text encoding can corrupt the binary archive. `pg_restore --list` establishes readability, not a successful restore. Retain the local archive, hash, code commit, image identities, schema revision, and private configuration copy; copy backups to a separate protected location outside Docker Desktop's disk. The script ignores `.backups/` in Git, but that does not encrypt or independently preserve it. No automated schedule, retention policy, or recovery-point/recovery-time objective has been measured.

## Restore first into a separate database

Choose the backup deliberately and retain the current database. The following example reserves `releaselens_restore` as the disposable destination. `createdb` must succeed; if that name already exists, stop and choose a new name consistently in all subsequent commands. Do not drop an unknown existing database.

```powershell
$backupPath = '.backups/releaselens-YYYYMMDD-HHMMSS.dump'
Get-FileHash -Algorithm SHA256 $backupPath
docker compose cp $backupPath db:/tmp/releaselens-restore.dump
docker compose exec -T db createdb -U releaselens releaselens_restore
docker compose exec -T db pg_restore -U releaselens --exit-on-error --no-owner -d releaselens_restore /tmp/releaselens-restore.dump
docker compose exec -T db psql -U releaselens -d releaselens_restore -v ON_ERROR_STOP=1 -c 'SELECT version_num FROM alembic_version; SELECT count(*) FROM documents; SELECT count(*) FROM revisions; SELECT count(*) FROM passages; SELECT count(*) FROM answers; SELECT count(*) FROM dependencies; SELECT count(*) FROM changes; SELECT count(*) FROM reviews;'
```

Check every exit code before continuing. Match the SHA-256 to the recorded backup hash, inspect restored contents, and compare expected counts/data signatures. Counts alone do not establish completeness or semantic correctness. Use the matching application/schema version for a restored backup; do not automatically point new code at an old schema. A recovery rehearsal must also test authorized question, citation, saved-answer, and history access against the restored copy before cutover. The helper below checks exact row signatures but does not perform that full user-facing rehearsal.

If the restore is an actual replacement of a failed local database, take a fresh preservation backup first where possible, stop writers, and switch names only after validating the clone. These commands **change the active database**; execute only for the intended recovery, with no other PostgreSQL clients connected to either target:

```powershell
docker compose stop frontend backend
docker compose exec -T db psql -U releaselens -d postgres -v ON_ERROR_STOP=1 -c 'ALTER DATABASE releaselens RENAME TO releaselens_before_restore;'
# Continue only after the rename succeeds. An existing preservation name is a stop condition.
docker compose exec -T db psql -U releaselens -d postgres -v ON_ERROR_STOP=1 -c 'ALTER DATABASE releaselens_restore RENAME TO releaselens;'
docker compose up -d --wait
Invoke-RestMethod http://127.0.0.1:8080/health
```

If the second rename fails, keep services stopped and restore the first name before resuming. Startup applies migrations, so confirm the checked-out code is compatible before `up`. Recheck authenticated access, preserved citations, original answers, dependencies, and history. Data created after the selected backup is absent from the restored copy; it remains in `releaselens_before_restore` for deliberate reconciliation. Do not delete that preservation database or the backup during the recovery session.

## Automated recovery check and rollback limits

`python scripts/verify_recovery.py` requires a running healthy Compose deployment and a quiet maintenance window, including no CLI writes. It captures table counts and deterministic row signatures, creates a custom-format backup through container-file copy, restores it to a random `releaselens_verify_<hex>` clone, compares all seven data tables, then runs Alembic downgrade-to-base and upgrade-to-head **only on that clone**. That destroys the clone's restored records and checks for empty recreated tables. The generated clone is dropped in `finally`; the backup is retained under `.backups/`. It then restarts the live backend and checks proxied PostgreSQL health and unchanged live signatures. Expect a brief API interruption.

The script does not restore over or downgrade the live database. A crash or early failure can leave a clone or a `/tmp` archive for manual inspection; identify it carefully before cleanup. It writes `evaluation/recovery-verification.json` only after success. A pre-existing success file does not prove the current invocation passed. The 2026-10-15 Windows run passed; the dated recovery-verification.json retains all checks and data signatures. Re-run for a new deployment rather than treating historical evidence as its verification.

The initial migration's downgrade drops application tables. It is a **destructive schema test**, not a safe production rollback. Application rollback requires a recorded previous commit/image and a schema compatibility assessment; source checkout alone does not roll back records or migrations. Before upgrades, back up, rehearse migrations/restore in a clone, and retain the previous build. If an incompatible migration has run, use a planned forward fix or validated restore rather than a blind downgrade. Current image tags (`python:3.12-slim`, `pgvector/pgvector:pg16`, `nginx:1.28-alpine`) and downloaded build dependencies are not a guarantee of byte-identical rebuilds; record resolved image IDs/digests and pin reviewed digests for a reproducibility-sensitive release.

## Fresh browser verification without touching the existing demo

On the owner’s Windows computer with the optional installed Edge/Playwright requirements, run `python scripts/verify_demo_v3.py`. It owns a new temporary 14-snapshot SQLite database and loopback port8001, executes browser/identity-race and100-request concurrency-eight checks, then stops its own process tree and removes only its temporary directory. It preserves the existing port8000 demo and Docker deployment. See `evaluation/demo-v3-verification.json`; these are functional checks, not a production capacity claim.
