# Current status — 2026-10-16 migration challenge

Authoritative repository: https://github.com/Jill-Vekariya/ReleaseLens. This continuation started from fetched `a703ea7a3b77ec36e7b4d52b7c731cd1807b8213`, preserved its work, and now continues on branch `milestone/migration-challenge-v1`, based on the owner-merged main commit `2fa5e18`. Read [RESUME.md](RESUME.md) first. The historical ZIP is not authoritative. See PROGRESS.md for chronology and V3_REPORT.md for generated measurements.

| Area | Executed result | Practical limit |
| --- | --- | --- |
| Baseline | Fresh Linux 106 passed / 1 PG skip; GitHub CI 38872433267 passed at a703ea7 | Earlier 101-test statements are historical |
| Current local static/regression | Linux and Windows challenge closeout: 163 passed / 2 PG-only skips; Ruff lint/format, JS syntax and compile pass | Regression checks do not establish semantic correctness |
| PostgreSQL and Docker | Rebuilt authenticated Nginx/FastAPI/PostgreSQL app; both PG integration tests and full HTTP workflow pass | Single API process; independent writers unsupported |
| Persistence/recovery | Fresh binary backup, isolated clone restore, clone downgrade/upgrade, live preservation and restart checks pass | No live DB downgrade or restore |
| Browser | Fresh isolated Edge on authenticated Docker app passes; current-source demo verification uses its own temporary DB/port | No personal browser profile; existing demo/data preserved |
| Authorization/evidence | Existing release/project/ACL/current-head/quarantine checks preserved; gate sees scoped candidates only | Fixed local bearer identities; no OIDC/multi-tenant production system |
| Corpus | Frozen v3:14 snapshots/534 passages; explicit challenge:19/707 | Original four remain deployment-ingestion default; corpus profiles are explicit |
| Dataset | 70 AI-proposed real-source questions; dev 30 / validation 20 / test 20 | Human-reviewed 0; six page families; sparse labels and easy negatives |
| Learned retrieval test | Recall@5: BM25 .6250, dense .5104, hybrid .7500, hybrid+CE .6875; nDCG@10 .6035/.5673/.6556/.7206 | 16 supported test questions, AI proposal labels, SQLite only |
| Cost of reranking | Test ranking p50 about 2281 ms vs hybrid 87 ms | Warm sequential CPU observations, no production SLA |
| Answerability | Validation-frozen -4 raw-logit gate: test 16/20 answered, 4/4 proposed unsupported abstained; proposed top-passage label hit 11/16 answered | Semantic error remains unmeasured; gate remains opt-in |
| New public prose | 12 exact-excerpt replays: candidate precision .25, recall .3333; 3 false alarms, 2 misses | Disabled by default; only manual-review candidates; not stale truth labels |
| Actual local inference | Pinned 135M CPU model made 2 real compatible HTTP calls; both invalid output schemas rejected | No accepted model extracts; no fluent answer quality claim |
| Real transport fix | Omit empty Bearer for keyless endpoints; bypass env proxy for loopback; real HTTP regression passes | Remote HTTPS still uses normal proxy configuration |
| Reviews/history | Immutable original, source evidence, dependency history and separate corrections preserved | Confirmed stale remains confined to defensible curated synthetic facts |
| Interview/ownership | New explanation/demo/Q&A and conditional résumé templates supplement existing package | No independent user coding/labels/review invented; personal exercise remains unsolved |
| CI | Prior exact7470e5 passed run38882662799; owner subsequently merged PR #1 | New challenge needs its own PR and exact-head unit/postgres/docker checks; see RESUME.md |

Current execution artifacts: `linux-verification-v3.json`, `verification.json`, `docker-verification.json`, `recovery-verification.json`, `browser-docker-verification.json`, `demo-v3-verification.json`, `v3-calibrate.json`, `v3-test.json`, `prose-impact-v3.json`, and `local-selector-v3*.json` under evaluation/.

## Remaining acceptance and scope

Independent human semantic correctness/relevance/completeness/support, real stale-answer precision/recall, independently adjudicated hard-negative/migration coverage, learned PostgreSQL quality and production load remain unmeasured. No neural training occurred. Models are pretrained integrations; threshold selection is not fine-tuning. V3 test is consumed; original pilot v2 holdout concepts now overlap v3 development and must not be called pristine for future tuning.

Off-device private hosting requires an available account and approved budget; no paid or public infrastructure was provisioned. The supported application remains loopback at http://127.0.0.1:8080 on the owner's computer. Existing credentials and storage are preserved. Learned gating and prose candidates remain opt-in because their evidence does not justify a reliable production-quality claim.


## Uploaded checklist closeout — 2026-10-16

See [TASK_COMPLETION.md](TASK_COMPLETION.md) for the eight-phase acceptance map, source/function references, pass/fail evidence, files changed and ranked remaining work. Fresh Linux closeout verification:149 passed,2 PG-only skips; all lint/format/JS/compile checks passed. Windows verification is retained separately. The new24-case regression suite first reproduced16 failures/2 passes, then passed after fixes;6 further checks validate metrics/provenance/profile scope. Frozen data, model policy and original rankings remain unchanged.

Fixed mechanically invalid/duplicate benchmark labels and review passage identity validation, plus non-finite scores in the older reranker script. Supplemental Precision@5/MRR@10 is computed from saved predictions without rerunning test. A new offline dev-only profile measured candidate Recall@20 .8076, reranking p50/p95 3298.9/4021.2ms, and process peak682.5MiB across30 dev questions/600 scored pairs. The absent offline revision fails explicitly. Current-head CI is on PR #1; never use an ancestor's passing run as its substitute.

The full research/ownership goal remains incomplete:zero human-reviewed labels; semantic answer quality and real stale accuracy unmeasured; realistic hard negatives/migration cases and a reviewed successor holdout pending; personal contribution exercise pending. Hosted deployment needs account/budget approval. Historically, private-repository protection returned403. The later owner-authorized public-source change enabled protection without a paid upgrade; see the latest current-state section below. PR #1 was merged by the owner. No paid provisioning or human annotation was performed on the owner's behalf.


## Necessary-only challenge follow-up — 2026-10-16

[CHALLENGE_V1.md](CHALLENGE_V1.md) records the bounded follow-up. New separate24-case AI proposal challenge covers real migration/default/API distinctions and realistic missing-input/workload/measurement negatives. Splits12 dev/4 validation/8 reserved; the runner rejects test selection. Five pinned MIT snapshots bring only this explicit challenge corpus to19 pages/707 passages. Original v3 data/policy/results and default four-page demo are preserved; `--expanded` explicitly selects14 pages and `--challenge` selects19. Blank review forms are provided, human-reviewed0.

Local Linux:163 passed/2 PG-only skips; static checks pass. Windows evidence and current-head CI are checked separately. Read the challenge report for actual learned diagnostic results. This is transferred frozen-policy testing without retuning, not new independent accuracy or a trained model. Paid protection, hosting, larger benchmarks and fine-tuning are optional for a local portfolio demo; human review remains required before independent accuracy claims, and personal understanding before first-person résumé/interview claims.

## Current measured challenge and publication state

The [challenge report](CHALLENGE_V1.md) contains the actual five-way comparison on12 dev/4 validation questions. Dev BM25 Recall@5 .9000 versus pretrained dense .5000, hybrid .6000, hybrid+CE .6000 and hash-reference .4000. Ranking p95 was 181ms for BM25 and 4781ms for hybrid+CE. These ten supported dev questions and two supported validation questions use sparse AI proposals, human-reviewed 0. All19source snapshots are indexed; eight reserved queries remain unscored and are not an unseen-corpus guarantee.

The transferred frozen gate answered 13/16 and answered both validation negatives; semantic correctness/support and comprehensive answered-question error remain unmeasured. Threshold, models and original v3 results were not changed. The existing opt-in experimental status and default demonstration remain appropriate.

PUBLIC source and protected main are verified in evaluation/github-publication.json. Required strict unit/postgres/docker checks are bound to GitHub Actions, administrators are covered, pull requests/conversation resolution are required, and force-push/delete are disabled. External approval count 0 reflects a sole owner, not independent review. The owner merged PR #1; this follow-up is a separate reviewable branch. The app remains loopback; no paid hosting or public app deployment occurred. [RESUME.md](RESUME.md) gives the current branch, exact-head CI verification procedure and remaining conditional work.
