"""Run inside the configured backend against its real HTTP API and PostgreSQL.

docker compose exec -T backend python scripts/docker_smoke.py
Seeds synthetic teaching records without altering existing document revisions.
Never prints credentials. Uses the configured local admin account for saved answers.
"""

import json
import os

import httpx

from releaselens.db import database
from releaselens.fixtures import fixture, seed
from releaselens.retrieval import configured_embedder


def run():
    credentials = json.loads(os.environ["RELEASELENS_TOKENS"])
    by_role = {identity["role"]: token for token, identity in credentials.items()}
    if not {"reader", "admin"} <= by_role.keys():
        raise RuntimeError("Smoke verification needs configured reader and admin identities")
    engine, factory = database()
    with factory.begin() as session:
        seed(session, configured_embedder())
    checks = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:

        def call(method, path, role="admin", body=None, expected=200):
            response = client.request(
                method, path, headers={"Authorization": "Bearer " + by_role[role]}, json=body
            )
            if response.status_code != expected:
                raise AssertionError(
                    f"{method} {path}: expected {expected}, received {response.status_code}: {response.text[:300]}"
                )
            return response.json()

        health = call("GET", "/health")
        assert health["database"] == "postgresql" and health["demo"] is False
        checks.append("authenticated-mode PostgreSQL health")
        assert client.get("/api/projects").status_code == 401
        checks.append("anonymous API rejected")

        def ask(question, role="admin", project="demo", release="1.0"):
            return call(
                "POST",
                "/api/ask",
                role,
                {"project": project, "release": release, "question": question, "k": 1},
            )

        private = ask("CANARY-ORCHID-7814")
        assert private["claims"]
        public = ask("CANARY-ORCHID-7814", "reader")
        assert not public["claims"] and not public["passages"]
        call("GET", "/api/evidence/" + private["passages"][0]["passage_id"], "reader", expected=404)
        call("GET", "/api/answers/" + private["saved_answer_id"], "reader", expected=404)
        checks.append("SQL-filtered canary, direct citation and saved-answer authorization")
        original = ask("request_timeout policy")
        document = next(
            d
            for d in call("GET", "/api/documents")
            if d["project"] == "demo" and d["key"] == "timeout-policy"
        )
        quote = original["passages"][0]["quote"]
        value = "60" if "30 seconds" in quote else "30"
        body = fixture(
            "demo",
            "1.0",
            "timeout-policy",
            f"Synthetic service timeout policy: set request_timeout to {value} seconds.",
            "request_timeout",
            value,
        ).model_dump(mode="json")
        body["expected_revision"] = document["revision_id"]
        update = call("POST", "/api/ingest", body=body)
        aid = original["saved_answer_id"]
        assert aid in update["affected_answer_ids"]
        review = call("POST", f"/api/answers/{aid}/revalidate")
        assert review["status"] == "confirmed_stale"
        assert call("POST", f"/api/answers/{aid}/revalidate") == review
        assert call("GET", f"/api/answers/{aid}")["payload"] == original
        correction = call("GET", "/api/answers/" + review["assessment"]["corrected_answer_id"])
        assert f"{value} seconds" in correction["payload"]["answer"]
        checks.append("real HTTP technical update, impact queue, correction and idempotent audit")
        current = ask("request_timeout policy")
        body["expected_revision"] = update["revision_id"]
        body["sections"][0]["text"] += "  \r\n"
        formatting = call("POST", "/api/ingest", body=body)
        assert formatting["kind"] == "formatting_only"
        assert current["saved_answer_id"] not in formatting["affected_answer_ids"]
        checks.append("formatting-only edit does not invalidate current answer")
        comparison = call(
            "POST",
            "/api/compare",
            body={
                "project": "pydantic",
                "left": "1.10.15",
                "right": "2.10.4",
                "question": "model configuration",
            },
        )
        assert comparison["left"]["passages"] and comparison["right"]["passages"]
        assert all(p["release"] == "1.10.15" for p in comparison["left"]["passages"])
        assert all(p["release"] == "2.10.4" for p in comparison["right"]["passages"])
        checks.append("independently release-filtered PostgreSQL comparison")
    record = {
        "status": "passed",
        "database": "postgresql",
        "transport": "real HTTP",
        "checks": checks,
        "original_answer_id": aid,
        "review_id": review["review_id"],
        "corrected_answer_id": review["assessment"]["corrected_answer_id"],
    }
    print(json.dumps(record, indent=2))
    engine.dispose()
    return record


if __name__ == "__main__":
    run()
