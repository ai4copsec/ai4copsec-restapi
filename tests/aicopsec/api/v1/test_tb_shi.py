import pytest
from fastapi.testclient import TestClient

from ai4copsec.restapi.v1 import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_shi_identify_returns_a_candidate(client):
    from ai4copsec.tbi.ship_identification.base import ShipIdentification

    sample = ShipIdentification().create_input_sample()

    response = client.post("/api/v1/technological_brick/shi/identify", json=sample.model_dump(mode="json"))
    assert response.status_code == 200

    body = response.json()
    assert len(body["candidates"]) == 1


def test_shi_identify_unknown_algorithm_is_a_bad_request(client):
    from ai4copsec.tbi.ship_identification.base import ShipIdentification

    sample = ShipIdentification().create_input_sample()
    sample.algorithm.name = "does-not-exist"

    response = client.post("/api/v1/technological_brick/shi/identify", json=sample.model_dump(mode="json"))
    assert response.status_code == 400


def test_shi_algorithms_lists_the_default_model(client):
    response = client.get("/api/v1/technological_brick/shi/algorithms")
    assert response.status_code == 200

    algorithms = {entry["algorithm"] for entry in response.json()}
    assert "our-best-shipidentification-algorithm" in algorithms
