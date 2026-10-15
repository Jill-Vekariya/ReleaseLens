from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Section(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    key: str = Field(min_length=1, max_length=240)
    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=16000)
    fact_key: str | None = Field(default=None, min_length=1, max_length=200)
    fact_value: str | None = Field(default=None, min_length=1, max_length=1000)

    @field_validator("fact_key", "fact_value")
    @classmethod
    def canonical_fact(cls, value):
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def paired_fact(self):
        if (self.fact_key is None) != (self.fact_value is None):
            raise ValueError("fact_key and fact_value must be paired")
        if self.fact_key is not None and (not self.fact_key.strip() or not self.fact_value.strip()):
            raise ValueError("Fact assertions must contain non-whitespace values")
        return self


class IngestRequest(Strict):
    project: str = Field(pattern=r"^[a-z][a-z0-9-]{0,79}$")
    release: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,79}$")
    document_key: str = Field(min_length=1, max_length=200)
    classification: Literal["public", "internal", "restricted"] = "public"
    source_type: Literal["synthetic", "upstream"] = "synthetic"
    source_url: HttpUrl
    license: str = Field(min_length=1, max_length=2000)
    attribution: str = Field(min_length=1, max_length=2000)
    upstream_commit: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    published_at: str | None = Field(default=None, max_length=80)
    expected_revision: str | None = Field(default=None, max_length=36)
    sections: list[Section] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def valid_source(self):
        if len({s.key for s in self.sections}) != len(self.sections):
            raise ValueError("Section keys must be unique")
        if self.source_type == "upstream" and not self.upstream_commit:
            raise ValueError("Upstream ingestion requires an immutable commit")
        if self.source_type != "synthetic" and any(
            s.fact_key is not None or s.fact_value is not None for s in self.sections
        ):
            raise ValueError("Machine fact assertions are supported only by synthetic fixtures")
        return self


class AskRequest(Strict):
    project: str = Field(min_length=1, max_length=80)
    release: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=3, max_length=2000)
    mode: Literal["lexical", "vector", "hybrid", "rerank", "version"] = "version"
    save: bool = True
    k: int = Field(default=4, ge=1, le=10)


class CompareRequest(Strict):
    project: str = Field(min_length=1, max_length=80)
    left: str = Field(min_length=1, max_length=80)
    right: str = Field(min_length=1, max_length=80)
    question: str = Field(min_length=3, max_length=2000)


class Citation(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    passage_id: str
    document_id: str
    revision_id: str
    section: str
    release: str
    quote: str
    source_url: str
    source_type: str
    normalized_hash: str


class Claim(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    text: str
    citation_ids: list[str]
    fact_key: str | None = None
    fact_value: str | None = None


class AnswerPayload(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    question: str
    project: str
    release: str
    answer: str
    claims: list[Claim]
    passages: list[Citation]
    conflicts: list[dict]
    abstention_reason: str | None
    metadata: dict
    saved_answer_id: str | None = None
