import pytest
from fastapi.testclient import TestClient

from ai4copsec.restapi.v1 import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_all_algorithms_lists_every_bricks_default_model(client):
    response = client.get("/api/v1/technological_brick/algorithms")
    assert response.status_code == 200

    all_algorithms = response.json()
    assert "default-sod-sar" in {entry["algorithm"] for entry in all_algorithms["SOD"]}
    assert "sample_algorithm" in {entry["algorithm"] for entry in all_algorithms["DAN"]}
    assert "our-best-shipidentification-algorithm" in {entry["algorithm"] for entry in all_algorithms["SHI"]}
    assert "default-trp" in {entry["algorithm"] for entry in all_algorithms["TRP"]}
