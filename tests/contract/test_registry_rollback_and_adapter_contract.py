"""Contract tests for registry rollback and runtime adapter strategy."""

import copy
import json
from pathlib import Path

import pytest

from src.models.model_registry import ModelRegistry, REGISTRY_PATH


REPO_ROOT = Path(__file__).resolve().parents[2]


def _tmp_registry(tmp_path: Path) -> ModelRegistry:
    state = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    file_path = tmp_path / "registry.json"
    file_path.write_text(json.dumps(copy.deepcopy(state)), encoding="utf-8")
    return ModelRegistry(registry_path=file_path)


def test_preview_promotion_dry_run_is_read_only(tmp_path):
    registry = _tmp_registry(tmp_path)
    before = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))

    preview = registry.preview_promotion(
        "neural_challenger_v1",
        {"brier_score": 0.12, "log_loss": 0.20, "n_eval_matches": 200},
    )

    after = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert "eligible" in preview
    assert before == after


def test_rollback_last_promotion_restores_previous_champion(tmp_path):
    registry = _tmp_registry(tmp_path)

    metrics = {"brier_score": 0.12, "log_loss": 0.20, "n_eval_matches": 200}
    registry.promote("neural_challenger_v1", metrics=metrics, reason="promotion test")
    assert registry.get_champion().model_id == "neural_challenger_v1"

    event = registry.rollback_last_promotion(reason="rollback test")
    assert event["event"] == "ROLLED_BACK"
    assert registry.get_champion().model_id == "ensemble_v1"


def test_runtime_adapter_is_available_for_known_models(tmp_path):
    registry = _tmp_registry(tmp_path)
    assert registry.get_runtime_adapter("ensemble_v1") == "ensemble"
    assert registry.get_runtime_adapter("neural_challenger_v1") == "neural"


def test_runtime_roles_returns_champion_and_challenger(tmp_path):
    registry = _tmp_registry(tmp_path)
    roles = registry.get_runtime_roles()
    assert roles["champion_id"] == "ensemble_v1"
    assert roles["challenger_id"] == "neural_challenger_v1"


def test_cli_script_exists_for_registry_ops():
    assert (REPO_ROOT / "scripts" / "model_registry_cli.py").exists()
