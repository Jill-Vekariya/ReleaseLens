# Deployment assessment — 2026-10-15

No hosting account was selected, no charges were authorized, no repository was published, and no live URL is claimed.

## Compared options

| Option | Fit | Restrictions/cost considerations | Decision |
| --- | --- | --- | --- |
| Local Compose | Full Python + persistent PG/pgvector | Requires Docker; local operation, no public demo URL | Reproducible configuration prepared; startup unverified here |
| Render | Python web service + managed PostgreSQL | Free web services sleep after 15 idle minutes; free PG expires after 30 days | Suitable short trial; not a durable free DB assumption |
| Railway | Container/Python + PostgreSQL + persistent volumes | Hobby documented at $5/month minimum commitment, resource usage can exceed it | Candidate for low-cost persistent pilot; requires account/budget choice |
| Fly.io | Container service + managed PG supporting pgvector | Managed PG plan/storage and app usage priced separately; more operations decisions | Viable alternative; no claim of a free persistent stack |
| Sites | Worker-based site hosting | Does not run this Python/PostgreSQL service as-is | Not a backend deployment substitute |

Primary references checked:

- [Render free services](https://render.com/docs/free)
- [Railway pricing](https://docs.railway.com/pricing)
- [Railway billing](https://docs.railway.com/pricing/understanding-your-bill)
- [Fly Managed PostgreSQL](https://fly.io/docs/mpg/)
- [Fly resource pricing](https://fly.io/docs/about/pricing/)

Prices and restrictions must be rechecked when provisioning. The candidate recommendation is an inference from the documented Python/database fit and cost structure, not a deployed comparison.

## Exact blockers

1. **GitHub connection:** plugin discovery found GitHub available but not installed/connected. A previous connection suggestion was already recent, so it was not repeated. Connect GitHub and select the account/repository visibility before remote publication.
2. **Docker/PG runtime:** absent in the execution environment. Run the prepared Compose or CI jobs in a Docker-enabled environment and fix any failures before claiming verified container operation.
3. **Hosting identity and spend:** select a provider/account and approve the intended budget before provisioning billable services. No API keys were requested or invented.
4. **Browser QA:** the managed preview supervisor could not locate Python. No browser screenshots or successful interactive QA are claimed.
5. **Learned inference:** encoder weights/provider credentials and a reviewed evaluation set are still needed for quality claims beyond exact extraction.

## Concrete publication sequence

Run unit/static checks, PostgreSQL integration, and actual Compose health tests. Verify pgvector/FTS queries and migration rollback in a disposable database. Inspect tracked files for credentials and confidential data; `.env`, runtime databases and logs are excluded. Create the chosen remote repository, push source and observe CI. Provision a persistent database and Python service with demo mode disabled. Configure server-side credentials/TLS, ingest approved pinned sources, test role/owner boundaries, and test a real hosted question/update/revalidation lifecycle. Record the returned URL only after deployment and smoke verification.

Before any public launch, complete authentication/rate-limit hardening described in SECURITY.md. A private engineering pilot can be considered after its actual operational checks pass; this repository alone does not establish production readiness.
