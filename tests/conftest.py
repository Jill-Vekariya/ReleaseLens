import pytest
from fastapi.testclient import TestClient

from releaselens.api import create_app


@pytest.fixture
def client():
    with TestClient(create_app("sqlite:///:memory:", demo=True)) as client:
        yield client


@pytest.fixture
def admin():
    return {"X-Demo-Role": "admin"}
