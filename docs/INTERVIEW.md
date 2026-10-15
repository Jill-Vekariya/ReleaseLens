# Demonstration and interview guide

## Executable 3–5 minute local demonstration

0:00–0:30: Explain that version-unfiltered retrieval can return newer instructions for an older dependency. State that the local default is a deterministic extraction demo.

0:30–1:15: Ask about Pydantic model configuration for 1.10.15. Inspect a cited passage. Run an unfiltered baseline and observe its release failure if it retrieves mixed releases; generation abstains rather than citing the wrong version. Compare 1.10.15 and 2.10.4 side by side.

1:15–2:45: Switch to Administrator and Change Intelligence. Save the current request-timeout answer. Toggle the synthetic policy value. Revalidate the pending old answer. Inspect old evidence, changed evidence, status, correction link, and audit history. Point out that synthetic structured facts make this verdict deterministic; real changed prose gets manual review.

2:45–3:20: Save the current answer and make a formatting-only update. Show that it does not automatically invalidate the answer. Repeating revalidation against the same heads returns the same audit result.

3:20–4:00: Probe the restricted synthetic canary as Reader vs Administrator. Explain the SQL/application permission boundary and owner-scoped histories.

4:00–5:00: Show Evaluation. State the 24-question synthetic scope, real latency output, unreviewed labels, missing learned-model quality measurements, and deployment limits. Never present the synthetic 100% change outcome as general accuracy.

## Interview prompts

1. Why do project and release predicates belong in data access rather than just the prompt?
2. What is BM25's document-length normalization doing, and why does RRF avoid raw score calibration?
3. What does exact citation membership fail to prove?
4. Why does a formatting-only intermediate revision create a subtle dependency-tracking bug?
5. How can a new source make an old answer wrong even if its cited passages never change?
6. Why is a same-user role downgrade different from an ordinary cross-user access test?
7. How would approximate vector indexes interact with ACL selectivity and recall?
8. At 10 million passages, what would you profile before adding ANN or distributed workers?
9. How would you use an outbox, review fingerprints and head-version checks to make async revalidation reliable?
10. How would you establish that a learned reranker improves held-out retrieval without evaluation leakage?

## Truthful current résumé material

These describe the implemented artifact; they do not imply employment experience or independent human authorship. After independently operating/reviewing it, adapt them to accurately describe your contribution.

- Built an AI-assisted FastAPI evidence system with release-scoped retrieval, deterministic citation checks, and four commit-pinned open-source documentation snapshots.
- Implemented immutable answer-to-source dependencies, transactional source updates, synthetic stale-answer revalidation, and preserved correction/audit history.
- Added automated lifecycle/security/source-integrity tests and a reproducible synthetic retrieval evaluation; documented unverified Docker, PostgreSQL, learned-model, and deployment work.

For experienced roles, emphasize the design tradeoffs, threat model, consistency model and measured evidence you actually reviewed. For junior roles, explain one component you independently implement and debug. Do not add leadership, production scale, cost savings or accuracy improvements without evidence.

## 30-second pitch

ReleaseLens tracks the software version behind a technical answer and records the exact documentation passages that support it. When those passages change, it identifies affected saved answers and creates an auditable review instead of silently overwriting history. The current verified implementation demonstrates the workflow with deterministic extraction and synthetic change facts; learned-model evaluation and hosted deployment remain follow-up engineering work.

## 60-second pitch

Developers can receive plausible advice from documentation for the wrong release. ReleaseLens puts project, release and permissions into retrieval itself, validates that citations exist, and saves passage dependencies with each answer. Its differentiator is the update lifecycle: immutable source revisions, relevant change detection, pending-answer identification, conservative revalidation and a preserved correction trail. The local implementation includes four pinned Pydantic/SQLAlchemy source snapshots, a working API-connected interface, automated regression/security tests and reproducible synthetic evaluations. I would be explicit that exact extraction is not proof of semantic correctness, that natural-language changes may need human review, and that production hosting and learned-model benchmark claims still require verification.

No live recording, fallback slide deck, human code interview result, or external review has been fabricated. This guide and actual test/evaluation artifacts are available if the service is unavailable; capture a recording or slide deck after browser execution is verified.
