# Architecture and provisional decisions

Date: 2026-10-15. Authored with AI assistance. Decisions below are proposals implemented to validate a vertical slice, not approvals attributed to the user.

| Decision | Chosen approach | Alternative / tradeoff | Validation |
| --- | --- | --- | --- |
| Service topology | One modular FastAPI application | Microservices increase operations and consistency complexity | In-process startup, endpoint, and transaction tests |
| Persistence | SQLAlchemy; SQLite locally, PostgreSQL deployment schema | PG-only would block useful execution where a server is absent | SQLite verified; PG integration job pending execution |
| Evidence identity | Document + release identity, immutable revision/passage UUID, logical passage key | Updating passage text in place destroys auditability | Original answer and evidence survive updates |
| Version selection | Explicit project/release fields; exact filtering | Inferring an unspecified release risks silent use of newer instructions | Unknown release abstains; prompt cannot override explicit release |
| Embeddings | Hash-based test double by default, opt-in learned encoder | Downloading a learned model adds runtime size and quality claims needing evaluation | Hash repeatability tested; learned quality pending |
| Lexical retrieval | BM25 locally, PostgreSQL FTS in deployment path | Their rankings differ; they are not interchangeable measurements | Local ranking tests; PG CI pending |
| Fusion | Reciprocal rank fusion, constant 60, candidate depth 20 | Score normalization needs calibration across dense/lexical scales | Development runner; tuning pending |
| Reranking | Optional section-overlap heuristic experiment | A cross-encoder may be more accurate but adds latency and downloads | Not enabled in default version mode; available for explicit comparison only |
| Generation | Exact extracts; compatible LLM adapter can select substrings | Fluent generation needs stronger entailment labels and validation | Exact membership checked without an LLM judge |
| Impact tracking | Relational answer → cited passage dependencies across all prior revisions | Whole-corpus revalidation is expensive; dependencies miss new contradictory sources | Multi-update and formatting-intermediate regressions |
| Revalidation | Synthetic structured fact comparison; real prose reviewed conservatively | General contradiction/entailment models introduce false positives | Synthetic diagnostics only; no semantic correctness claim |
| Authorization | Trusted principal, SQL/application ACL, owner-private answers | LLM or frontend-only enforcement is insufficient | Multi-role, ID access, role downgrade, saved history tests |
| Caching | No result cache in v0.1 | A future cache needs principal, ACL epoch, release, revision and model scope | Repeated cross-role/version tests; no cache-performance claims |
| Deployment | Full Python service + PostgreSQL; no substituted static demo | Sites uses a Worker runtime incompatible with this backend | Local source prepared; hosting account and billing decision pending |

## Data lifecycle and consistency

An administrator submits a document snapshot with a unique logical key per section. Input uses strict schemas and rejects unknown fields. A document update must carry `expected_revision`; conflicting writes return 409. A PostgreSQL row lock serializes updates to an existing document, while the unique project/release/key constraint catches concurrent creation. A local process lock serializes SQLite transactions. This is not a distributed job system.

The entire revision, passages, document head change, change record, and affected-answer state transition occur in one database transaction. An exception rolls them back. Repeat ingestion of identical content/provenance is a no-op. Revalidation is idempotent for an answer and set of observed current evidence heads; a unique review fingerprint and answer row lock prevent duplicate audit/correction rows in the supported endpoint path.

Dependencies reference physical passage IDs. Formatting changes still create a new immutable snapshot, but need not mark an answer pending. Impact detection examines historical citations as well as the immediately previous revision. Without that step, an answer citing revision 1 would be missed after formatting revision 2 followed by technical revision 3.

Review compares saved evidence with the **latest head in the same release**, not the newest software release. A new software version does not automatically invalidate historical guidance for an older release.

## State semantics

| State | Meaning |
| --- | --- |
| unaffected | No detected relevant change to the cited evidence since save |
| revalidation_pending | At least one cited logical passage changed or disappeared |
| reviewed_still_valid | Normalized extract unchanged, or explicit synthetic fact value unchanged |
| confirmed_stale | A trusted synthetic exclusive fact has a different value |
| insufficient_evidence | Source missing/quarantined, or no dependencies available |
| manual_review_required | Real or unstructured prose changed; correctness is not determined |

`unaffected` does not guarantee overall correctness: newly introduced contradictory evidence, initially incomplete retrieval, and unrecorded dependencies can escape this detector. A saved answer with conflicting evidence is an abstention; its citations are retained for review, not presented as a supported answer.

## Scale and next boundaries

SQLite ranking loads the authorized small corpus and computes scores in process; it is not a million-chunk architecture. The PostgreSQL path performs exact vector search and full-text ranking with ACL/version predicates before candidate limits. No approximate vector index, row-level security, tenant partitioning, distributed revalidation worker, or load-tested throughput is claimed. Exact vector scans will need profiling and ANN experiments before scaling.

Future workers need transactional outbox/event IDs, idempotent job claims, retries, stale-head detection, and a review policy for concurrent document updates. User/tenant access should become an audited membership table with revocation epochs and PG row-level security as defense in depth. The current fixed classifications demonstrate role permissions only, not organization tenancy.
