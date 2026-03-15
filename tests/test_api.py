"""API contract tests."""

import pytest
from fastapi.testclient import TestClient

from ntl_engine.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_inference_returns_202_when_not_cached(client: TestClient) -> None:
    r = client.post(
        "/inference",
        json={"feeder_id": "f1", "window_id": "w1"},
    )
    assert r.status_code == 202
