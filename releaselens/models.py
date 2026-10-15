"""Immutable evidence revisions; mutable document heads and answer review state."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("project", "release", "key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project: Mapped[str] = mapped_column(String(80), index=True)
    release: Mapped[str] = mapped_column(String(80), index=True)
    key: Mapped[str] = mapped_column(String(200))
    classification: Mapped[str] = mapped_column(String(20))
    current_revision: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Revision(Base):
    __tablename__ = "revisions"
    __table_args__ = (UniqueConstraint("document_id", "sequence"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    raw_hash: Mapped[str] = mapped_column(String(64))
    raw_content: Mapped[str] = mapped_column(Text)
    normalized_hash: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(Text)
    license: Mapped[str] = mapped_column(Text)
    attribution: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30))
    upstream_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Passage(Base):
    __tablename__ = "passages"
    __table_args__ = (UniqueConstraint("revision_id", "logical_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    revision_id: Mapped[str] = mapped_column(ForeignKey("revisions.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    logical_key: Mapped[str] = mapped_column(String(240))
    section: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    normalized_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list] = mapped_column(JSON)
    embedding_model: Mapped[str] = mapped_column(String(300))
    fact_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    fact_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    quarantined: Mapped[bool] = mapped_column(Boolean, default=False)


class Answer(Base):
    __tablename__ = "answers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner: Mapped[str] = mapped_column(String(100), index=True)
    project: Mapped[str] = mapped_column(String(80))
    release: Mapped[str] = mapped_column(String(80))
    question: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="unaffected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Dependency(Base):
    __tablename__ = "dependencies"
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"), primary_key=True)
    passage_id: Mapped[str] = mapped_column(ForeignKey("passages.id"), primary_key=True)


class Change(Base):
    __tablename__ = "changes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    old_revision: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    new_revision: Mapped[str] = mapped_column(ForeignKey("revisions.id"))
    kind: Mapped[str] = mapped_column(String(40))
    delta: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("answer_id", "evidence_fingerprint"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    answer_id: Mapped[str] = mapped_column(ForeignKey("answers.id"), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    evidence_fingerprint: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40))
    assessment: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


Index("passage_revision_document", Passage.revision_id, Passage.document_id)
