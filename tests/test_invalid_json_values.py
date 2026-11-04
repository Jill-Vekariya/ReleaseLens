import pytest


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_json_returns_validation_error(client, number):
    response = client.post(
        "/api/ask",
        content='{"project":"demo", "release":"v1", "question":"private input", "k":'
        + number
        + "}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "k"]
    assert "input" not in response.json()["detail"][0]
