# Evaluation protocol

See [measured report](BENCHMARK_REPORT.md) and raw `evaluation/` JSON for results; protocol and measurement are separate.

## Historical frozen pilot

The current `pilot-manifest.json` references pilot-v2: 40 records, comprising 32 real-source retrieval questions and eight executable synthetic scenarios. There are 24 proposed supported retrieval cases and eight realistic unsupported cases. Twenty-two retrieval records are tuning (16 supported, six unsupported); ten are held out (eight supported, two unsupported). Whole topic families are disjoint. All four source releases remain indexed: this is not release holdout. Casefolded alphanumeric duplicate checks, split checks, exact source/license hashes, logical anchors and passage hashes are validated before execution.

All labels are `ai_reviewed_proposal`, human-reviewed count zero. Source/label checks are AI assistance, not independent ground truth. V1 is preserved; v2 changes only the expected outcome of the new-counterevidence scenario after its actual bug fix. No retrieval labels or splits changed. Do not tune on held-out families; the runner refuses heldout use without an explicit AI-diagnostic override. No heldout run is necessary to produce a useful tuning pilot.

## Matched comparisons

Run from the repository checkout after locked installation:

```bash
python -m releaselens.benchmark --output evaluation/pilot-hash-tuning.json
# After pinned learned model setup described in BENCHMARK_REPORT.md:
python scripts/run_pilots.py
```

All components use identical source chunks, release/ACL scopes, question bytes, labels, k=4, candidate depth=20 and RRF constant 60. Lexical mode does not call the encoder. Dense is an exact normalized-vector comparison; hybrid combines lexical/dense ranks with a positive lexical eligibility gate. SQLite BM25 and PostgreSQL FTS are different algorithms; pilot scores measure SQLite only. PG tests verify scoped behavior and operations, not quality parity. This original three-way pilot excludes the learned reranker; the later v3 experiment evaluates it explicitly. The section-overlap heuristic remains a separate named experiment.

Metrics are passage Recall@4, first relevant MRR@4, graded nDCG@4, hit rate, wrong-release hits and unauthorized hits. Most positives have one proposed relevant passage, so recall then equals hit rate. Latency is one warmed pass, rotating mode order; excludes loading/indexing. Family-cluster bootstrap uses 2,000 fixed-seed draws and paired differences, with very few families: intervals are descriptive. Wilson intervals assume independent cases and are not generalization bounds.

Resource output records model identity/commit, CPU runtime versions, model snapshot checksums, cache bytes, model load time, repeated-encoding check and whole-process peak memory. Cache/network/power costs are not metered. Default extraction makes zero paid provider calls. Local latency is not a production SLA.

## Separate measures and honest unknowns

Retrieval relevance labels do not establish that the assembled answer semantically answers the question. Exact citation membership, authorization and version checks are deterministic safeguards, not semantic support labels. The synthetic 24-question development runner, change scenarios and canary probes remain separate diagnostics (`results.json` / `semantic-results.json`). A/B/C intentionally disable release filtering only in that offline contamination experiment; every production mode scopes releases.

Unsupported pilot queries deliberately overlap source vocabulary. Nonempty retrieval on them exposes the need for relevance/answerability calibration; it is not silently counted as a correct abstention. Natural-language answer support, appropriate abstention precision/recall and change-impact precision/recall on independently labeled real documentation remain unmeasured. Synthetic verdicts only validate the curated fixture contract. `manual_review_required` is not a verdict that an answer is wrong.

The live HTTP load smoke is a separate 100-request, concurrency-eight local functional check. Browser checks include delayed identity responses, errors, evidence and workflow state; they do not validate semantic correctness.

## Human review and expansion

Follow [PILOT_ANNOTATION.md](PILOT_ANNOTATION.md). Review the exact pinned source, proposed relevance, release, missing context, contradictions and answerability. Keep all relevant blocks, not just an easy positive. Record reviewer/date, uncertainty, adjudication and rejected labels. Preserve frozen bytes and create a new manifest/dataset version for human changes. Never set `human_verified` based on AI review.

Before a larger benchmark, add independently reviewed source coverage and adjudication capacity. Expand toward 300–500 questions only then. Include topic/release holdout, multi-passage answers, cross-version tasks, irrelevant overlap, unsupported questions, assertions added/removed, uncited sections, formatting/code indentation, ACL changes and adversarial text. A 400-case allocation is a planning target, not completed work. Freeze labels before selecting models or thresholds and keep heldout labels out of prompts, reranker training and error-driven tuning.

## Expanded v3 protocol (2026-10-16)

[V3_REPORT.md](V3_REPORT.md) reports the executed 70-question, 14-snapshot experiment; [DATASET_V3.md](DATASET_V3.md) defines its source/family freeze and independent review workflow. The old pilot is preserved, not overwritten. V3 uses passage Recall@5/nDCG@10, pretrained cross-encoder and feature-hash reference, and a validation-only fixed-grid gate selected before the test run. All labels remain AI proposals. Test has now been consumed; v2 holdout concepts overlapping new dev may not be described as pristine for future tuning.

Binary answerability metrics count answers on proposed unsupported questions; they do not measure wrong answers to answerable questions. The relevant-passage hit proxy, exact citation validation, completeness and semantic correctness remain distinct. The real-prose replay measures review candidates, never confirmed-stale accuracy. No automated judge or neural training was used. See raw `v3-calibrate.json`, `v3-test.json`, `prose-impact-v3.json`, `local-selector-v3-before.json` and `local-selector-v3.json`.

## Descriptive supplement and development-only profile

`python -m scripts.supplement_v3 --output evaluation/my-supplement.json` recomputes Recall@5/nDCG@10 against the original saved per-query rankings and rejects any mismatch. It adds proposal-label Precision@5 (unique positive proposal hits divided by five; missing returned positions count zero) and MRR@10. Unsupported questions stay outside ranking averages. Cutoffs serve short evidence lists and ordering inspection; no cutoff/model/threshold search is performed. Original dataset, policies and ranking artifacts remain byte-identical. This is post-hoc descriptive reporting, not a new confirmatory test. Incomplete positive judgments make precision a proposal-match measure; an unjudged passage is not known irrelevant. Raw output records input hashes and family-bootstrap intervals; two supported families per split cannot support robust significance claims.

The original final-top-ten predictions cannot recover pre-rerank Recall@20 or isolate stage latency. Those historical fields are explicitly null. `python -m scripts.supplement_v3 --profile-dev --output evaluation/my-dev-profile.json` instead executes a new **development-only** warmed pass with cached pinned models, same 14 snapshots, one fresh SQLite index, hybrid depth20, raw-logit pair scoring, batch8, 256 tokens and two CPU threads. It records candidate Recall@20, retrieval and reranking timings, model loading/indexing, model identities and code hashes. A scope assertion precedes scoring. Non-dev rows, unavailable revisions and non-finite scores fail explicitly; no hash/model fallback. One missing offline revision is tested after successful cached loads. Whole-process peak resident memory includes imports, indexing and both models; it is not isolated model memory. No provider call, threshold change or new test inference occurs.

The module invocation (`python -m scripts.supplement_v3`) is the supported entry point. Reproductions require a new output path and preserve all previous evidence. The canonical Windows run uses `$env:HF_HOME=Join-Path $PWD '.model-cache'`; install the locked optional environment first. CI validates the non-ML supplement with tests; actual model profiling is a separately recorded Windows execution.

## Separate migration challenge protocol

[CHALLENGE_V1.md](CHALLENGE_V1.md) defines a separately frozen24-question source-inspected AI-proposal diagnostic:12 dev/4 validation/8 reserved. Its corpus is19 snapshots/707 passages; original v3 selection remains14/534. The runner rejects reserved-test selection without an override. Newly added reserved source text is indexed, so this is a query/family holdout, not unseen-corpus or pretraining independence. Review workflow is dataset-aware and exported forms omit AI answer/relevance proposals. Human labels remain 0.

The actual Windows comparison uses the same pinned pretrained models, scoped candidates and fixed parameters across five retrieval approaches. No threshold/model search occurs; the original -4 gate is transferred unchanged. Sparse-label Recall@5/nDCG@10 and timing observations are diagnostics, not semantic answer correctness. The report retains two validation unsupported-answer failures and a supported dev abstention. No gate promotion, fresh test accuracy, confidence/significance claim or trained model is inferred from this small sample. Preserve original evidence and use new output paths for reproduction.
