import pytest
from fastapi.testclient import TestClient

from ai4copsec.restapi.v1 import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_trp_predict_returns_a_trajectory(client):
    from ai4copsec.tbi.trajectory_prediction.base import TrajectoryPrediction

    sample = TrajectoryPrediction().create_input_sample()

    response = client.post("/api/v1/technological_brick/trp/predict", json=sample.model_dump(mode="json"))
    assert response.status_code == 200

    body = response.json()
    assert len(body["trajectory"]) == len(sample.context.trajectory)


def test_trp_predict_unknown_algorithm_is_a_bad_request(client):
    from ai4copsec.tbi.trajectory_prediction.base import TrajectoryPrediction

    sample = TrajectoryPrediction().create_input_sample()
    sample.algorithm.name = "does-not-exist"

    response = client.post("/api/v1/technological_brick/trp/predict", json=sample.model_dump(mode="json"))
    assert response.status_code == 400


def test_trp_algorithms_lists_the_default_model(client):
    response = client.get("/api/v1/technological_brick/trp/algorithms")
    assert response.status_code == 200

    algorithms = {entry["algorithm"] for entry in response.json()}
    assert "default-trp" in algorithms
