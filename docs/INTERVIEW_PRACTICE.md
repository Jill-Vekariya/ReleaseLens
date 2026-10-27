# ReleaseLens — interview practice

## Five-sentence technical summary

ReleaseLens retrieves documentation evidence within an exact project, release and permission scope. It keeps immutable revisions, exact extracts and the passages used by saved answers. When sources change, it queues affected answers for review while preserving the original. The engineering purpose is to make documentation-dependent answers traceable and reviewable. Its synthetic change rules and recorded retrieval experiments do not establish general semantic correctness or independently reviewed accuracy.

This explains the project’s engineering purpose. Describe your own motivation and role using actual experience; this document does not invent either.

## Ten questions and simple answers

1. **Why filter the release before ranking?** A highly relevant passage from another release may be wrong for the request. Filtering scope before candidate selection prevents cross-release evidence from competing.

2. **Why filter permissions before top-k?** Selecting first and filtering afterward can lose allowed results and leak identifiers. Candidate selection must operate within the authorized scope.

3. **What does an exact citation prove?** It proves the quoted text belongs to an eligible stored passage and revision. It does not prove relevance, completeness or truth.

4. **What is the default encoder?** A deterministic hash-based vector test double. It is not a trained semantic model; pretrained retrieval is optional and evaluated separately.

5. **Why keep immutable revisions?** A later source update must not silently alter the evidence behind an old answer. Immutable records let a reviewer see what was actually used.

6. **Does every document edit invalidate every answer?** No. Passage-level dependencies distinguish a cited change from an unrelated section edit, reducing unnecessary review.

7. **What happens when new conflicting evidence appears?** The bounded public counterevidence rules can queue manual review. A disagreement does not automatically establish that the original answer is false.

8. **Why preserve the old answer after correction?** It provides an audit trail. The correction is a separate record, so history is not rewritten.

9. **Can several writers run independently?** The supported consistency contract uses one serialized API process. Independent ingestion or multiple workers need additional coordination that is not a completed guarantee.

10. **What evaluation is still missing?** Independent human semantic labels and a reviewed successor benchmark. AI-proposed relevance matches and exact extract membership are not independent answer accuracy.

## Study before an interview

- Trace ingestion, logical passages, revision heads and answer dependencies.
- Explain project/release/ACL filtering and transaction completion before success.
- Compare BM25, hash vectors, dense retrieval and cross-encoder reranking.
- Distinguish confirmed synthetic staleness from manual-review candidates.
- Study the failed answerability transfer, data-family splits and owner exercise.

See [current status](CURRENT_STATUS.md) and the existing project-specific interview and ownership material. These answers are practice aids, not completed personal contributions.
