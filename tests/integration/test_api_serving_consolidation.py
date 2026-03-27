"""Integration characterization tests for consolidated HTTP serving routes."""

from fastapi.testclient import TestClient

import src.api.server as api_server


class _DummyConn:
    """Simple connection stub that satisfies close() contract."""

    def close(self):
        """No-op close for test cursor lifecycle."""
        return None


class _DummyDb:
    """Simple db stub that satisfies close() contract."""

    def close(self):
        """No-op close for test db lifecycle."""
        return None


def _stub_open_db_cursor():
    """Return deterministic db/cursor tuple for endpoint tests."""
    return _DummyDb(), _DummyConn(), object()


def test_auth_route_uses_http_backend_contract(monkeypatch):
    """Auth endpoint must return canonical success payload from domain auth service."""
    monkeypatch.setattr(api_server, "_open_db_cursor", _stub_open_db_cursor)
    monkeypatch.setattr(
        api_server,
        "auth_user",
        lambda cursor, username, password: {"success": True, "userId": 7, "username": username},
    )

    client = TestClient(api_server.app)
    response = client.post("/api/auth", json={"username": "alice", "password": "secret"})

    assert response.status_code == 200
    assert response.json()["userId"] == 7


def test_feed_and_leaderboard_routes_expose_backend_data(monkeypatch):
    """Feed and leaderboard endpoints must expose domain outputs through HTTP."""
    monkeypatch.setattr(api_server, "_open_db_cursor", _stub_open_db_cursor)
    monkeypatch.setattr(api_server, "get_public_feed", lambda cursor, limit: [{"bet_id": 1, "limit": limit}])
    monkeypatch.setattr(api_server, "get_leaderboard", lambda cursor: [{"username": "alice", "wins": 10}])

    client = TestClient(api_server.app)

    feed_response = client.get("/api/feed", params={"limit": 25})
    leaderboard_response = client.get("/api/leaderboard")

    assert feed_response.status_code == 200
    assert feed_response.json()["feed"][0]["limit"] == 25

    assert leaderboard_response.status_code == 200
    assert leaderboard_response.json()["leaderboard"][0]["username"] == "alice"


def test_performance_and_bankroll_routes_return_expected_payload(monkeypatch):
    """Performance and bankroll endpoints must preserve expected HTTP response shapes."""
    monkeypatch.setattr(api_server, "_open_db_cursor", _stub_open_db_cursor)
    monkeypatch.setattr(api_server, "get_performance_data", lambda from_date, to_date: {"overall_metrics": {"win_rate": 50.0}})
    monkeypatch.setattr(api_server, "get_current_balance", lambda cursor, user_id: 123.45)
    monkeypatch.setattr(api_server, "get_bet_history", lambda cursor, user_id: [{"id": 1}])
    monkeypatch.setattr(api_server, "get_stats", lambda cursor, user_id: {"total_bets": 1})
    monkeypatch.setattr(api_server, "place_bet", lambda cursor, conn, payload, uid: {"bet_id": 99})
    monkeypatch.setattr(api_server, "delete_bet", lambda cursor, conn, bet_id, user_id: {"success": True})

    client = TestClient(api_server.app)

    perf_response = client.get("/api/performance")
    bankroll_get = client.get("/api/bankroll", params={"type": "all", "user_id": 1})
    bankroll_post = client.post("/api/bankroll", json={"stake": 10, "items": [], "userId": 1})
    bankroll_delete = client.delete("/api/bankroll", params={"id": 10, "user_id": 1})

    assert perf_response.status_code == 200
    assert perf_response.json()["overall_metrics"]["win_rate"] == 50.0

    assert bankroll_get.status_code == 200
    assert bankroll_get.json()["balance"] == 123.45

    assert bankroll_post.status_code == 200
    assert bankroll_post.json()["bet_id"] == 99

    assert bankroll_delete.status_code == 200
    assert bankroll_delete.json()["success"] is True


def test_system_status_and_validate_routes_use_backend_contract(monkeypatch):
    """System status and validate routes must return stable payloads via backend services."""

    class _ProviderStub:
        def get_system_status(self):
            return {"status": "online", "last_updated": "2026-03-27 12:00:00", "live_matches": 3}

    monkeypatch.setattr(api_server, "provider", _ProviderStub())
    monkeypatch.setattr(api_server, "validate_pending_bets", lambda: 5)

    client = TestClient(api_server.app)

    status_response = client.get("/api/system-status")
    validate_response = client.post("/api/validate-bets")

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "online"
    assert status_response.json()["live_matches"] == 3

    assert validate_response.status_code == 200
    assert validate_response.json()["success"] is True
    assert validate_response.json()["validated_count"] == 5


def test_scanner_run_and_control_routes_preserve_expected_response_shapes(monkeypatch):
    """Scanner run/control routes must preserve response contract used by dashboard UI."""
    monkeypatch.setattr(api_server, "scan_opportunities_core", lambda **kwargs: [{"id": 1}, {"id": 2}])
    monkeypatch.setattr(api_server, "ManagerAI", lambda db: object())

    client = TestClient(api_server.app)

    scanner_response = client.post("/api/scanner", json={"date": "today"})
    assert scanner_response.status_code == 200
    assert scanner_response.json()["success"] is True
    assert scanner_response.json()["matchesProcessed"] == 2

    monkeypatch.setattr(api_server, "_read_scanner_pid", lambda: 4321)
    monkeypatch.setattr(api_server, "_is_pid_running", lambda pid: True)

    control_status_response = client.get("/api/scanner/control")
    control_start_response = client.post("/api/scanner/control", json={"action": "start"})

    assert control_status_response.status_code == 200
    assert control_status_response.json()["active"] is True
    assert control_status_response.json()["pid"] == 4321

    assert control_start_response.status_code == 200
    assert control_start_response.json()["status"] == "running"
