# Requested task completion and remaining requirements

2026-10-16. This is a review of the uploaded eight-phase specification against actual source and retained execution artifacts, followed by a focused engineering closeout. It is not independent human review. The source of truth is the private repository's `milestone/evaluation-v3` branch; main and existing deployment data are preserved.

**The complete research/ownership objective is not finished.** The implemented local portfolio workflow and its engineering checks are demonstrable. Human semantic evaluation, realistic migration/hard-negative adjudication and the owner's independent implementation/understanding remain unfinished. More AI-generated rows cannot satisfy those requirements. Off-device deployment and enforceable private branch protection need external setup/decisions. Nothing has been merged, released publicly or made public.

## Original state and consequential problems

The original archive contained the immutable-evidence/change-review workflow, a hash-vector reference, selected documentation and a small synthetic evaluation. The canonical repository was newer: at the start of the earlier v3 continuation, `a703ea7` already included a pretrained-reranker experiment. It passed a fresh 106-test Linux baseline with one PG-only skip. The expanded source/evaluation milestone reached 125 passing unit/regression tests, two PG-only skips, plus actual passing PG/Docker/browser/recovery checks; see [audit](AUDIT.md), [progress](PROGRESS.md) and [v3 report](V3_REPORT.md). Do not compare these counts as performance gains.

Earlier actual defects included PostgreSQL DISTINCT over JSON, a cross-thread transaction lock, historical formatting requeues, missing release predicates in non-default production modes, request-body limit bypass, empty Bearer transport and failed-output usage accounting. Their regression/evidence records are retained; they are not newly discovered in this closeout.

This closeout began at canonical `0d60883`, PR #1, clean worktree. All ten existing files selected for edits matched SHA-256 hashes in the development mirror before transfer. New regressions reproduced acceptance of invalid label grades, duplicate labels/questions, nonboolean answerability, bad split totals, nonexistent/wrong-release review evidence, blank reviewer/answer fields and non-finite older reranker scores. Initial regression execution: **16 failed / 2 passed**, preserved in `evaluation/closeout-regression-before.json`; fixes passed all 24 closeout tests. No existing benchmark row, split, model, threshold or ranking was changed.

## Eight-phase acceptance map

| Phase | State | Source/evidence and practical boundary |
| --- | --- | --- |
| 1. Audit existing repository | Completed for recorded local scope | `AUDIT.md`, `V3_REVIEW.md`, this report and source map below. The current pass checks the delta and outstanding claims; earlier inspected components use their recorded audit, not a fictitious new whole-system audit. |
| 2. Cross-encoder comparison | Executed, bounded diagnostic | `relevance.RelevanceScorer`, `scripts/evaluate_v3.evaluate`, `v3-*.json`, `retrieval-supplement-v3.json`; cached-model dev profile adds stage timings/coverage. No independently verified accuracy or backend parity. |
| 3. Evaluation quality | Pipeline complete; semantic acceptance incomplete | 70 source-linked AI proposals, family split integrity, blank independent review export and stricter validation. Human-reviewed 0; realistic migration/removed-API/hard-negative coverage and adjudicated successor still pending. |
| 4. Change-impact verification | Controlled workflow verified; general-language accuracy incomplete | Lifecycle, impact and prose tests cover the matrix below. Real prose replay has poor precision/recall; only queues review and stays off by default. |
| 5. Security/reliability | Tested within local threat model | Scoped retrieval/direct-ID/history, fixed-token auth, transaction serialization, body limits, browser identity races and clone recovery. Not penetration-tested or public multi-tenant production. |
| 6. Fix real problems | Completed for reproduced defects | Three small validation areas changed; regressions preserve the original behavior and fail on actual invalid inputs. No new framework, neural training or unrelated refactor. |
| 7. Reproducibility/CI | Local checks executed; current-head CI linked from PR | `closeout-*-verification.json` records commands and exit codes. CI retains unit/static/prose, both PG tests and Docker/recovery jobs, and now publishes the supplemental ranking output. Current-head status must be read on PR #1. |
| 8. Portfolio/interview | Deliverables prepared; personal readiness incomplete | README comparison and existing `interview/V3_UPDATE.md`, `QUESTION_BANK.md`, `PRACTICE.md`, `WALKTHROUGH.md`, `OWNERSHIP.md`. Templates do not prove independent authorship. |

## Source-level audit map

| Capability | Inspected implementation / regression entry points |
| --- | --- |
| Source verification and immutable revisions | `sources.ingest_snapshot`, `sources.chunks`, `ingestion.ingest`; `tests/test_sources.py`, `test_lifecycle.py` |
| BM25/hash/learned/PG vector retrieval | `retrieval.bm25`, `HashEmbedder`, `SentenceEmbedder`, `rank`, `postgres_rank`; `test_retrieval.py`, `test_postgres.py` |
| Cross-encoder and finite scores | `relevance.RelevanceScorer.score` uses pinned pretrained pair scoring, raw logits and Identity activation; `evaluate_reranker.order_reranked`; `test_reranker_evaluation.py`, `test_closeout.py` |
| Answer selection, citations and review | `service.ask`, `validate_citations`, `revalidate`, `generation` compatible adapter; `test_generation.py`, `test_security.py`, `test_lifecycle.py` |
| Newly added counterevidence | `impact.current_public_counterevidence`, `queue_new_public_counterevidence`, `review_fingerprint`; `prose_impact.py`, `test_impact.py`, `test_v3.py` |
| API/security/storage | `api.create_app` and transaction dependency, `security.Principal`/`authorized_document`, `middleware.py`, SQLAlchemy models; `test_api_contract.py`, `test_body_limit.py`, `test_concurrency.py`, `test_migrations.py` |
| Dataset integrity and review | `review_dataset.load_dataset`, `scripts/review_benchmark.validate`; mutated disposable dataset and fictional review fixtures in `test_closeout.py` |
| Frontend and deployment | `web/app.js`, Compose, Nginx and Docker configuration; browser/security/load scripts, `verify_docker.py`, `verify_recovery.py`; prior actual outputs retained |

The ML modules are optional. `SentenceEmbedder` validates 384 dimensions; configured loading requires an immutable 40-character revision. The cross-encoder reranks after scoped retrieval and cannot add candidates; the API experiment scores four scoped results and chooses at most one extract. Empty pairs skip inference. Model failures propagate explicitly rather than switching encoders; a real cached offline run also probes a deliberately unavailable revision. Both models are pretrained integrations, not trained weights. [MODELS.md](MODELS.md) records exact revisions, dependencies, token budgets, index requirements and setup.

## Controlled change-impact matrix

| Requested scenario | Executed regression / outcome |
| --- | --- |
| Material cited fact change | `test_end_to_end_stale_correction_preserves_history`: curated exclusive synthetic assertion can confirm stale, preserving original and separate correction |
| Unrelated document/section | Dependency keys and prose scope tests; no blanket invalidation. Personal two-section exercise remains for the owner. |
| Formatting-only | `test_formatting_does_not_invalidate_and_next_update_still_finds_old_dependencies`, formatting/requeue regressions |
| Documentation version | `test_version_validation_even_for_unfiltered_baselines`, unknown-release and wrong-release candidate tests |
| Removed evidence | `test_removed_passage_is_insufficient_evidence` |
| Conflicting evidence | `test_conflicting_synthetic_evidence_abstains`, original-conflict revalidation regression |
| New public evidence | `test_new_public_source_queues_without_changing_original_evidence`, new-prose candidate test |
| Restricted/private evidence | ACL/direct-ID/owner tests and no-effect status/fingerprint impact tests |
| Repeated change/review | Idempotent ingestion, stable review fingerprint and repeated revalidation tests |
| Missing/ambiguous support | Unsupported/unknown-release abstention, removal and changed-prose manual-review tests |
| Transaction/failure recovery | Commit failure cannot return success, concurrent compare-and-swap winner/409, actual PG lifecycle and isolated clone migration/restart recovery |

These test names refer to the existing executable suite. Twelve licensed prose replays remain a separate AI-proposal diagnostic: 1 true candidate, 3 false alarms, 2 missed candidates; precision .25, recall .3333. They do not establish arbitrary contradiction or confirmed-stale accuracy. Newly added agreement can false-alarm and paraphrased contradiction can be missed. No NLI/truth classifier is claimed.

## Measured retrieval and answer behavior

The original v3 test has 20 questions, 16 proposed supported, two families. All methods use the same 14 snapshots/534 passages, queries and release/access boundaries. Recall/Precision averages exclude unsupported cases. Unjudged passages are unmatched proposals, not verified irrelevant.

| Method | Recall@5 | Proposal-label Precision@5 | MRR@10 | nDCG@10 | Original ranking p50/p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 | .6250 | .2000 | .6042 | .6035 | 54.7 / 79.5 |
| Pretrained dense | .5104 | .1625 | .6938 | .5673 | 83.6 / 130.6 |
| Hybrid | .7500 | .2375 | .6589 | .6556 | 86.6 / 131.9 |
| Hybrid + pretrained cross-encoder | .6875 | .2250 | .7674 | .7206 | 2280.7 / 2824.0 |
| Feature-hash hybrid reference | .5625 | .1875 | .5115 | .5553 | 34.4 / 64.7 |

Precision@5/MRR@10 were calculated descriptively from saved rankings, with original Recall/nDCG cross-checks and source identity/hash validation. The original consumed test was not rerun, relabeled or retuned. Input SHA-256 values, per-query results and descriptive family-bootstrap intervals are in `retrieval-supplement-v3.json`. Two families are insufficient for robust significance claims. Historical pre-rerank Recall@20 and reranking-only timings were never captured and remain null; the new development profile is separately measured rather than invented by subtracting different runs.

Hybrid wins the proposed Recall metric; reranking improves proposed ordering metrics at substantial CPU cost. No independent evidence justifies changing the demo default. Learned retrieval/gating remain opt-in, BM25 is the inexpensive lexical comparison, and hash-384 remains explicitly a reference. The positive lexical eligibility gate and 256-token truncation are known recall limits. Neural fine-tuning awaits appropriate independent labels and a new split.

The validation-frozen -4 raw-logit gate answered 16/20 test questions and abstained on 4/4 proposed unsupported cases; 11/16 selected passages matched proposed relevance. This is not zero semantic error. Semantic correctness, relevance, completeness/support and real-world stale-answer precision/recall are null/unmeasured. Actual tiny compatible model: two real calls, two rejected output schemas; no usable fluent generation claimed. Token usage is recorded, failed-call cost can remain unknown, and local model inference incurred no provider API fee. Electricity/network/CI billing and hosting cost are not measured.

New offline **development-only** profile (30 dev questions, 24 proposed supported, 600 pairs; same 534 passages): candidate Recall@20 **.8076**; retrieval p50/p95 **93.3/155.6 ms**; reranking **3298.9/4021.2 ms**; combined ranking **3391.7/4225.4 ms**. Loading took 14.2s, indexing 85.6s. Process peak resident working set was **715,669,504 bytes (682.5 MiB)**, including imports, both models, index and the unavailable-revision probe. Windows Python3.12.10, Intel family6/model186, 12 logical CPUs, torch2.14.1+cpu, two inference threads. Cached pinned models loaded offline; a requested all-zero absent revision raised OSError explicitly. These dev observations are not historical test timings or a production SLA. The profile preserves per-query values and code hashes.

## Verification and reproduction

Use Python 3.12 with `requirements.lock` and editable installation; see README. No type checker is configured, so no type-check success is claimed. Current static/unit commands:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest -q --junitxml=evaluation/my-tests.xml
node --check web/app.js
python -m compileall -q releaselens scripts alembic
python -m scripts.supplement_v3 --output evaluation/my-supplement.json
# Locked Windows ML environment, HF_HOME points to the existing populated cache:
python -m scripts.supplement_v3 --profile-dev --output evaluation/my-dev-profile.json
```

The supplement/profile refuse existing output paths. The profiler uses only dev rows, offline cached pinned models, two CPU threads, depth20, batch8 and a fresh memory-only index. It changes no model/policy. Full historical benchmark commands remain in V3_REPORT.md; repeating calibration requires a disposable copy and must not overwrite the frozen policy. The old original pilot is not a pristine future holdout because v3 development overlaps its concepts.

| Check | Actual evidence | Interpretation |
| --- | --- | --- |
| New regressions before fixes | 16 failed / 2 passed | Genuine reproduced validation defects, not suppressed tests |
| New regressions after fixes | 24 passed | Label/review/reranker/supplement/offline-error contracts |
| Linux static/unit | 149 passed, 2 PG-only skipped; lint/format/JS/compile pass | Fresh closeout execution, `closeout-linux-verification.json` |
| Windows static/unit | See `closeout-windows-verification.json` | Actual fresh Windows exit codes/counts; no cross-platform inference from Linux |
| PG integration | Both existing PG tests executed by CI and earlier actual Docker verification | Local unit skips are not database passes |
| Docker/HTTP/recovery | Actual prior verification artifacts and current PR CI jobs | No deletion/restore of owner data; disposable clone only |
| Browser/security/load | Prior `demo-v3-verification.json` and Docker/browser artifacts | Authenticated Edge and fresh demo; 100-request concurrency8 smoke, zero observed HTTP/wrong-release failures; no capacity claim. No UI/runtime path changed in this closeout. |
| Learned dev profile | `reranker-profile-dev-v3.json` | Separate actual development-only CPU execution; no test quality retuning |
| Current-head CI | [PR #1 checks](https://github.com/Jill-Vekariya/ReleaseLens/pull/1/checks) | Check exact head; previous 0d60883 run38879646646 passed all three jobs |
| Hosted deployment | Not run | No off-device account/budget approved; precise setup in DEPLOYMENT.md |

## Security findings and unresolved risks

Tested: server-owned token roles, no credentials in model context, parameterized SQL, pre-scoring release/project/ACL/current-head/quarantine scope, owner-private saved answers and history, role downgrade, no-store responses, identity-epoch UI suppression, bounded request bytes and commit-before-success. No response cache exists. Security tests do not prove absence of all vulnerabilities or constitute a penetration test.

The retained Oct15 dependency audit found no remaining reported PyPI advisories in the scanned pinned requirements after setuptools fixes; its local `torch+cpu` build was not covered. This closeout adds no dependencies and did not run a new container/OS/binary scan. `evaluation/dependency-verification.json` records that scope; do not label the project vulnerability-free.

Known limits: one serialized API process, no independent concurrent CLI writers, fixed local bearer credentials, no OIDC/organization tenancy, limited quarantine heuristic, no production rate/tenant quotas, no distributed snapshot guarantees. No public production-readiness claim. Source provenance for API uploads is a trusted administrator assertion. Private GitHub branch protection returned 403 on the current plan; checks run but merging is not server-enforced. Enabling protection needs a plan upgrade or explicit visibility decision; public visibility is prohibited by this task.

## Files changed in this closeout

| File(s) | Purpose |
| --- | --- |
| `releaselens/review_dataset.py` | Reject mechanically invalid grades, duplicates, types, block positions, review counts and split totals |
| `scripts/review_benchmark.py` | Validate submitted evidence against real same-project/release passage identities; require useful review fields without promoting labels |
| `scripts/evaluate_reranker.py` | Reject non-finite logits in the earlier experiment |
| `scripts/supplement_v3.py` | Preserve originals; compute sparse-label metrics and run separate offline dev-only stage profiling |
| `tests/test_closeout.py` | 24 regression/metric/provenance/scope/failure checks |
| `.github/workflows/ci.yml` | Execute/publish descriptive supplement within existing unit job |
| `README.md`, `docs/ARCHITECTURE.md`, `docs/EVALUATION.md`, `docs/DATASET_V3.md` | Measured comparison, current learned-stage description, protocol and review format |
| `docs/TASK_COMPLETION.md`, `docs/STATUS.md`, `docs/PROGRESS.md` | Acceptance map, concrete remaining work and durable resume point |
| `evaluation/closeout-*`, `retrieval-supplement-v3.json`, `reranker-profile-dev-v3.json` | Actual command results, initial failure evidence, immutable-input hashes and dev runtime observations |

## Remaining tasks, in priority order

1. **Real people:** independently review source relevance, answers, completeness and support; adjudicate disagreement with the supplied blank-review workflow. Create a new frozen successor and fresh holdout before error-driven tuning. Broader realistic hard negatives, changed defaults and removed APIs still need curation; not solved by inflated AI counts.
2. **Owner:** personally reproduce an experiment, explain a failed query and implement the unsolved contribution exercise. Record only commands/code/review actually performed by you. Prepared interview answers and résumé templates cannot substitute for this.
3. **Research after labels:** measure semantic selective risk/coverage and actual stale precision/recall; compare a narrowly scoped reranker fine-tune only when suitable labels exist. Keep weak prose detector experimental. Learned PG quality and production-scale load remain unmeasured; no current need justifies adding distributed infrastructure.
4. **Optional deployment/governance:** choose private off-device account/budget; verify TLS, secrets, persistence and recovery there. A paid API/host, main merge, release publication or visibility change requires explicit approval. Private branch protection additionally needs a supported GitHub plan. None was performed.

The code is demonstrable locally; full public-release readiness and independent scientific claims are **not accepted** until the corresponding reviews and deployment/security decisions occur. No pending item is silently called complete.

## Recruiter and interview deliverables

**Project description:** ReleaseLens is an AI-assisted Python/FastAPI documentation-change review service with immutable evidence, release- and permission-scoped retrieval, saved-answer dependencies and separate review/correction history. It includes PostgreSQL/pgvector persistence, Docker/CI verification and reproducible pretrained retrieval experiments with explicitly AI-proposed labels and measured limitations.

Use [the v3 update](interview/V3_UPDATE.md) for a two-minute introduction, architecture walkthrough and three conditional résumé bullets. Use [the 42-question bank](interview/QUESTION_BANK.md) and [personal exercises](interview/PRACTICE.md). No résumé/JD was supplied; templates require your actual contribution before submission.

Five-minute demo: 0:00–0:40 state the product question and show release selection; 0:40–1:40 ask/inspect immutable citation and compare releases; 1:40–2:50 change a synthetic cited fact and show preserved original, review and separate correction; 2:50–3:30 show formatting/no-effect and restricted-ID behavior; 3:30–4:30 compare measured quality/latency and state zero human labels; 4:30–5:00 explain failed local-model outputs, weak prose results and one concrete owner contribution. Use a separate demo database, not the owner's live storage.

Interview checklist: explain exact pre-scoring scope; hashing versus pretrained dense versus reranking; positive lexical gate and candidate ceiling; raw logits versus probability/entailment; family leakage and consumed holdout; citation membership versus truth; unchanged citation plus new counterevidence; manual candidate versus confirmed stale; idempotency/fingerprints; transaction/backup boundary; actual failure and regression; current cost/resource limits; personal work versus AI assistance.
