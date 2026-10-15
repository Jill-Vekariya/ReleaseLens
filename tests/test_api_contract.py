import pytest

from releaselens.fixtures import fixture
from releaselens.schemas import IngestRequest


def test_frontend_assets_and_openapi_contract(client):
    for path, expected in [
        ("/", "text/html"),
        ("/app.js", "javascript"),
        ("/style.css", "text/css"),
        ("/docs", "text/html"),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.headers["content-type"]
        assert response.headers["cache-control"] == "no-store"
    schema = client.get("/openapi.json").json()
    assert "/api/ask" in schema["paths"]
    assert "additionalProperties" in schema["components"]["schemas"]["AskRequest"]
    assert schema["components"]["schemas"]["AskRequest"]["additionalProperties"] is False


def test_duplicate_logical_passages_rejected():
    body = fixture("demo", "1.0", "document", "sample").model_dump(mode="json")
    body["sections"] *= 2
    with pytest.raises(ValueError, match="unique"):
        IngestRequest(**body)
