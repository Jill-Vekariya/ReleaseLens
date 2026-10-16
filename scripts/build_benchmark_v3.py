"""Freeze the source-inspected AI proposal set; never modifies earlier pilots.

This is curation bookkeeping, not a model-generated mass paraphrase pipeline.
Expected answers are reviewer aids, never retrieval inputs. Run once before tuning.
"""

import json
from collections import Counter
from pathlib import Path

from releaselens.benchmark import sha256
from releaselens.sources import chunks

ROOT = Path(__file__).resolve().parents[1]

# (question, proposed answer, exact anchor). Related releases share a page family.
ITEMS = {
    "pydantic/1.10.15": [
        (
            "Where is model-wide configuration declared?",
            "In an inner Config class.",
            "`Config` class on a model",
        ),
        (
            "What does validate_all control by default?",
            "Validation of field defaults; False by default.",
            "validate_all",
        ),
        (
            "How are unexpected extra attributes handled by default?",
            "The extra option defaults to ignore.",
            "default: `Extra.ignore`",
        ),
        (
            "Which setting enables assignment-time validation?",
            "validate_assignment; False by default.",
            "validate_assignment",
        ),
    ],
    "pydantic/2.10.4": [
        (
            "Where is model-wide configuration declared?",
            "In the model_config class attribute.",
            "Behaviour of Pydantic can be controlled",
        ),
        (
            "Can configuration be passed as model class keyword arguments?",
            "Yes; the page demonstrates class keyword arguments.",
            "class Model(BaseModel, extra='forbid')",
        ),
        (
            "How can a shared parent provide configuration to child models?",
            "Inherit from a custom BaseModel with model_config.",
            "class Parent(BaseModel)",
        ),
        (
            "How does child model configuration interact with parent configuration?",
            "The model_config dictionaries are merged.",
            "it will _merge_ with",
        ),
    ],
    "pydantic/1.10.15/models": [
        (
            "How can a model be created without validation?",
            "Use construct only with trusted or already validated data.",
            "construct()",
        ),
        (
            "How do models parse attributes from ORM objects?",
            "Enable orm_mode and use from_orm.",
            "orm_mode",
        ),
        (
            "Which factory creates a model class dynamically?",
            "create_model creates a model from field definitions.",
            "create_model",
        ),
        ("How are custom root types declared?", "Declare the __root__ field.", "__root__"),
    ],
    "pydantic/2.10.4/models": [
        (
            "How can a model be created without validation?",
            "Use model_construct only for trusted or already validated data.",
            "model_construct()",
        ),
        (
            "How do models parse attributes from ORM objects?",
            "Set from_attributes=True and use model_validate.",
            "from_attributes=True",
        ),
        (
            "Which factory creates a model class dynamically?",
            "create_model creates a model from field definitions.",
            "DynamicFoobarModel = create_model(",
        ),
        (
            "How are custom root types declared?",
            "Use RootModel with the desired root type.",
            "RootModel[List[str]]",
        ),
    ],
    "pydantic/1.10.15/validators": [
        (
            "Does pre=True run a validator before other validation?",
            "Yes, pre invokes it before other validation.",
            "prior to other validation",
        ),
        (
            "How does each_item=True affect collection validation?",
            "It validates individual values instead of the whole object.",
            "passing `each_item=True`",
        ),
        (
            "Why can an assert-based validator stop working under python -O?",
            "Optimization disables assert statements.",
            "disables `assert` statements",
        ),
        (
            "Are validators called for an omitted field by default?",
            "No; always=True is available when appropriate.",
            "by default validators are not called",
        ),
    ],
    "pydantic/2.10.4/validators": [
        (
            "When do after validators run relative to internal validation?",
            "After Pydantic internal validation.",
            "run after Pydantic's internal validation",
        ),
        (
            "When do before validators run relative to internal validation?",
            "Before Pydantic internal parsing and validation.",
            "run before Pydantic's internal parsing and validation",
        ),
        (
            "What must a field validator return on success?",
            "The validated value.",
            "returning the validated value",
        ),
        (
            "Are default values validated automatically?",
            "No, unless configured to validate defaults.",
            "default values",
        ),
    ],
    "pydantic/1.10.15/serialization": [
        (
            "Does model.dict recursively convert submodels?",
            "Submodels are recursively converted to dictionaries.",
            "recursively converted to dictionaries",
        ),
        (
            "Does dict(model) recursively convert submodels?",
            "No, raw field values are returned.",
            "raw field values",
        ),
        (
            "How can JSON encoding of custom types be configured?",
            "Use json_encoders in model configuration.",
            "json_encoders",
        ),
        ("Is model.copy deep by default?", "The deep argument defaults to False.", "deep"),
    ],
    "pydantic/2.10.4/serialization": [
        (
            "Does model_dump recursively convert submodels?",
            "Submodels are recursively converted to dictionaries.",
            "recursively converted to dictionaries",
        ),
        (
            "Does dict(model) recursively convert submodels?",
            "No, raw field values are returned.",
            "raw field values",
        ),
        (
            "Which method returns a JSON-encoded string?",
            "model_dump_json serializes to a JSON-encoded string.",
            "JSON-encoded string",
        ),
        (
            "Which runtime setting enables duck-typed serialization?",
            "serialize_as_any=True.",
            "serialize_as_any=True",
        ),
    ],
}

for release in ("1.4.54", "2.0.36"):
    ITEMS[f"sqlalchemy/{release}"] = [
        (
            "What does Engine.connect return for database interaction?",
            "A Connection object.",
            "Engine.connect",
        ),
        (
            "How can Engine.begin manage a transaction context?",
            "It provides a connection with commit or rollback on context exit.",
            "Engine.begin",
        ),
        (
            "What does Connection.execution_options configure for transaction isolation?",
            "The isolation_level option.",
            "isolation_level",
        ),
        (
            "What does yield_per control when fetching a large result?",
            "The buffering and fetch batch size for streamed results.",
            "yield_per",
        ),
    ]
    ITEMS[f"sqlalchemy/{release}/engines"] = [
        (
            "Does constructing an Engine immediately open a DBAPI connection?",
            "No; connection creation is lazy until connect or begin is used.",
            "lazy initialization",
        ),
        (
            "Must special characters in a string database URL password be encoded?",
            "Yes; URL-encode special characters in URL strings.",
            "quote_plus",
        ),
        (
            "Can URL.create accept an unescaped password?",
            "Yes; URL.create accepts individual unescaped fields.",
            "URL.create(",
        ),
        (
            "Which create_engine option hides SQL parameter values from logs?",
            "hide_parameters=True.",
            "hide_parameters",
        ),
    ]
    ITEMS[f"sqlalchemy/{release}/select"] = [
        (
            "How can multiple WHERE expressions be combined with AND?",
            "Call where repeatedly or pass multiple expressions.",
            "joined by AND",
        ),
        (
            "Which flags request LEFT OUTER or FULL OUTER JOIN?",
            "isouter and full, respectively.",
            "isouter",
        ),
        (
            "Which methods build GROUP BY and HAVING clauses?",
            "Select.group_by and Select.having.",
            "Select.group_by",
        ),
        (
            "Which method turns a SELECT into a common table expression?",
            "Select.cte creates a CTE.",
            "cte()",
        ),
    ]

UNSUPPORTED = {
    "configuration": (
        "Which model configuration guarantees globally serializable writes across distributed database replicas?",
        "No distributed database consistency guarantee is supplied by these model-configuration pages.",
    ),
    "models": (
        "How does model construction guarantee cryptographic authenticity of every input field?",
        "The model pages do not provide cryptographic input authentication.",
    ),
    "validators": (
        "Which validator automatically proves an arbitrary Python function terminates for every possible input?",
        "The validator pages do not supply a general termination proof mechanism.",
    ),
    "serialization": (
        "Which serialization option automatically rotates database encryption keys every hour?",
        "The serialization pages do not define database key rotation.",
    ),
    "connections": (
        "What transaction option guarantees an atomic commit across every independent database in the world?",
        "The connection pages provide no universal distributed atomic-commit guarantee.",
    ),
    "engines": (
        "Which Engine argument guarantees zero downtime during every network partition?",
        "The engine pages do not guarantee availability under every network partition.",
    ),
    "select": (
        "Which SELECT modifier guarantees that every query finishes in one millisecond on all databases?",
        "The SELECT pages do not supply this latency guarantee.",
    ),
}


def build():
    records, sources = [], []
    for identity, items in ITEMS.items():
        project, release, *tail = identity.split("/")
        page = (
            tail[0] if tail else {"pydantic": "configuration", "sqlalchemy": "connections"}[project]
        )
        family = f"{project}:" + ("modeling" if page in ("configuration", "models") else page)
        split = (
            "dev"
            if page in ("configuration", "models", "connections")
            else "validation"
            if page in ("validators", "engines")
            else "test"
        )
        relative = Path("data/upstream") / identity / "manifest.json"
        meta = json.loads((ROOT / relative).read_text())
        blocks = chunks((ROOT / relative.parent / "source.txt").read_bytes().decode())
        sources.append(
            {
                "manifest": relative.as_posix(),
                "family_id": family,
                "split": split,
                "passages": len(blocks),
                **{
                    k: meta[k]
                    for k in (
                        "project",
                        "release",
                        "path",
                        "commit",
                        "raw_sha256",
                        "license_sha256",
                    )
                },
            }
        )
        for index, (question, answer, anchor) in enumerate(items + [(*UNSUPPORTED[page], None)]):
            positives = []
            if anchor:
                for i, block in enumerate(blocks):
                    if anchor.casefold() in block.casefold():
                        # Store exact bytes, including case, for deterministic review.
                        start = block.casefold().index(anchor.casefold())
                        positives.append(
                            {
                                "document_key": meta["path"],
                                "logical_key": f"{meta['path']}#block-{i:04}",
                                "grade": 1,
                                "anchor": block[start : start + len(anchor)],
                                "passage_sha256": __import__("hashlib")
                                .sha256(block.encode())
                                .hexdigest(),
                            }
                        )
                if not positives:
                    raise ValueError(f"Missing inspected anchor: {identity}: {anchor}")
            records.append(
                {
                    "id": f"v3-{len(records) + 1:03}",
                    "kind": "retrieval",
                    "project": project,
                    "release": release,
                    "family_id": family,
                    "split": split,
                    "dedup_group": f"{project}:{page}:{index}",
                    "question": f"In {project} {release}, {question[0].lower() + question[1:]}",
                    "category": "unanswerable" if anchor is None else "version_specific_api",
                    "role": "reader",
                    "source_commit": meta["commit"],
                    "source_manifest": relative.as_posix(),
                    "expected_answer": answer,
                    "expected_abstention": anchor is None,
                    "relevance": positives,
                    "question_origin": "ai_authored",
                    "label_origin": "ai_source_inspected_proposal",
                    "review_status": "ai_reviewed_proposal",
                    "human_review": None,
                    "annotation_completeness": "proposed anchors; exhaustive relevance requires independent review",
                }
            )
    output = ROOT / "evaluation/benchmark-v3.jsonl"
    if output.exists():
        raise ValueError("Frozen dataset exists; create a new version instead of overwriting")
    output.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
    )
    manifest = {
        "dataset_version": "v3-ai-proposal-70",
        "dataset": "evaluation/benchmark-v3.jsonl",
        "dataset_sha256": sha256(output),
        "records": len(records),
        "splits": dict(Counter(r["split"] for r in records)),
        "family_splits": {r["family_id"]: r["split"] for r in records},
        "sources": sources,
        "human_reviewed_records": 0,
        "independently_reviewed_records": 0,
        "freeze_basis": "Document families and paired versions assigned before ranking or threshold experiments; previous pilots preserved",
        "test_policy": "One explicitly labeled AI diagnostic after policy freeze; no tuning on test results",
        "pretraining_contamination": "Not audited; public upstream pages may have been seen during pretraining",
    }
    (ROOT / "evaluation/benchmark-v3-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {k: manifest[k] for k in ("dataset_version", "dataset_sha256", "records", "splits")}
        )
    )


if __name__ == "__main__":
    build()
