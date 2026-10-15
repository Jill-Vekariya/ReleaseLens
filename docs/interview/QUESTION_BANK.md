# ReleaseLens answered interview questions

AI-assisted study material, 2026-10-15. Answers describe the inspected v0.1 source, not independent user expertise. Reproduce the behavior and explain it in your own words. Proposed scale designs are explicitly future work.

## Product and evidence

### 1. What engineering problem does ReleaseLens address?

A saved technical answer can outlive the documentation that supported it. ReleaseLens records immutable supporting passages, detects changes to their logical sections, queues affected answers and preserves a review/correction trail. It also scopes retrieval by project, release and permissions. It does not generally determine whether arbitrary natural-language advice is still correct.

### 2. How is this more than an ordinary retrieval demo?

The central workflow continues after answering: save dependencies → ingest a new revision → determine affected answers → revalidate against current heads → retain the original payload and append review/correction records. This is an implemented lifecycle, not a claim of research novelty.

### 3. Does a valid citation prove an answer is correct?

No. `validate_citations` checks identity, authorization, metadata, exact quotation, project/release, quarantine, claim substring membership and assembly of the final answer. An irrelevant passage can satisfy those checks. Relevance, completeness and semantic support need separate labels and evaluation.

### 4. What is the distinction between immutable and logical passage IDs?

`Passage.id` identifies one immutable snapshot. `logical_key` identifies a section within a revision and connects corresponding sections across a document's revisions. A saved dependency references the physical ID; change/review logic uses the logical key to find current evidence. Renames or structural movement can break that correspondence.

### 5. Why is “latest documentation” the wrong default for a historical answer?

Pydantic 1.10.15 and 2.10.4 have different configuration interfaces. Newer guidance is not automatically correct for the older release. Review follows the latest revision of the same release-specific document, not the newest software version.

## Retrieval and ML

### 6. Is the default dense vector learned semantic retrieval?

No. `HashEmbedder` hashes lowercased tokens into 384 count dimensions and normalizes the vector. It is deterministic and useful as a test double, but token collisions and lack of learned semantics limit it. A `SentenceEmbedder` adapter exists; installation or code existence does not establish model execution or quality.

### 7. Why normalize vectors?

For unit vectors, dot product equals cosine similarity, letting the SQLite path compare angular similarity without document magnitude dominating. Empty-token input remains a zero vector. PostgreSQL uses cosine distance via pgvector; the two paths still need separate execution and ranking checks.

### 8. How does local BM25 differ from counting query matches?

It weights rarer terms more and saturates repeated term frequency while adjusting for passage length. The implementation uses `k1=1.2`, `b=0.75` and tokenized section plus text. Repeating a common term does not increase its score linearly without bound.

### 9. Why reciprocal rank fusion instead of adding dense and lexical scores?

Their score scales are incompatible. RRF adds `1/(60+rank)` from each top-20 list, so a candidate supported by both rankings can rise without calibrating raw scores. It discards score magnitude and still has depth/constant choices that need independent tuning.

### 10. What exactly do vector, hybrid, rerank and version modes mean?

`lexical` uses BM25 locally / FTS on PostgreSQL; `vector` uses dense ranking; `hybrid` and default `version` use RRF with lexical eligibility; `rerank` adds an experimental section-token-overlap heuristic. Every production mode filters exact release, project and ACL before candidates. Only explicit offline contamination experiments opt out of release filtering.

### 11. Why can a semantically relevant passage still be missed after adding a learned encoder?

Hybrid/version modes require positive lexical evidence: BM25 overlap locally, full-text matching in PostgreSQL. A synonym-only learned match can fail that gate. PostgreSQL further limits the lexical candidate set to 20 before fusion. Improving encoder quality alone does not fix that recall bottleneck.

### 12. Are SQLite and PostgreSQL rankings equivalent?

No. SQLite loads the scoped corpus and computes BM25 and dot products in process. PostgreSQL performs exact vector ordering and English full-text ranking with SQL limits; its lexical matching/stemming differs. In SQLite lexical eligibility includes all positive-scoring passages, whereas PostgreSQL eligibility is limited to its lexical candidate rows. Equal RRF constants do not make backend measurements interchangeable.

### 13. What happens if a user asks the model to ignore the selected version?

The request's project/release fields determine the default database predicate. Question text cannot change the principal or scope. Production modes all enforce release. The offline contamination runner can opt out of release filtering for an ablation; `ask` also defensively rejects wrong-release rows.

### 14. What prevents searching embeddings from incompatible models?

Passages store an encoder identity, and retrieval filters it against `embedder.name`. Repeat ingestion with an encoder change is rejected rather than treating the old embedding as current. The learned adapter requires a model plus 40-character commit pin and a 384-dimensional output. A fresh database or explicit reindex migration is required; equal dimensionality alone does not mean compatible vector spaces.

### 15. Is the reranker a trained cross-encoder?

No. It favors section-title token overlap among candidates. It remains an experimental baseline because no independently reviewed experiment establishes benefit. A future cross-encoder would require pinned weights, controlled candidates, held-out relevance labels and latency/cost measurement.

### 16. What does the compatible LLM adapter actually do?

It calls an OpenAI-compatible `/chat/completions` endpoint to select up to four exact extracts and passage IDs. No tools or permission decisions are delegated. Unknown IDs and unsupported text fail deterministic validation and produce abstention. This is not fluent synthesis, and the current verified default invokes no LLM.

## Backend and consistency

### 17. What is atomic during ingestion?

Within the API session transaction, revision/passages, document head, change record and dependent-answer state changes commit together or roll back together. `ingest` flushes rows but does not independently commit. Moving any of those operations to an external queue would require a new atomicity design.

### 18. What does `expected_revision` protect against?

For a non-identical update, the submitted head must match the current head or ingestion returns a revision conflict (409). PostgreSQL locks existing document rows; uniqueness constraints cover identity/sequence conflicts. Identical content and provenance are checked first and can return the existing revision without a new snapshot. This is deliberate idempotence, not permission to overwrite arbitrary stale state.

### 19. Is the async application lock sufficient for several server processes?

No. Each app instance owns its own lock. It currently serializes all session-backed requests within one app, including reads and PostgreSQL requests. PostgreSQL row locks and uniqueness constraints protect some write conflicts, but do not establish a consistent corpus snapshot across ask/ingest/review. Supported operation is one API process with no concurrent independent writer; multiworker requires a snapshot/retry protocol.

### 20. Why not update the old answer when its source changes?

Replacing the payload would erase what the user saw and which evidence justified it. The mutable status signals review state while the original payload/dependencies remain. A confirmed synthetic fact change creates a separate answer and stores its ID in a new audit assessment. The correction can itself abstain, so inspect the linked payload rather than assuming a successful answer from the link alone.

### 21. Why search historical dependencies after a technical update?

An answer may cite revision 1, formatting creates revision 2, and a technical update creates revision 3. Looking only at revision-2 passage IDs misses the original dependency. The implementation finds all historical passage IDs for logical keys changed by the current event, preserving reach across formatting-only revisions.

### 22. Can a formatting event requeue an old confirmed-stale answer?

It previously did when historical differences were treated as changes caused by the current event. The fix first computes changed logical keys from old head to new head, then follows history for those keys only. A formatting event has no changed keys and leaves the previous status intact. A genuinely later technical edit can queue it again for a new review.

### 23. What is revalidation idempotence keyed on?

A SHA-256 fingerprint of sorted cited passage/head pairs, current eligible public counterevidence and the review-policy version, scoped by answer ID. A unique review constraint and the API answer row lock support one review/correction per evidence-head set. An unchanged head returns the same review ID; changing a head produces a new fingerprint even for a formatting snapshot. Authorization is rechecked before exposing history.

### 24. How are multiple review outcomes combined?

Original abstentions stay insufficient or conflict/manual review and cannot be confirmed incorrect. For substantive supported claims, changed full synthetic facts take precedence as confirmed stale, then missing dependencies as insufficient; uncertain text/metadata or public counterevidence requires manual review; otherwise reviewed still valid. Read the assessment reasons when several conditions coexist. `unaffected` means no detected relevant change, not globally correct.

### 25. What kinds of edits are treated as formatting?

Normalization converts CRLF to LF, removes trailing spaces and collapses runs of blank lines. It preserves case and code indentation. The document normalized representation also includes title and synthetic fact metadata, so changing them is not erased. This conservative equivalence is narrower than “all meaning-preserving edits.”

### 26. What is an important change-detection false negative?

A newly added passage can contradict an answer while its cited sections remain unchanged. The implemented bounded stage checks newly introduced public synthetic fact assertions within the same project/release and queues relevant supported saved claims for manual review. It does not declare disagreement confirmed incorrect. Public counterevidence enters the fingerprint; private evidence cannot change public status. Arbitrary prose contradictions still escape this policy.

### 27. Why did PostgreSQL fail when SQLite passed?

The affected-answer query once selected `DISTINCT` full `Answer` rows, including JSON payloads. PostgreSQL JSON has no equality operator for that deduplication. Selecting outer answers by an ID subquery avoids JSON equality and duplicate answer matches. Actual PostgreSQL lifecycle integration now exercises this path; ORM portability still needs backend-specific tests.

### 28. Why did a thread-owned lock fail in a yielding dependency?

FastAPI can enter and exit a synchronous dependency on different worker threads. An `RLock` must be released by its owning thread. The current dependency is async and uses `asyncio.Lock` around the transaction. The 50-request regression checks successful completion and distinct saved IDs, not production throughput or all possible scheduling behaviors.

## Security

### 29. Why enforce ACL before top-k?

Unauthorized passages must not reach candidate scoring, generation or returned identifiers. Filtering only after top-k can also fill the shortlist with forbidden documents and remove authorized recall. Retrieval predicates, direct-evidence access and saved-answer/history access each enforce their own boundary; frontend role controls are insufficient.

### 30. Can an administrator read another user's answers?

No. Answers are owner-private even for administrators. Ingestion can mark another owner's answer pending because its evidence changed, but the returned affected-answer IDs include only the ingestion principal's own answers. History and dependency access require both ownership and current access to the underlying documents.

### 31. Why test same-user role downgrade separately?

An answer may belong to the same user yet contain evidence the user can no longer access. An owner check alone would leak it after downgrade. `owned_answer` rechecks every dependency's document classification; the test uses the same user ID with admin and reader bearer identities and expects inaccessible answer/detail/history/revalidation to be withheld.

### 32. How does demo authentication differ from Docker authentication?

Explicit loopback demo mode trusts a bounded synthetic role header and maps each role to a distinct demo user. Outside demo mode valid bearer credentials are required, and the synthetic header grants nothing. The demo is a teaching sandbox, not an organizational identity provider. Production mode does not seed fixtures automatically.

### 33. Does quarantine solve prompt injection?

No. `injection_marker` recognizes a few patterns and zero-width characters and hides those passages. Obfuscated attacks can evade it. Default extraction has no tools, while the optional selector receives only already authorized evidence and its output is validated. This narrows consequences but does not prove comprehensive resistance or establish relevance.

### 34. Why return 404 for unavailable evidence rather than 403?

The same response covers nonexistent and unauthorized resources, reducing direct ID enumeration signals. It is a local interface choice, not a proof against timing or all side channels. Administrator-only ingestion uses a distinct forbidden-operation response.

### 35. What would a safe result cache need? (Future design)

At least principal/tenant identity, effective permissions and revocation epoch, project/release, source heads, normalized question, retrieval/generator/model configuration and expiry/invalidation policy. Cache hits must honor current permissions. There is no answer-result cache in v0.1, so no cache performance benefit is claimed.

## Evaluation and scale

### 36. What do the existing retrieval metrics establish?

The legacy diagnostic has24 synthetic development questions at document level. The separate frozen source pilot measured16 supported tuning questions (eight topic families), six realistic unsupported probes and eight synthetic scenarios. Passage Recall@4 is15/16 lexical,15/16 learned dense and16/16 learned hybrid; its AI-reviewed labels and small sample do not establish human accuracy or general benefit. Heldout families were not run.

### 37. Why are answer accuracy and abstention precision null?

No independent human entailment/relevance labels exist. Exact membership cannot substitute for them. The newer pilot deliberately tests vocabulary-overlapping unsupported questions: default extraction abstained on0/6 AI-proposed unsupported tuning cases, an observed answerability failure. Abstention precision requires labeled answerable and unanswerable cases and counts of appropriate abstentions across that distribution.

### 38. Why include uncertainty when there are no observed leaks?

Eight restricted-retrieval trials are a very small sample. A Wilson interval leaves a positive upper bound even with zero observed leaks. It quantifies sampling uncertainty for that controlled rate; it does not model unseen attack classes or certify security.

### 39. How would you evaluate a learned encoder or reranker? (Future experiment)

Pin corpus, encoder/model commits, candidate depth, questions and scoring. Build independently reviewed development and held-out family/release splits; deduplicate paraphrases across splits. Compare lexical-only, learned-dense and hybrid, then rerankers on fixed candidates. Use per-query error analysis and paired ranking uncertainty, plus backend-specific latency and resource/cost measurements. Do not tune on held-out failures and keep calling that set held out.

### 40. How would you scale revalidation? (Future design)

Profile actual query plans, locks and queue volume first. A transactional outbox could commit source changes plus event IDs atomically; workers could claim jobs idempotently, retry bounded failures and verify head versions before finalizing reviews. Multiple updates require a supersession policy. This architecture is proposed, not present, and the current global session lock would need careful redesign.

### 41. What changes at ten million passages? (Future design)

Measure exact-scan cost, filter selectivity, lexical index performance and dependency fanout. Compare partitioning and ANN recall under real ACL/release filters, not unfiltered benchmark recall. Scope identity, deletion/retention and reindex migration also matter. v0.1 has exact pgvector search, fixed classifications and no tenant isolation, ANN index or load-tested throughput.

### 42. What is your honest contribution answer today?

“I supplied the project requirements and used AI assistance to create and verify the implementation. Independent implementation, review and annotation are still pending. I am now working through the code and will identify specific changes I implement myself.” Replace the final sentence only with work actually performed. Operating or memorizing the demo does not make all code independently authored.
