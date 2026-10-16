# Current status — 2026-10-16 v3 continuation

Authoritative repository: https://github.com/Jill-Vekariya/ReleaseLens. This continuation started from fetched `a703ea7a3b77ec36e7b4d52b7c731cd1807b8213`, preserved its work, and uses branch `milestone/evaluation-v3`. The historical ZIP is not authoritative. See PROGRESS.md for chronology and V3_REPORT.md for generated measurements.

| Area | Executed result | Practical limit |
| --- | --- | --- |
| Baseline | Fresh Linux 106 passed / 1 PG skip; GitHub CI 38872433267 passed at a703ea7 | Earlier 101-test statements are historical |
| Current local static/regression | Linux and Windows closeout: 149 passed / 2 PG-only skips; Ruff lint/format, JS syntax and compile pass | Regression checks do not establish semantic correctness |
| PostgreSQL and Docker | Rebuilt authenticated Nginx/FastAPI/PostgreSQL app; both PG integration tests and full HTTP workflow pass | Single API process; independent writers unsupported |
| Persistence/recovery | Fresh binary backup, isolated clone restore, clone downgrade/upgrade, live preservation and restart checks pass | No live DB downgrade or restore |
| Browser | Fresh isolated Edge on authenticated Docker app passes; current-source demo verification uses its own temporary DB/port | No personal browser profile; existing demo/data preserved |
| Authorization/evidence | Existing release/project/ACL/current-head/quarantine checks preserved; gate sees scoped candidates only | Fixed local bearer identities; no OIDC/multi-tenant production system |
| Corpus | 14 pinned MIT-licensed snapshots, 534 deterministic passages | Original four remain deployment-ingestion default; extra pages opt-in |
| Dataset | 70 AI-proposed real-source questions; dev 30 / validation 20 / test 20 | Human-reviewed 0; six page families; sparse labels and easy negatives |
| Learned retrieval test | Recall@5: BM25 .6250, dense .5104, hybrid .7500, hybrid+CE .6875; nDCG@10 .6035/.5673/.6556/.7206 | 16 supported test questions, AI proposal labels, SQLite only |
| Cost of reranking | Test ranking p50 about 2281 ms vs hybrid 87 ms | Warm sequential CPU observations, no production SLA |
| Answerability | Validation-frozen -4 raw-logit gate: test 16/20 answered, 4/4 proposed unsupported abstained; proposed top-passage label hit 11/16 answered | Semantic error remains unmeasured; gate remains opt-in |
| New public prose | 12 exact-excerpt replays: candidate precision .25, recall .3333; 3 false alarms, 2 misses | Disabled by default; only manual-review candidates; not stale truth labels |
| Actual local inference | Pinned 135M CPU model made 2 real compatible HTTP calls; both invalid output schemas rejected | No accepted model extracts; no fluent answer quality claim |
| Real transport fix | Omit empty Bearer for keyless endpoints; bypass env proxy for loopback; real HTTP regression passes | Remote HTTPS still uses normal proxy configuration |
| Reviews/history | Immutable original, source evidence, dependency history and separate corrections preserved | Confirmed stale remains confined to defensible curated synthetic facts |
| Interview/ownership | New explanation/demo/Q&A and conditional résumé templates supplement existing package | No independent user coding/labels/review invented; personal exercise remains unsolved |
| CI | Code fc856cb passed run38878092006; PR #1 head verification restored by the GitHub workflow correction | Check current-head unit, PostgreSQL and Docker results on PR #1; do not rely on an ancestor run |

Current execution artifacts: `linux-verification-v3.json`, `verification.json`, `docker-verification.json`, `recovery-verification.json`, `browser-docker-verification.json`, `demo-v3-verification.json`, `v3-calibrate.json`, `v3-test.json`, `prose-impact-v3.json`, and `local-selector-v3*.json` under evaluation/.

## Remaining acceptance and scope

Independent human semantic correctness/relevance/completeness/support, real stale-answer precision/recall, realistic hard-negative coverage, broader changed-default/removed-API migration cases, learned PostgreSQL quality and production load remain unmeasured. No neural training occurred. Models are pretrained integrations; threshold selection is not fine-tuning. V3 test is consumed; original pilot v2 holdout concepts now overlap v3 development and must not be called pristine for future tuning.

Off-device private hosting requires an available account and approved budget; no paid or public infrastructure was provisioned. The supported application remains loopback at http://127.0.0.1:8080 on the owner's computer. Existing credentials and storage are preserved. Learned gating and prose candidates remain opt-in because their evidence does not justify a reliable production-quality claim.


## Uploaded checklist closeout — 2026-10-16

See [TASK_COMPLETION.md](TASK_COMPLETION.md) for the eight-phase acceptance map, source/function references, pass/fail evidence, files changed and ranked remaining work. Fresh Linux closeout verification:149 passed,2 PG-only skips; all lint/format/JS/compile checks passed. Windows verification is retained separately. The new24-case regression suite first reproduced16 failures/2 passes, then passed after fixes;6 further checks validate metrics/provenance/profile scope. Frozen data, model policy and original rankings remain unchanged.

Fixed mechanically invalid/duplicate benchmark labels and review passage identity validation, plus non-finite scores in the older reranker script. Supplemental Precision@5/MRR@10 is computed from saved predictions without rerunning test. A new offline dev-only profile measured candidate Recall@20 .8076, reranking p50/p95 3298.9/4021.2ms, and process peak682.5MiB across30 dev questions/600 scored pairs. The absent offline revision fails explicitly. Current-head CI is on PR #1; never use an ancestor's passing run as its substitute.

The full research/ownership goal remains incomplete:zero human-reviewed labels; semantic answer quality and real stale accuracy unmeasured; realistic hard negatives/migration cases and a reviewed successor holdout pending; personal contribution exercise pending. Hosted deployment needs account/budget approval. GitHub private-branch protection is blocked by the current plan (403); repository remains private. No merge, publication, visibility change, paid provisioning or human work performed on the owner's behalf.
