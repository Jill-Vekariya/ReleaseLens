# Public synthetic counterevidence: design and AI specialist review

Date: 2026-10-15. This is an AI specialist implementation/design review. It is not an independent human review, a human benchmark annotation, or evidence of general semantic correctness. The reviewed local mirror is the ReleaseLens implementation; deployment evidence is maintained separately by the coordinating agent.

## Decision and bounded claim

A new source or an uncited section can introduce a competing assertion without changing any cited passage. The new `releaselens/impact.py` helper detects that case for curated synthetic facts. It compares exact, case-sensitive `fact_key`/`fact_value` pairs within one project and release. Different values are a reason for review; they do not establish which source is correct.

The admission conditions are deliberately narrow:

- The saved answer is non-abstaining and has a structured claim anchored to its actual relational passage dependencies.
- Each accepted claim has matching synthetic fact metadata and contains the complete cited passage. Partial extracts are excluded because passage-level metadata does not prove that a substring asserts the fact.
- Counterevidence is synthetic, public, nonquarantined, and in its document's current revision. Internal/restricted counterevidence does not enter status transitions, returned records, or fingerprints, even for an administrator.
- The competing passage shares the saved claim's exact project, release, and fact key, and has a different non-null value.
- The claim's cited `(document_id, logical_key)` origins are excluded from this new comparison. Replacing a cited logical section remains the existing dependency-revalidation path.

This catches a new document, a newly added uncited section, a changed uncited assertion, or newly unquarantined public evidence. Existing immutable answers, claims, dependencies, and citations are preserved. It does not infer contradictions in prose, compare releases, adjudicate source authority, or claim general correctness.

## Integration contract

The helpers do not commit transactions and do not create reviews or corrections.

| Hook | Required integration |
| --- | --- |
| `queue_new_public_counterevidence(session, principal, document, old_passages, new_passages)` | Call in `ingest` after the new head/passages are flushed, before transaction completion, including newly created documents. Keep the existing identical-ingestion early return. Merge/deduplicate its returned IDs with the existing affected IDs. |
| `current_public_counterevidence(session, answer)` | Call in `revalidate` after owner/dependency authorization and the endpoint answer-row lock. Capture its result once for both the fingerprint and review assessment. |
| `review_fingerprint(heads, counterevidence)` | Replace the old cited-head-only hash. Check for an existing review using this result. |

The queue hook locks candidate answers in ID order, marks matching answers `revalidation_pending`, and returns IDs only for the ingesting principal's own answers. Its administrator check is additional protection; the ingestion endpoint remains the authorization boundary. Original answer owner scope must still be enforced on detail, history, and revalidation routes.

When counterevidence exists, add its returned records to the assessment and choose `manual_review_required` unless an independently supported, existing cited-source-change rule determines a stronger outcome. In particular, a new competing source alone must never yield `confirmed_stale`, create a definitive correction, or silently replace the original answer. The review should state that public synthetic assertions disagree and need adjudication.

## Fingerprints, permissions, and event semantics

The exact fingerprint input is a JSON object with `policy`, sorted `cited_heads`, and sorted `public_counterevidence`. The policy is `public-synthetic-counterevidence-v1`; JSON uses `sort_keys=True` and `separators=(",", ":")`, then SHA-256 of UTF-8 bytes. Each counterevidence record includes fact key, saved and counter values, and immutable document/revision/passage IDs. Sorting and deduplication occur in the helper's output. Repeated review of the same evidence and policy produces the same fingerprint; introducing or withdrawing a competing source changes it even when all cited heads remain unchanged. The policy component prevents reuse of pre-feature reviews under the old detector semantics.

Only public counterevidence can affect this fingerprint. Including private IDs in a hash would still create an observable status/review-existence side channel, so hashing private evidence is not an acceptable substitute for excluding it. The answer's own cited evidence continues to require authorization before review and before history access. Classification is currently immutable; if relabeling or source-specific revocation is introduced, all stored review evidence will need read-time ACL checks, including newly public-source-derived records that later become restricted.

Formatting revisions that preserve an existing `(logical_key, fact_key, fact_value)` do not requeue answers, including previously `confirmed_stale` answers. A deliberate new review after formatting can have a new fingerprint because it observes new immutable evidence IDs. An identical ingestion returns before this hook. Duplicate saved claims do not duplicate one counterevidence record. Distinct public passages with the same competing value remain distinct evidence identities.

The helper is an ingestion hook, not an asynchronous event consumer. Replaying the same event after a completed review can requeue an answer; a distributed worker requires durable event IDs and an idempotent claim/outbox mechanism. Removal or quarantine of existing counterevidence does not currently queue a resolution event. Explicit revalidation observes only current eligible evidence, changes the fingerprint, and can resolve the prior review state.

No candidate cap is applied. The implementation scans saved answers in the affected project/release and performs bounded-scope SQL reads of current structured evidence. This preserves completeness within this narrow detector at the cost of small-corpus performance. Any future cap must surface an incomplete/manual-review outcome; it must not label the answer validated after skipping candidates. An indexed claim-fact dependency table is the next scale improvement.

## Validation performed

The specialist ran the helper test suite locally. Tests exercise new documents and uncited sections, owner-private returned IDs with cross-owner state updates, exact project/release isolation, private-source state/fingerprint exclusion, quarantine and unquarantine, unsupported/partial/forged/null claims, abstentions, immutable payload/dependency preservation, duplicate claims, current-head withdrawal, formatting without requeue, and deterministic fingerprints. These are synthetic regression tests, not independently annotated contradiction benchmarks. The coordinating agent must separately run integrated endpoint and PostgreSQL checks after wiring the hooks.

## Read-only audit findings and priorities

These findings describe the runtime inspected before coordinating-agent fixes. They are actionable review observations, not a penetration-test report. Later fixes should be recorded in the main verification artifacts and assessed again.

| Priority | Finding | Consequence and recommended action |
| --- | --- | --- |
| High, correctness | Production retrieval modes can omit the requested release before candidate limits, then generation abstains if wrong-release candidates appear. | The release check prevents a wrong-release answer but relevant authorized evidence can be displaced. Scope every production mode before ranking; retain unsafe baselines only through explicit offline evaluation configuration. |
| High, UI confidentiality | Clearing rendered views on a role/token change does not stop an older in-flight request from rendering afterward. | Previously privileged content can reappear in the lower-role UI. Increment an identity epoch or cancel requests, and suppress all old-identity renders. Backend authorization remains necessary. |
| High, review correctness | Partial provider extracts inherit whole-passage synthetic fact metadata; revalidation also operates on dependencies of abstentions. | An extract that never asserted the fact, or an empty answer, can receive a confident stale/valid label. Bind structured facts to full claims or curated spans; review supported claims, and keep abstentions/partial extracts conservative. This new helper rejects those cases. |
| High before multiworker deployment | The request lock is process-local, and answer creation/ingestion are not a corpus-snapshot protocol. | Across workers, an answer can be saved after an ingestion impact scan using pre-update retrieval, or a review can observe mixed heads. Establish snapshot/epoch checks and transaction retry policy before claiming cross-worker consistency. |
| Medium, metadata integrity | Identical normalized text can fall through to `reviewed_still_valid` after a fact key is removed/renamed. | The saved metadata may no longer be supported. Compare fact presence/key/value as well as text; require manual review when metadata changes outside the supported exclusive-fact rule. |
| Medium, availability | The process-wide transaction lock also covers compatible-provider calls and health checks; answer scans have no quota. | A slow provider request or large corpus blocks unrelated requests. Bound ingestion/answer work and move provider calls outside global critical sections with snapshot validation. |

Additional known limits remain accurate: administrator-provided upstream provenance is not independently fetched/attested, substring membership is not entailment, quarantine is a bypassable heuristic, bearer tokens are not a complete identity system, and current source authority has no conflict-adjudication hierarchy. This feature addresses a specific missed-impact case without removing those limits.
