# ReleaseLens browser demo

[Open the live GitHub Pages demo](https://jill-vekariya.github.io/ReleaseLens/).

This folder contains the complete standalone browser demo: exact-release BM25 search over four pinned documentation snapshots, citation inspection, release comparison, immutable saved evidence, synthetic source updates, revalidation, separate corrections, and review history. All interactions run locally in the browser; changes persist in browser storage. No API key or build step is required.

Roles are teaching controls, not authentication. No real secrets are bundled. This demo does not run or connect to the Python/FastAPI/PostgreSQL backend, load neural models, or call a generation provider. Recorded evaluation tables use separate preserved experiments and AI-proposed relevance labels; independent human review remains outstanding.

## Run and verify

From this folder, run `python -m http.server 8001 --bind 127.0.0.1` and open http://127.0.0.1:8001. Run `node --test tests/engine.test.mjs`, `node --check app.js`, and `node --check engine.js` to verify the browser logic and syntax.

The four pinned snapshots preserve 208 original passages, upstream commit URLs, raw-source and license SHA-256 values, original MIT licenses and attribution. The sixteen automated checks cover release and role scoping, citation membership, quarantined fixtures, immutable answers, formatting and uncited changes, stale-answer review, idempotency, structured counterevidence, and provenance hashes. Browser visual QA was unavailable; live deployment verification checked the page and eleven assets byte-for-byte.

## Deployment source

GitHub Pages currently publishes the root of the separate [gh-pages branch](https://github.com/Jill-Vekariya/ReleaseLens/tree/gh-pages). This folder is the same runnable source arranged inside the main project for inspection and testing. To update the deployment, review and sync these files into the root of `gh-pages`, then push that branch. Do not replace the Python project on main with these static assets. All asset URLs are relative and work beneath `/ReleaseLens/`.
