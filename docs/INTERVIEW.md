# Interview and ownership package

Start with [overview, architecture, setup, five-minute demo and decisions](interview/README.md).

- [42 project-specific questions and accurate answers](interview/QUESTION_BANK.md)
- [Unsolved coding, backend, ML-evaluation and system-design exercises; four-week schedule](interview/PRACTICE.md)
- [Source walkthrough and understanding checklist](interview/WALKTHROUGH.md)
- [Measured benchmark and error analysis](BENCHMARK_REPORT.md)
- [Actual correctness failures and AI final review](FINAL_AI_REVIEW.md)
- [Operational setup, backup, restore and rollback](OPERATIONS.md)
- [Implemented limits and proposed scale architecture](SCALE.md)
- [Contribution record and preserved ownership exercise](OWNERSHIP.md)

These are AI-assisted learning materials, not evidence of independent user authorship or interview outcomes. Résumé claims must describe the work you actually understood, modified and verified. No users, business savings, production traffic or human annotation are invented.

The current [v3 interview update](interview/V3_UPDATE.md) includes the expanded experiment, current measured limits, actual local inference failure and conditional résumé templates. Earlier pilot/test counts remain historical.

## Migration challenge discussion

Read [CHALLENGE_V1.md](CHALLENGE_V1.md) for a useful interview failure case: BM25 beat the pretrained approaches on the small dev diagnostic, while a previously frozen relevance threshold answered two new unsupported validation questions. Explain why relevance scores and exact citations do not prove that missing production input records exist, why a transferred threshold is not recalibration, and why inspecting these failures forbids treating them as a future untouched test. No human correctness score or neural training is claimed. Use [RESUME.md](RESUME.md) for the current branch and handoff.
