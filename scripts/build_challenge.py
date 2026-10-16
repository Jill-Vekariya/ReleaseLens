"""Freeze a small source-grounded migration challenge without changing v3.

Run with python -m scripts.build_challenge [--fetch]. AI proposals, not human gold.
"""

import argparse
import hashlib
import json
from collections import Counter

from releaselens.review_dataset import ROOT, file_hash
from releaselens.sources import chunks
from scripts.fetch_expanded_sources import fetch_page

NEW_PAGES = [
    ("pydantic", "1.10.15", "json-schema", "test", "docs/usage/schema.md"),
    ("pydantic", "2.10.4", "json-schema", "test", "docs/concepts/json_schema.md"),
    ("sqlalchemy", "1.4.54", "sessions", "test", "doc/build/orm/session_basics.rst"),
    ("sqlalchemy", "2.0.36", "sessions", "test", "doc/build/orm/session_basics.rst"),
    ("pydantic", "2.10.4", "migration", "dev", "docs/migration.md"),
]
# Source directory, split, category, question, proposed answer, exact anchor.
SPECS = [
    (
        "pydantic/2.10.4/migration",
        "dev",
        "removed_api",
        "Does native V2 still use GetterDict for ORM parsing, or was that mechanism removed?",
        "GetterDict and orm_mode were removed from the native V2 mechanism; V1 compatibility imports are a separate path.",
        "`GetterDict` has been removed",
    ),
    (
        "pydantic/2.10.4/migration",
        "dev",
        "removed_setting",
        "How should I migrate allow_mutation=False in a V1 Config to V2 configuration?",
        "The allow_mutation setting was removed; use frozen with the inverse boolean meaning.",
        "`allow_mutation` — this has been removed",
    ),
    (
        "pydantic/2.10.4/migration",
        "dev",
        "renamed_setting",
        "Which V2 setting replaces validate_all when deciding whether defaults are validated?",
        "validate_default replaces validate_all.",
        "`validate_all` → `validate_default`",
    ),
    (
        "pydantic/2.10.4/migration",
        "dev",
        "deprecated_api",
        "For JSON input in native V2, is parse_raw removed or deprecated, and what should I use?",
        "parse_raw is deprecated; model_validate_json is the recommended JSON-input path.",
        "`parse_raw` and `parse_file` are now deprecated",
    ),
    (
        "pydantic/2.10.4/migration",
        "dev",
        "removed_api",
        "Do I still need pydantic.generics.GenericModel for a native V2 generic model?",
        "No; the migration page says it was removed. Inherit BaseModel and Generic directly.",
        "class is no longer necessary, and has been removed",
    ),
    (
        "pydantic/2.10.4/migration",
        "dev",
        "changed_behavior",
        "After migrating, should I keep underscore_attrs_are_private=False to retain the old behavior?",
        "That setting was removed; V2 behaves as if the V1 setting were always True.",
        "`underscore_attrs_are_private` — the Pydantic V2 behavior",
    ),
    (
        "pydantic/1.10.15/models",
        "dev",
        "version_specific_api",
        "May I pass untrusted, not-yet-validated input to construct to save validation work?",
        "No; construct performs no validation and is for trusted or already validated data.",
        "`construct()` does not do any validation",
    ),
    (
        "pydantic/2.10.4/models",
        "dev",
        "false_premise",
        "With extra=forbid, will model_construct reject unexpected fields as normal validation does?",
        "No; model_construct ignores extra inputs under forbid rather than raising the normal validation error.",
        "set to `'forbid'` doesn't raise an error",
    ),
    (
        "pydantic/2.10.4/models",
        "dev",
        "hard_negative_missing_measurement",
        "What is the median model_construct duration in milliseconds for our 200-field Order model on our service hardware?",
        None,
        "you may want to profile your use case",
    ),
    (
        "sqlalchemy/1.4.54/engines",
        "dev",
        "false_premise",
        "Does creating a default QueuePool immediately open its full five database connections?",
        "No; the pool opens connections on demand, with a default size of five and overflow ten.",
        "database on an as-needed basis",
    ),
    (
        "sqlalchemy/2.0.36/engines",
        "dev",
        "backend_exception",
        "Should I assume the default QueuePool five-plus-ten rule applies to every SQLite engine?",
        "No; this page explicitly says QueuePool is not used by default for SQLite engines. Do not infer backend policy from the generic paragraph.",
        "is not used by default for SQLite engines",
    ),
    (
        "sqlalchemy/2.0.36/engines",
        "dev",
        "hard_negative_missing_workload",
        "What exact pool_size and max_overflow should I choose for our production workload?",
        None,
        "default size of five",
    ),
    (
        "pydantic/1.10.15/serialization",
        "validation",
        "similar_terminology",
        "Are nested models converted recursively in dict(model), just as they are in model.dict()?",
        "No; dict(model) exposes raw field values, while model.dict recursively converts submodels.",
        "With this approach the raw field values",
    ),
    (
        "pydantic/1.10.15/serialization",
        "validation",
        "hard_negative_missing_input",
        "How many bytes will model.json() produce for the User objects in our production database?",
        None,
        "model.json",
    ),
    (
        "pydantic/2.10.4/serialization",
        "validation",
        "changed_default",
        "After moving to V2, will an added password field on a subclass be included by default when the field is annotated as its parent model?",
        "No; by default only fields of the annotated type are serialized. Duck-typed serialization is a separate opt-in.",
        "only the fields from the _annotated_ type",
    ),
    (
        "pydantic/2.10.4/serialization",
        "validation",
        "hard_negative_missing_input",
        "What exact datetime string will model_dump_json emit for our production records?",
        None,
        "datetime",
    ),
    (
        "pydantic/1.10.15/json-schema",
        "test",
        "version_specific_api",
        "Which model schema method returns a dictionary and which returns a JSON string?",
        "BaseModel.schema returns a dictionary; BaseModel.schema_json returns a JSON string.",
        "`BaseModel.schema` will return a dict",
    ),
    (
        "pydantic/1.10.15/json-schema",
        "test",
        "default_behavior",
        "Does schema generation use aliases as keys by default, and how can I request property names?",
        "Aliases are the default; pass by_alias=False for property names.",
        "schema is generated by default using aliases as keys",
    ),
    (
        "pydantic/2.10.4/json-schema",
        "test",
        "similar_terminology",
        "Does model_dump_json generate a model JSON schema, or should I call model_json_schema?",
        "model_json_schema generates a jsonable schema dictionary; model_dump_json serializes an instance to a JSON string.",
        "These methods are not to be confused",
    ),
    (
        "pydantic/2.10.4/json-schema",
        "test",
        "version_specific_standard",
        "Which JSON Schema draft does this release say its generated schemas comply with?",
        "JSON Schema Draft 2020-12.",
        "JSON Schema Draft 2020-12",
    ),
]
for version in ("1.4.54", "2.0.36"):
    SPECS.extend(
        [
            (
                f"sqlalchemy/{version}/sessions",
                "test",
                "default_behavior",
                "Why are objects expired after Session.commit, and which option disables that behavior?",
                "Session.commit expires associated objects by default; expire_on_commit can disable expiration.",
                "Session.expire_on_commit",
            ),
            (
                f"sqlalchemy/{version}/sessions",
                "test",
                "concurrency_boundary",
                "Should unrelated concurrent threads share one Session, or keep a Session per thread?",
                "Keep a separate Session per concurrent thread rather than sharing a mutable Session concurrently.",
                "concurrent thread",
            ),
        ]
    )


def family_for(directory):
    project, _, page = directory.split("/")
    return f"{project}:" + ("modeling" if page in ("models",) else page)


def freeze(root=ROOT):
    output = root / "evaluation/migration-challenge-v1.jsonl"
    manifest_path = root / "evaluation/migration-challenge-v1-manifest.json"
    if output.exists() or manifest_path.exists():
        raise ValueError("Challenge already frozen; preserve it and version successor data")
    old = json.loads((root / "evaluation/benchmark-v3-manifest.json").read_text())
    source_paths = [s["manifest"] for s in old["sources"]]
    source_paths += [f"data/upstream/{p}/{v}/{f}/manifest.json" for p, v, f, _, _ in NEW_PAGES]
    splits = {family_for(d): split for d, split, *_ in SPECS}
    sources, blocks_by_dir = [], {}
    for relative in source_paths:
        path = root / relative
        meta = json.loads(path.read_text())
        blocks = chunks((path.parent / "source.txt").read_bytes().decode())
        directory = str(path.parent.relative_to(root / "data/upstream")).replace("\\", "/")
        family = (
            family_for(directory)
            if directory.count("/") == 2
            else (
                "pydantic:modeling" if meta["project"] == "pydantic" else "sqlalchemy:connections"
            )
        )
        source = {
            "manifest": relative,
            "family_id": family,
            "split": splits.get(family, "dev"),
            "passages": len(blocks),
            **{
                k: meta[k]
                for k in ("project", "release", "path", "commit", "raw_sha256", "license_sha256")
            },
        }
        sources.append(source)
        blocks_by_dir[directory] = (relative, source, blocks)
    cases = []
    for index, (directory, split, category, question, answer, anchor) in enumerate(SPECS, 1):
        relative, source, blocks = blocks_by_dir[directory]
        # Sparse proposals: one inspected anchor block, never exhaustive or human labels.
        position = next((i for i, block in enumerate(blocks) if anchor in block), None)
        if position is None:
            raise ValueError(f"Missing proposed anchor: {directory}: {anchor}")
        label = {
            "document_key": source["path"],
            "logical_key": f"{source['path']}#block-{position:04}",
            "grade": 1,
            "anchor": anchor,
            "passage_sha256": hashlib.sha256(blocks[position].encode()).hexdigest(),
        }
        unsupported = answer is None
        cases.append(
            {
                "id": f"mc1-{index:03}",
                "kind": "retrieval",
                "project": source["project"],
                "release": source["release"],
                "family_id": source["family_id"],
                "split": split,
                "dedup_group": f"{source['family_id']}:{category}:{question}",
                "question": f"In {source['project']} {source['release']}, {question[0].lower() + question[1:]}",
                "category": category,
                "role": "reader",
                "source_commit": source["commit"],
                "source_manifest": relative,
                "expected_answer": answer,
                "expected_abstention": unsupported,
                "relevance": [] if unsupported else [label],
                "proposed_hard_negatives": [
                    {
                        **label,
                        "release": source["release"],
                        "rationale": "Lexically related general guidance/example cannot determine deployment-specific measurements, workload choices or missing input values.",
                    }
                ]
                if unsupported
                else [],
                "question_origin": "ai_authored",
                "label_origin": "ai_source_inspected_proposal",
                "review_status": "ai_reviewed_proposal",
                "human_review": None,
                "annotation_completeness": "Sparse source-inspected proposals; independent exhaustive review pending",
            }
        )
    output.write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases),
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "dataset_version": "migration-challenge-v1-ai-proposal-24",
        "dataset": str(output.relative_to(root)).replace("\\", "/"),
        "dataset_sha256": file_hash(output),
        "records": len(cases),
        "splits": dict(Counter(c["split"] for c in cases)),
        "family_splits": splits,
        "human_reviewed_records": 0,
        "independently_reviewed_records": 0,
        "sources": sources,
        "parent_v3_sha256": old["dataset_sha256"],
        "new_holdout_sources": [
            p for p in source_paths if "/json-schema/" in p or "/sessions/" in p
        ],
        "freeze_basis": "Migration/construct/engine families dev; serialization validation; newly added JSON-schema/session families test, before this challenge is scored",
        "prior_exposure": "V3 serialization was already consumed and may serve only as development/validation here; new holdout source files were absent from v3, but semantic/public-pretraining independence is not guaranteed",
        "test_policy": "Not scored by this runner; reserve for independent review and a future preregistered evaluation",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()
    if args.fetch:
        for page in NEW_PAGES:
            fetch_page(page)
    result = freeze()
    print(json.dumps({k: v for k, v in result.items() if k != "sources"}, indent=2))
