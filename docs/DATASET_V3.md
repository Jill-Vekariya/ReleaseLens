# Expanded dataset and human-review workflow

`evaluation/benchmark-v3-manifest.json` pins 70 question records, 14 source snapshots, source/license hashes, release commits, deterministic chunk counts and six document-family splits. Original pilot v1/v2 files remain unchanged. Every v3 question and label is an AI-authored, source-inspected **proposal**; human and independent review counts are zero.

The raw snapshot is authoritative for provenance. Expected answers are interpretations for review and are never supplied to the encoder, scorer or generator. Proposed positive labels identify blocks containing inspected anchors; they are sparse and can include repeated API mentions rather than exhaustive support. An unanswerable label means unsupported by this selected corpus, not impossible in the software. Include directives, links and external examples remain unresolved. Several negative questions ask conspicuous impossible guarantees, so difficult realistic unsupported queries are still needed.

| Group | Split | Questions | Scope |
| --- | --- | ---: | --- |
| Pydantic configuration + model construction | dev | 20 | Both release families kept together |
| SQLAlchemy connections | dev | 10 | Both releases; overlaps some original pilot heldout concepts |
| Pydantic validators | validation | 10 | Both releases |
| SQLAlchemy engine configuration | validation | 10 | Both releases |
| Pydantic serialization | test | 10 | Both releases |
| SQLAlchemy SELECT tutorial | test | 10 | Both releases |

There are 56 proposed supported and 14 unsupported questions. Test labels are in the repository, so holdout is a procedural boundary, not secret gold data. V3 validation selected the threshold before the explicitly labeled test diagnostic. Once its results influence engineering, v3 test is consumed; use a successor holdout for any further final accuracy claim. Pretraining contamination is unaudited. V2 heldout rows were not scored, but overlapping isolation/streaming topics are now in v3 dev and must no longer be described as pristine for future selection.

`releaselens.review_dataset.load_dataset` verifies source bytes, license bytes, immutable commits, evidence identity/hash/anchor, family assignments, version-variant dedup groups, normalized duplicate questions and cross-split duplicate labeled passages. These mechanical checks do not establish semantic relevance. Whole document-family grouping reduces leakage but does not prove conceptual independence between related library pages.

## Practical independent review

1. Export blank forms without showing the AI-proposed answers or relevance labels:

   ```bash
   python scripts/review_benchmark.py export --split dev --file reviews/dev-review.jsonl
   ```

2. A real reviewer reads the question and **all permitted same-project/release snapshots**. Record answerability, concise expected answer, every supporting document/logical-key pair, source-based support or absence rationale, uncertainty, actual reviewer identity and review date. Inspect alternative passages, conflicting context, missing examples and token truncation. Review technical relevance/completeness separately from exact quote membership.
3. Have another person review ambiguous cases independently. Record disagreements and adjudication; do not silently drop rejected proposals. Verify the person actually performed the review. Script validation cannot authenticate a human.
4. Validate the submitted form:

   ```bash
   python scripts/review_benchmark.py validate --file reviews/dev-review.jsonl
   ```

   This produces `submitted_for_adjudication` and changes no labels. It never upgrades automated review to `human_verified`.
5. Curate a new immutable successor dataset/manifest after adjudication. Preserve original bytes, rejected examples, reviewer metadata, lineage, split boundaries and a fresh holdout. Do not rewrite the v3 freeze or retroactively call the AI diagnostic human accuracy.

The twelve real-prose excerpt replays in `evaluation/prose-impact-v3.json` assess **review candidate** behavior, not actual historical staleness. The original executable synthetic pilot scenarios still cover access restrictions, conflicting curated assertions, formatting, changed values and quarantine; they are not counted in the 70 real-source retrieval-question denominator. Broader changed-default/removed-API migration coverage remains a specific gap. Expand toward 300–500 only after this review process and source coverage support it.

## Mechanical validation hardening

The closeout regression suite reproduced and fixed acceptance of out-of-range/noninteger relevance grades, duplicate evidence, duplicate questions within a release, nonboolean answerability and incorrect split totals. Blank anchors, unknown roles and block-range errors now fail explicitly too. The original 70 rows already satisfy these checks and remain unchanged.

Review submission validation checks actual passage identities across **all** bundled sources for the question's project/release, rejects duplicate/nonexistent/wrong-release pairs, and requires a nonblank reviewer and expected answer for supported cases. A permitted proposal may be rejected or additional evidence selected; matching the AI's proposed label is not required. The `relevant_evidence` format is:

```json
[{"document_key": "docs/usage/model_config.md", "logical_key": "docs/usage/model_config.md#block-0000"}]
```

This validates structure and source scope only. It cannot establish semantic relevance, authenticate the reviewer or create human-reviewed status. Test fixtures use a visibly fictional reviewer and never become submissions or labels. Human/adjudicated successor data and realistic migration/hard-negative coverage remain pending.
