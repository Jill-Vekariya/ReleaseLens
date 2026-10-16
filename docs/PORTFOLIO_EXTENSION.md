# Portfolio extension — October 16, 2026

## Scope and evidence

Authoritative checkout: `C:\Users\jillv\source\ReleaseLens\releaselens`; canonical private GitHub repository `Jill-Vekariya/ReleaseLens`. Original source ZIP remains a historical baseline. No existing corpus, database, secrets, label manifest, or application default were overwritten. This extension implements a **separate offline pretrained cross-encoder retrieval benchmark**. It is not a production reranker rollout or a replacement for independent answerability evaluation.

Fresh baseline audit: 101 passing pytest cases, one PostgreSQL-only skip, clean Ruff lint and formatting, October 16. The existing Docker deployment responds on loopback; PostgreSQL and backend health was observed. Historical CI and recovery results remain historical unless rerun.

## Why this milestone

The previous 16-supported-query tuning pilot favored learned hybrid on Recall@4 (16/16 vs lexical 15/16) but it reported default **0/6 abstentions** on six AI-proposed unsupported questions. It did not measure a cross-encoder. These numbers do not establish better real-world answering. Do not turn on a complex model merely because an AI-labeled tiny pilot improves one metric. The new reproducible comparison directly answers whether reranking the authorized candidate set helps enough to justify latency, memory, dependency size, and ongoing review.

## Reproducible tuning-only experiment

Python 3.12, project environment, locked learned retrieval dependencies and local CPU model cache are required. No paid inference endpoint is used. Model identities:

- Bi-encoder: `sentence-transformers/all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41`; 384 dimensions; normalized vectors; model switching requires a full separate corpus index.
- Cross-encoder: `cross-encoder/ms-marco-MiniLM-L-6-v2@233902d25c440f23af6f7d6e94d2946bac0bee0a`; pretrained text-ranking head, Apache-2.0 per model card; CPU, max 256 tokens, batch size 16. No fine-tuning claim.
- Source data: four already pinned/licensed pages and immutable `evaluation/pilot-v2.jsonl` with SHA-256 verified by `load_pilot`.
- Exact-revision/project/role/current-head/quarantine/model filters apply **before** candidate scoring. The hybrid mode retains its existing positive lexical gate. The reranker receives at most 20 in-scope candidates and cannot reintroduce excluded passages.

PowerShell, run from repository root:

```powershell
$env:HF_HOME="$PWD\.model-cache"
$env:EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
$env:EMBEDDING_REVISION="1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
$env:HF_HUB_DISABLE_TELEMETRY="1"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\evaluate_reranker.py
```

Output: `evaluation/pretrained-reranker-tuning.json`. Measures Recall@5, nDCG@10, MRR@5, sequential warmed retrieval p50/p95, and family-bootstrap intervals for paired reranker differences. Results are AI-proposed passage relevance **not** independently verified ground truth. Scores are not calibrated confidence, relevance is not answer support, and latencies are not throughput/load or production SLAs. Held-out questions are intentionally blocked by CLI. Inspect `records` for per-question failures and actual retrieved evidence identities.

## Acceptance decisions and missing evidence

- Keep current default deterministic extractive/hybrid application behavior. The experiment is offline and has no schema/index change. Any learned production switch must explicitly regenerate all passage embeddings, scope the index by encoder identity, and rerun PostgreSQL-specific authorization and performance tests.
- Track **unsupported coverage** and unsupported answer errors independently of retrieval metrics. The observed 0/6 abstention baseline is a stop sign for quality claims, not a reason to suppress those questions in the report. Calibrate answerability on independent reviewed development/validation labels; do not choose an arbitrary cross-encoder logit threshold using the frozen heldout set.
- Human review protocol: `docs/PILOT_ANNOTATION.md`. Record annotator identity, date, exact source/passage/release, competing citations, expected extract or abstention, and disagreement resolution. No labels can be upgraded to `human_verified` by automated checks. Fifty to 100 reviewed questions should precede a defensible expansion to 300-500; split families and near-duplicate release variants before tuning.
- Real-prose contradiction, removal, false-alarm/missed-change precision and recall, OIDC/production rate limiting, a deployed private off-device URL, and independent human semantic support remain **unmeasured or unimplemented**. Preserve original answers; any learned classifier must only suggest manual review until defensible confirmed-stale rules or recorded human verification exist.
- Compatible extract-selector currently has mock tests; do not claim actual model usage without reproducible provider/local endpoint evidence and measured token/cost metadata.

## Recruiter description

ReleaseLens is an AI-assisted version-aware documentation review service. It records immutable cited answers and passage-level dependencies, so a documentation update can queue saved answers for review while retaining the original evidence and any separately saved correction. A modular FastAPI application uses SQLite for local development and a Dockerized PostgreSQL/pgvector stack for private loopback operation. Scope filtering occurs before retrieval; human judgment remains required for non-deterministic claims.

## Two-minute technical introduction

“I worked with AI assistance to turn a documentation question-answering prototype into an auditable change-impact workflow. Instead of treating a response as disposable text, ReleaseLens stores the exact release and passage revision behind it. When documentation changes, it compares logical passages and identifies answers whose cited evidence may need review. It deliberately does not call every changed statement incorrect. Synthetic exclusive facts permit a narrow deterministic stale verdict; prose and conflicting new evidence require review. Retrieval is scoped by project, release, and authorization before scoring. I used repeatable source hashes, tests, a local PostgreSQL deployment and a small pilot to check behavior, but the relevance labels are AI-assisted proposals, not human ground truth. The failure I emphasize is abstention: the initial selector answered all six unsupported tuning probes. My next decision depends on human-verified evaluation, not just making the model more complicated. The implementation and documentation are AI-assisted; I’m using this project to demonstrate reproducible technical understanding and hands-on code review rather than claiming that I personally authored every module.”

## Five-minute demonstration script

0:00–0:45 — Introduce product question and show project/release selector and evidence metadata.
0:45–1:30 — Ask a Pydantic v1 configuration question, inspect exact quote, immutable citation and selected release; compare Pydantic v2.
1:30–2:50 — Save a synthetic timeout answer, edit its cited passage, inspect pending impact then confirmed-stale review and separately linked corrected answer. Explain restricted synthetic evidence is not real-world prose entailment.
2:50–3:35 — Change an uncited section or whitespace, show no blanket document-level invalidation.
3:35–4:15 — Switch Reader/Admin roles, demonstrate direct-reference access controls and why filtering after top-k is insufficient.
4:15–5:00 — Present tuning metrics with dataset and reviewer caveats, show an unsupported case the extractor failed to abstain on, and explain why the reranker stays offline pending human evaluation.

## Architecture interview walkthrough

Trusted curator -> immutable versioned document/passages -> current-head SQL indices -> project/release/classification/quarantine predicates -> BM25 / exact dense / hybrid -> constrained extract selector -> exact citation validation -> saved answer+dependencies -> changed logical section and eligible public synthetic counterevidence -> fingerprinted manual review or narrowly justified stale classification -> immutable original plus separately linked correction. FastAPI owns transactions within one process; independent writers and multiworker snapshots need further design.

## Focused interview questions

1. **Why not put version in the prompt?** A prompt cannot enforce retrieval eligibility; SQL pre-filtering prevents wrong-release evidence from entering candidates.
2. **Why can a citation still be wrong?** Identifier and exact quote membership establish provenance, not relevance, contextual completeness, or entailment.
3. **Where can hybrid fail?** A lexical eligibility gate can suppress zero-overlap semantic matches; rank fusion can also demote an otherwise good literal match.
4. **Why test Recall@5 and nDCG@10?** Recall measures presence among top five; graded nDCG exposes ranking order among ten, including early precision.
5. **How avoid leakage?** Freeze family/near-duplicate/version split before tuning, keep related variants together, withhold independently adjudicated test labels.
6. **Why a separate reranker?** It attends jointly to query and passage but adds CPU latency, model dependencies, and token truncation risk; benefit must be measured.
7. **What makes an answer stale?** An explicit curated exclusive synthetic value changed can warrant deterministic classification; competing prose or a new source triggers review, not automatic guilt.
8. **What does 101 passing tests mean?** Regression coverage within a supported single-process design, not independently measured user correctness, distributed consistency, or production security.
9. **Why not train immediately?** Only AI-proposed labels are available; a fine-tuned reranker could overfit the limited corpus and undermine held-out independence.
10. **What would you change first?** Human-adjudicated unsupported queries, calibrated abstention and an expanded licensed corpus, then a frozen test and matched reranker comparisons.

## Contribution record and résumé text

Current attributable user work: project specifications, quality goals, access authorization and engineering priorities. Earlier code and this extension were AI-assisted; independent user-authored coding, annotation and review remain unrecorded. To claim personal implementation, make and explain your own test or code modification and record it in `docs/OWNERSHIP.md`. The two-section lifecycle test in that document remains an unsolved personal exercise.

**Conditional résumé bullets — use only after personally reviewing and reproducing the work; do not present as independent implementation without doing so:**

- Explored a FastAPI/PostgreSQL documentation-change review system with immutable cited answers, version-scoped retrieval, passage dependencies, and review history; validated local regression coverage of 101 passing tests (one database-specific skip).
- Benchmarked pretrained MiniLM dense and hybrid retrieval against lexical search using 16 AI-reviewed supported tuning questions; documented Recall@4 of 15/16 lexical and 16/16 hybrid alongside limitations from zero human-reviewed cases.
- Added and examined a repeatable offline pretrained cross-encoder comparison with authorization-scoped candidates, Recall@5, nDCG@10 and paired family-bootstrap intervals; report actual values from `evaluation/pretrained-reranker-tuning.json` only after the model run succeeds.

Target-role keywords supported by implemented or explored work: Python, FastAPI, SQLAlchemy, PostgreSQL, pgvector, SQLite, Docker, pytest, retrieval evaluation, sentence-transformers, provenance, access control, CI, regression testing. Do not claim model fine-tuning, RAG generation accuracy, production scale, or human-validated relevance.


## Actual cross-encoder tuning result — 2026-10-16

The offline CPU benchmark completed successfully: `evaluation/pretrained-reranker-tuning.json` (22 tuning retrieval questions, of which 16 were AI-proposed supported and six were AI-proposed unsupported; zero independently human-reviewed). Four original pinned source pages and the frozen `pilot-v2` dataset were reused, not edited. The run used the pinned MiniLM bi-encoder and `cross-encoder/ms-marco-MiniLM-L-6-v2@233902d25c440f23af6f7d6e94d2946bac0bee0a`. All results were release/permission scoped before candidate scoring; there were zero observed wrong-release/unauthorized hits in this small experiment.

| CPU offline retrieval | Recall@5 | nDCG@10 | Warm p50 / p95 ms |
| --- | ---: | ---: | ---: |
| BM25 | 15/16 (0.9375) | 0.8454 | 15.35 / 73.45 |
| Pinned dense | 15/16 (0.9375) | 0.8348 | 42.15 / 101.78 |
| Hybrid | 16/16 (1.0000) | 0.8558 | 39.34 / 91.83 |
| Hybrid + pretrained cross-encoder | 15/16 (0.9375) | 0.9054 | 701.39 / 1404.72 |

Paired reranker-minus-hybrid nDCG@10 +0.04966; descriptive family-bootstrap 95% interval [-0.1463, 0.2034], spanning zero. Recall@5 delta -0.0625, family-bootstrap interval [-0.25, 0]. This is **not** evidence of reliable superiority: the reranker sacrificed one proposed relevant top-five hit and added large CPU cost. Leave it **offline only**. Labels are AI proposals; human semantic support, answerability, prose-change precision/recall, and held-out results remain unmeasured. CPU timings are sequential warmed pilot observations, not production throughput or a rate-limited SLA. Six unsupported probes were not turned into true negatives for retrieval scoring; do not infer improved abstention from logits. No hosting expenses or provider calls.

Reproduce with `python scripts/evaluate_reranker.py` after setting model/revision environment as above. The output contains per-question ranked evidence identities, model revision, dataset hash, paired confidence intervals and the full limitations. The test module `tests/test_reranker_evaluation.py` checks deterministic reranking and metric bookkeeping.
