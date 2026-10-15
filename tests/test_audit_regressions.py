"""Regress actual defects found in the final engineering review."""

import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from releaselens.api import create_app
from releaselens.fixtures import fixture
from releaselens.models import Answer
from tests.test_lifecycle import ask, update


def test_preserve_immutable_whitespace_in_fresh_claim_and_citation(client, admin):
    text = "    Synthetic service timeout policy: set request_timeout to 30 seconds.  \r\n"
    update(client, admin, "30", text)
    result = ask(client, admin)
    assert result["answer"] == text
    assert result["claims"][0]["text"] == text
    assert result["claims"][0]["fact_value"] == "30"
    assert result["passages"][0]["quote"] == text
    assert (
        client.get("/api/evidence/" + result["passages"][0]["passage_id"], headers=admin).json()[
            "quote"
        ]
        == text
    )


@pytest.mark.parametrize(
    "key,value", [("", "30"), ("  ", "30"), ("timeout", ""), ("timeout", "\t")]
)
def test_blank_machine_fact_assertions_are_rejected(client, admin, key, value):
    body = fixture("demo", "1.0", "blank-fact", "timeout is 30").model_dump(mode="json")
    body["sections"][0].update(fact_key=key, fact_value=value)
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 422


def test_upstream_machine_assertions_rejected(client, admin):
    body = fixture("demo", "1.0", "upstream-fact", "timeout is 30", "timeout", "30").model_dump(
        mode="json"
    )
    body.update(source_type="upstream", upstream_commit="a" * 40)
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 422


def test_commit_failure_cannot_acknowledge_a_saved_answer():
    app = create_app("sqlite:///:memory:", demo=True)
    with TestClient(app, raise_server_exceptions=False) as c:

        def fail(session):
            if any(isinstance(row, Answer) for row in session.identity_map.values()):
                raise RuntimeError("injected commit failure")

        event.listen(Session, "before_commit", fail)
        try:
            result = c.post(
                "/api/ask",
                json={"project": "demo", "release": "1.0", "question": "request_timeout"},
            )
            assert result.status_code == 500
        finally:
            event.remove(Session, "before_commit", fail)
        with app.state.factory() as session:
            assert session.scalar(select(Answer)) is None
        assert c.get("/health").status_code == 200


def test_new_public_counterevidence_endpoint_history_and_withdrawal(client, admin):
    original = ask(client, admin)
    aid = original["saved_answer_id"]
    initial = client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()
    assert initial["status"] == "reviewed_still_valid"
    body = fixture(
        "demo", "1.0", "counter-review", "request_timeout is 999 seconds.", "request_timeout", "999"
    ).model_dump(mode="json")
    change = client.post("/api/ingest", headers=admin, json=body).json()
    assert aid in change["potentially_affected_answer_ids"]
    assert (
        client.get(f"/api/answers/{aid}", headers=admin).json()["status"] == "revalidation_pending"
    )
    review = client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()
    assert review["status"] == "manual_review_required"
    assert review["assessment"]["corrected_answer_id"] is None
    assert review["assessment"]["public_counterevidence"]
    assert client.post(f"/api/answers/{aid}/revalidate", headers=admin).json() == review
    assert client.get(f"/api/answers/{aid}", headers=admin).json()["payload"] == original
    body["expected_revision"] = change["revision_id"]
    body["sections"][0].update(text="Unrelated public statement.", fact_key=None, fact_value=None)
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 200
    # Explicit review observes removal; automatic resolution is deliberately unimplemented.
    assert client.post(f"/api/answers/{aid}/revalidate", headers=admin).json() == initial
    assert len(client.get(f"/api/answers/{aid}/history", headers=admin).json()) == 2


def test_private_counterevidence_does_not_change_public_answer_status_or_review(client, admin):
    reader = {"X-Demo-Role": "reader"}
    aid = ask(client, reader)["saved_answer_id"]
    before = client.post(f"/api/answers/{aid}/revalidate", headers=reader).json()
    body = fixture(
        "demo",
        "1.0",
        "private-counter",
        "request_timeout is 999 seconds.",
        "request_timeout",
        "999",
        classification="restricted",
    ).model_dump(mode="json")
    change = client.post("/api/ingest", headers=admin, json=body).json()
    assert not change["affected_answer_ids"]
    assert client.post(f"/api/answers/{aid}/revalidate", headers=reader).json() == before
    assert client.get(f"/api/answers/{aid}", headers=admin).status_code == 404


def test_removing_fact_metadata_with_same_text_requires_review(client, admin):
    result = ask(client, admin)
    aid = result["saved_answer_id"]
    body = fixture("demo", "1.0", "timeout-policy", result["answer"]).model_dump(mode="json")
    body["expected_revision"] = result["passages"][0]["revision_id"]
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 200
    assert (
        client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()["status"]
        == "manual_review_required"
    )


def test_original_conflict_abstention_never_becomes_confirmed_incorrect(client, admin):
    body = fixture(
        "demo",
        "1.0",
        "abstention-conflict",
        "request_timeout is 999 seconds.",
        "request_timeout",
        "999",
    ).model_dump(mode="json")
    client.post("/api/ingest", headers=admin, json=body)
    result = ask(client, admin, k=4)
    assert result["abstention_reason"] and not result["claims"]
    update(client, admin, "60")
    review = client.post(
        "/api/answers/" + result["saved_answer_id"] + "/revalidate", headers=admin
    ).json()
    assert review["status"] == "manual_review_required"
    assert review["assessment"]["corrected_answer_id"] is None


def test_concurrent_updates_share_one_expected_revision():
    async def run():
        app = create_app("sqlite:///:memory:", demo=True)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1)),
                base_url="http://test",
            ) as c:
                docs = (await c.get("/api/documents", headers={"X-Demo-Role": "admin"})).json()
                head = next(d["revision_id"] for d in docs if d["key"] == "timeout-policy")
                bodies = []
                for value in ("60", "90"):
                    b = fixture(
                        "demo",
                        "1.0",
                        "timeout-policy",
                        "request_timeout is " + value,
                        "request_timeout",
                        value,
                    ).model_dump(mode="json")
                    b["expected_revision"] = head
                    bodies.append(b)
                results = await asyncio.gather(
                    *(
                        c.post("/api/ingest", headers={"X-Demo-Role": "admin"}, json=b)
                        for b in bodies
                    )
                )
                assert sorted(r.status_code for r in results) == [200, 409]

    asyncio.run(run())


def test_fact_metadata_whitespace_does_not_create_false_staleness(client, admin):
    original = ask(client, admin)
    body = fixture("demo", "1.0", "timeout-policy", original["answer"]).model_dump(mode="json")
    body["sections"][0].update(fact_key=" request_timeout ", fact_value=" 30 ")
    body["expected_revision"] = original["passages"][0]["revision_id"]
    result = client.post("/api/ingest", headers=admin, json=body)
    assert result.status_code == 200
    assert result.json()["kind"] == "identical"
    assert (
        client.post(
            "/api/answers/" + original["saved_answer_id"] + "/revalidate", headers=admin
        ).json()["status"]
        == "reviewed_still_valid"
    )
