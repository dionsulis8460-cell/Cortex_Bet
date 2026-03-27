"""tests/contract/test_champion_challenger_registry_contract.py
================================================================
Contract tests for Phase 5 — Champion-Challenger Registry.

These tests enforce the following architectural invariants:

1. The registry JSON exists and is valid.
2. There is exactly one champion at all times.
3. Champion artifact paths are declared in the registry.
4. A challenger cannot be promoted without meeting the promotion policy.
5. A successful promotion writes RETIRED + PROMOTED events to the audit trail.
6. The audit trail is append-only per promotion cycle (length grows monotonically).
7. ``update_metrics`` appends an EVALUATED event.

Tests are deterministic and require no DB, no network, no model files.
Mutations run against a temporary copy of the registry (tmp_path fixture).
"""

import copy
import json
import pytest
from pathlib import Path

from src.models.model_registry import (
    ModelRegistry,
    ModelRole,
    PromotionPolicy,
    REGISTRY_PATH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_registry(tmp_path: Path, state_override: dict = None) -> ModelRegistry:
    """Create a ModelRegistry backed by a temp file seeded from the real bootstrap."""
    real_state = json.loads(REGISTRY_PATH.read_text("utf-8"))
    state = copy.deepcopy(real_state)
    if state_override:
        state.update(state_override)
    tmp_file = tmp_path / "model_registry.json"
    tmp_file.write_text(json.dumps(state), encoding="utf-8")
    return ModelRegistry(registry_path=tmp_file)


# ---------------------------------------------------------------------------
# Static registry contract (no mutation)
# ---------------------------------------------------------------------------

class TestRegistryBootstrapContract:
    """The bootstrap state of data/model_registry.json satisfies invariants."""

    def test_registry_file_exists(self):
        assert REGISTRY_PATH.exists(), (
            f"Registry file missing: {REGISTRY_PATH}. "
            "Run bootstrap or check git history."
        )

    def test_registry_is_valid_json(self):
        content = REGISTRY_PATH.read_text("utf-8")
        state = json.loads(content)
        assert isinstance(state, dict)
        assert "schema_version" in state
        assert "current_champion" in state
        assert "models" in state
        assert "audit_trail" in state
        assert "promotion_policy" in state

    def test_registry_has_exactly_one_champion(self):
        registry = ModelRegistry()
        champion = registry.get_champion()
        all_models = registry.get_all_models()
        champions = [m for m in all_models if m.role == ModelRole.CHAMPION]
        assert len(champions) == 1, (
            f"Expected 1 CHAMPION, found {len(champions)}: {[m.model_id for m in champions]}"
        )
        assert champions[0].model_id == champion.model_id

    def test_champion_has_declared_artifact_paths(self):
        registry = ModelRegistry()
        champion = registry.get_champion()
        assert len(champion.artifact_paths) > 0, (
            f"Champion '{champion.model_id}' has no artifact_paths declared in registry."
        )

    def test_challenger_is_registered(self):
        registry = ModelRegistry()
        challengers = registry.get_challengers()
        assert len(challengers) >= 1, (
            "At least one CHALLENGER must be registered. "
            "NeuralChallenger (neural_challenger_v1) should be present."
        )

    def test_audit_trail_has_bootstrap_events(self):
        registry = ModelRegistry()
        trail = registry.get_audit_trail()
        assert len(trail) >= 2, "Audit trail must contain at least the two bootstrap REGISTERED events."
        event_types = {e["event"] for e in trail}
        assert "REGISTERED" in event_types

    def test_promotion_policy_thresholds_are_positive(self):
        registry = ModelRegistry()
        policy = registry.get_policy()
        assert policy.min_brier_improvement_pct > 0
        assert policy.min_log_loss_improvement_pct > 0
        assert policy.min_eval_matches > 0


# ---------------------------------------------------------------------------
# Promotion policy enforcement
# ---------------------------------------------------------------------------

class TestPromotionPolicyContract:
    """is_eligible_for_promotion enforces the policy before any write."""

    def test_rejects_when_n_eval_matches_below_threshold(self, tmp_path):
        registry = _make_registry(tmp_path)
        metrics = {"brier_score": 0.10, "log_loss": 0.30, "n_eval_matches": 50}
        eligible, reason = registry.is_eligible_for_promotion("neural_challenger_v1", metrics)
        assert not eligible
        assert "Insufficient evaluation window" in reason

    def test_rejects_unknown_model_id(self, tmp_path):
        registry = _make_registry(tmp_path)
        metrics = {"brier_score": 0.10, "log_loss": 0.30, "n_eval_matches": 200}
        eligible, reason = registry.is_eligible_for_promotion("nonexistent_model", metrics)
        assert not eligible
        assert "not found" in reason

    def test_rejects_when_challenger_brier_not_better_enough(self, tmp_path):
        # Set champion metrics so the threshold test triggers
        state = json.loads(REGISTRY_PATH.read_text("utf-8"))
        state["models"]["ensemble_v1"]["metrics"] = {
            "brier_score": 0.20,
            "log_loss": 0.50,
            "n_eval_matches": 300,
        }
        registry = _make_registry(tmp_path, state_override=state)
        # challenger Brier only 1% better — below the 3% threshold
        metrics = {"brier_score": 0.198, "log_loss": 0.48, "n_eval_matches": 200}
        eligible, reason = registry.is_eligible_for_promotion("neural_challenger_v1", metrics)
        assert not eligible
        assert "Brier" in reason

    def test_rejects_when_challenger_log_loss_not_better_enough(self, tmp_path):
        state = json.loads(REGISTRY_PATH.read_text("utf-8"))
        state["models"]["ensemble_v1"]["metrics"] = {
            "brier_score": 0.20,
            "log_loss": 0.50,
            "n_eval_matches": 300,
        }
        registry = _make_registry(tmp_path, state_override=state)
        # Brier passes (5% better), log-loss only 1% better
        metrics = {"brier_score": 0.190, "log_loss": 0.495, "n_eval_matches": 200}
        eligible, reason = registry.is_eligible_for_promotion("neural_challenger_v1", metrics)
        assert not eligible
        assert "Log-loss" in reason

    def test_eligible_when_all_criteria_met(self, tmp_path):
        state = json.loads(REGISTRY_PATH.read_text("utf-8"))
        state["models"]["ensemble_v1"]["metrics"] = {
            "brier_score": 0.20,
            "log_loss": 0.50,
            "n_eval_matches": 300,
        }
        registry = _make_registry(tmp_path, state_override=state)
        # Both metrics improve by > 3%, eval window sufficient
        metrics = {"brier_score": 0.190, "log_loss": 0.480, "n_eval_matches": 200}
        eligible, reason = registry.is_eligible_for_promotion("neural_challenger_v1", metrics)
        assert eligible, f"Expected eligible, got reason: {reason}"
        assert reason == "ok"

    def test_eligible_when_champion_metrics_are_null(self, tmp_path):
        """When champion has no metrics yet, only n_eval_matches is enforced."""
        registry = _make_registry(tmp_path)
        # champion metrics are null in the bootstrap JSON
        metrics = {"brier_score": 0.15, "log_loss": 0.40, "n_eval_matches": 200}
        eligible, reason = registry.is_eligible_for_promotion("neural_challenger_v1", metrics)
        assert eligible, f"Expected eligible (null champion metrics), got: {reason}"


# ---------------------------------------------------------------------------
# Promotion mutation and audit trail
# ---------------------------------------------------------------------------

class TestPromotionAuditTrailContract:
    """promote() writes the correct audit events and updates roles atomically."""

    def _valid_metrics(self):
        return {"brier_score": 0.15, "log_loss": 0.40, "n_eval_matches": 200}

    def test_promote_raises_if_policy_not_met(self, tmp_path):
        registry = _make_registry(tmp_path)
        with pytest.raises(ValueError, match="Promotion rejected"):
            registry.promote(
                "neural_challenger_v1",
                metrics={"brier_score": 0.10, "log_loss": 0.30, "n_eval_matches": 5},
                reason="Should be rejected",
            )

    def test_promote_changes_champion(self, tmp_path):
        registry = _make_registry(tmp_path)
        registry.promote(
            "neural_challenger_v1",
            metrics=self._valid_metrics(),
            reason="Test promotion — metrics meet threshold",
        )
        new_champion = registry.get_champion()
        assert new_champion.model_id == "neural_challenger_v1"
        assert new_champion.role == ModelRole.CHAMPION

    def test_promote_retires_old_champion(self, tmp_path):
        registry = _make_registry(tmp_path)
        registry.promote(
            "neural_challenger_v1",
            metrics=self._valid_metrics(),
            reason="Test promotion",
        )
        all_models = registry.get_all_models()
        old = next(m for m in all_models if m.model_id == "ensemble_v1")
        assert old.role == ModelRole.RETIRED

    def test_promote_appends_retired_event(self, tmp_path):
        registry = _make_registry(tmp_path)
        before = len(registry.get_audit_trail())
        registry.promote(
            "neural_challenger_v1",
            metrics=self._valid_metrics(),
            reason="Test promotion",
        )
        trail = registry.get_audit_trail()
        assert len(trail) == before + 2  # one RETIRED + one PROMOTED
        events = [e["event"] for e in trail[before:]]
        assert "RETIRED" in events
        assert "PROMOTED" in events

    def test_promote_records_metrics_at_promotion(self, tmp_path):
        registry = _make_registry(tmp_path)
        metrics = self._valid_metrics()
        registry.promote("neural_challenger_v1", metrics=metrics, reason="Test")
        trail = registry.get_audit_trail()
        promoted_event = next(e for e in trail if e["event"] == "PROMOTED")
        assert promoted_event["metrics_at_promotion"] == metrics

    def test_promote_persists_to_json(self, tmp_path):
        """Champion change must survive a round-trip load."""
        registry = _make_registry(tmp_path)
        registry.promote(
            "neural_challenger_v1",
            metrics=self._valid_metrics(),
            reason="Persistence test",
        )
        # Re-load from the same file
        registry2 = ModelRegistry(registry_path=registry._path)
        assert registry2.get_champion().model_id == "neural_challenger_v1"

    def test_audit_trail_is_append_only(self, tmp_path):
        """Audit trail length must only grow — no events are ever removed."""
        registry = _make_registry(tmp_path)
        original_trail = registry.get_audit_trail()
        original_len = len(original_trail)

        registry.promote(
            "neural_challenger_v1",
            metrics=self._valid_metrics(),
            reason="Append-only check",
        )
        new_trail = registry.get_audit_trail()
        assert len(new_trail) > original_len
        # Original prefix must be intact
        for i, event in enumerate(original_trail):
            assert new_trail[i] == event


# ---------------------------------------------------------------------------
# update_metrics
# ---------------------------------------------------------------------------

class TestUpdateMetricsContract:

    def test_update_metrics_appends_evaluated_event(self, tmp_path):
        registry = _make_registry(tmp_path)
        before = len(registry.get_audit_trail())
        registry.update_metrics(
            "neural_challenger_v1",
            {"brier_score": 0.18, "log_loss": 0.45, "n_eval_matches": 180},
        )
        trail = registry.get_audit_trail()
        assert len(trail) == before + 1
        assert trail[-1]["event"] == "EVALUATED"
        assert trail[-1]["model_id"] == "neural_challenger_v1"

    def test_update_metrics_raises_for_unknown_model(self, tmp_path):
        registry = _make_registry(tmp_path)
        with pytest.raises(ValueError, match="not found"):
            registry.update_metrics("ghost_model", {"brier_score": 0.10})
