# Expanded evaluation milestone — 2026-10-16

This report is generated from the actual v3 artifacts. All 70 questions and relevance/answerability labels are AI-authored, source-inspected proposals. Human-reviewed and independently reviewed records: **0**. No human accuracy, production impact, or independently authored user implementation is claimed.

## Corpus and split contract

Four original pages are preserved; ten additional MIT-licensed pages give 14 snapshots and 534 fixed passages. Each snapshot retains the immutable commit, release, raw SHA-256, original license, license SHA-256 and attribution. The new question dataset SHA-256 is `d7c88287d5df00991f44829d6fb45ce8835ffa92e36868d040fedcdc369cb512`.

Development: 30 questions (24 supported/6 unsupported); validation: 20 (16/4); test: 20 (16/4). Six entire document-family groups are assigned before model experiments; paired releases and intent duplicates stay together. Models/configuration and connections are development; validators/engines validation; serialization/SELECT test. All sources remain searchable: this is family holdout, not unseen-release holdout. Cross-project/release/ACL/current-head/model/quarantine filtering precedes ranking.

The original v1/v2 files remain byte-preserved and their heldout rows were not scored. However, v3 development includes isolation/streaming concepts also present in v2 heldout families, so do not call v2 holdout untouched for future tuning claims. V3 test is a separate procedural holdout and is consumed by the recorded test run. Public-source pretraining contamination is not audited.

## Matched retrieval results

SQLite BM25, exact normalized MiniLM vectors, RRF hybrid, hybrid plus pretrained cross-encoder, and feature-hash hybrid reference use identical corpus/question/scope settings. Recall is passage Recall@5; nDCG@10 uses the proposed sparse relevance grades. Larger multi-positive labels make these recall values incomparable with the saturated original top-four pilot.

| Split | Method | Recall@5 | nDCG@10 | Warm p50 / p95 ms |
| --- | --- | ---: | ---: | ---: |
| dev | bm25 | 0.4705 | 0.4548 | 43.2 / 99.4 |
| dev | dense | 0.4899 | 0.5792 | 76.5 / 147.1 |
| dev | hybrid | 0.5734 | 0.5872 | 81.6 / 148.0 |
| dev | hybrid-cross-encoder | 0.6185 | 0.6409 | 2489.8 / 2896.2 |
| dev | feature-hash-reference | 0.5164 | 0.4865 | 32.7 / 100.8 |
| validation | bm25 | 0.6875 | 0.5351 | 56.5 / 83.9 |
| validation | dense | 0.7500 | 0.5755 | 91.4 / 144.9 |
| validation | hybrid | 0.6875 | 0.5509 | 101.0 / 163.1 |
| validation | hybrid-cross-encoder | 0.6875 | 0.6172 | 2649.7 / 2977.3 |
| validation | feature-hash-reference | 0.6250 | 0.5372 | 42.1 / 68.8 |
| test | bm25 | 0.6250 | 0.6035 | 54.7 / 79.5 |
| test | dense | 0.5104 | 0.5673 | 83.6 / 130.6 |
| test | hybrid | 0.7500 | 0.6556 | 86.6 / 131.9 |
| test | hybrid-cross-encoder | 0.6875 | 0.7206 | 2280.7 / 2824.0 |
| test | feature-hash-reference | 0.5625 | 0.5553 | 34.4 / 64.7 |

Raw JSON includes per-question ranked identities, source/passage hashes, code hashes and descriptive 2,000-draw family-bootstrap intervals. Each split has only two families; these intervals are unstable descriptive summaries, not population or significance evidence. Candidate depth 20, RRF constant 60, cross-encoder pair budget 256 tokens, batch size 8. Positive lexical eligibility remains in hybrid; this is not a pure fusion ablation. No wrong-release/unauthorized hits were observed in these queries; synthetic access-boundary tests provide separate adversarial checks.

## Validation-frozen answerability experiment

The fixed grid selected raw relevance logit threshold **-4.0** using validation only, minimizing `3 × unsupported answers + supported abstentions`. Frozen policy SHA-256: `13e40a1b8504101a04bf09be670edafb8b53fd91bb52632dfd66af0acf6f4bbb`. The same policy was used for test without retuning. The gate scores the production version-mode top four and returns at most one exact extract. Raw logits are not confidence or entailment probabilities.

| Split / path | Answer coverage | Unsupported answers | Supported abstentions | Unsupported errors / answered |
| --- | ---: | ---: | ---: | ---: |
| validation / baseline | 20/20 (100%) | 4 | 0 | 0.2000 |
| validation / gate | 16/20 (80%) | 1 | 1 | 0.0625 |
| test / baseline | 20/20 (100%) | 4 | 0 | 0.2000 |
| test / gate | 16/20 (80%) | 0 | 0 | 0.0000 |

Test gate end-to-end p50/p95: **540.2/680.5 ms**; includes retrieval, scoring, exact selection and citation checks; excludes loading/indexing. Answerability precision/recall and abstention precision/recall are in raw JSON. These use the proposed binary answerability labels, not semantic correctness. Among gated answered test questions, the top passage matches a proposed relevance label at rate 0.6875; incomplete labels and passage truncation limit that proxy.

**Decision:** keep learned scoring and the gate opt-in. The modest, AI-labeled evaluation does not establish reliable answer support. The current deterministic demo remains the default; BM25 is the inexpensive explicit comparison baseline. No claim that the default is the most accurate model. Do not promote a model based solely on test deltas. Threshold training is not neural model training; no weights were fine-tuned.

## New-public-prose impact experiment

Twelve exact, licensed same-release excerpt replays across three source families observed **1 true candidate, 3 false alarms, and 2 missed candidates** against AI-proposed review labels. Candidate precision 0.2500, recall 0.3333. Agreeing duplicates deliberately expose false positives. This reorders ingestion of real prose, not historical upstream accuracy. Confirmed-stale precision/recall remain unmeasured.

The lexical stage is disabled by default (`ENABLE_PROSE_REVIEW_CANDIDATES=true` enables it experimentally). It only proposes manual review and cannot confirm stale status. Public current passages in the same project/release, introduced after the saved answer, join the review fingerprint; private/wrong-release/quarantined material does not. Cited logical sources retain existing dependency handling. Original answers and evidence remain immutable; withdrawal resolution requires an explicit review.

## Actual compatible inference

Pinned `HuggingFaceTB/SmolLM2-135M-Instruct@12fd25f77366fa6b3b4b768ec3050bf629380bac` ran on CPU through a real loopback compatible HTTP endpoint: **2 inference requests**. This tiny model is a smoke fixture, not the recommended production model. Exact selections and failures are preserved in `evaluation/local-selector-v3.json`; usage tokens and actual outputs are recorded separately from human judgments.

- `What is the request_timeout default?` → abstained; deterministic citation validation passed; semantic correctness unmeasured.
- `Does request_timeout guarantee every database transaction is serializable?` → abstained; deterministic citation validation passed; semantic correctness unmeasured.

A real transport bug was found and fixed: a keyless endpoint received an invalid empty Bearer header. `local-selector-v3-before.json` records zero actual inference calls before the fix; it is not presented as a model run. A real HTTP regression supplements mock tests. Extract selection remains distinct from synthesized prose; fluent answer quality was not evaluated.

## Runtime, cost and limits

Test runtime: Windows-11-10.0.26200-SP0, Python 3.12.10, 12 logical CPUs, torch 2.14.1+cpu, 2 inference threads, CPU only. Timings are one warmed sequential pass with rotating ranking order on the owner's active computer, not isolated hardware, load-test percentiles, or an SLA. Test model loading 17.2s; ingestion of learned and hash copies 70.1s. Indexing/model loading are outside ranking latency.

MiniLM is 384-dimensional, normalized, commit-pinned; switching its model space requires a fresh database/index. The cross-encoder is pinned separately and does not require passage reindexing. Character chunking can exceed both models' token budgets and truncate supporting tails. Snapshot hashes identify source bytes, not relevance truth. No API or hosting fee was incurred. Token usage is measured for the local selector; electricity/network cost and production inference cost are unmeasured. Human answer correctness/relevance/completeness/semantic support, general contradiction accuracy, real stale-answer precision/recall, PostgreSQL learned retrieval quality and production load remain unmeasured.

The unsupported set includes conspicuous impossible guarantees and is easier than realistic user ambiguity. Labels identify proposed anchor-containing blocks, not exhaustive supporting evidence. Improve these with independent review before expanding toward 300–500. Removed-API and changed-default coverage needs a curated migration challenge set; existing version-specific and synthetic change checks do not establish broad migration accuracy.

## Reproduce

Follow `docs/MODELS.md` for the locked environment and pinned CPU models. Do not overwrite frozen datasets or policies.

```powershell
$env:HF_HOME=Join-Path $PWD '.model-cache'
$env:EMBEDDING_MODEL='sentence-transformers/all-MiniLM-L6-v2'
$env:EMBEDDING_REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
.venv\Scripts\python.exe scripts/evaluate_v3.py --stage calibrate  # fresh experiment only; refuses existing policy
.venv\Scripts\python.exe scripts/evaluate_v3.py --stage test --allow-ai-test-diagnostic
.venv\Scripts\python.exe scripts/evaluate_prose_impact.py
.venv\Scripts\python.exe scripts/verify_local_selector.py
.venv\Scripts\python.exe scripts/report_v3.py
```

To reproduce the exact frozen calibration, run in a separate checkout/output directory retaining the original dataset, remove only that disposable copy's generated policy, and compare the resulting threshold. Never use a failed/test run to tune the same heldout families. A successor human-reviewed dataset and new holdout are required after error-driven changes.
