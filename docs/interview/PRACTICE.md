# Independent practice and four-week preparation

AI-assisted exercise design, 2026-10-15. The exercises below are intentionally unsolved. Completing them independently is the next step toward genuine ownership. Keep a record of what you wrote, what assistance you requested, what you observed and what remains uncertain. No completion or independent review is asserted here.

## Start with the original ownership exercise

From [OWNERSHIP.md](../OWNERSHIP.md), implement a regression test before looking at any generated solution:

1. Save an answer supported by one passage in a two-section document.
2. Change only the other section.
3. Assert the saved answer remains `unaffected` and is absent from affected-answer IDs.
4. Change the cited section and assert it becomes pending.

Use `tests/test_lifecycle.py` as the entry point. Explain the false positive document-wide invalidation would create. Do not solve it by disabling impact tracking, reducing the document to one section, or changing the assertion. The interview package supplies no test code or generated solution for this task. Ask for review of your attempt after writing it; preserve your contribution when incorporating feedback.

## Unsolved coding exercises

| Task | Deliverable | Acceptance criteria and discussion |
| --- | --- | --- |
| C1: Removed logical section | Add an independent focused regression around a two-section document and an answer citing the removed section | Verify pending transition, insufficient-evidence review, preserved original payload and no accidental claim that another section supports it. Explain the difference between removal and a rename. |
| C2: Provenance-only revision | Write a test and short behavior note for changed source provenance with unchanged section text | Observe whether a revision is created, whether review is queued, and what an old citation resolves to. State desired behavior before deciding if code should change. |
| C3: Stable ranking | Construct ties across at least two documents/releases and test order under repeated fresh database creation | Identify deterministic tie fields. Do not assert a random UUID ordering. Discuss which ordering is a contract and which is an implementation detail. |
| C4: Extract-selector failure | Add a provider-mock case currently absent from the test suite | Fabricated/unsupported evidence must not become a claim. Inspect coverage first to avoid duplicating an existing test. State whether failure details could expose sensitive content. |
| C5: Data-model reading | Draw the relevant foreign keys for save → update → review and write a diagnostic query for orphan candidates | Do not delete rows. Explain which apparent “old” rows are required historical evidence and which would be an integrity violation. |

Write tests that can fail for a real broken behavior, not tests that repeat implementation expressions. Run the narrow test first, then the relevant existing suite after any code edit. Record the actual command, environment and result.

## Unsolved backend exercises

**B1 — Concurrent ingestion.** Against a migrated disposable PostgreSQL database, design an experiment with two different updates carrying the same expected head. Define allowed outcomes and invariants before running it. Check committed heads, sequences, passages, change rows and pending answers, not just HTTP statuses. Compare one app instance with two app instances. Explain what the per-app lock masks. Do not use a live database containing user work.

**B2 — Retry after uncertain delivery.** Design a request/retry sequence where ingestion commits but the client does not receive the response. Determine the behavior for identical retry, changed retry and stale expected head. Write the protocol your client should implement. Keep rollback, idempotence and compare-and-swap semantics distinct.

**B3 — Review races.** Describe a race among source update, answer review and another source update across separate app instances. Inspect the exact locks in `api.py`, `ingestion.py` and `service.py`. Identify which consistency promise the current implementation can actually make, then propose and test a stronger promise if needed. Do not infer full snapshot consistency solely from the presence of a row lock.

**B4 — Authorization revocation.** Extend the same-user role-downgrade scenario to an answer citing both public and restricted evidence. List every endpoint that could expose content, IDs or audit reasons. Decide whether hiding the whole answer or redacting portions is the desired contract; justify and test your choice without weakening backend checks.

**B5 — Session serialization.** Profile where time is spent with the current async session lock, then propose narrower serialization. Include SQLAlchemy session lifecycle and thread use, SQLite limitations, PostgreSQL locking and error handling. Do not remove the lock solely to improve a synthetic request-per-second number. Demonstrate preserved correctness before comparing latency.

## Unsolved ML and evaluation exercises

**M1 — Learned retrieval experiment.** First verify whether pinned encoder execution actually succeeded in the latest environment. Independently annotate a small source-grounded question set with relevant passages, requested releases and reasons for unanswerability. Compare lexical-only, learned dense and hybrid retrieval on the same frozen questions. Include synonym-only queries that challenge the lexical gate. Report a small pilot as a pilot; keep the 300–500-question final target separate.

**M2 — Relevance versus membership.** Find examples where the current pipeline returns a perfectly quoted but irrelevant or incomplete extract. For each, record the source revision, question, result, why membership passed and which human label captures the failure. Do not fabricate an example without running it. Propose one fix and an experiment that could disprove its benefit.

**M3 — Reranker decision.** Define a decision rule before comparing the section-overlap heuristic with no reranker. State the minimum quality gain and latency budget you would accept. Hold candidates fixed, separate tuning from assessment, and inspect failures by topic. A tie or regression is a valid result; do not retain a component merely because it was planned.

**M4 — Abstention calibration.** Design answerable, missing-evidence, wrong-release, conflicting and misleading-overlap questions. Define precision/recall for abstention and specify the denominator of each metric. Decide how an extract that is present but unhelpful should be labeled. Explain why the existing two no-overlap probes cannot calibrate confidence.

**M5 — Natural-language change labels.** Create independently reviewed examples of technical change, harmless paraphrase, context change, code-indentation change, newly added contradiction and removed evidence. Keep synthetic fact equality distinct from semantic judgments. Draft an adjudication protocol for disagreement before proposing automatic semantic stale-answer verdicts.

## Unsolved system-design exercises

These are proposals for a future system, not claims about implemented features.

**S1 — Multi-tenant service.** Specify tenant and membership tables, per-request identity, role changes, PostgreSQL RLS, evidence access and answer sharing. Define a complete permission-revocation contract, including caches, search indexes and audit histories. Produce a threat model and migration sketch; explain how a tenant ID cannot be injected through question text.

**S2 — Asynchronous change fanout.** Design a transactional outbox and worker protocol for a revision affecting 100,000 saved answers. Define event identity, deduplication, retry, dead-letter policy, job claims and state transitions. Handle repeated updates, head supersession, corrected-answer creation and a worker crash after a partial action. Explain which steps are atomic and how a reviewer sees pending work.

**S3 — Large-corpus retrieval.** Plan an experiment for exact vector scan versus ANN under selective release and ACL filters. Define recall, latency, index memory/build time, ingestion freshness and permission safety. Describe query-plan inspection and fallbacks. Do not assume unfiltered ANN recall transfers to a permission-filtered workload.

**S4 — Retention and deletion.** Immutable evidence is useful but not a complete retention policy. Propose how to handle an upstream license withdrawal, sensitive-source removal or user deletion request while preserving permitted audit information. Decide how dependent answers become unavailable, what tombstones mean and what cannot remain in logs/backups. Do not call the current append-only model a finished solution.

**S5 — Safe fluent generation.** Propose a separate acceptance contract for paraphrased answers: claim segmentation, source mapping, entailment labels, contradictions, abstention, provider failure, prompt injection and version correctness. Specify what can still be checked deterministically and what requires human evaluation. Explain why the current exact-substring validator cannot simply be reused unchanged.

## Four-week preparation schedule

Suggested effort: five sessions of 60–90 minutes each week. Adjust time to actual progress; unresolved work carries forward. Preserve factual logs instead of marking scheduled work complete automatically.

| Week | Sessions | Concrete output | Readiness gate |
| --- | --- | --- | --- |
| 1: Operate and map | Run a fresh demo; reproduce the 30→60 lifecycle; read schemas/models/API; trace ask and citation validation; rehearse a two-minute explanation | Environment/run log, hand-drawn architecture, one saved old/new evidence pair and a limitation list | Explain default encoder, exact extraction, release predicates, ownership and current verification without notes |
| 2: Own a regression | Write the original uncited-section exercise independently; run it; seek review; inspect historical-impact/normalization code; reproduce one actual fixed failure from the case studies in an isolated branch | Your regression, explanation of failure it would catch, review notes and a precise contribution record | Explain why the test distinguishes relevant from irrelevant section edits; identify code you wrote versus assistance |
| 3: Measure and reason | Complete one backend concurrency exercise; independently label a small relevance pilot; run one controlled retrieval comparison; inspect metric denominators and errors; present a future scale design | Experiment design, frozen pilot labels, actual result/error table and a proposal clearly marked future work | Defend what the result measures and what it cannot support; do not confuse passing execution with semantic quality |
| 4: Interview rehearsal | Answer ten random questions aloud; perform one 45-minute coding exercise; present a 20-minute system design; run five-minute demo with interruption; update résumé to actual contributions | Recorded self-review notes, runnable demo checklist, final claim audit and remaining gaps | Explain source paths and one failure deeply, handle an unknown honestly, and complete demo without unsupported claims |

Weekly self-review: What did I implement? What did AI supply? What did I independently verify? Which assumption failed? Which source/test supports my claim? What is still pending?

## Interview practice formats

- **Junior, 30 minutes:** two-minute pitch; trace one request; solve a small regression; explain one data-model/ACL choice; finish with an honest limitation.
- **Experienced, 45 minutes:** five-minute demo; discuss transaction and lock boundaries; evaluate a concrete failure race; propose scale options with decision criteria; distinguish implemented behavior from future design.
- **ML/backend crossover, 45 minutes:** describe the lexical gate and model identity contract; define held-out labels and metrics; inspect an irrelevant exact extract; design an ablation; reason about latency and evidence provenance.

If you cannot answer a question, identify the function, test or experiment that would resolve it. That is a stronger learning habit than memorizing an unsupported answer.
