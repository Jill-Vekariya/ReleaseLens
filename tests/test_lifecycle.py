from releaselens.fixtures import fixture


def ask(
    client,
    headers,
    question="What is the request_timeout?",
    project="demo",
    release="1.0",
    **kwargs,
):
    result = client.post(
        "/api/ask",
        headers=headers,
        json={"project": project, "release": release, "question": question, "k": 1, **kwargs},
    )
    assert result.status_code == 200, result.text
    return result.json()


def update(client, headers, value="60", text=None):
    document = next(
        d
        for d in client.get("/api/documents", headers=headers).json()
        if d["key"] == "timeout-policy"
    )
    body = fixture(
        "demo",
        "1.0",
        "timeout-policy",
        text or f"Synthetic service timeout policy: set request_timeout to {value} seconds.",
        "request_timeout",
        value,
    ).model_dump(mode="json")
    body["expected_revision"] = document["revision_id"]
    response = client.post("/api/ingest", headers=headers, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_end_to_end_stale_correction_preserves_history(client, admin):
    original = ask(client, admin)
    aid = original["saved_answer_id"]
    change = update(client, admin)
    assert change["kind"] == "technical_review_needed"
    assert aid in change["affected_answer_ids"]
    assert (
        client.get(f"/api/answers/{aid}", headers=admin).json()["status"] == "revalidation_pending"
    )
    review = client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()
    assert review["status"] == "confirmed_stale"
    correction = client.get(
        "/api/answers/" + review["assessment"]["corrected_answer_id"], headers=admin
    ).json()
    assert "60 seconds" in correction["payload"]["answer"]
    assert client.get(f"/api/answers/{aid}", headers=admin).json()["payload"] == original
    assert len(client.get(f"/api/answers/{aid}/history", headers=admin).json()) == 1


def test_formatting_does_not_invalidate_and_next_update_still_finds_old_dependencies(client, admin):
    original = ask(client, admin)
    result = update(
        client,
        admin,
        "30",
        "Synthetic service timeout policy: set request_timeout to 30 seconds.  \r\n",
    )
    assert result["kind"] == "formatting_only"
    assert result["affected_answer_ids"] == []
    aid = original["saved_answer_id"]
    assert client.get(f"/api/answers/{aid}", headers=admin).json()["status"] == "unaffected"
    result = update(client, admin, "90")
    assert aid in result["affected_answer_ids"]
    assert (
        client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()["status"]
        == "confirmed_stale"
    )


def test_technical_edit_same_fact_is_still_valid(client, admin):
    aid = ask(client, admin)["saved_answer_id"]
    update(
        client,
        admin,
        "30",
        "Synthetic timeout policy clarification: request_timeout is 30 seconds for a request.",
    )
    assert (
        client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()["status"]
        == "reviewed_still_valid"
    )


def test_removed_passage_is_insufficient_evidence(client, admin):
    aid = ask(client, admin)["saved_answer_id"]
    doc = next(
        d
        for d in client.get("/api/documents", headers=admin).json()
        if d["key"] == "timeout-policy"
    )
    body = fixture("demo", "1.0", "timeout-policy", "Unrelated replacement section").model_dump(
        mode="json"
    )
    body["sections"][0]["key"] = "replacement"
    body["expected_revision"] = doc["revision_id"]
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 200
    assert (
        client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()["status"]
        == "insufficient_evidence"
    )


def test_changed_unstructured_text_requires_review(client, admin):
    aid = ask(client, admin, "internal routing", k=1)["saved_answer_id"]
    doc = next(
        d
        for d in client.get("/api/documents", headers=admin).json()
        if d["key"] == "internal-routing"
    )
    body = fixture(
        "demo",
        "1.0",
        "internal-routing",
        "Synthetic internal routing is updated.",
        classification="internal",
    ).model_dump(mode="json")
    body["expected_revision"] = doc["revision_id"]
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 200
    assert (
        client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()["status"]
        == "manual_review_required"
    )


def test_idempotent_ingestion_and_compare_and_swap(client, admin):
    body = fixture(
        "demo",
        "1.0",
        "timeout-policy",
        "Synthetic service timeout policy: set request_timeout to 30 seconds.",
        "request_timeout",
        "30",
    ).model_dump(mode="json")
    first = client.post("/api/ingest", headers=admin, json=body).json()
    assert first["kind"] == "identical"
    body["sections"][0]["text"] = "Changed timeout policy"
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 409


def test_unanswerable_and_release_unknown(client, admin):
    assert ask(client, admin, "zyzzyva teleportation qubits")["abstention_reason"]
    assert ask(client, admin, "timeout", release="9.9")["abstention_reason"]


def test_conflicting_synthetic_evidence_abstains(client, admin):
    body = fixture(
        "demo",
        "1.0",
        "timeout-alternative",
        "request_timeout policy is 999 seconds.",
        "request_timeout",
        "999",
    ).model_dump(mode="json")
    assert client.post("/api/ingest", headers=admin, json=body).status_code == 200
    result = ask(client, admin, "request_timeout", k=4)
    assert result["conflicts"] and not result["claims"]
    assert result["abstention_reason"]


def test_two_updates_before_revalidation_uses_latest_head(client, admin):
    aid = ask(client, admin)["saved_answer_id"]
    update(client, admin, "60")
    update(client, admin, "120")
    review = client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()
    assert review["assessment"]["reasons"][0]["new_value"] == "120"


def test_rollback_to_original_value_is_valid(client, admin):
    aid = ask(client, admin)["saved_answer_id"]
    update(client, admin, "60")
    update(client, admin, "30")
    assert (
        client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()["status"]
        == "reviewed_still_valid"
    )


def test_revalidation_is_idempotent_for_same_evidence_heads(client, admin):
    aid = ask(client, admin)["saved_answer_id"]
    update(client, admin, "60")
    first = client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()
    second = client.post(f"/api/answers/{aid}/revalidate", headers=admin).json()
    assert first == second
    assert len(client.get(f"/api/answers/{aid}/history", headers=admin).json()) == 1
