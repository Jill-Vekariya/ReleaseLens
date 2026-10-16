# Architecture and decisions

AI-assisted engineering record, 2026-10-15. This describes implemented behavior; scaling proposals are in [SCALE.md](SCALE.md).

| Decision | Implemented approach | Trade-off |
| --- | --- | --- |
| Service | Modular FastAPI monolith and buildless UI | Simple reproducible deployment; serialized request transactions limit throughput |
| Persistence | SQLite demo; PostgreSQL/pgvector Compose deployment | Different lexical implementations; one benchmark does not validate both |
| Source identity | Project/release/document, append-only revisions and passages, logical section keys | Positional chunk movement can conservatively over-flag changes |
| Retrieval | SQL/application project, exact release, ACL, current head, quarantine and encoder filters before candidates | No inference of unspecified versions; unknown versions yield no evidence |
| Ranking | Lexical, exact dense, RRF depth 20 / constant 60 | Default hybrid has lexical eligibility gate and can miss zero-overlap semantic matches |
| Encoder | Hash test double; opt-in commit-pinned MiniLM | Stable baseline; learned download/runtime and fresh-index requirement |
| Generation | Exact extract selector and deterministic membership validation | Quotation is verifiable; relevance, completeness and entailment remain separate |
| Reranking | Pinned pretrained cross-encoder in offline matched evaluation; optional four-candidate relevance gate in API; section-overlap heuristic remains separate | Reranking improves some proposed ordering metrics at substantial CPU latency; no independent semantic accuracy claim |
| Dependencies | Physical cited passage IDs, historical logical-key matching on changes | Avoids mutable citations; uncited general counterevidence remains a hard problem |
| Counterevidence | New public synthetic fact assertions, same project/release, differing value | Bounded policy, potential effect only; private existence cannot leak through status |
| Reviews | Fingerprint of cited heads + current public fact conflicts + policy version | Idempotent within supported writer model; no natural-language adjudicator |
| Authorization | Fixed server-side roles; owner-private answers, dependencies, history | Demonstrates permissions, not organization tenancy or full identity lifecycle |
| UI identity | Epoch and AbortController across async workflows | Suppresses stale responses; cannot undo a server mutation already committed |
| Transactions | One process async lock; dependency function scope commits before send | Avoids false success on failed commits; independent writers/multiworker unsupported |
| Cache | No result cache | Avoids premature authorization/revision cache key contracts |

## Lifecycle

An administrator ingests strict validated sections. Existing-document edits require `expected_revision`; stale updates return 409. Existing PostgreSQL document rows are locked; unique constraints protect creation identity. Revision, passages, current head, diff and answer-state updates share one transaction. Identical source/provenance is a no-op. Errors roll back before the response acknowledges success.

Dependencies cite physical immutable passages. A formatting-only revision still creates a snapshot. Subsequent impact searches historical dependencies using the logical keys changed in the current event; it does not invalidate every answer citing the same document. Normalization preserves case and code indentation, canonicalizes line endings/trailing whitespace/blank runs, and is intentionally narrow. Output schemas preserve exact whitespace.

A provider-selected substring inherits synthetic fact metadata only if it equals the full assertion passage. Upstream metadata assertions, blank fact keys and values are rejected; revalidation also checks synthetic source provenance defensively. Synthetic fact equality validates the curated fact, not all prose in a changed passage.

## Review states

| State | Meaning |
| --- | --- |
| unaffected | No detected effect under the implemented policy; not a correctness guarantee |
| revalidation_pending | Cited logical content changed/disappeared, or eligible new public counterevidence arrived |
| reviewed_still_valid | Existing normalized extract or curated synthetic assertion remains supported under this policy |
| confirmed_stale | A cited full synthetic exclusive assertion has a different value |
| insufficient_evidence | Missing/quarantined support or an original unsupported abstention |
| manual_review_required | Changed prose, assertion metadata uncertainty, conflict abstention, or public counterevidence; correctness undetermined |

New unrelated conflicting fact passages produce manual review without a correction, preserving the distinction between potentially affected and confirmed stale. Private/internal new counterevidence is excluded from public status/fingerprints, even for admin-owned answers. This trades completeness for a clear confidentiality contract. Removed counterevidence does not automatically queue resolution; explicit review observes the new fingerprint, which may reuse an earlier matching assessment. Review histories record distinct evidence states, not every button press.

## Consistency and security boundaries

The process lock covers the supported API path. CLI ingestion and other processes bypass it. Neither row locks nor unique review fingerprints establish a serializable corpus snapshot across distributed ask/ingest/review operations. Production deployment is constrained to one worker and maintenance-mode ingestion until a snapshot/retry protocol exists. Provider calls hold the request lock, so a slow selector can delay other DB requests.

Source ACL and owner access are rechecked on direct IDs, dependencies and histories. Fixed roles are server-configured, tokens compared in constant time, responses uncached, request bodies bounded, and logs omit source text/questions/tokens. Prompt quarantine is a limited heuristic; it is not comprehensive prompt-injection prevention. Trusted admin provenance assertions and SQLite physical file access are explicit trust boundaries.

## Optional v3 stages

`relevance.py` implements an opt-in pinned cross-encoder relevance gate after authorized version-mode retrieval and before extraction. It was calibrated only for SQLite, its recorded learned encoder, k=4, and at most one selected extract; startup rejects encoder/backend mismatch and incompatible HTTP requests return 422. It does not classify entailment, contradiction or permissions. Default operation does not import/load learned models.

`prose_impact.py` adds an opt-in deterministic lexical candidate stage for public upstream prose. New normalized content after an answer was saved, same project/release, current head and quarantine filters apply before comparison. Cited logical sections stay with dependency handling; private source existence cannot affect public answer status/fingerprints. Candidate evidence includes the immutable quote, source and matched terms, and joins review fingerprints. Poor replay results keep this stage disabled by default. General prose cannot produce `confirmed_stale` through this rule. No schema migration is required.

Keyless compatible endpoints omit Authorization rather than sending an invalid empty Bearer header. Loopback inference bypasses environment proxies, preserving local-only routing; remote HTTPS endpoints retain normal proxy behavior. Actual small-model output and transport failures remain separate evidence.
