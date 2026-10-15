# ReleaseLens AI specialist review

Date: 2026-10-15. This is an AI-assisted code review of the local development mirror. It is not an independent human review, a penetration test, or a claim of general semantic correctness. Runtime verification performed by the coordinating agent is recorded separately; this review did not access remote services or Git.

## Scope and decision

Reviewed the six project orientation documents, `docs/IMPACT_REVIEW.md`, and the actual ingestion, retrieval, generation, revalidation, authorization, persistence and endpoint code. The review concentrates on the new public synthetic counterevidence integration and its interaction with existing claims, dependencies and review fingerprints. A separate specialist reviews the browser identity-transition behavior.

Three additional defects were reproduced in the supported single-process API path and fixed by the coordinating agent. The original reproductions now pass independently, and the final local suite passes **101 tests with one PostgreSQL-only skip**. The latest source review found no remaining high-severity correctness blocker in the supported serialized API scope. This is a bounded review conclusion, not a guarantee of absence of defects or approval for multiworker/public production use.

## Findings and corrections

| Priority | Reproduced finding | Correction observed and independently checked |
| --- | --- | --- |
| High: evidence fidelity and availability | Ingesting a synthetic fact passage ending in spaces and CRLF succeeded, but asking about it returned HTTP 500. Output schemas stripped whitespace after the service bound full-passage fact metadata. They also removed leading code indentation and changed citation quotes. | Citation, claim and answer payload schemas preserve whitespace. A fresh answer for an indented, CRLF-terminated fact passage now returns HTTP 200; the claim, quote and answer exactly equal the stored passage. |
| High: trusted fact boundary | `fact_key=""` bypassed the upstream metadata prohibition. Updating that upstream assertion from 30 to 60 produced `confirmed_stale`, despite the synthetic-only contract. | Blank metadata is rejected; upstream requests reject any fact metadata rather than testing its truthiness. Revalidation additionally requires both prior and current revisions to be synthetic. Empty and whitespace-only upstream keys now return HTTP 422. Only fact key/value boundary whitespace is canonicalized; evidence text remains exact. A regression verifies that adding metadata whitespace does not create false staleness. |
| High: transaction acknowledgement | The default FastAPI yielded dependency committed after the response. Injecting a commit failure produced HTTP 200 with a saved answer ID even though the answer was rolled back. | Database dependencies use function scope so transaction completion precedes response transmission. The same injected failure now produces HTTP 500 and the failed answer is absent. |

The earlier impact-design findings are also addressed in the inspected integration: partial provider extracts do not inherit passage-level facts, removed or renamed fact metadata requires review, empty/abstaining answers cannot become `confirmed_stale`, cited logical origins are excluded from new-source counterevidence, and production retrieval modes apply release filtering before ranking. Deliberately unsafe release ablations require an explicit offline flag.

## Evidence and permission assessment

The counterevidence query checks project, release, public classification, current revision, synthetic source type and quarantine status in SQL. Structured saved claims are anchored to their real relational dependencies and must equal the complete asserted passage. New counterevidence compares exact fact keys and unequal values. It excludes each cited `(document_id, logical_key)` origin, keeping an ordinary cited-source replacement on the dependency review path.

The queue updates affected answers inside the ingestion transaction and returns only the ingesting principal's own answer IDs. Revalidation first checks ownership and permission for all saved dependencies. Private competing evidence does not enter the queue decision, returned counterevidence or review fingerprint. This matters because even a hash or changed review-existence result could reveal a private source's existence.

Review fingerprints include an explicit policy version, cited document heads, and immutable public counterevidence identities. The service captures counterevidence once for the fingerprint and assessment. Repeated review of the same evidence reuses the audit row. A public disagreement alone requires manual review and does not create a definitive correction. Original answer payloads and passage dependencies are preserved.

These observations support the bounded detector within the serialized endpoint scope. They do not establish source truth, relevant retrieval, natural-language contradiction detection, or correctness of every sentence in a full passage. In particular, an unchanged synthetic fact value validates the curated assertion only; it does not validate additional rewritten prose.

## Supported scope and remaining limits

- One application process serializes database request transactions. Multiple workers, independent applications, or a concurrent ingestion script bypass that shared lock. The source-ingestion CLI should not run concurrently with API writes under the claimed consistency scope.
- Multiworker operation needs a corpus snapshot/epoch protocol, stale-head validation and retries. Otherwise an answer can be saved after an impact scan using older retrieval, and reviews can observe incompatible heads. Distributed work additionally needs durable events/outbox entries and idempotent job claims. Existing per-document/answer row locks do not prove that wider protocol.
- The request lock covers provider calls, health checks and the uncapped answer scan. A slow provider or a large corpus can block other requests. This is an availability/scale limit, not a measured throughput claim.
- Removing or quarantining counterevidence does not automatically queue a resolution event. Explicit revalidation observes current eligible evidence and can resolve the prior result. This limitation must remain visible in the product contract.
- Source classification is immutable today. Future relabeling or revocation requires read-time authorization of stored review evidence, not only original dependencies.
- The detector handles public curated synthetic facts only. It does not discover arbitrary prose contradictions, adjudicate competing source authority, or calibrate semantic confidence.
- Successful historical checks and successful checks of the final source are distinct facts. Keep captured evidence tied to the source version actually executed.

## Final verification record

The reviewer initially ran 66 existing tests before the new regressions were added. That passing suite did not catch the defects above. The reviewer then independently repeated all three fault reproductions after the fixes and observed the corrected outcomes described in the findings table.

The reviewer reran the full final local suite: **101 passed, one PostgreSQL-only test skipped**. Ruff lint, Ruff formatting and JavaScript syntax checks also passed. One Starlette/httpx test-client deprecation warning remains. The integrated regressions cover fresh whitespace-preserving answers, blank/upstream fact rejection, failed commits without success acknowledgement, new public counterevidence, unchanged private counterevidence fingerprints, withdrawal through explicit review, metadata removal, abstention handling, concurrent expected-head conflicts and metadata-whitespace canonicalization. The PostgreSQL test now includes all production rank modes and the public counterevidence review path; the local skip is not substituted for its actual database execution.

The reviewer also inspected captured coordinating-agent artifacts:

- `evaluation/docker-verification.json` records a successful actual Docker build/start, authenticated PostgreSQL HTTP lifecycle and a separately executed PostgreSQL integration test.
- `evaluation/recovery-verification.json` records backup, isolated restore, table-signature preservation, disposable-clone migration round trip and restart persistence.
- `evaluation/browser-verification.json` and `evaluation/browser-security-verification.json` record installed Edge execution and delayed-response identity-change checks with no JavaScript errors.
- `evaluation/semantic-verification.json` records actual execution of the pinned 384-dimensional CPU encoder. The tuning pilot artifacts use 30 AI-labeled records, including 16 supported retrieval questions, with zero human-reviewed labels. Their 15/16 lexical, 15/16 learned-vector and 16/16 learned-hybrid Recall@4 results are descriptive tuning observations. Held-out generalization, semantic answer accuracy and abstention precision remain unmeasured.

No Docker, PostgreSQL, browser, CI or hosting execution is attributed to this reviewer. Reading a captured report is distinct from independently running its environment. The source-snapshot/chunking helper is now in the importable `releaselens.sources` module, avoiding a runtime package dependency on the scripts directory.

## Documentation and artifact handoff

The final read-only pass identified several descriptions for the coordinating agent to reconcile: the interview question bank's cross-instance consistency wording and verdict precedence; the walkthrough's all-mode release filtering, pre-response commit boundary, new counterevidence stage and UI identity epoch; and older status/progress descriptions of learned execution and browser checks. These are documentation drift, not newly discovered runtime blockers.

At the handoff, the newly extended resource-observation script had not yet been reflected in the transferred `retrieval-resources.json`, the Docker-browser artifact was awaiting transfer, and the pilot reports' recorded `benchmark.py` hash differed from the latest source. Refresh those artifacts before describing their new fields or the latest runner hash as verified. The coordinating agent owns that final evidence reconciliation.
