# Acceptance checklist and verification status

The exact latest test/static results are in `evaluation/verification.json` and `evaluation/test-results.xml`. Results below distinguish executed checks from prepared configuration. No live deployment or human review is implied.

| Requirement | Status | Evidence or remaining work |
| --- | --- | --- |
| Application startup | Verified in-process | FastAPI TestClient lifespan, DB initialization, health and endpoint tests |
| Local executable entry point | Implemented | `python -m releaselens --demo`; live TCP/browser not independently verified here |
| Four immutable licensed source snapshots | Verified | `data/source-status.json`, adjacent LICENSE/manifests, hash-tamper tests |
| Repeatable ingestion | Verified locally | Four source manifests ingested in tests and CLI; repeat is idempotent |
| Release separation | Verified locally | Explicit filtering, unknown-release abstention, prompt override/baseline checks |
| Learned semantic retrieval | Adapter only | Hashing is the default test double; learned weights/quality unverified |
| Hybrid retrieval | Verified locally | BM25 + hash dot product/RRF; controlled 24-case diagnostics |
| Reranking | Experimental heuristic | No cross-encoder quality claim; independent ablation required |
| PostgreSQL pgvector + FTS | Prepared, not executed | Alembic vector/FTS migration, SQL ranking path, dedicated integration test and CI service |
| Citation traceability | Verified locally | Exact immutable quote, metadata and claim containment; tampering rejected |
| General claim entailment | Pending | Exact extraction does not prove relevance or completeness |
| Cross-version comparison | Verified locally | Independent cited results for both versions |
| Unsupported queries | Limited verified probes | No-overlap/unknown-release abstention; calibrated unanswerability remains pending |
| General conflict detection | Partial | Explicit synthetic fact disagreement only; natural-language contradictions pending |
| Saved source dependencies | Verified locally | Relational passage dependencies, owner-scoped inspection |
| Meaningful source change handling | Verified synthetic lifecycle | Technical edits queue cited answers; same fact can remain valid |
| Formatting-only change handling | Verified conservative subset | Trailing whitespace/line endings; subsequent technical update still finds old citations |
| Structural source diff | Partial | Logical-key comparison; upstream paragraph movement can create broad review work |
| Revalidation/correction/audit | Verified synthetic lifecycle | Original preserved, separate correction, immutable idempotent review per evidence heads |
| Real prose semantic staleness | Pending | Changed prose goes to manual review; no automatic correctness claim |
| Authorization | Verified tested boundaries | Multi-role retrieval, direct IDs, owner/history scopes, downgrade, generator spy |
| Injection defenses | Limited demonstration | Quarantine patterns + no tools + exact output validation; comprehensive resistance unproven |
| Frontend | Implemented, API/assets verified | JavaScript syntax and backend contract tests; browser interaction/layout unverified |
| Browser preview | Blocked | Managed supervisor shell could not locate Python |
| Docker startup | Blocked | Docker unavailable; Compose, Dockerfile, health checks and CI job prepared |
| Tests and static checks | Executed | Latest report records counts, skipped PostgreSQL test and dependency warning |
| Dependency scan | Executed | `evaluation/dependency-audit.json`; no known vulnerabilities reported for scanned locked dependencies |
| Human-reviewed benchmark | Pending | 24 synthetic development cases only; 300–500 final target not populated |
| Tuning/held-out results | Pending | Protocol defines family/release holdout; no test-split results invented |
| p50/p95/cost | Limited measured diagnostics | Local retrieval timing, default no-provider cost; model cost/serving latency unmeasured |
| GitHub repository/CI | Blocked | Connection not installed; workflow source prepared but not remotely run |
| Hosting URL | Blocked | Account, provider and budget choice required; no deployment claimed |
| Human engineering ownership | Pending | User specification recorded; no independent code/review attributed yet |
| Astra Extra High final review | Pending | Requested model preference recorded; no ability to switch active model here |

## Next feasible milestone

Run the downloadable source locally, implement the uncited-section regression in `OWNERSHIP.md`, and review one design choice. In parallel once an appropriate environment/account is available: execute PostgreSQL/Compose CI, select a pinned learned encoder, and begin independent relevance annotations. Browser verification and external publication follow those concrete checks.
