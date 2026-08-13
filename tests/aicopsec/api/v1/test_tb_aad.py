import pytest
from fastapi.testclient import TestClient

from ai4copsec.restapi.v1 import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_aad_compute_returns_a_trajectory(client):
    from ai4copsec.tbi.ais_anomaly_detection.base import AISAnomalyDetection

    sample = AISAnomalyDetection().create_input_sample()

    response = client.post("/api/v1/technological_brick/aad/compute", json=sample.model_dump(mode="json"))
    assert response.status_code == 200

    body = response.json()
    assert len(body["actual_trajectory"]) == len(sample.trajectory)


def test_aad_predict_unknown_algorithm_is_a_bad_request(client):
    from ai4copsec.tbi.ais_anomaly_detection.base import AISAnomalyDetection

    sample = AISAnomalyDetection().create_input_sample()
    sample.algorithm.name = "does-not-exist"

    response = client.post("/api/v1/technological_brick/aad/compute", json=sample.model_dump(mode="json"))
    assert response.status_code == 400


def test_aad_algorithms_lists_the_default_model(client):
    response = client.get("/api/v1/technological_brick/aad/algorithms")
    assert response.status_code == 200

    algorithms = {entry["algorithm"] for entry in response.json()}
    assert "default-aad" in algorithms
