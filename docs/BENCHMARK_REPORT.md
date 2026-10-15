# Retrieval pilot and error analysis

Measured 2026-10-15 on the owner's Windows 11 computer, Python 3.12.10, 12 logical CPUs. AI-authored questions and AI-reviewed proposed labels; **zero human-reviewed records**. These are tuning diagnostics, not independent accuracy or generalization evidence.

## Scope and protocol

Pilot v2 SHA-256: `7845da6dc157666d48805e854066bc128a57c8aba93656cbe4120ec117ac968b`. Four licensed selected pages produce 208 fixed passages. Forty records contain 32 retrieval questions and eight synthetic scenarios. The executed tuning split has 16 supported, six unsupported and eight scenario records. Ten whole-family heldout questions were not run or used for tuning. No release holdout is claimed. V1 bytes remain preserved; v2 changes the fixed contradiction scenario's expected behavior, with retrieval questions/labels unchanged.

All modes use the same questions, k=4, SQL/application project/release/ACL scope, chunking and RRF depth20/constant60. SQLite BM25 and exact normalized dot-product vectors are measured; this is **not PostgreSQL FTS quality evaluation**. One warmup per component, rotating mode order, one measured pass. Raw per-query results, code hashes, family-bootstrap intervals and paired differences are in `evaluation/pilot-*-tuning.json`.

## Quality observations

| Encoder | Retrieval | Passage Recall@4 | MRR@4 |
| --- | --- | ---: | ---: |
| Deterministic hash test double | Lexical | 0.9375 (15/16) | 0.7865 |
| Deterministic hash test double | Dense | 0.8125 (13/16) | 0.6510 |
| Deterministic hash test double | Hybrid | 0.9375 (15/16) | 0.7552 |
| Pinned learned MiniLM | Lexical | 0.9375 (15/16) | 0.7865 |
| Pinned learned MiniLM | Dense | 0.9375 (15/16) | 0.7708 |
| Pinned learned MiniLM | Hybrid | 1.0000 (16/16) | 0.8073 |

No wrong-release or unauthorized hits were observed in these scoped queries; scenario tests probe real synthetic ACL/quarantine boundaries separately. That does not establish zero leak probability. All eight synthetic behavior scenarios passed; these are policy-contract checks, not real-document impact precision/recall.

Learned hybrid minus lexical Recall@4 is +0.0625, with descriptive paired family-bootstrap 95% interval [0, 0.158]. MRR delta +0.0208 has interval about [-0.069, 0.135]. Few families and AI proposals limit interpretation; no statistically established improvement is claimed. The lexical row is identical regardless of encoder because it performs no model inference. Retain the learned model as **opt-in**, keep the deterministic baseline, and do not add a learned reranker yet. Sixteen supported queries do not justify its operational complexity or model-selection claims.

## Actual failures and complementary retrieval

- `pilot-001`, Pydantic 1 model-wide configuration: lexical top four miss the proposed block0000; learned hybrid includes it at rank3. This is one useful example, not proof of broad semantic superiority.
- `pilot-008`, Pydantic 1 `validate_all`: learned dense misses the relevant proposed block0000; lexical finds it at rank2 and hybrid at rank4. Learned retrieval can regress a literal option lookup.
- Pydantic 2 configuration `pilot-002`: lexical ranks the proposed block at2, hybrid at3. Perfect Recall@4 can conceal a worse ordering.
- Every unsupported tuning question returns some evidence because it deliberately shares vocabulary. Default extract probes observed **0/6 abstentions** for these AI-proposed unsupported cases, for both encoder runs. This is a concrete answerability failure, not a success metric. Exact-membership success must never be counted as correct semantic support or appropriate abstention.

The fixed update-lifecycle failure is separate: dependency-only invalidation missed a newly added contradictory source. The bounded public synthetic fact stage now queues a potential effect and records manual review, without deciding competing truth or overwriting the answer. General prose contradictions remain outside the detector.

## Latency, resources and cost

Read `evaluation/retrieval-resources.json` for the exact pinned CPU run and memory/cache observations, and each pilot's p50/p95 for ranking. CPU model loading, indexing and warm ranking are separate costs. The final learned run measured ranking p50/p95 of 43.05/99.75ms lexical, 95.80/159.63ms dense and 103.06/173.07ms hybrid. These single-pass timings have OS/cache/load noise and do not establish a causal speedup/slowdown bound. Raw hash timing is retained separately; no latency is inferred from quality scores.

Whole-process peak was 643,342,336 bytes (about614MiB), including Python, model and both indexes; cache91,618,258 bytes. Resource JSON records model token limit256, snapshot file hashes and a zero repeated-vector difference on the fixed probe. Model load including cache/metadata checks took38.73 seconds. MiniLM truncates beyond its configured token budget; paragraph packing is character-based, so truncated context is a remaining retrieval risk. CPU, electricity, network and hosting were not metered in dollars. No paid provider API was called; provider cost is zero for exact local extraction.

The separate live hash/SQLite HTTP smoke sent 100 requests at concurrency8: zero failures/wrong-release responses, about17.2 requests/s, p50 443ms and p95 517ms on that run. This measures the serialized loopback prototype, not capacity or an SLA. See `load-verification.json`.

## Reproduce learned indexing and comparisons

From the repository with Python3.12 on Windows, install the captured environment (separate from project editable install):

```powershell
.venv\Scripts\python.exe -m pip install torch==2.14.1+cpu --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python.exe -m pip install -r requirements-ml-windows.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
$env:HF_HOME="$PWD\.model-cache"
$env:EMBEDDING_MODEL='sentence-transformers/all-MiniLM-L6-v2'
$env:EMBEDDING_REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
$env:HF_HUB_DISABLE_TELEMETRY='1'
.venv\Scripts\python.exe scripts\verify_semantic.py
.venv\Scripts\python.exe scripts\run_pilots.py
```

Model license Apache-2.0. `trust_remote_code=False`, CPU, normalized384 dimensions, pinned model commit. The Windows environment lock is not a Linux platform lock or wheel-hash supply-chain guarantee. Re-run verification after platform changes. Model switching requires a fresh corpus database or an explicit verified reindex; mixed model identities are rejected. Experiments use in-memory databases and do not replace the deployed hash corpus.

## Unmeasured and next review

Natural-language answer support, appropriate abstention precision/recall, human relevance, real change-impact precision/recall, heldout generalization, learned PostgreSQL retrieval quality and production load remain unmeasured. The answer-probe output records default behavior against AI-proposed unsupported labels without relabeling it human accuracy. Follow PILOT_ANNOTATION.md for independent source review, ambiguity/adjudication and a new frozen version. Calibrate answerability only on reviewed tuning data, then freeze settings before any heldout run. Expand source coverage/review capacity before approaching300–500 questions.
