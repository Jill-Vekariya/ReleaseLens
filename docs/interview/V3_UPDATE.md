# Interview update for the expanded evaluation milestone

Read the measured numbers in [V3_REPORT.md](../V3_REPORT.md), the model contract and the existing 42-question bank. These scripts describe AI-assisted project work; use first-person ownership only for work you personally reviewed, reproduced and understood.

## Recruiter explanation

ReleaseLens tracks which saved documentation answers may need review after source changes. It retains immutable citations, exact release and permission boundaries, passage dependencies, and review/correction history. Its portfolio value is the reproducible backend and the candid model evaluation, including failures, rather than an unsupported claim that generated answers are correct.

## Two-minute introduction

“ReleaseLens focuses on a specific problem: when documentation changes, which answers should I review and why? It saves the answer with immutable passage citations instead of overwriting evidence. Retrieval applies project, exact release, permissions, current revision and quarantine filters before scoring. A FastAPI service supports SQLite and a locally deployed Docker/PostgreSQL/pgvector stack. I used AI assistance for implementation and evaluation. The current benchmark has 70 AI-proposed questions across 14 pinned licensed snapshots, with whole-family dev/validation/test splits. It compares lexical, pretrained dense, hybrid and cross-encoder retrieval, retaining feature hashing as a reference. A relevance threshold is chosen on validation and frozen before the test diagnostic. Neither relevance logits nor exact citation membership prove a correct answer. A new prose-impact experiment performed poorly enough to remain disabled by default. The most useful engineering lesson was a real HTTP failure that mock tests missed: an empty authentication header stopped local inference. The project records the failed attempt, regression, fix and actual model output. My next contribution is independent label review and a code change I can explain myself.”

## Five-minute demonstration

- 0:00–0:40: State the product question and show release selection and immutable evidence.
- 0:40–1:40: Ask, inspect the original source, compare releases and explain why retrieval filtering precedes ranking.
- 1:40–2:50: Save the synthetic answer, update its cited fact, revalidate and show the preserved original and separate correction. Distinguish a deterministic fixture rule from prose truth.
- 2:50–3:30: Show a formatting-only event and a restricted direct-ID request.
- 3:30–4:30: Open `docs/V3_REPORT.md` and the raw per-query results; compare Recall@5/nDCG@10, latency, coverage and unsupported errors. State zero human-reviewed labels.
- 4:30–5:00: Explain why the prose experiment and learned gate remain opt-in, and show the real HTTP regression and local selector artifact. If enabling an experiment, use a separate database and the model instructions; do not switch the deployed corpus in place.

## Architecture walkthrough

Trusted curator → verified source bytes → immutable revision/passages and mutable current head → SQL/application scope → lexical/exact dense/hybrid → optional already-scoped relevance scorer → exact extract selection → citation identity/quote checks → saved owner-private answer/dependencies → cited logical changes or enabled public new-evidence candidates → fingerprinted review → preserved original plus separate correction. Transactions are serialized in one API process. Independent writers and multiworker snapshots remain unsupported; no OIDC or production capacity claim.

## Questions to practice

1. **Why can the larger recall score be lower than the original pilot?** The corpus and proposed relevant sets changed. Recall over many positive passages is harder than a single easy hit among a few candidates. The numbers are not directly comparable.
2. **What did you train?** No neural model weights. I integrated pinned pretrained encoders and evaluated a validation-selected decision threshold. Calling this model fine-tuning would be inaccurate.
3. **Why is a threshold of -4 not “negative confidence”?** It is an uncalibrated raw cross-encoder logit; its numeric scale depends on the model. It is not a probability or entailment score.
4. **How was leakage reduced?** Whole document families, release variants and duplicate intent groups stay together. Dataset/source hashes freeze bytes before tuning. Related concepts and public-source pretraining still limit independence; v3 test is now consumed.
5. **What is error among answered questions?** The measured proxy counts answers on proposed unsupported questions among answered cases. It misses wrong answers to answerable questions, so semantic error remains unmeasured.
6. **Why not deploy the prose detector?** It flags agreements and misses lexical paraphrases. The measured 12-case replay was poor; it remains opt-in and only queues manual review.
7. **Why is exact citation validation still useful?** It blocks invented IDs, wrong releases and modified quotes. Those are necessary provenance checks even though relevance/completeness need separate evaluation.
8. **What did live inference add beyond mocks?** Actual HTTP rejected an empty Bearer header that MockTransport accepted. The fix omits authentication when no key is configured, with a real HTTP regression.
9. **Why no fine-tuned reranker?** There is no sufficiently independent human-labeled training set. First curate hard negatives and a fresh holdout, then compare against the pretrained baseline.
10. **What can you personally defend?** Demonstrate your own reproduction, review and modification. The contribution log does not automatically attribute AI-authored code or labels to the user.

## Conditional résumé templates

No résumé or target job description was supplied. Use standard headings such as Projects, Skills and Experience. The following are templates; replace placeholders only with your own verified contribution and the current report numbers.

- `[Personally reviewed/reproduced/contributed to]` an AI-assisted Python/FastAPI documentation-change review service with immutable citations, exact-release/ACL filtering, saved-answer dependencies and PostgreSQL/pgvector persistence; verified `[checks you personally executed]`.
- `[Personally ran/analyzed]` a reproducible comparison of BM25, pretrained dense, hybrid and cross-encoder retrieval on 70 AI-proposed questions and 14 pinned licensed snapshots; documented `[test Recall@5/nDCG@10 from V3_REPORT]`, latency and zero human-reviewed labels.
- `[Personally diagnosed/implemented/reproduced]` `[your actual change]`; used `[actual regression/HTTP/CI evidence]` and reported coverage/unsupported-answer trade-offs without claiming model training or production deployment.

Supported terminology: Python, FastAPI, SQLAlchemy, SQLite, PostgreSQL, pgvector, Docker, pytest, CI, BM25, dense retrieval, hybrid search, cross-encoder reranking, provenance, access control and evaluation. Include only skills you can demonstrate. Private loopback deployment is not production hosting, and no guaranteed ATS selection is implied.
