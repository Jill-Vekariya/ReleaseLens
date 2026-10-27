# References inside preserved upstream excerpts

Checked 2026-10-23. Pinned upstream pages and the blind review packet quote original documentation. Their bytes, source hashes and provenance must stay intact even when an upstream URL later changes. The following are reader navigation notes, not edits to the quoted corpus or new evaluation labels.

| Quoted reference | Current navigation / observation |
|---|---|
| JSON Schema `/latest/json-schema-core.html` | Original endpoint returned 404. The [Draft 2020-12 core specification](https://json-schema.org/draft/2020-12/json-schema-core) is a verified versioned reference; draft versions are not automatically interchangeable. |
| JSON Schema `/latest/json-schema-validation.html` | Original endpoint returned 404. See the [Draft 2020-12 validation specification](https://json-schema.org/draft/2020-12/json-schema-validation), verified separately. |
| Python command-line fragment `cmdoption-o` | The retrieved page has uppercase `cmdoption-O`: [optimization option](https://docs.python.org/3/using/cmdline.html#cmdoption-O). |

Both HTTP and HTTPS occurrences of the old JSON Schema endpoints are historical references. Quoted URL-joining examples such as a Google `/api` address are examples, not advertised running services. A request to create an upstream GitHub issue may redirect to sign-in without making that upstream project private.
