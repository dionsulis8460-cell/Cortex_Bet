"""Characterization tests for current project entrypoints and runtime contracts."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_ENTRYPOINTS = [
    REPO_ROOT / "start_system.py",
    REPO_ROOT / "scripts" / "system_entrypoint.py",
    REPO_ROOT / "src" / "main.py",
    REPO_ROOT / "src" / "api" / "server.py",
    REPO_ROOT / "scripts" / "run_scanner.py",
    REPO_ROOT / "scripts" / "quick_scan.py",
    REPO_ROOT / "scripts" / "train_model.py",
    REPO_ROOT / "scripts" / "update_results.py",
    REPO_ROOT / "web_app" / "app" / "api" / "predictions" / "route.ts",
]


def test_required_entrypoints_exist_in_repo():
    """Current runtime-critical entrypoints must exist before refactor moves them."""
    missing = [str(p.relative_to(REPO_ROOT)) for p in REQUIRED_ENTRYPOINTS if not p.exists()]
    assert missing == [], f"Missing required entrypoints: {missing}"


def test_start_system_keeps_expected_process_contract():
    """start_system must stay as compatibility wrapper to consolidated orchestration."""
    content = (REPO_ROOT / "start_system.py").read_text(encoding="utf-8")

    assert "run_system_stack" in content


def test_system_entrypoint_keeps_expected_runtime_commands():
    """Consolidated system entrypoint must keep API, scanner, and web start commands."""
    content = (REPO_ROOT / "scripts" / "system_entrypoint.py").read_text(encoding="utf-8")

    assert "src/api/server.py" in content
    assert "scripts/quick_scan.py" in content
    assert 'WEB_COMMAND = ["npm", "run", "dev"]' in content


def test_next_predictions_route_targets_python_http_backend():
    """Next predictions route must proxy to Python HTTP backend endpoint."""
    content = (
        REPO_ROOT / "web_app" / "app" / "api" / "predictions" / "route.ts"
    ).read_text(encoding="utf-8")

    assert "http://127.0.0.1:8000/api/predictions" in content
