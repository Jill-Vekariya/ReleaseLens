# Security boundary and observed limits

## Trust model

Inputs: users/questions, untrusted documentation, trusted curator metadata, server-owned token-to-principal mappings. No model receives credentials, selects a role, chooses SQL predicates, or has tool execution capability.

`RELEASELENS_DEMO=true` intentionally permits synthetic role selection only for loopback/test clients. Do not expose this mode through a public reverse proxy. Non-demo mode refuses startup without configured bearer credentials and ignores `X-Demo-Role`. Tokens are random in the Compose setup and never persisted in browser storage. HTTP transport should terminate TLS outside loopback deployment.

| Surface | Enforced boundary |
| --- | --- |
| Retrieval | ACL, current revision, project, selected release before scoring/limits |
| Experimental baselines | ACL still applies; release omission intentional, wrong-release generation rejected |
| Direct passage IDs | Document permission checked; quarantine hidden; unauthorized and absent return 404 |
| Document metadata and diffs | Role classification checked |
| Saved answers/dependencies | Exact owner plus source ACL checked, even for admins |
| Review and history | Same owner/source scope, including after role downgrade |
| Model context | Only already authorized candidates; no credentials or private conversation history |
| Logging | Request ID, route template, status, latency; no token, question, quote or raw URL |
| Cache | No response cache; `Cache-Control: no-store`; role switch clears rendered results |
| Source ingestion | Admin only; parameterized SQL; no arbitrary URL fetching by API; classification immutable |

## Prompt injection

Suspicious instructions and some invisible Unicode markers cause quarantine. This is an illustrative heuristic that can be bypassed by obfuscation, multilingual instructions, or novel patterns. It is **not** proof that the corpus is safe. The default generator executes no instructions. The optional provider has no tools and can select only exact substrings from supplied authorized passages; fabricated IDs/text cause abstention. A malicious passage can still supply false information, bias selection, or be echoed as an extract. Source trust and reviewed relevance remain necessary.

## References reviewed

- [OWASP RAG Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html)
- [OWASP Prompt Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [OWASP LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

These inform the threat model; passing project tests is not an OWASP certification.

## Tests and deployment gaps

Tests exercise direct IDs, role permissions, same-user role downgrade, cross-owner answer/history access, invalid production tokens, unknown body fields, cross-version queries, baseline citation rejection, source quarantine, private canary exclusion, and citation tampering.

Not implemented: OIDC login, expiring/revocable per-user sessions, multi-tenant membership tables, database row-level security, comprehensive rate limits, request quotas, full hostile-file parsers, supply-chain attestation, or penetration testing. Nginx and the ASGI body middleware enforce a 2 MB body limit; ASGI counts actual bytes even without a trustworthy Content-Length. The middleware buffers bounded input, so public concurrency quotas/rate limits remain necessary. Initial bearer tokens are a local engineering authentication mechanism, not a complete identity platform.

No private user documents were used. Internal/restricted examples contain synthetic canaries, not actual secrets.

## V3 experimental model boundaries

The optional relevance scorer receives only already scoped candidates and cannot add passage IDs or choose permissions. Its raw score is metadata, not a permission or stale verdict. The calibration policy is restricted to its measured backend/encoder/request shape. The optional prose stage considers only current public same-project/release evidence introduced after the saved answer; restricted, internal, quarantined and wrong-release evidence is excluded from its shared statuses/fingerprints. Ownership/source ACLs remain mandatory on review/history access. The stage is disabled by default after poor measured replay results.

Local compatible inference omits empty authentication headers and bypasses environment proxies for literal loopback endpoints. No weights, tokens, real databases or backups are committed. The small local model has no tools; malformed JSON, unsupported IDs or nonmember quotes fail closed. A real loopback HTTP test supplements MockTransport; neither two smoke calls nor existing tests prove comprehensive prompt-injection resistance.
