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
            for mode in ("lexical", "vector", "hybrid", "rerank", "version"):
                hits = rank(
                    session, reader, "integration", "1.0", "request_timeout", embedder, mode, 10
                )
                assert hits
                assert all(d.release == "1.0" and d.classification == "public" for _, d, _ in hits)
                assert not rank(
                    session, reader, "integration", "9.9", "request_timeout", embedder, mode, 10
                )
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
            initial = revalidate(session, reader, saved.saved_answer_id)
            counter = ingest(
                session,
                admin,
                fixture(
                    "integration",
                    "1.0",
                    "counter",
                    "request_timeout is 999 seconds",
                    "timeout",
                    "999",
                ),
                embedder,
            )
            assert not counter["affected_answer_ids"]  # Never return another owner's IDs.
            assert session.get(Answer, saved.saved_answer_id).status == "revalidation_pending"
            potential = revalidate(session, reader, saved.saved_answer_id)
            assert potential["status"] == "manual_review_required"
            assert potential["assessment"]["corrected_answer_id"] is None
            assert potential["review_id"] != initial["review_id"]
            assert revalidate(session, reader, saved.saved_answer_id) == potential
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


def test_postgres_public_prose_candidates_preserve_owner_and_release_boundaries():
    engine, factory = database()
    encoder = HashEmbedder()
    with factory() as session:
        transaction = session.begin()
        try:
            admin, reader = Principal("prose-admin", "admin"), Principal("prose-reader", "reader")
            session.info["embedder"] = encoder
            session.info["prose_review_candidates"] = True
            original = fixture(
                "pg-prose",
                "1.0",
                "original",
                "Field validation checks input data before creating instances.",
            )
            original.source_type, original.upstream_commit = "upstream", "a" * 40
            ingest(session, admin, original, encoder)
            saved = ask(
                session,
                reader,
                AskRequest(
                    project="pg-prose",
                    release="1.0",
                    question="Does field validation check input data?",
                    k=1,
                ),
                encoder,
            )
            for release, classification in [
                ("2.0", "public"),
                ("1.0", "restricted"),
                ("1.0", "public"),
            ]:
                new = fixture(
                    "pg-prose",
                    release,
                    classification,
                    "Field validation can bypass input data checks during construction.",
                    classification=classification,
                )
                new.source_type, new.upstream_commit = "upstream", "b" * 40
                event = ingest(session, admin, new, encoder)
                assert not event["affected_answer_ids"]
                expected = (
                    "revalidation_pending"
                    if release == "1.0" and classification == "public"
                    else "unaffected"
                )
                assert session.get(Answer, saved.saved_answer_id).status == expected
            assert (
                revalidate(session, reader, saved.saved_answer_id)["status"]
                == "manual_review_required"
            )
        finally:
            transaction.rollback()
    engine.dispose()
