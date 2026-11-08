# Design decisions

Each entry names a decision visible in the code, the alternative it rejects, and the cost accepted. [ARCHITECTURE.md](ARCHITECTURE.md) has the full implementation table and review-state semantics; this page is the shorter "why".

## 1. Filter by release and access policy before ranking, never after

**Decision.** `releaselens/retrieval.py` restricts candidates to the exact project, release, ACL, current head and quarantine state in SQL before any lexical or dense scoring runs. An unspecified or unknown release yields no evidence rather than the nearest one.

**Rejected.** Retrieve the top-k globally, then drop what the user may not see. That leaks existence through ranking and can quote the wrong version.

**Cost.** Users must say which release they run; the system never guesses.

## 2. Hybrid ranking with fixed, documented constants

**Decision.** Lexical and exact dense results are fused with reciprocal rank fusion at depth 20 and constant 60. The default hybrid keeps a lexical eligibility gate.

**Rejected.** A learned fusion model, for which the 70-question study was too small to validate.

**Cost.** Zero-lexical-overlap semantic matches can be missed; the study reports where this happened.

## 3. Generation is extract selection, and quotations are verified

**Decision.** The default generator (`ExtractiveGenerator`) invokes no model. The optional provider path (`CompatibleGenerator`) may only pick up to four extracts by passage ID. `service.validate_citations` then checks membership, authorization, release, exact quotation and claim containment (`claim.text not in passage.text` fails the answer).

**Rejected.** Free-form generated answers with citations appended.

**Cost.** Answers are quotations, not synthesis. Relevance, completeness and entailment remain separate, unclaimed properties.

## 4. Citations point at immutable physical passages

**Decision.** Ingestion is append-only: each revision creates new passage rows, and saved answers cite physical passage IDs. Impact analysis later matches those passages to changed logical sections.

**Rejected.** Citing document plus offset, which moves when the document is edited.

**Cost.** Storage grows with every revision, including formatting-only ones.

## 5. Change impact is section-level and conservative

**Decision.** Re-ingesting a source diffs logical sections; every saved answer whose cited section changed goes to `revalidation_pending`. Formatting-only edits (line endings, trailing whitespace, blank runs) do not trigger review; prose changes do.

**Rejected.** Invalidating every answer that cites the document, or trusting a model to decide whether the change matters.

**Cost.** Positional chunk movement can over-flag; the review queue is sometimes larger than strictly necessary.

## 6. Review states distinguish "possibly affected" from "confirmed stale"

**Decision.** Six explicit states (`unaffected`, `revalidation_pending`, `reviewed_still_valid`, `confirmed_stale`, `insufficient_evidence`, `manual_review_required`). Only a cited synthetic assertion with a different value can produce `confirmed_stale`; new conflicting prose produces `manual_review_required` without a correction.

**Rejected.** A single boolean "stale" flag.

**Cost.** Reviewers see more nuance than a simple queue; the UI has to explain each state.

## 7. Private counterevidence cannot leak through public status

**Decision.** New private or internal passages are excluded from public answers' status and fingerprints, even for administrator-owned answers.

**Rejected.** Completeness of impact detection.

**Cost.** A public answer can remain "unaffected" while private sources contradict it. The confidentiality contract was chosen over completeness, and the docs say so.

## 8. Optimistic concurrency on ingestion

**Decision.** Edits to an existing document require `expected_revision`; a stale value returns HTTP 409 (`RevisionConflict`). Revision, passages, head, diff and answer-state updates share one transaction and roll back together.

**Rejected.** Last-write-wins ingestion.

**Cost.** Clients must read before they write.

## 9. One process, one async lock, written down as a limit

**Decision.** `api.py` serialises request transactions with a single `Lock`, and provider calls hold it. Production deployment is constrained to one worker and maintenance-mode ingestion.

**Rejected.** Multi-worker deployment without a snapshot/retry protocol, which would make "the corpus the answer was computed against" ill-defined.

**Cost.** A slow provider delays other requests. SCALE.md describes the path to multiple writers.

## 10. Security choices that cost nothing to keep

**Decision.** Bearer tokens compared with `secrets.compare_digest`; fixed server-side roles; bounded request bodies; no result cache; logs omit source text, questions and tokens; source ACL and owner access are rechecked on direct ID access, dependencies and histories.

**Rejected.** A result cache, because its key would have to encode authorization and revision state correctly from day one.

## 11. Two backends, one claim

**Decision.** SQLite for the demo and tests; PostgreSQL with pgvector for the Compose deployment. The lexical implementations differ, so the benchmark is stated as validating the SQLite path only.

**Rejected.** Presenting one benchmark as covering both.

## 12. Learned models are opt-in and pinned

**Decision.** The default encoder is a hash-based test double. The MiniLM encoder and the cross-encoder relevance gate are opt-in, commit-pinned, and startup rejects an encoder/backend mismatch. The prose-impact lexical stage stays off by default because replay results were poor.

**Rejected.** Shipping the learned path as the default because it looks better in a demo.

**Cost.** The out-of-the-box experience is deliberately plain; the retrieval study documents what the learned components add and at what CPU latency.
