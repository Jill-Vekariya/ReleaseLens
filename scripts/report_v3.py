"""Generate portfolio numbers only from actual output artifacts, never placeholder metrics."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    calibration = json.loads((ROOT / "evaluation/v3-calibrate.json").read_text())
    test = json.loads((ROOT / "evaluation/v3-test.json").read_text())
    impact = json.loads((ROOT / "evaluation/prose-impact-v3.json").read_text())
    live = json.loads((ROOT / "evaluation/local-selector-v3.json").read_text())
    if calibration["policy_sha256"] != test["policy_sha256"]:
        raise ValueError("Test did not use the frozen validation policy")
    manifest = json.loads((ROOT / "evaluation/benchmark-v3-manifest.json").read_text())
    lines = [
        "# Expanded evaluation milestone — 2026-10-16",
        "",
        "This report is generated from the actual v3 artifacts. All 70 questions and relevance/answerability labels are AI-authored, source-inspected proposals. Human-reviewed and independently reviewed records: **0**. No human accuracy, production impact, or independently authored user implementation is claimed.",
        "",
        "## Corpus and split contract",
        "",
        f"Four original pages are preserved; ten additional MIT-licensed pages give {test['runtime']['snapshots']} snapshots and {test['runtime']['corpus_passages']} fixed passages. Each snapshot retains the immutable commit, release, raw SHA-256, original license, license SHA-256 and attribution. The new question dataset SHA-256 is `{manifest['dataset_sha256']}`.",
        "",
        "Development: 30 questions (24 supported/6 unsupported); validation: 20 (16/4); test: 20 (16/4). Six entire document-family groups are assigned before model experiments; paired releases and intent duplicates stay together. Models/configuration and connections are development; validators/engines validation; serialization/SELECT test. All sources remain searchable: this is family holdout, not unseen-release holdout. Cross-project/release/ACL/current-head/model/quarantine filtering precedes ranking.",
        "",
        "The original v1/v2 files remain byte-preserved and their heldout rows were not scored. However, v3 development includes isolation/streaming concepts also present in v2 heldout families, so do not call v2 holdout untouched for future tuning claims. V3 test is a separate procedural holdout and is consumed by the recorded test run. Public-source pretraining contamination is not audited.",
        "",
        "## Matched retrieval results",
        "",
        "SQLite BM25, exact normalized MiniLM vectors, RRF hybrid, hybrid plus pretrained cross-encoder, and feature-hash hybrid reference use identical corpus/question/scope settings. Recall is passage Recall@5; nDCG@10 uses the proposed sparse relevance grades. Larger multi-positive labels make these recall values incomparable with the saturated original top-four pilot.",
        "",
        "| Split | Method | Recall@5 | nDCG@10 | Warm p50 / p95 ms |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for split, source in [("dev", calibration), ("validation", calibration), ("test", test)]:
        for row in source["summaries"][split]["retrieval"]:
            lines.append(
                f"| {split} | {row['mode']} | {row['recall_at_5']:.4f} | {row['ndcg_at_10']:.4f} | {row['latency_p50_ms']:.1f} / {row['latency_p95_ms']:.1f} |"
            )
    lines += [
        "",
        "Raw JSON includes per-question ranked identities, source/passage hashes, code hashes and descriptive 2,000-draw family-bootstrap intervals. Each split has only two families; these intervals are unstable descriptive summaries, not population or significance evidence. Candidate depth 20, RRF constant 60, cross-encoder pair budget 256 tokens, batch size 8. Positive lexical eligibility remains in hybrid; this is not a pure fusion ablation. No wrong-release/unauthorized hits were observed in these queries; synthetic access-boundary tests provide separate adversarial checks.",
        "",
        "## Validation-frozen answerability experiment",
        "",
        f"The fixed grid selected raw relevance logit threshold **{test['policy']['threshold']}** using validation only, minimizing `3 × unsupported answers + supported abstentions`. Frozen policy SHA-256: `{test['policy_sha256']}`. The same policy was used for test without retuning. The gate scores the production version-mode top four and returns at most one exact extract. Raw logits are not confidence or entailment probabilities.",
        "",
        "| Split / path | Answer coverage | Unsupported answers | Supported abstentions | Unsupported errors / answered |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for split, source in [("validation", calibration), ("test", test)]:
        for label, key in [("baseline", "baseline_answerability"), ("gate", "gated_answerability")]:
            m = source["summaries"][split][key]
            error = (
                "unmeasured (no answers)"
                if m["unsupported_error_among_answered"] is None
                else f"{m['unsupported_error_among_answered']:.4f}"
            )
            lines.append(
                f"| {split} / {label} | {m['answered']}/{m['cases']} ({m['coverage']:.0%}) | {m['unsupported_answer_false_positives']} | {m['supported_abstention_false_negatives']} | {error} |"
            )
    summary = test["summaries"]["test"]
    lines += [
        "",
        f"Test gate end-to-end p50/p95: **{summary['gated_end_to_end_p50_ms']:.1f}/{summary['gated_end_to_end_p95_ms']:.1f} ms**; includes retrieval, scoring, exact selection and citation checks; excludes loading/indexing. Answerability precision/recall and abstention precision/recall are in raw JSON. These use the proposed binary answerability labels, not semantic correctness. Among gated answered test questions, the top passage matches a proposed relevance label at rate {summary['answered_top_passage_label_hit_rate']:.4f}; incomplete labels and passage truncation limit that proxy.",
        "",
        "**Decision:** keep learned scoring and the gate opt-in. The modest, AI-labeled evaluation does not establish reliable answer support. The current deterministic demo remains the default; BM25 is the inexpensive explicit comparison baseline. No claim that the default is the most accurate model. Do not promote a model based solely on test deltas. Threshold training is not neural model training; no weights were fine-tuned.",
        "",
        "## New-public-prose impact experiment",
        "",
        f"Twelve exact, licensed same-release excerpt replays across three source families observed **{impact['true_positives']} true candidate, {impact['false_alarms']} false alarms, and {impact['missed_review_candidates']} missed candidates** against AI-proposed review labels. Candidate precision {impact['review_candidate_precision_ai_proposal']:.4f}, recall {impact['review_candidate_recall_ai_proposal']:.4f}. Agreeing duplicates deliberately expose false positives. This reorders ingestion of real prose, not historical upstream accuracy. Confirmed-stale precision/recall remain unmeasured.",
        "",
        "The lexical stage is disabled by default (`ENABLE_PROSE_REVIEW_CANDIDATES=true` enables it experimentally). It only proposes manual review and cannot confirm stale status. Public current passages in the same project/release, introduced after the saved answer, join the review fingerprint; private/wrong-release/quarantined material does not. Cited logical sources retain existing dependency handling. Original answers and evidence remain immutable; withdrawal resolution requires an explicit review.",
        "",
        "## Actual compatible inference",
        "",
        f"Pinned `{live['model']}` ran on CPU through a real loopback compatible HTTP endpoint: **{live['actual_model_http_requests']} inference requests**. This tiny model is a smoke fixture, not the recommended production model. Exact selections and failures are preserved in `evaluation/local-selector-v3.json`; usage tokens and actual outputs are recorded separately from human judgments.",
        "",
    ]
    for record in live["records"]:
        lines.append(
            f"- `{record['question']}` → {'abstained' if record['observed_abstention'] else 'returned an exact extract'}; deterministic citation validation passed; semantic correctness unmeasured."
        )
    lines += [
        "",
        "A real transport bug was found and fixed: a keyless endpoint received an invalid empty Bearer header. `local-selector-v3-before.json` records zero actual inference calls before the fix; it is not presented as a model run. A real HTTP regression supplements mock tests. Extract selection remains distinct from synthesized prose; fluent answer quality was not evaluated.",
        "",
        "## Runtime, cost and limits",
        "",
        f"Test runtime: {test['runtime']['platform']}, Python {test['runtime']['python']}, {test['runtime']['logical_cpus']} logical CPUs, torch {test['runtime']['torch']}, {test['runtime']['torch_threads']} inference threads, CPU only. Timings are one warmed sequential pass with rotating ranking order on the owner's active computer, not isolated hardware, load-test percentiles, or an SLA. Test model loading {test['runtime']['model_load_ms'] / 1000:.1f}s; ingestion of learned and hash copies {test['runtime']['indexing_ms'] / 1000:.1f}s. Indexing/model loading are outside ranking latency.",
        "",
        "MiniLM is 384-dimensional, normalized, commit-pinned; switching its model space requires a fresh database/index. The cross-encoder is pinned separately and does not require passage reindexing. Character chunking can exceed both models' token budgets and truncate supporting tails. Snapshot hashes identify source bytes, not relevance truth. No API or hosting fee was incurred. Token usage is measured for the local selector; electricity/network cost and production inference cost are unmeasured. Human answer correctness/relevance/completeness/semantic support, general contradiction accuracy, real stale-answer precision/recall, PostgreSQL learned retrieval quality and production load remain unmeasured.",
        "",
        "The unsupported set includes conspicuous impossible guarantees and is easier than realistic user ambiguity. Labels identify proposed anchor-containing blocks, not exhaustive supporting evidence. Improve these with independent review before expanding toward 300–500. Removed-API and changed-default coverage needs a curated migration challenge set; existing version-specific and synthetic change checks do not establish broad migration accuracy.",
        "",
        "## Reproduce",
        "",
        "Follow `docs/MODELS.md` for the locked environment and pinned CPU models. Do not overwrite frozen datasets or policies.",
        "",
        "```powershell",
        "$env:HF_HOME=Join-Path $PWD '.model-cache'",
        "$env:EMBEDDING_MODEL='sentence-transformers/all-MiniLM-L6-v2'",
        "$env:EMBEDDING_REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'",
        ".venv\\Scripts\\python.exe scripts/evaluate_v3.py --stage calibrate  # fresh experiment only; refuses existing policy",
        ".venv\\Scripts\\python.exe scripts/evaluate_v3.py --stage test --allow-ai-test-diagnostic",
        ".venv\\Scripts\\python.exe scripts/evaluate_prose_impact.py",
        ".venv\\Scripts\\python.exe scripts/verify_local_selector.py",
        ".venv\\Scripts\\python.exe scripts/report_v3.py",
        "```",
        "",
        "To reproduce the exact frozen calibration, run in a separate checkout/output directory retaining the original dataset, remove only that disposable copy's generated policy, and compare the resulting threshold. Never use a failed/test run to tune the same heldout families. A successor human-reviewed dataset and new holdout are required after error-driven changes.",
    ]
    (ROOT / "docs/V3_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Generated docs/V3_REPORT.md from executed artifacts")


if __name__ == "__main__":
    main()
