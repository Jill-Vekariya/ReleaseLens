# Engineering ownership and decision log

## Actual contribution record

| Work | Attribution | User independent review |
| --- | --- | --- |
| Initial specification, quality expectations, model preferences | User-provided | Supplied in this conversation |
| v0.1 implementation, fixtures, tests, documentation, evaluation runner | AI-assisted implementation | Pending |
| Human-authored implementation code | None recorded yet | Pending |
| Human verification of evaluation labels | None recorded yet | Pending |
| Production architecture approvals | None recorded yet | Pending |
| GPT-6.1 Sol High specialists | Pilot, UI identity handling, operations and interview materials | AI work; independent user review pending |
| GPT-6 Astra Extra High specialists | Counterevidence design and final correctness review executed | AI review; findings in FINAL_AI_REVIEW.md, not human review |

No Git history, human implementation, manual annotations, deployments, or reviews have been fabricated.

## Provisional decision log

1. **2026-10-15 / AI proposal:** implement the dependency/change lifecycle before fluent generation. Outcome: runnable synthetic scenario and tests; user review pending.
2. **2026-10-15 / AI proposal:** keep SQLite as a reproducible execution path while providing PostgreSQL schema and integration tests. Outcome: SQLite and PostgreSQL/pgvector executed, with real HTTP and Docker verification artifacts.
3. **2026-10-15 / AI proposal:** use pinned Pydantic/SQLAlchemy source pages. Outcome: four snapshots downloaded with license and content hashes; suitability independently reviewable.
4. **2026-10-15 / AI proposal:** mark changed unstructured prose for manual review. Outcome: deterministic synthetic staleness does not overclaim general natural-language detection.
5. **2026-10-15 / user preference:** GPT-6.1 Sol + High for routine work; GPT-6 Astra + Extra High for hardest decisions/final review. Outcome: specialist model selections ran as requested; the active root session model was not switched.

6. **2026-10-15 / AI review:** the heuristic has no independently validated benefit and did not improve the tiny synthetic ranking comparison. Outcome: removed from the default version path; retained solely as the explicitly requested experimental baseline.

## First meaningful user contribution

Implement a regression test for this scenario **before looking at a generated solution**:

1. Save an answer supported by one passage in a two-section document.
2. Change only the other section.
3. Assert the saved answer stays `unaffected` and is not returned among affected answer IDs.
4. Change the cited section and assert it becomes pending.

Use `tests/test_lifecycle.py` as the entry point. Explain why document-level invalidation would create a false positive here. Submit your test for review; the review should explain improvements and preserve your contribution rather than replacing it automatically.

## First consequential decision for the user

The AI implementation selected a pinned local CPU encoder for the requested evaluation. This engineering choice is not attributed to the user. Independently decide whether the measured evidence justifies enabling it for your demonstration:

- **Local encoder + exact extraction (recommended first):** low recurring inference cost; requires model download and resources; isolates retrieval quality.
- **Hosted compatible model selector:** easier model access; incurs provider costs and requires credentials; extraction remains constrained.
- **Fluent generation:** more natural responses, but requires claim segmentation, entailment labels, stronger abstention evaluation, and additional attack testing.

Record your choice, reasoning, expected failure modes, and the experiment that could change your mind. No choice has been recorded on your behalf.

## Understanding checkpoints

Explain: why exact release equality is stronger than putting the version in the prompt; why a citation's existence does not establish support; why formatting and technical changes differ; why ACL filtering after top-k loses recall and can leak identifiers; and why a new contradictory source can escape dependency-only impact analysis.

## 2026-10-16 continuation attribution

The current continuation adds the 14-snapshot/70-question AI-proposal dataset, scoped retrieval comparisons, validation-frozen relevance-gate experiment, opt-in public-prose review candidates, real compatible local inference smoke and transport regression, and review/export/report tooling. Implementation, source inspection, diagnostics and documentation were AI-assisted. No new independent user coding, human labels, human review, training, production users or employment outcomes are attributed to the user. The original personal two-section exercise remains unsolved.

A useful next independent contribution is to reproduce one experiment, explain a failed query, and write your own reviewed-source case and regression. Record the exact commit, what you changed, commands you personally ran, observed result, and what you can explain without assistance. Do not fill that record automatically on the user's behalf.

## Public-source and challenge continuation attribution

The owner explicitly requested public GitHub source and independently merged PR #1 on 2026-10-16. Those owner actions are distinct from human-authored code or human-reviewed evaluation labels, neither of which is recorded. The challenge implementation, source inspection, model execution, regression tests, reports and checkpoint were AI-assisted. Human-reviewed examples remain0. A resumed agent preserved all pending file hashes while creating a separate branch based on the owner's merge. Do not attribute pretrained integration to model training or use generated interview answers as proof of personal understanding.
