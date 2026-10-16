# ReleaseLens browser demo

A self-contained, browser-local working demonstration based on the provided ReleaseLens project description. This `gh-pages` branch contains the deployment assets at the repository root. No installation, API key or build step is required.

The application implements exact-project/exact-release BM25 retrieval, citation inspection, side-by-side release evidence, immutable saved answer extracts, synthetic source revisions, dependency review, separate corrections, public structured counterevidence, and simulated role and quarantine filters. Local changes persist through localStorage and can be exported or reset.

Four checksum-verified, pinned documentation snapshots preserve their original text, commit, source/license SHA-256 and MIT licenses. They yield 208 passages with the original project's deterministic paragraph packing. The source and attribution are included in `data.json` and `licenses/`.

The browser role switcher is a teaching control, not authentication. No real secrets are bundled. This site does not run or connect to the original Python/FastAPI/PostgreSQL application. BM25 here is a JavaScript implementation; neural retrieval and generation are not enabled. Displayed evaluation results are preserved recorded experiments over separate corpora, not benchmarks run by this site. All relevance labels in those records remain AI proposals with no independent human review.

Run `npm test` for meaningful retrieval, immutable evidence, revalidation, role-filter and scenario checks. `npm run check` validates JavaScript syntax. Browser visual QA was unavailable in the managed environment; no browser test result is claimed.

The original ReleaseLens and upstream licenses are retained in `licenses/`.

## GitHub Pages deployment

GitHub Pages serves the root of this `gh-pages` branch. The main branch contains the original Python/FastAPI project. Updating this branch republishes the browser demonstration. All fetch, script, stylesheet and license URLs are relative, including when hosted below `/ReleaseLens/`. The original backend remains a separate application.
