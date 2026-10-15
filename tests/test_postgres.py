"""Integration test runs only against a migrated, disposable PostgreSQL database."""

import os

import pytest
from sqlalchemy import text

from releaselens.db import database
from releaselens.fixtures import fixture
from releaselens.ingestion import ingest
from releaselens.models import Answer
from releaselens.retrieval import HashEmbedder, rank
from releaselens.schemas import AskRequest
from releaselens.security import Principal
from releaselens.service import ask, revalidate

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL runtime unavailable; CI service is configured",
)


def test_postgres_vectors_fts_and_authorization():
    engine, factory = database()
    embedder = HashEmbedder()
    with factory() as session:
        transaction = session.begin()
        try:
            admin, reader = (
                Principal("integration-admin", "admin"),
                Principal("integration-reader", "reader"),
            )
            ingest(
                session,
                admin,
                fixture(
                    "integration",
                    "1.0",
                    "timeout-policy",
                    "request_timeout is 30 seconds",
                    "timeout",
                    "30",
                ),
                embedder,
            )
            ingest(
                session,
                admin,
                fixture(
                    "integration",
                    "2.0",
                    "timeout-policy",
                    "request_timeout is 60 seconds",
                    "timeout",
                    "60",
                ),
                embedder,
            )
            ingest(
                session,
                admin,
                fixture(
                    "integration",
                    "1.0",
                    "private-canary",
                    "request_timeout SECRET_CANARY",
                    classification="restricted",
                ),
                embedder,
            )
            hits = rank(
                session, reader, "integration", "1.0", "request_timeout", embedder, "version", 10
            )
            assert hits
            assert all(d.release == "1.0" and d.classification == "public" for _, d, _ in hits)
            assert (
                session.scalar(text("SELECT count(*) FROM passages WHERE dense_vector IS NOT NULL"))
                >= 3
            )
            assert (
                session.scalar(
                    text("SELECT count(*) FROM pg_indexes WHERE indexname='passages_fts'")
                )
                == 1
            )
            session.info["embedder"] = embedder
            saved = ask(
                session,
                reader,
                AskRequest(project="integration", release="1.0", question="request_timeout", k=1),
                embedder,
            )
            update = fixture(
                "integration",
                "1.0",
                "timeout-policy",
                "request_timeout is 45 seconds",
                "timeout",
                "45",
            )
            update.expected_revision = saved.passages[0].revision_id
            ingest(session, admin, update, embedder)
            # PostgreSQL JSON has no equality operator: selecting DISTINCT entire
            # Answer rows used to fail here. Select affected IDs in a subquery instead.
            assert session.get(Answer, saved.saved_answer_id).status == "revalidation_pending"
            review = revalidate(session, reader, saved.saved_answer_id)
            assert review["status"] == "confirmed_stale"
            assert review["assessment"]["corrected_answer_id"]
        finally:
            transaction.rollback()
    engine.dispose()
