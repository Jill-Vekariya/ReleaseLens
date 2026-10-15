# Evaluation protocol

See [measured report](BENCHMARK_REPORT.md) and raw `evaluation/` JSON for results; protocol and measurement are separate.

## Frozen pilot

The current `pilot-manifest.json` references pilot-v2: 40 records, comprising 32 real-source retrieval questions and eight executable synthetic scenarios. There are 24 proposed supported retrieval cases and eight realistic unsupported cases. Twenty-two retrieval records are tuning (16 supported, six unsupported); ten are held out (eight supported, two unsupported). Whole topic families are disjoint. All four source releases remain indexed: this is not release holdout. Casefolded alphanumeric duplicate checks, split checks, exact source/license hashes, logical anchors and passage hashes are validated before execution.

All labels are `ai_reviewed_proposal`, human-reviewed count zero. Source/label checks are AI assistance, not independent ground truth. V1 is preserved; v2 changes only the expected outcome of the new-counterevidence scenario after its actual bug fix. No retrieval labels or splits changed. Do not tune on held-out families; the runner refuses heldout use without an explicit AI-diagnostic override. No heldout run is necessary to produce a useful tuning pilot.

## Matched comparisons

Run from the repository checkout after locked installation:

```bash
python -m releaselens.benchmark --output evaluation/pilot-hash-tuning.json
# After pinned learned model setup described in BENCHMARK_REPORT.md:
python scripts/run_pilots.py
```

All components use identical source chunks, release/ACL scopes, question bytes, labels, k=4, candidate depth=20 and RRF constant 60. Lexical mode does not call the encoder. Dense is an exact normalized-vector comparison; hybrid combines lexical/dense ranks with a positive lexical eligibility gate. SQLite BM25 and PostgreSQL FTS are different algorithms; pilot scores measure SQLite only. PG tests verify scoped behavior and operations, not quality parity. No learned reranker is enabled; the section-overlap heuristic remains a named experiment, outside this three-way pilot.

Metrics are passage Recall@4, first relevant MRR@4, graded nDCG@4, hit rate, wrong-release hits and unauthorized hits. Most positives have one proposed relevant passage, so recall then equals hit rate. Latency is one warmed pass, rotating mode order; excludes loading/indexing. Family-cluster bootstrap uses 2,000 fixed-seed draws and paired differences, with very few families: intervals are descriptive. Wilson intervals assume independent cases and are not generalization bounds.

Resource output records model identity/commit, CPU runtime versions, model snapshot checksums, cache bytes, model load time, repeated-encoding check and whole-process peak memory. Cache/network/power costs are not metered. Default extraction makes zero paid provider calls. Local latency is not a production SLA.

## Separate measures and honest unknowns

Retrieval relevance labels do not establish that the assembled answer semantically answers the question. Exact citation membership, authorization and version checks are deterministic safeguards, not semantic support labels. The synthetic 24-question development runner, change scenarios and canary probes remain separate diagnostics (`results.json` / `semantic-results.json`). A/B/C intentionally disable release filtering only in that offline contamination experiment; every production mode scopes releases.

Unsupported pilot queries deliberately overlap source vocabulary. Nonempty retrieval on them exposes the need for relevance/answerability calibration; it is not silently counted as a correct abstention. Natural-language answer support, appropriate abstention precision/recall and change-impact precision/recall on independently labeled real documentation remain unmeasured. Synthetic verdicts only validate the curated fixture contract. `manual_review_required` is not a verdict that an answer is wrong.

The live HTTP load smoke is a separate 100-request, concurrency-eight local functional check. Browser checks include delayed identity responses, errors, evidence and workflow state; they do not validate semantic correctness.

## Human review and expansion

Follow [PILOT_ANNOTATION.md](PILOT_ANNOTATION.md). Review the exact pinned source, proposed relevance, release, missing context, contradictions and answerability. Keep all relevant blocks, not just an easy positive. Record reviewer/date, uncertainty, adjudication and rejected labels. Preserve frozen bytes and create a new manifest/dataset version for human changes. Never set `human_verified` based on AI review.

Before a larger benchmark, add independently reviewed source coverage and adjudication capacity. Expand toward 300–500 questions only then. Include topic/release holdout, multi-passage answers, cross-version tasks, irrelevant overlap, unsupported questions, assertions added/removed, uncited sections, formatting/code indentation, ACL changes and adversarial text. A 400-case allocation is a planning target, not completed work. Freeze labels before selecting models or thresholds and keep heldout labels out of prompts, reranker training and error-driven tuning.
