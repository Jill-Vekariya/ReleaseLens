# ReleaseLens durable progress record

Updated 2026-10-15. This file records actual work and pending acceptance, not a production-readiness claim.

## Authoritative work

- Canonical repository: https://github.com/Jill-Vekariya/ReleaseLens (private).
- Canonical execution checkout: `C:\Users\jillv\source\ReleaseLens\releaselens` on the user's authorized Windows computer.
- Local development mirror: `/workspace/scratch/358c61ba2ebc/releaselens`.
- Original `ReleaseLens_v0.1_Source.zip` SHA-256: `0d91544c796c99c4236ee617b9e58fad6aa43c4f20b48e9f2ff69e91c1c54b0e`. This is a preserved historical baseline, not the latest code.
- Latest verified remote commit at the start of the expanded audit: `da89ef2452651b81cbd6649ebb024ae9f2367243`. Uncommitted learned-model/verification work is preserved and will be committed after checks.

## Executed evidence

- Original Linux baseline: 44 passed, one PostgreSQL test skipped.
- Current extended Linux suite before expanded audit: 46 passed, one PostgreSQL test skipped locally; no suppressed failures.
- Windows Python 3.12.10 installation and isolated `.venv` completed.
- Actual Docker Desktop Linux engine started. PostgreSQL/pgvector, FastAPI and Nginx built and started successfully.
- Real authenticated HTTP/PostgreSQL source ingestion, ACL/citation checks, document update, impact queue, correction, idempotency and formatting scenario passed.
- PostgreSQL integration test executed and passed separately, resolving the original runtime skip.
- Installed Microsoft Edge 155 browser exercised Ask, evidence, comparison, roles, source change/revalidation, evaluation and 390px viewport with no JavaScript errors.
- Private GitHub repository created and pushed. CI run `38725181855` succeeded for unit, PostgreSQL and Docker jobs at commit `da89ef2`.
- Native loopback demo runs on port 8000; authenticated Compose application on port 8080. No public hosting service or charges have been created.

## Actual failures corrected

1. PostgreSQL cannot apply `DISTINCT` over a row containing a JSON column. Impact lookup now selects affected answer IDs in a subquery; PG regression exercises the complete update/review path.
2. A thread-owned `RLock` in a sync FastAPI generator dependency could enter and exit on different workers. Transaction serialization now uses an async dependency and `asyncio.Lock`; 50 concurrent requests are tested.
3. A formatting-only change could requeue already reviewed stale answers through broad historical comparisons. Historical dependencies now follow the logical sections actually changed by the current event.
4. Git line-ending conversion could alter hash-pinned snapshot bytes. `.gitattributes` preserves upstream bytes and uses LF for project text.

## Active plan and acceptance

1. Audit correctness and claims; read all six required documents. **Read completed; claims update in progress.**
2. Add bounded newly introduced contradiction detection without disclosing private source existence. **Astra specialist design/implementation in progress.** Acceptance: new public synthetic counterevidence queues same-release relevant answers, never labels disagreement confirmed incorrect, and changes review fingerprints; private/wrong-release/quarantined sources do not affect reader-visible outcomes.
3. Make every production retrieval mode enforce project/release/permissions before candidate limits. **In progress.** Legacy version-contamination ablations remain explicitly offline.
4. Execute pinned CPU learned retrieval and a frozen small evaluation pilot. **Dependency installation in progress.** Model: `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions, Apache-2.0. No success or accuracy claim until executed.
5. Test persistence/restart/backup restoration, migrations, real HTTP failures, concurrent updates and browser errors/loading. **Partly verified; remaining checks planned.**
6. Deliver operations and interview materials, source archive, repository links and evidence. **Sol specialists working on pilot and interview package.**

## Assistance and ownership

The user supplied the specification, model preferences, computer/GitHub/Docker authorization and the expanded requirements. Implementation and current test/review documents are AI-assisted. No independent user coding or human label review has been recorded.

Specialist models launched for this milestone: GPT-6.1 Sol with High reasoning for pilot/interview work; GPT-6 Astra with Extra High reasoning for impact design/review. Completion of a launched review is recorded only after its findings are received and assessed. The active root session's model has not been switched.

## Remaining external decisions

No paid or public hosting is authorized. A persistent off-device private deployment requires an available hosting account and an explicit cost decision before provisioning. Human benchmark review and independent implementation understanding remain genuine user work; synthetic or AI-reviewed labels cannot substitute for them.

## Expanded milestone completed — 2026-10-15

Supersedes the earlier in-progress status above. Current local suite:101 passed +1 PG-only skip, lint/format/JS/compile passed. Actual Docker/PG integration and authenticated HTTP passed, including public synthetic counterevidence and all production retrieval modes. Binary backup/restore into a random clone, schema downgrade/upgrade only in that clone, live-data preservation and backend restart persistence passed. Edge main workflow/mobile, delayed admin identity races and real bearer-authenticated Docker UI passed with zero observed JS errors.100-request concurrency-eight local smoke passed with no HTTP/wrong-release failures (not a capacity claim).

The pinned CPU MiniLM model ran successfully using sentence-transformers6.1.0 and torch2.14.1+cpu. The frozen40-record pilot-v2 preserves v1 and changes only the previously buggy new-contradiction scenario outcome. Tuning:16 supported retrieval,6 unsupported,8 synthetic scenarios;10 heldout topic-family questions untouched; human-reviewed0. Lexical15/16, learned dense15/16 and learned hybrid16/16 Recall@4. AI-label intervals do not establish independent improvement. Default extraction abstained on0/6 realistic unsupported questions: documented actual answerability failure, not hidden behind citation validity. The learned encoder stays opt-in; learned reranking/fluent generation deferred.

Final Astra Extra High AI review reproduced three additional defects: output whitespace broke exact extracts; blank facts bypassed upstream restrictions; commit failures could follow HTTP200. All fixed with regressions and independently rechecked. Review found no remaining high-severity blocker within serialized API operation; independent CLI writers/multiple workers remain unsupported. Sol High UI, pilot, interview and operations specialists completed their assigned work. The root model was not switched.

Dependency scanning found two setuptools advisories in the captured78.1.0 environment and an older build pin. Both are updated to83.0.0, scanned again and build-tested. CPU torch's local-version binary is not covered by PyPI vulnerability lookup; that gap is retained. No secrets, databases, backups or model weights are included in source delivery. Local credentials and existing data remain on the owner's computer.

Interview/operations package is complete; ownership exercise remains unsolved. Final repository commits and CI execution are traceable in GitHub. Off-device private deployment requires account/budget setup; no public or paid infrastructure was provisioned.
