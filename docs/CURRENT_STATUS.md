# Current status

Updated 2026-10-23 for the cleanup review. Main includes the migration challenge and browser-demo changes: the older branch/PR instructions in [the historical handoff](RESUME.md) describe earlier checkpoints. Inspect current branches and checks before resuming work.

## Supported demonstrations

The public Pages edition runs release-scoped lexical retrieval, exact source inspection and synthetic saved-answer/change/revalidation scenarios in browser storage. Roles are teaching controls. The Python teaching sandbox and authenticated FastAPI/PostgreSQL application are separate local deployments, with setup in the root README. No remote authenticated backend is claimed.

## Verify without changing recorded evidence

`python scripts/verify.py` writes a new directory under `evaluation/local/`. `python -m releaselens.evaluate` writes a new dated result there without rewriting the frozen development corpus. An explicit `--output` must name a new file. Historical results are never replaced by these commands. `python scripts/check_links.py` checks Markdown paths/anchors; add `--online` for external reachability.

## Remaining work

Independent semantic labels and owner exercises remain unfinished. Exact extract membership is not proof of relevance or completeness. The hash encoder is a test double; learned retrieval is opt-in. Failed transferred answerability cases and the eight unscored challenge questions remain preserved. Generic prose contradiction detection, multiple API writers/workers, tenancy and ANN scale designs are not implemented guarantees. The current consistency contract is one serialized API process.

The [source-link errata](SOURCE_LINK_ERRATA.md) explains obsolete URLs inside immutable upstream excerpts. Original snapshot bytes, licenses, labels and measured reports remain unchanged. See [ownership](OWNERSHIP.md), [challenge results](CHALLENGE_V1.md) and [impact policy](IMPACT_REVIEW.md).

[Cleanup changes and local verification](CLEANUP_VERIFICATION.md).
