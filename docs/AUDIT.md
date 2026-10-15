# Audit, priority and acceptance

Audit date: 2026-10-15. The six requested project documents were read before this expanded implementation. They accurately described the original archive but several deployment statements were stale relative to the newer private repository and Windows runtime.

## Source of truth

The original source ZIP is preserved by checksum in PROGRESS.md. The private GitHub repository and its Windows working tree are authoritative for execution. Uncommitted improvements were inventoried before further changes; the Linux workspace is a development mirror. No existing database, private credentials or prior answer history has been replaced.

## Highest priority findings

| Finding | Consequence | Action / acceptance |
| --- | --- | --- |
| PostgreSQL DISTINCT over JSON answer payload | Update endpoint fails despite SQLite tests | Fixed with affected-ID subquery; actual PG update/revalidation regression must pass |
| Thread-owned lock across FastAPI dependency worker threads | Real browser requests can fail under concurrency | Async transaction dependency lock; 50 concurrent requests complete without lock error |
| Formatting event compares all divergent historical evidence | Already adjudicated stale answers are unnecessarily requeued | Limit historical impact to logical keys changed by current event; regression asserts no requeue |
| Non-default production retrieval modes omit release predicate | Wrong-version candidates enter selection and are blocked only later | Exact release scope becomes default for every API mode; only explicit offline contamination experiment opts out |
| New contradictory passage leaves cited source untouched | Dependency-only graph misses affected saved answer | Bounded public synthetic fact counterevidence design; manual review, never automatic incorrect verdict from disagreement |
| Header-only body size guard | Chunked/false-size requests evade application limit | ASGI byte limit before JSON parsing; chunked and falsified-header tests |
| Hash encoder labeled by architecture ambitions | Readers could mistake a test double for learned semantics | Preserve explicit hash label; execute a commit-pinned CPU model separately and record actual environment/results |
| Tiny development suite overlaps all experimentation | Apparent retrieval improvement may not generalize | Frozen pilot; whole-topic family holdout; AI-reviewed labels clearly distinct from human verification |
| Runtime documentation lags actual evidence | Unsupported claims of both success and blocked work | Update README/status only against retained command/browser/CI evidence |

## Acceptance gates

1. Existing deterministic behavior and exact citation validation remain runnable.
2. Every production lexical/dense/hybrid query scopes project, release, current revision and authorization before limits; unknown releases abstain.
3. New public structured contradiction queues only relevant same-release saved claims and revalidation yields manual review. Private/wrong-release/quarantined sources cause no source-existence leak.
4. Original answers and evidence stay immutable; repeat reviews against identical evidence return the same audit; concurrent compare-and-swap updates have one winner and a clear 409 loser.
5. The learned encoder's model identity/commit, dependencies, indexing and actual diagnostic outputs are recorded; no human or general accuracy claim is inferred.
6. Real browser, Docker/PG, persistence restart, backup/restore and failure recovery checks pass or retain a precise failure report.
7. CI runs on the final pushed code. Repository and local services remain private/loopback; no charge or public host is created without approval.
8. Interview package includes verified demo, decisions, actual failure study, 25+ answered questions, independent exercises, walkthrough and four-week schedule.

## Limits retained deliberately

Exact quote membership does not prove relevance/completeness. Structured synthetic facts are not general contradiction detection. Fixed roles are not multi-tenant identity management. The small-corpus exact vector architecture has not been proven at large scale. A public production service still needs an identity platform, quotas/rate control and operational review. The 300–500-question target is not filled with artificial duplicates or relabeled as human-reviewed.
