# Focused migration and hard-negative challenge

2026-10-16. This closes a useful evaluation-coverage gap without adding a model, service, training job or public deployment. It is a separate frozen **24-question AI-proposal diagnostic**, not an extension of the consumed v3 test and not human ground truth. The original 70 questions, original source snapshots, model pins, threshold and ranking artifacts are preserved.

## Scope and provenance

Twelve development cases cover native V2 removals versus deprecations (GetterDict, GenericModel, allow_mutation, parse_raw), renamed settings, changed underscore behavior, bypassed validation, a backend-specific pool exception, and missing performance/workload information. Four validation cases address dict versus model.dict, subclass serialization defaults and missing production serialization inputs. Eight reserved questions concern JSON Schema and ORM session behavior from newly added page families.

Four questions are realistically unsupported because deployment measurements, workload or input records are missing. Their same-release lexically related passages are recorded as **proposed insufficient evidence**, with identity, hash, anchor and rationale. These are not proven negatives: a reviewer may reject the proposal or add supporting context. False premises that the source actually resolves are answerable with a correction, not automatically abstentions. Removed, renamed and deprecated APIs stay distinct; V1 compatibility namespaces do not imply native V2 support.

Five additional snapshots (one migration guide and four JSON-schema/session pages) retain the four already verified release commits, original MIT licenses, source/license hashes and canonical URLs. The challenge indexes all 19 snapshots / 707 passages, including reserved-family text. Default demo ingestion stays four pages; `--expanded` explicitly preserves the frozen v3 14-page / 534-passage set. Only `--challenge` selects 19 pages, in a fresh database or maintenance window. Adding files cannot silently change the v3 corpus. This guard fixes a reproduced 19-versus-14 CLI regression, with initial failure in `evaluation/challenge-ingestion-before.json` and a passing regression.

Dataset SHA-256: `f21d1cb2843ed8f977011d0ece86b32a9249d4ff4d3d0c488de58c75ac932a0b`. The manifest freezes 12 dev / 4 validation / 8 test questions, six page families, all release variants and source hashes. Human-reviewed and independently reviewed records remain **zero**.

## Leakage boundary

JSON-schema and ORM-session files were absent from v3. Their eight questions are not scored by the new runner, which rejects test selection with no override. Related concepts can still overlap other pages; public-model pretraining contamination is unaudited. Source text is indexed, so this is an unscored query/family holdout rather than an unseen corpus. The old v3 test is consumed. Serialization was already inspected in v3 and serves only as validation here. No claim of a fresh, secret, independently labeled test is made.

No model/threshold search occurs. The optional learned run uses the same pinned MiniLM, pretrained cross-encoder, fixed retrieval parameters and **previously frozen -4 threshold**. Applying that old threshold to new source/questions is an out-of-distribution transfer diagnostic, not calibration or approval to enable it in the application. The production default is unchanged. Exact citation checks, proposal-label relevance and semantic support remain separate.

## Reproduce and review

```bash
# Existing frozen files are verified by tests; the builder refuses overwriting them.
python -m pytest tests/test_challenge.py -q
python -m scripts.evaluate_challenge --split dev validation --output evaluation/my-challenge-hash.json
# In the locked Windows learned environment; HF_HOME points to the populated cache:
python -m scripts.evaluate_challenge --learned --split dev validation --output evaluation/my-challenge-learned.json
# Export a new blank reviewer copy; do not edit the shipped template in place.
python -m scripts.review_benchmark export --dataset challenge --split dev --file reviews/my-challenge-dev.jsonl
python -m scripts.review_benchmark validate --dataset challenge --file reviews/my-challenge-dev.jsonl
```

`python -m scripts.build_challenge --fetch` fetches only pinned public sources and freezes once, in a disposable fresh curation copy without existing challenge outputs. It never replaces v3. `load_challenge` checks source and hard-negative identities, exact anchors/hashes, family boundaries and that reserved source files were absent from v3. The evaluation uses new memory-only indexes, cached offline models, two CPU threads, rotating modes and no paid API. It refuses existing output paths and verifies original v3 data/policy/prediction hashes after execution.

The ready-to-copy [blank development review packet](review/challenge-dev-blank.jsonl) contains questions and source references without AI-proposed answers, passage labels or hard-negative proposals. Read all same-project/release snapshots, record a source-based answer or absence rationale and all relevant passage identities. Use a genuine reviewer identity/date and record uncertainty. A second person should adjudicate ambiguous cases. Mechanical validation cannot authenticate a person or prove relevance; it never promotes labels or claims a human review occurred. Preserve rejected proposals and curate an explicitly reviewed successor before confirmatory evaluation or training.

## Results and interpretation

Actual diagnostic outputs are `evaluation/challenge-hash-v1.json` (Linux reference) and `evaluation/challenge-learned-v1.json` (cached Windows learned comparison). Their code, dataset, manifest, old-policy and original-v3 hashes identify the run. Results use sparse AI proposals, and even a correct answerable classification may return an irrelevant extract. Human semantic error is unmeasured. Do not compare these scores as gains over v3: the corpus, questions, supported denominator and machine differ. With only two supported validation cases and four negatives overall, significance or population-accuracy claims would be unjustified.

The original threshold is not retuned even when the realistic negatives expose failures. The weak prose candidate stage stays disabled by default. No neural training, public hosting or paid infrastructure was added.

## What is required now

For a **local portfolio demonstration**, core workflow, safe corpus selection, regression/CI checks and honest results are the acceptance scope. Extra hosting, paid GitHub protection, larger benchmarks, fine-tuning and distributed infrastructure are optional future work, not mandatory blockers.

For **independent accuracy claims**, actual human/adjudicated relevance and answer-support labels remain necessary. For **personal résumé/interview claims**, personally reproduce and explain a change using the preserved ownership exercise. Neither can be performed or recorded on the user's behalf. Off-device/private production needs separate account, cost and security decisions only if requested.

## Actual CPU diagnostic - 2026-10-16

The saved Windows run scored 12 dev and 4 validation queries, zero reserved queries, across five modes (80 retrieval records). Dev has 10 proposed supported queries; validation has only 2. Ranking averages exclude unsupported cases; timing includes all queries in the split. Parameters: Recall@5/nDCG@10, candidate depth 20, RRF constant 60, gate top 4. Windows 11 / Python 3.12.10, 12 logical CPUs, 2 Torch threads, SQLite memory-only exact vectors/BM25. Cached pinned model loading took 145.9 s and index building 117.7 s. These stages are outside warmed ranking/answer timings; results are sequential local observations, not an HTTP service SLA.

| Split / retrieval | Recall@5 | nDCG@10 | Ranking p50 / p95 ms |
| --- | ---: | ---: | ---: |
| dev / bm25 | 0.9000 | 0.7595 | 94.93 / 181.22 |
| dev / dense | 0.5000 | 0.3595 | 155.67 / 353.03 |
| dev / feature-hash-reference | 0.4000 | 0.4896 | 63.88 / 117.49 |
| dev / hybrid | 0.6000 | 0.5919 | 155.45 / 239.44 |
| dev / hybrid-cross-encoder | 0.6000 | 0.5051 | 3716.15 / 4781.16 |
| validation / bm25 | 0.0000 | 0.3333 | 53.65 / 128.76 |
| validation / dense | 0.5000 | 0.5000 | 140.23 / 209.58 |
| validation / feature-hash-reference | 0.5000 | 0.3155 | 64.23 / 104.91 |
| validation / hybrid | 0.5000 | 0.3155 | 147.02 / 179.50 |
| validation / hybrid-cross-encoder | 0.5000 | 0.5000 | 3925.33 / 5039.39 |

BM25 won the development Recall@5 comparison and was much faster than pretrained reranking. On validation, the tiny two-supported-case denominator does not support reliable model selection. Sparse AI relevance proposals can omit valid evidence; no score above is independent accuracy. The unchanged demonstration default remains a reference; no evidence here supports enabling the learned gate or changing it after observing failures.

The ungated learned-encoder ask baseline answered 16/16, including all four proposed unsupported questions. The unchanged -4 gate answered 9/12 dev (two correct proposed abstentions and one supported abstention) and 4/4 validation, including BOTH unsupported validation cases: mc1-014 requests exact production User JSON bytes without records; mc1-016 requests exact production datetime serialization without values. Overall coverage was 13/16=81.25%; 2/13 answered cases were proposed unsupported. That narrower unsupported-answer diagnostic omits wrong or incomplete answers to answerable questions, so semantic answer error remains unmeasured. Exact citation validation passed, demonstrating why quote membership is insufficient evidence of an answer.

Across the16 selected sequential service-call probes, baseline end-to-end p50/p95 was 160.87/245.01 ms and gated service-call p50/p95 was 843.87/1636.97 ms. This measures the in-process ask workflow without HTTP/network overhead or model/index loading, not a deployed-load benchmark. Model memory was not captured separately for this challenge. Provider API cost was 0; electricity/network/CI billing was not metered. Full per-query timings, hashes, model revisions and limits remain in evaluation/challenge-learned-v1.json.

Local Linux and Windows each passed 163 tests/2 PG-only skips, with lint/format/JS/compile passing. Windows initially exposed implicit-encoding test-fixture failures; explicit UTF-8 preserved the assertions, with failure and passing artifacts retained. Challenge exact-head CI is checked on its new PR; previous passing PR #1 is not evidence for this delta.
