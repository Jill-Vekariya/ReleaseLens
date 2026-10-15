from releaselens.ingestion import normalize
from releaselens.retrieval import HashEmbedder, bm25


def test_bm25_orders_relevant_document():
    scores = bm25("autocommit transactions", ["model configuration", "autocommit transactions"])
    assert scores[1] > scores[0]


def test_hash_demo_is_reproducible_and_normalized():
    import math

    a = HashEmbedder().encode("hello model")
    assert a == HashEmbedder().encode("hello model")
    assert abs(math.sqrt(sum(v * v for v in a)) - 1) < 1e-10


def test_normalizer_preserves_code_indentation_and_case():
    assert normalize("if x:\n    call()") != normalize("if x:\ncall()")
    assert normalize("Config") != normalize("config")
    assert normalize("line  \r\n\r\n\r\nnext") == normalize("line\n\nnext")


def test_cross_version_compare_has_both_releases(client, admin):
    response = client.post(
        "/api/compare",
        headers=admin,
        json={
            "project": "pydantic",
            "left": "1.10.15",
            "right": "2.10.4",
            "question": "model configuration",
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["left"]["passages"] and result["right"]["passages"]
    assert all(p["release"] == "1.10.15" for p in result["left"]["passages"])
    assert all(p["release"] == "2.10.4" for p in result["right"]["passages"])


def test_every_production_ranking_mode_filters_release_before_selection(client):
    from releaselens.retrieval import rank
    from releaselens.security import Principal

    with client.app.state.factory() as session:
        for mode in ("lexical", "vector", "hybrid", "rerank", "version"):
            hits = rank(
                session,
                Principal("reader", "reader"),
                "pydantic",
                "1.10.15",
                "ConfigDict model_config configuration",
                client.app.state.embedder,
                mode,
                10,
            )
            assert all(doc.release == "1.10.15" for _, doc, _ in hits)
            assert not rank(
                session,
                Principal("reader", "reader"),
                "pydantic",
                "missing",
                "configuration",
                client.app.state.embedder,
                mode,
                10,
            )


def test_version_contamination_is_an_explicit_offline_experiment(client):
    from releaselens.retrieval import rank
    from releaselens.security import Principal

    with client.app.state.factory() as session:
        hits = rank(
            session,
            Principal("reader", "reader"),
            "pydantic",
            "1.10.15",
            "model configuration",
            client.app.state.embedder,
            "vector",
            10,
            enforce_release=False,
        )
        assert {doc.release for _, doc, _ in hits} == {"1.10.15", "2.10.4"}
