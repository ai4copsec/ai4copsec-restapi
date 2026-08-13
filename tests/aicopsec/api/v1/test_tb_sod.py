import pytest
from fastapi.testclient import TestClient

from ai4copsec.restapi.v1 import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_sod_detect_returns_a_detection(client):
    from ai4copsec.tbi.sod.base import ShipOilDetection

    sample = ShipOilDetection().create_input_sample()

    response = client.post("/api/v1/technological_brick/sod/detect", json=sample.model_dump(mode="json"))
    assert response.status_code == 200

    body = response.json()
    assert len(body["ships"]) == 1


def test_sod_detect_unknown_algorithm_is_a_bad_request(client):
    from ai4copsec.tbi.sod.base import ShipOilDetection

    sample = ShipOilDetection().create_input_sample()
    sample.algorithm.name = "does-not-exist"

    response = client.post("/api/v1/technological_brick/sod/detect", json=sample.model_dump(mode="json"))
    assert response.status_code == 400


def test_sod_algorithms_lists_the_default_model(client):
    response = client.get("/api/v1/technological_brick/sod/algorithms")
    assert response.status_code == 200

    algorithms = {entry["algorithm"] for entry in response.json()}
    assert "default-sod-sar" in algorithms
