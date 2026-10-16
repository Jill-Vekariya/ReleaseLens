# Model and inference contract

The default encoder is `hash-384-demo-not-semantic`: a deterministic reference, with no learned semantic claim. Default generation returns exact extracts. No neural weights have been trained or fine-tuned in this project.

| Component | Immutable model identity | Input / output | Operational requirement |
| --- | --- | --- | --- |
| Learned bi-encoder | `sentence-transformers/all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Section + passage, or question; 384 normalized dimensions; 256-token model limit | CPU, optional `sentence-transformers`; fresh index/database on model change |
| Relevance scorer | `cross-encoder/ms-marco-MiniLM-L-6-v2@233902d25c440f23af6f7d6e94d2946bac0bee0a` | Question paired with section + passage; raw scalar logit; combined 256-token budget | CPU, batch 8; no vector reindex; already scoped candidates only |
| Compatible selector smoke | `HuggingFaceTB/SmolLM2-135M-Instruct@12fd25f77366fa6b3b4b768ec3050bf629380bac` | Chat-template input; unconstrained text parsed as extract JSON; 192 new-token smoke cap | CPU, local loopback endpoint; weights about 269 MB; not a recommended answer model |

These three pretrained models declare Apache-2.0 in upstream model metadata/cards. Model weights stay in the ignored local cache and are not included in source delivery. Downloaded snapshot file hashes are retained in execution artifacts where measured; model identifiers alone do not attest the entire installed supply chain. `trust_remote_code=False` is used. The local selector explicitly requires safetensors. The source licenses for bundled documentation are retained separately alongside each page.

## Reproduce the CPU environment

Use Python 3.12 and a separate virtual environment. The captured learned environment is Windows-specific; Linux installation must be resolved and verified separately.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install -r requirements-ml-windows.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
$env:HF_HOME=Join-Path $PWD '.model-cache'
$env:HF_HUB_DISABLE_TELEMETRY='1'
$env:EMBEDDING_MODEL='sentence-transformers/all-MiniLM-L6-v2'
$env:EMBEDDING_REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
.venv\Scripts\python.exe scripts/verify_semantic.py
```

Initial execution downloads public weights without a paid inference account. Set `HF_HUB_OFFLINE=1` only after the requested snapshots are cached. There is no provider API charge; network/electricity cost is not metered. Optional model imports stay outside default application startup.

## Indexing and opt-in policies

The schema fixes vectors at 384 dimensions. Passage records include encoder identity, and ranking filters that identity before limits. A changed encoder is not a configuration-only upgrade: use a fresh database, ingest the identical licensed corpus, verify identities/counts and evaluate before switching. The CLI rejects an identical source re-ingestion with a different encoder. Do not silently mix hash and learned vectors. No ANN quality or PostgreSQL/SQLite lexical equivalence is claimed.

The expanded corpus is explicitly opt-in for application ingestion:

```powershell
# Fresh database or a maintenance window; independent writers are unsupported.
.venv\Scripts\python.exe scripts/ingest_sources.py --expanded
```

The v3 answerability policy is experimental, calibrated on AI-proposed validation labels, and **disabled by default**. It is restricted to the measured SQLite backend, the recorded learned encoder, `mode=version`, and `k=4`. Invalid request shapes receive 422. Use a fresh native SQLite demonstration database and the learned encoder before setting:

```powershell
$env:ANSWERABILITY_POLICY='evaluation/answerability-policy-v3.json'
```

It scores the four authorized retrieval results and selects at most one passage above the fixed threshold. It cannot recover a missed candidate or prove semantic support. Model errors fail the request; there is no silent unscored fallback. The compatible generator remains a separate exact-substring selector, not fluent synthesis. A relevance score cannot confirm stale status.

`ENABLE_PROSE_REVIEW_CANDIDATES=true` enables the separate conservative public-prose overlap experiment. Its measured false alarms/misses do not justify a default rollout. The existing public synthetic fact detector remains separate and enabled; general prose always requires review.

Fine-tuning is deferred: 70 AI-proposed examples with zero human labels are not a defensible training set. First adjudicate real hard negatives from permitted releases, create a new family-disjoint training/validation/test version, and compare a small reranker fine-tune with this fixed pretrained scorer. Preserve the original test and avoid training on errors from the consumed v3 test.
