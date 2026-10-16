# Resume ReleaseLens

Updated 2026-10-16. This repository checkpoint survives deleting a chat. A future chat may need the repository URL and these instructions; automatic memory is not guaranteed.

## Start here

Resume ReleaseLens from https://github.com/Jill-Vekariya/ReleaseLens. Read docs/RESUME.md, docs/PROGRESS.md and docs/STATUS.md first. Preserve existing work and continue from the recorded stopping point. Use branch milestone/migration-challenge-v1 until its PR has been reviewed and merged; do not assume main already contains this follow-up.

Canonical execution checkout: C:\Users\jillv\source\ReleaseLens\releaselens on the owner's Windows computer. A clean clone is suitable for read-only review/reproduction; it cannot recover future uncommitted owner work. Check actual git status, branch and open PRs before editing. Never reset/clean the canonical worktree or restore over the live database. If the computer is offline, ask to start Desktop Commander Remote; do not claim pending files were pushed.

## Recorded completed work

- Original v3 milestone merged by owner Jill-Vekariya in PR #1 at 2026-10-16T10:02:25Z, main merge 2fa5e189b88219b4cbccb84436e0b1478e49b6ea. The agent did not merge. New challenge branch preserves that merge and the prior branch.
- Public GitHub source at the owner's explicit request, after targeted secret/history review. Readbacks in evaluation/github-publication.json verify main protection with strict unit/postgres/docker checks bound to GitHub Actions, administrator enforcement, pull requests/conversation resolution, no force-push/delete. External approving-review count 0 because it is a sole-owner repository. This is not independent review.
- Actual local app remains loopback 8080 (authenticated Docker/PostgreSQL) and demo 8000. No public application, paid hosting/API or plan upgrade was provisioned. Existing credentials and persistent volumes were preserved.
- Separate migration challenge: five new pinned MIT snapshots, 19 documents/707 passages, 24 AI proposal questions split 12 dev/4 validation/8 reserved, human-reviewed 0. Original v3 remains 70 questions/14 documents/534 passages; original corpus, policy and predictions are byte-preserved. Default ingestion 4 pages, --expanded 14, --challenge 19. Test scoring is refused; reserved source text is indexed, so no unseen-corpus claim.
- Actual Windows CPU five-way comparison, fixed models/threshold, no training or retuning. Dev BM25 Recall@5 .9000 versus hybrid+CE .6000; p95 ranking 181/4781 ms. The frozen gate answered 13/16 and failed both unsupported validation cases. Semantic accuracy remains unmeasured. CHALLENGE_V1.md has the table, failures and commands.
- Linux/Windows each 163 passed/2 PG-only skips plus static checks. Prior exact 7470e5 CI run 38882662799 passed unit/PostgreSQL/Docker/recovery; the new challenge must have its own exact-head checks. Initial ingestion and Windows encoding failures and fixes are retained.

## Verify the handoff before reporting completion

Find the newest PR with head milestone/migration-challenge-v1 and compare its head SHA to the three check runs. Required jobs are unit, postgres and docker. Passing ancestor/local checks do not establish the current head passed. Actual CI result and run link are recorded in the PR description after execution; do not infer execution from the workflow YAML. This checkpoint is written before that push and deliberately makes no claim that future checks already passed.

Useful commands from the canonical repository:

    git status --short
    git branch --show-current
    gh pr list --head milestone/migration-challenge-v1 --state all
    gh pr view <number> --json headRefOid,state,statusCheckRollup,url
    gh run list --branch milestone/migration-challenge-v1

The source workflow includes a hash-only challenge run. Reproduce to a NEW output path using Python 3.12 and the locked environment:

    python -m scripts.evaluate_challenge --split dev validation --output evaluation/my-challenge-hash.json
    python -m scripts.evaluate_challenge --learned --split dev validation --output evaluation/my-challenge-learned.json

The learned command requires the locked optional dependencies and HF_HOME pointing to the existing populated .model-cache. It uses cached pinned models offline, memory-only indexes and no provider calls. Do not overwrite frozen reports/policies or rescore a consumed test for tuning. Do not run ingestion concurrently with the single-process application; use a fresh database or maintenance window.

## Genuine next work, only where needed

1. If the new PR or its checks are unfinished, complete source/provenance review, commit/push and exact-head CI verification. Leave it reviewable; no agent main merge/release is authorized.
2. For independent accuracy claims, have real people complete/adjudicate the blank review packet at docs/review/challenge-dev-blank.jsonl. Export copies with scripts.review_benchmark --dataset challenge; structural validation cannot authenticate reviewers or prove semantic support. Freeze a new reviewed successor before tuning or confirmatory testing. Do not label AI work human review.
3. For personal interview/résumé claims, the owner should reproduce a measured experiment, explain a failed query and perform the unsolved exercise in OWNERSHIP.md. Record only work actually performed and understood. Interview materials and conditional résumé templates are prepared, not proof of independent authorship.
4. Hosted production, larger datasets and supervised training are optional, deferred until genuine account/budget/label need exists. Obtain explicit approval before paid charges. Public source authorization does not authorize exposing demo mode, secrets or the database.

Preserve immutable evidence, same-project/release/access filters before scoring, answer dependencies, original answers and separately linked corrections/history. Keep model predictions separate from confirmed stale outcomes. The weak prose-candidate detector stays disabled by default. No independent semantic accuracy, production users, guaranteed ATS outcome or model training is claimed.
