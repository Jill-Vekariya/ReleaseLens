# Reproducible evaluation and annotation protocol

## What ran

`python -m releaselens.evaluate` writes the exact development candidate JSONL and results with dataset SHA-256. All four modes use the same corpus, hash encoder, question set, top-k=4, and candidate depth=20. A/B/C intentionally omit the release predicate. D applies it. Local lexical ranking uses BM25 with k1=1.2 and b=0.75; fusion uses 1/(60+rank). The section-overlap heuristic is experimental.

There is one labeled relevant document per development case, making document-level Recall@4 equivalent to hit rate. MRR uses the first matching project/release/document. Ranking ties use stable release, document, and logical passage identity rather than random physical UUIDs. Latency is measured with perf_counter; cold first calls and tiny sample sizes limit interpretation. There is no load-test or provider-latency claim.

Synthetic expected document labels and change outcomes are authored from controlled fixture identities/values, without an LLM as detector and judge. They are still AI-authored, not independent human-reviewed generalization evidence. Tests for unsupported words are deliberately trivial probes, not a calibrated abstention benchmark.

Wilson 95% intervals describe binomial outcomes. Zero observed unauthorized retrievals does not prove a zero leak rate. Exact citation membership is reported separately from semantic support. Human accuracy, version-correct substantive answers, and abstention precision remain null until reviewed labels exist.

## Final scope and splits (not yet populated or evaluated)

Target 300–500 independently reviewed questions. A suggested allocation for 400 is: 100 version-specific, 60 cross-version, 50 retrieval relevance, 40 unsupported, 40 misleading newer-source, 30 conflict, 40 change/formatting, 20 authorization, 20 injection/leakage. Counts are a planning allocation, not a completed dataset.

Keep the current 24 synthetic cases as a separate development smoke suite. Build distinct development/tuning/held-out splits with entire topic families and selected patch releases held out. Deduplicate paraphrases, record question-family IDs, keep held-out labels out of prompts/reranker tuning, and freeze hashes before running final evaluation. Do not randomly split near-duplicate questions and call the result independent.

## Human review checklist

For every candidate record:

1. Read the pinned source revision, not a search snippet or current docs.
2. Confirm the requested release, mode caveats, relevant passage(s), and document permissions.
3. Record the expected answer or reason to abstain; identify every substantive claim.
4. Label entailment: supported, conflicting, missing, wrong-version, or unsupported.
5. For changes, independently compare the old and new fact/behavior and mark technical effect. Do not equate changed text with a stale answer.
6. Record reviewer identity/date, ambiguity notes, source IDs, and adjudication if reviewers disagree.
7. Set `review_status=human_verified` only after actual review. AI proposals start as `unreviewed`.

Example annotation fields: id, family_id, split, project, release(s), question, expected_claims, relevant_logical_passages, role, expected_abstention, change_scenario, review_status, reviewer, reviewed_at, notes.

## Required future experiments

Learned encoder vs lexical-only vs hybrid; no reranker vs heuristic vs learned cross-encoder; release filtering on/off; dependency impact vs document invalidation; normalization on/off; conservative manual review vs independently labeled semantic revalidation. Keep model commits, token budgets, prompts, inference settings, datasets and source revisions fixed across comparisons. Measure latency and actual provider usage/cost as well as quality. Use paired bootstrap uncertainty for ranking changes and Wilson intervals for appropriate binary rates.

Error analysis should include irrelevant extracts with shared vocabulary, missing context in paragraph chunks, deprecated alternatives still mentioned in documentation, lexical gates suppressing semantically relevant evidence, newly added contradictory passages, structural moves that change logical keys, and injected text that evades quarantine.

Do not retain the reranker or a future router solely because a synthetic demo looks attractive.
