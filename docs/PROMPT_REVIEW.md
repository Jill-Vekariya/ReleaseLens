# Selected engineering improvements from the October 16 proposal

The owner requested judgment, not literal execution of every item in Pasted text(9).txt. This is an implementing-AI audit and change record, not an independent human review or a claim about hiring outcomes.

Starting state: f1f93d511dfe2146cad87cc9d20bd149ba86aedb, clean canonical and development checkouts on milestone/migration-challenge-v1. PR #2 was open; exact-head CI run38915032709 passed unit/PostgreSQL/Docker. Canonical GitHub permissions were ADMIN and source visibility PUBLIC. Existing source, datasets, model revisions, results, live data and credentials were preserved. No repository visibility change or main merge is part of this follow-up.

| Requirement | Existing implementation / actual evidence | Gap and selected action |
| --- | --- | --- |
| Authentic migration questions and provenance | 24 frozen proposals, 19 pinned MIT snapshots, source/license/anchor validation; actual CPU comparison retained | Already implemented; preserve rather than add another AI dataset |
| Independent evaluation | Blank JSONL forms and structural submission validation; human-reviewed0 | Add an offline readable packet with all permitted source blocks, immutable URLs, licenses and a review rubric; retain human review as pending |
| Strict dataset schema | Existing IDs, grades, split, release, hash, annotation-state checks | Four mutations were accepted: unknown version, unknown field, category and authorship. Add explicit frozen-version/field/category/origin contracts |
| Split isolation | Family/intent/exact-label checks and reserved-test refusal | Add deterministic machine-readable near-question, source-page, passage, labeled-evidence and upstream-revision audit; do not label a heuristic proof of no leakage |
| Retrieval/abstention metrics | Actual matched five-way CPU comparisons and two failed validation negatives | Preserve consumed results and failed threshold transfer; no fresh model selection or threshold tuning |
| Saved-answer impact and authorization | Immutable originals/corrections, dependency tests, restricted-counterevidence exclusion, poor real-prose replay retained | Existing scope remains sufficient; retrieval questions do not become historical migration-impact truth labels |
| Deployment and CI | Actual local Docker/PG/recovery/browser checks; exact-head CI | No new infrastructure justified; verify this code delta with local checks and new exact-head CI |

## Why these changes matter

Dataset contracts prevent silent schema drift from looking like a legitimate evaluation run. The audit exposes what the procedural split does and does not isolate. The packet reduces the work needed for a qualified person to inspect real evidence without seeing expected answers, rankings, negative labels or model scores. These are useful engineering and evaluation trade-offs to explain in an interview; additional frameworks, model training, or more synthetic question counts would not supply independent evidence.

The review packet includes full passage inventories for every selected project/release, including alternative evidence outside the AI's named anchors. Sources are deduplicated and collapsible. All content is escaped, no JavaScript is used, source links must match their recorded immutable GitHub repository/commit/path, and original licenses accompany source text. Question categories and expected answerability are omitted. Public Git still contains proposal labels, so blindness remains a reviewer procedure, not secret-label isolation. The packet is read-only; use the existing JSONL form for submissions. Support, relevance, completeness, uncertainty and impact are distinct rubric dimensions. Partial/uncertain support belongs in the rationale and requires adjudication; do not force it into confident answerability or invent agreement statistics.

## Reproduce

Run in the locked Python3.12 environment, choosing new output paths:

```bash
python -m scripts.review_benchmark audit --dataset challenge --file evaluation/my-split-audit.json
python -m scripts.review_benchmark packet --dataset challenge --split dev --file reviews/my-review-packet.html
python -m scripts.review_benchmark export --dataset challenge --split dev --file reviews/my-review.jsonl
python -m scripts.review_benchmark validate --dataset challenge --file reviews/my-completed-review.jsonl
```

The audit reads source/label metadata but makes zero model calls and scores zero questions. It reports fixed token-set Jaccard >=0.8 after release-prefix removal as a review flag, not a learned semantic duplicate classifier. Shared upstream revision identities across different pages are reported rather than treated automatically as label leakage. Output is deterministic for unchanged source/code. Audit/packet commands refuse to overwrite existing reviewer or evidence files.

Committed outputs: evaluation/challenge-split-audit-v1.json and docs/review/challenge-dev-packet.html. Open the HTML locally; the adjacent challenge-dev-blank.jsonl remains the submission template. The packet is generated from validated source/question metadata, independently of expected answers and relevance anchors. It is not an executed human review.

## Actual outcomes and limits

New tests initially failed7/7: four reproduced schema gaps, three missing audit/packet capabilities. This is retained in evaluation/review-audit-before.xml; the missing capabilities are not retrospectively called application defects. Two further regressions verify audit/packet overwrite refusal. All9 focused cases pass after implementation, without weakening assertions.

The actual challenge audit reports24cases, splits12/4/8, zero cross-split family/intent/source-page/labeled-evidence/exact-passage groups and zero near-question flags at the fixed heuristic. Four upstream project/release commit identities are shared across splits, as expected for multiple pages from the same library releases. This is not unseen-release, unseen-corpus or pretraining independence. Public proposals, shared concepts and missed paraphrases remain limitations. The audit contains identities/counts, not test questions, expected answers or prediction scores. Schema validation/source hashes do not prove semantic truth.

The real held-out questions remain unscored. No original benchmark, dataset, label, threshold or model changed; learned inference is not repeated to improve the narrative. Actual local/Windows verification for this follow-up is recorded separately in evaluation/review-audit-*-verification.json. Check PR #2's latest head and execution link for current CI rather than relying on the starting run.

## Intentionally deferred or discarded

- A third product/domain and a larger dataset: useful later, but adding unreviewed labels now does not solve the main evidence gap. Existing new JSON-schema/session source families remain reserved; they are not called an unseen product.
- New NLI, fluent generation, reranker training or statistical agreement output: unsupported by current human labels and unnecessary for this bounded milestone. Agreement/kappa cannot be fabricated from AI review.
- Repeating every historical browser/load/model benchmark: no application, identity, schema migration or frontend workflow changed; run the affected suite plus actual current-head PostgreSQL/Docker CI instead.
- A new deployment framework, multiworker system or paid service: no concrete need under the local portfolio scope.
- The proposal's private-repository wording: stale. Keep the owner's authorized PUBLIC source and existing branch protection; do not change visibility.

Human/adjudicated relevance and semantic answer support, actual historical migration-impact ground truth, and personal ownership remain genuine work by people. Pretrained integration is not model training, and passing CI is not production readiness or a hiring guarantee.


## Executed follow-up verification

Linux and Windows each passed **172 tests, 2 PostgreSQL-only skips**, with Ruff lint/format, JavaScript syntax, compilation, provenance/contract audit and a fresh dev/validation hash diagnostic all exiting0. Original frozen data, policy and model outputs stayed unchanged. The audit and review HTML regenerated byte-for-byte across both platforms. Isolated installed Edge verified12questions/19source documents, native expandable sections, zero scripts and zero observed page errors; screenshot inspection confirmed readable source/provenance/license layout. No personal browser profile or live app state was used.

The nine focused regressions pass. Existing tracked evaluation artifacts were compared against starting commit f1f93d5 and preserved; new command reports, initial failures and outputs use separate paths. CI now executes and uploads the split audit in the unit job. The latest PR #2 description records actual exact-head unit/PostgreSQL/Docker results after the push; this paragraph does not substitute prepared configuration for execution.
