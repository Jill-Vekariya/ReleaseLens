# Evidence sufficiency review

Exact quotation and citation provenance do not establish that an extract answers
every part of a question. The offline Stage 4 packet records both dimensions
without turning unreviewed labels into a serving policy.

```bash
python -m scripts.evaluate_sufficiency --output evaluation/local/stage4-001
python -m pytest tests/test_sufficiency.py -q
```

Six predefined, AI-authored, development-exposed synthetic cases cover direct
support, an absent latency measurement, partial question coverage, a function
available in another release, restricted evidence and an unrelated question.
All extracts must still pass the existing authorization, release and immutable
citation validation. The packet includes only the requesting reader's evidence.
It does not export the restricted source.

The mechanical probe returned valid citations in all six cases. It answered the
direct, missing-measurement, partial and wrong-release questions, and abstained on
the access-boundary and unrelated questions. These observations are retained;
they are not independently reviewed semantic-quality labels or benchmark uplift.

Each review must bind the original packet hash, identify a human reviewer and
attest independence. It must assess every required aspect and give exact excerpts
from that authorized packet for support or contradiction. Changed questions,
evidence, answers, missing aspects and foreign passage references are rejected.
Identity/independence remain self-attested; this is not technical identity proof.
Use synthetic reviewer identities only in tests, never as completed human reviews.

Review JSON is an array of objects containing `case_id`, `packet_sha256`,
`reviewer_kind: "human"`, `reviewer`, `independent_of_author: true`, `decision`
(`sufficient`, `partial`, `unsupported`, `conflicting`) and an `aspects` mapping
whose keys exactly match `required_aspects`. Each aspect contains `status`
(`supported`, `missing`, `contradicted`), `rationale`, and `evidence`, a list of
`passage_id` / exact `quote` pairs. Missing aspects can have an empty evidence list.

```bash
python -m scripts.evaluate_sufficiency --packet evaluation/local/stage4-001/review-packet.json --reviews reviews.json --output evaluation/local/stage4-reviewed-001
```

Reusing the original packet matters: regenerating fixture evidence creates new
passage IDs. Summaries count reviewed cases and unreviewed cases separately;
semantic error rates are null when there are no reviewed cases.

**VERIFIED:** local suite 182 passed; lint/format passed.
**BLOCKED:** two PostgreSQL cases skipped without that runtime; zero independent
reviews. No new CI, live provider experiment or production improvement is claimed.
Existing AI-assistance and ownership disclosures are preserved.
