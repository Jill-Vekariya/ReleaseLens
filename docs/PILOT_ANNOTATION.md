# Frozen pilot v2: annotation and interpretation

This is a deliberately small **AI-reviewed proposal**, not a human-reviewed benchmark.
The 40 frozen records contain 32 retrieval questions and eight separately executable
synthetic behavior checks. Twenty-four retrieval questions have proposed supporting
passages; eight realistic unsupported questions share vocabulary with the sources.
No hundreds of automatically generated paraphrases have been added.

The four pinned, licensed snapshots are Pydantic 1.10.15 / 2.10.4 model configuration
and SQLAlchemy 1.4.54 / 2.0.36 Core connections. They are selected source pages, not
complete documentation. Markdown include directives and reStructuredText cross references
remain unresolved. An absent answer means absent **from this corpus**, not impossible in
the software or absent from the complete upstream documentation.

## Freeze and labels

`evaluation/pilot-manifest.json` freezes the question JSONL SHA-256, source and license
hashes, immutable source commits, paragraph-packing counts, family assignments and
parameters. Each positive label names a document and logical block, exact passage hash,
and source anchor. Labels are binary relevance grade 1; the runner also supports grades
2/3 without asserting that such grades were annotated here. Expected claims are concise
AI-proposed interpretations for a future reviewer, never text supplied to the encoder.
Source hashes/anchors prove provenance and existence, not that the proposed interpretation
is correct or that every relevant passage has been exhaustively identified.

AI inspection checked the selected source blocks against the question and proposed claim,
including mode caveats, deprecated alternatives, and negative claims. Unsupported questions
were chosen because they ask for guarantees or mechanisms not supplied by these selected
pages, despite overlap with real configuration/transaction terms. The inspection is not
independent human adjudication. Every record remains `ai_reviewed_proposal` with no human
reviewer or human-reviewed-result claim.

The 22 tuning retrieval cases comprise 16 supported questions and six unsupported probes.
The ten heldout retrieval cases comprise eight supported questions and two unsupported
probes. Entire union, alias-precedence, isolation, streaming, and credential-policy topic
families are reserved for heldout; paired release questions share a family and split.
All four releases remain indexed in both experiments. There is **no patch-release holdout**
or evidence of generalization to unseen releases. The eight synthetic scenarios are tuning
only and are never included in retrieval quality denominators.

Casefolded/alphanumeric exact duplicate detection runs before evaluation, together with
family split checks and AI inspection for near paraphrases. `dedup_group` preserves an
individual intent; `family_id` groups related questions, including intentional release
pairs. No independent human or embedding-based deduplication is claimed.

## Running the pilot

The source-only runner uses no network or provider when using the default hash test double:

```bash
python -m releaselens.benchmark --output evaluation/pilot-hash-tuning.json
```

For an already installed, immutable-revision learned encoder, use the same corpus,
question freeze, parameters and output schema:

```bash
python -m releaselens.benchmark --configured-encoder --output evaluation/pilot-learned-tuning.json
```

The CLI reads `EMBEDDING_MODEL` and `EMBEDDING_REVISION` through the existing configured
encoder. Model weights must already be present for an offline learned run. Loading or
downloading weights is outside retrieval timing; the result records the actual encoder
identity, Python version, dataset/manifest/code hashes and ingestion time.

Default execution selects tuning only. Selecting heldout or all records refuses to run
unless every selected heldout label is `human_verified`. An explicit diagnostic override
is available for engineering inspection:

```bash
python -m releaselens.benchmark --split heldout --allow-ai-reviewed-heldout --output evaluation/pilot-hash-heldout-diagnostic.json
```

The override never upgrades labels, and outputs record both the override and label counts.
Once heldout results have influenced tuning or model selection, these families are consumed;
create a new independently reviewed holdout before any final generalization claim. Do not
silently re-freeze labels after inspecting rankings. Record a new dataset version, reasons,
reviewer, and adjudication whenever questions or labels change. Human verification requires
actual reviewer identity/date, full source reading and support/absence assessment, including
alternative supporting chunks; do not merely rename the AI status.

The dataset and its labels are present in the repository, so the holdout is a procedural
boundary, not access-isolated secret gold data. Pretrained encoders and question-authoring
models may already have seen these public upstream pages; pretraining contamination has
not been audited. A topic holdout does not establish source or pretraining independence.

## Controlled retrieval comparison

Lexical-only BM25, dense-only dot product, and production hybrid RRF use the same
SQLite corpus, reader permissions, project and explicit release. The production ranker
applies current-revision, quarantine, encoder identity, ACL and release predicates before
scoring/limits. The pilot does not call an unfiltered version-omission experiment and label
it as a component ablation. Synthetic examples are excluded from upstream retrieval scoring.
There is no heuristic or learned reranker in these comparisons.

The production hybrid uses a positive lexical overlap eligibility gate, RRF constant 60
and depth 20 per component; consequently dense-only and hybrid may differ because that
gate suppresses zero-overlap results as well as because of fusion. This is a comparison of
these implemented configurations, not a clean estimate of fusion alone. Lexical-only skips
query encoding. PostgreSQL FTS is a separate backend and is not measured by this runner.

All rankings and proposed labels are written per query. A passage is relevant only when its
document plus logical key matches a positive label within the selected project/release.
The runner verifies exact source hashes before ingestion and records retrieved hashes.
The current sparse Pydantic pages have only eight or three blocks, making top-4 recall easy
and sometimes saturated; SQLAlchemy has a substantially larger candidate pool. Report
these corpus limitations when comparing encoders. No ranking delta establishes a component
benefit from this pilot alone.

## Metric definitions and uncertainty

For supported questions only, unique-passage Recall@k is the fraction of labeled relevant
passages in the top k. Hit@k is whether any labeled relevant passage appears. MRR@k is
1/rank of the first relevant result, or zero if absent. nDCG@k uses gain `2**grade - 1`
and discount `log2(rank + 1)`, divided by the ideal top-k gain; grades are binary in v1.
Duplicate retrievals do not earn additional relevance credit. The denominator includes
supported queries with no retrievals, scored zero. Since almost all cases have one positive
chunk, Recall@k here equals hit rate and does not establish exhaustive evidence coverage.

Unsupported questions have no nDCG/MRR/Recall value and are excluded from those means.
Their nonempty retrieval count is reported separately. A nonempty ranking is not a model
answer. No confidence threshold has been calibrated, and this runner does not calculate
abstention precision, natural-language accuracy or semantic citation support. Exact extract
membership and citation existence must never be called semantic entailment.

Per-metric intervals and hybrid-minus-component differences use 2,000 deterministic
percentile bootstrap draws, resampling whole topic families and retaining paired queries
within a draw. The point estimate is the query-weighted mean. Families are few, hand chosen,
and AI annotated: these are descriptive uncertainty estimates, not population confidence
bounds or proof of significance. Query-level Wilson hit intervals are separately labeled
descriptive because queries within families are dependent.

Latency is `perf_counter` elapsed time around each complete rank call, including SQL,
query encoding where required, and scoring. It excludes model loading, source ingestion,
annotation and synthetic scenarios. One warm-up per component precedes a single pass with
rotating component order. Report p50/p95 as small local diagnostics, not throughput or
production service-level guarantees. No external provider is called; local electricity,
hardware and weight-download costs are not estimated.

## Executed synthetic scenarios and known limits

The runner executes each selected scenario in an isolated seeded SQLite database using
HashEmbedder, regardless of the upstream ranking encoder. It reports execution, observed
values and expected-behavior checks separately from all retrieval metrics:

| Scenario | Expected implemented behavior |
| --- | --- |
| Cited structured fact changes 30 → 60 | Review confirms synthetic staleness |
| Trailing whitespace and CRLF only | Formatting-only; saved answer remains unaffected |
| Unchanged cited evidence | Review still valid |
| Two retrieved synthetic exclusive facts disagree | Conflict causes abstention |
| Reader probes restricted canary | All three configurations exclude protected document |
| Source contains known injection marker | Quarantined document excluded in all configurations |
| Prompt requests newer release against explicit old request | All configurations retain selected release |
| New contradictory document, cited evidence unchanged | Dependency tracker leaves original unaffected: measured limitation |

Passing the last check confirms a known blind spot, not correctness of the saved answer.
The contradiction checks use structured synthetic fact keys and do not measure general
natural-language contradiction detection. The injection probe exercises one known marker,
not comprehensive resistance. Scenario checks are not promoted to measured outcomes until
actually executed; the frozen JSONL itself contains expected outcomes only.

For human review, read each immutable snapshot, confirm requested release/mode/permissions,
mark all supporting passages or reason for absence, and record ambiguity and adjudication.
Review semantic relevance independently from exact quotation, and technical impact
independently from textual change. A final larger benchmark remains separate work.

## Dataset history

Frozen v1 is preserved as `pilot-v1.jsonl` with `pilot-v1-manifest.json`. V2 changes only the expected behavior of the new-counterevidence scenario after fixing the documented dependency-only gap. Retrieval questions, labels, family assignments and settings are identical. The current manifest points to v2. Human review must create a new dataset version and preserve these bytes; never relabel an AI review as human review.
