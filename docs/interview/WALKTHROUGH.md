# Code walkthrough and understanding checklist

AI-assisted navigation guide, 2026-10-15. All checkboxes begin unchecked. A reader should mark one complete only after explaining the behavior and showing the relevant code or observed output. This is separate from verification reports and does not claim human review.

## Trace one answer end to end

| Step | Source to read | Explain or inspect |
| --- | --- | --- |
| 1. Startup | `releaselens/__main__.py`, `api.py:create_app`, `db.py:database` | Loopback binding, demo flag, configured bearer identities, encoder/generator selection, SQLite schema creation and demo-only seeding |
| 2. Request/UI | `web/app.js:api`, ask-form handler; `schemas.py:AskRequest` | POST body, auth headers, default `save=True`, `k` bounds, rejected extra fields; frontend identity-view clearing |
| 3. Identity and session | `api.py:principal`, `session_dep`; `security.py:Principal` | Bearer precedence, role classifications, async lock covering every session-backed request and transaction lifecycle |
| 4. Retrieval | `service.py:ask`; `retrieval.py:rank`, `postgres_rank` | Current-head, project, ACL, quarantine and model predicates; release filtering in every production mode; lexical eligibility, candidate limits and stable ties |
| 5. Selection and validation | `generation.py`; `service.py:citation`, `validate_citations` | Default full-passage extracts, compatible selector boundary, exact metadata/quote checks, claim substring membership and final answer assembly |
| 6. Save | `service.py:ask`; `models.py:Answer`, `Dependency` | Owner, original payload and physical passage dependencies; abstentions can also be saved, so inspect dependencies and claims separately |
| 7. Read later | `service.py:owned_answer`; answer/detail/history routes | Owner checks plus current document authorization; administrators cannot bypass owner privacy |

Use a single real request and record its saved answer ID, one passage ID, one revision ID, encoder and source type. Explain where each field originates instead of copying an entire JSON response into notes.

## Trace a source update and review

| Step | Source to read | Explain or inspect |
| --- | --- | --- |
| 1. Ingest contract | `schemas.py:Section`, `IngestRequest`; `api.py:ingest_route` | Administrator-only write; unique logical section keys; fact assertions restricted to synthetic evidence; immutable source commit required for upstream provenance |
| 2. Existing identity | `ingestion.py:ingest` | `(project, release, document_key)`, existing-row lock, classification immutability, identical content/provenance early return and model identity check |
| 3. Snapshot | `ingestion.py`; `models.py:Revision`, `Passage` | Expected-head conflict, new immutable physical IDs, conservative normalization, raw/normalized hashes and source metadata; PG dense-vector update |
| 4. Impact | `ingestion.py:changed`, `changed_keys`, `changed_ids` | Compare immediate heads to identify changed keys, then find all historical physical IDs for those keys; answer-ID subquery avoids JSON DISTINCT |
| 5. Visibility/commit | `ingestion.py`; `api.py:session_dep` | Other owners' affected answers can become pending without their IDs being returned; transaction commits snapshot, head, diff and statuses together |
| 6. Review | `api.py:revalidate_route`; `service.py:revalidate` | Answer row lock in supported API path, ownership, latest same-release heads, fingerprint lookup and verdict precedence |
| 7. Audit/correction | `models.py:Review`; `service.py:revalidate` | Separate correction ask, preserved original payload, updated evidence and immutable review record; correction existence does not ensure non-abstention |

Trace 30 → formatting 30 → 60 and separately 30 → 60 → reviewed stale → formatting 60. Explain why these sequences guard different bugs. Leave the original independent two-section exercise unsolved until you implement it yourself.

## Read the tests as contracts

| Test file | Contract to understand | What it does not establish |
| --- | --- | --- |
| `tests/test_lifecycle.py` | Staleness/corrections, formatting, removals, changed prose, idempotence, latest heads and rollback | General semantic correctness or every structural edit |
| `tests/test_security.py` | ACL before retrieval, direct IDs, owner histories, same-user downgrade, production auth, quarantine and citation tampering | Complete prompt-injection resistance or a formal information-flow proof |
| `tests/test_concurrency.py` | 50 concurrent ASGI requests complete with distinct saved IDs | Load capacity, real-network scheduling or cross-process correctness |
| `tests/test_postgres.py` | Actual pgvector/FTS, release/ACL boundaries and save/update/revalidate lifecycle when configured | SQLite tests cannot substitute for running it; functional pass is not scale evidence |
| `tests/test_sources.py` | Source/manifest integrity and ingestion expectations | Independent upstream attestation for arbitrary administrator-submitted URLs |
| `tests/test_generation.py` | Compatible-selector contract and failure behavior with mocks | Live provider quality, cost or availability |
| `tests/test_migrations.py`, `test_api_contract.py` | Migration/API contracts exercised by their assertions | A full deployment guarantee; read exact assertions before describing coverage |
| `tests/test_retrieval.py`, `test_evaluation.py` | Ranking/normalization basics and metric edge cases | Human-reviewed answer accuracy or calibrated abstention |

## Read operational boundaries

- [ ] Explain `docker-compose.yml`, `Dockerfile`, `nginx.conf` and `alembic/versions/0001_initial.py`: service topology, migration startup, health checks and database exposure.
- [ ] Inspect `scripts/configure.py` without printing tokens into shared notes. Explain why random local tokens are credentials, while synthetic canaries are teaching data.
- [ ] Read `scripts/ingest_sources.py` and one source manifest. Distinguish source-file/license hash checks from HTTP provenance assertions.
- [ ] Read `scripts/docker_smoke.py`, `scripts/verify_docker.py` and browser verification code before claiming the exact scope of a passing report.
- [ ] Inspect `.github/workflows/` and the CI run for the commit under discussion. A previous green run does not verify later fixes.
- [ ] Inspect `evaluation/results.json` and `releaselens/evaluate.py`. Find the dataset hash, mode definitions, latency clock, relevant-document denominator and null metrics.
- [ ] Explain why `scripts/verify_semantic.py` passing would demonstrate learned-encoder execution on selected snapshots and controlled diagnostics, while human relevance/accuracy remains pending.

## Understanding checklist

### Evidence and retrieval

- [ ] I can state the document identity and explain physical versus logical passage identity.
- [ ] I can show why source revisions and old passage text remain accessible after the head changes.
- [ ] I can distinguish a raw hash, normalized hash, upstream commit and passage UUID.
- [ ] I can explain why no learned semantic claim follows from the default 384-dimensional hash vector.
- [ ] I can compute a small RRF example and explain why raw score magnitudes are discarded.
- [ ] I can show the lexical gate and explain a synonym-only false negative.
- [ ] I can identify concrete SQLite/PostgreSQL ranking differences without calling them equivalent.
- [ ] I can explain why exact membership is weaker than relevance, entailment or completeness.

### Consistency and changes

- [ ] I can identify exactly where the API transaction begins/ends and which writes roll back together.
- [ ] I can explain why identical ingestion is checked before a non-identical expected-head conflict.
- [ ] I can distinguish the per-app async lock, PostgreSQL row locks and database uniqueness constraints.
- [ ] I can describe both the RLock ownership failure and the current serialization limitation.
- [ ] I can explain why affected-answer lookup uses an ID subquery rather than DISTINCT JSON rows.
- [ ] I can trace historical citations through an intermediate formatting revision.
- [ ] I can explain why a formatting event should not requeue an already reviewed stale answer.
- [ ] I can state every review verdict, its limits and the current multi-condition precedence.
- [ ] I can explain the review fingerprint and why a new head yields a new review identity.
- [ ] I can trace the bounded public synthetic counterevidence stage and identify a prose contradiction it still misses.

### Permissions, evaluation and ownership

- [ ] I can show backend ACL predicates and owner checks on retrieval, evidence, answers and history.
- [ ] I can explain why a same-owner downgrade still requires dependency authorization checks.
- [ ] I can distinguish synthetic demo role selection from bearer authentication and tenancy.
- [ ] I can describe quarantine bypass limitations and why text/model output cannot grant access.
- [ ] I can state the actual 24/6/8 development scope and why it is not a held-out benchmark.
- [ ] I can explain why zero observed leaks and perfect synthetic outcomes are limited evidence.
- [ ] I can identify which claims remain pending: human labels, learned-model quality, load scale and production hosting.
- [ ] I can name the exact code or tests I independently wrote, or honestly say none yet.
- [ ] I can finish the demo while preserving original evidence and distinguishing synthetic from upstream sources.

## Record your own walkthrough

Copy these prompts into your personal notes after completing a session: date/environment; request IDs and source IDs used; functions traced; output observed; unexpected behavior; independent change; assistance used; review received; next unresolved question. Keep credentials and private source text out of shared notes. Do not mark the checklist complete just because tests ran.
