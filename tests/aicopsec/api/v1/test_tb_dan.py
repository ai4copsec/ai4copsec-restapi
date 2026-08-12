import pytest
from fastapi.testclient import TestClient

from ai4copsec.restapi.v1 import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_dan_compute_returns_a_forecast(client):
    from ai4copsec.tbi.drift_analysis.base import DriftAnalysis

    sample = DriftAnalysis().create_input_sample()

    response = client.post("/api/v1/technological_brick/dan/compute", json=sample.model_dump(mode="json"))
    assert response.status_code == 200
    assert "trajectory" in response.json()


def test_dan_compute_unknown_algorithm_is_a_bad_request(client):
    from ai4copsec.tbi.drift_analysis.base import DriftAnalysis

    sample = DriftAnalysis().create_input_sample()
    sample.approach["algorithm"] = "does-not-exist"

    response = client.post("/api/v1/technological_brick/dan/compute", json=sample.model_dump(mode="json"))
    assert response.status_code == 400


def test_dan_compute_unsupported_mode_is_a_bad_request(client):
    from ai4copsec.tbi.drift_analysis.base import DriftAnalysis

    sample = DriftAnalysis().create_input_sample()
    sample.mode = "interpolate"

    response = client.post("/api/v1/technological_brick/dan/compute", json=sample.model_dump(mode="json"))
    assert response.status_code == 400


def test_dan_algorithms_lists_the_default_model(client):
    response = client.get("/api/v1/technological_brick/dan/algorithms")
    assert response.status_code == 200

    algorithms = {entry["algorithm"] for entry in response.json()}
    assert "sample_algorithm" in algorithms
