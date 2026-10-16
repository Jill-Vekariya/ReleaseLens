# Deployment state

The complete application is deployed locally on the owner's authorized Windows computer using Docker Desktop: Nginx → FastAPI → PostgreSQL/pgvector, with persistent named database storage. Access is loopback-only at http://127.0.0.1:8080. A separate teaching demo runs at http://127.0.0.1:8000. These addresses work on that computer, not as externally reachable demo links.

Source is in the [private GitHub repository](https://github.com/Jill-Vekariya/ReleaseLens). CI executes unit/static, PostgreSQL and Docker jobs. Check the commit/run recorded in STATUS.md; configuration alone is not a passing run. No public hosting, subscription or paid service has been provisioned.

## Reproduce the private local deployment

Follow README setup and [OPERATIONS.md](OPERATIONS.md). Generate private credentials once with `scripts/configure.py`, start Compose, ingest approved snapshots in a maintenance window, then run `scripts/verify_docker.py` and `scripts/verify_recovery.py`. The latter restores and migrates only a generated disposable database and retains its binary backup locally. It never restores over the live DB.

Keep one backend process and do not run independent CLI writes concurrently. Demo mode stays disabled in Compose. Tokens are server-configured; fixed role identities are a local engineering authentication mechanism. Never share `.env`, real tokens, backup contents or database files.

## Exact remaining off-device setup

1. Select an account/provider with an existing authorized private container/Python runtime, persistent PostgreSQL 16 with pgvector, and a known budget. Do not assume a durable database is free; recheck prices and limits before approval.
2. Configure private network access or authenticated site gating and TLS before ingesting data. Retain application authentication as well; network gating does not replace source/owner authorization.
3. Store `DATABASE_URL` and `RELEASELENS_TOKENS` in provider secret storage. Deploy a reviewed immutable image/commit, run Alembic, and use one API worker. Do not expose PostgreSQL or demo mode.
4. Ingest the licensed source snapshots, run the authenticated HTTP workflow and direct-ID/owner/history checks, and verify backup/restore and restart persistence on that provider. Set health checks and collect request-ID/status/latency logs without source text or secrets.
5. Record the actual private URL, image digest, database backup policy and tested rollback only after verification. Public accessibility requires the owner's explicit approval.

A compatible off-device private hosting account/budget is not available in this session. This is the remaining external dependency, not an implementation substitute. Sites' Worker runtime does not execute the Python backend; a static page would not complete this deployment.

## V3 deployment compatibility

This continuation needs no schema migration beyond the existing Alembic head. Default Docker operation retains deterministic retrieval/extraction; learned weights are not baked into the image. The expanded snapshots are bundled, and optional ingestion must happen in a maintenance window. Do not run an independent CLI writer concurrently with active API traffic.

For an existing Compose deployment, first back up and verify recovery per OPERATIONS.md. Build the reviewed image, stop the backend, run `docker compose run --rm --no-deps backend python scripts/ingest_sources.py --expanded`, then start the backend and verify health/authorization. Keep the existing `.env` and named PostgreSQL volume. Never use `docker compose down -v` on the owner's deployment. The CI cleanup command applies only to ephemeral CI data.

`ANSWERABILITY_POLICY` is a native SQLite experiment requiring the recorded learned index; the measured SQLite policy deliberately refuses PostgreSQL startup. `ENABLE_PROSE_REVIEW_CANDIDATES=true` is experimental and defaults false. Neither experiment is a production rollout. Human review, production identity/rate limiting, distributed consistency, resource/cost-approved off-device hosting and final semantic accuracy remain external/unfinished scope.
