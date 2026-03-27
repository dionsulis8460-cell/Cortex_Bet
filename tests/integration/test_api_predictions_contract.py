"""Contract tests for the official HTTP predictions endpoint."""

from fastapi.testclient import TestClient

import src.api.server as api_server


class _ProviderStub:
    """Simple provider stub that records call arguments and returns fixed data."""

    def __init__(self):
        self.called_with = None

    def get_predictions_with_reasoning(self, **kwargs):
        """Return deterministic payload and capture kwargs for assertion."""
        self.called_with = kwargs
        return [{"match_id": 123, "confidence": 0.71}]


def test_predictions_endpoint_uses_provider_and_maps_query_params():
    """The endpoint must forward query params to provider and return provider payload."""
    provider = _ProviderStub()
    api_server.provider = provider

    client = TestClient(api_server.app)

    response = client.get(
        "/api/predictions",
        params={
            "date": "2026-03-27",
            "league": "all",
            "status": "scheduled",
            "top7_only": "true",
            "sort_by": "confidence",
        },
    )

    assert response.status_code == 200
    assert response.json() == [{"match_id": 123, "confidence": 0.71}]
    assert provider.called_with == {
        "date_str": "2026-03-27",
        "league": "all",
        "status": "scheduled",
        "top7_only": True,
        "sort_by": "confidence",
    }


def test_predictions_endpoint_returns_503_when_provider_missing():
    """The endpoint must fail fast with 503 while provider is not initialized."""
    api_server.provider = None
    client = TestClient(api_server.app)

    response = client.get("/api/predictions")

    assert response.status_code == 503
    assert "Provider not initialized" in response.text
