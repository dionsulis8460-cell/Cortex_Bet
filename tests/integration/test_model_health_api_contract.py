"""Integration contract tests for online model health endpoint."""

from fastapi.testclient import TestClient

import src.api.server as api_server


def test_model_health_endpoint_returns_alert_payload(monkeypatch):
    monkeypatch.setattr(
        api_server,
        "get_model_health_snapshot",
        lambda: {
            "champion": "ensemble_v1",
            "champion_runtime_adapter": "ensemble",
            "ece_v2_mean": 0.25,
            "ece_legacy_mean": 0.24,
            "alert_count": 1,
            "alerts": [{"severity": "warning", "type": "calibration", "message": "ECE high"}],
        },
    )

    client = TestClient(api_server.app)
    response = client.get("/api/model-health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["champion"] == "ensemble_v1"
    assert isinstance(payload["alerts"], list)
