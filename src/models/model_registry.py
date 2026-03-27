"""src/models/model_registry.py
==============================
Champion-Challenger Registry with Promotion Policy and Audit Trail.

The registry is backed by ``data/model_registry.json``, which is the single
source of truth for which model is the production champion and which models
are under evaluation as challengers.

Registry Rules
--------------
- There is always **exactly one** CHAMPION at any point in time.
- There can be zero or more CHALLENGERS coexisting.
- A promotion atomically:
    1. Demotes the current champion to RETIRED.
    2. Promotes the challenger to CHAMPION.
    3. Appends two audit events (RETIRED + PROMOTED) — never deleted.
- Promotion is only allowed when ``PromotionPolicy`` criteria are met.

Promotion Policy (default thresholds)
--------------------------------------
- ``brier_improvement_pct`` >= 3.0
    Challenger Brier score must be at most  champion_brier * 0.97.
- ``log_loss_improvement_pct`` >= 3.0
    Challenger log-loss must be at most  champion_log_loss * 0.97.
- ``n_eval_matches`` >= 150
    Minimum evaluation window before any promotion is allowed.

When champion metrics are null (first ever champion), the metric thresholds
are skipped and only ``n_eval_matches`` is enforced.

Usage
-----
    registry = ModelRegistry()
    champion = registry.get_champion()
    eligible, reason = registry.is_eligible_for_promotion("neural_challenger_v1", metrics)
    if eligible:
        registry.promote("neural_challenger_v1", metrics, reason="Brier -4.1% on Q1 2026 holdout")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REGISTRY_PATH = Path("data/model_registry.json")
SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

class ModelRole(str, Enum):
    CHAMPION = "CHAMPION"
    CHALLENGER = "CHALLENGER"
    RETIRED = "RETIRED"


class PromotionPolicy:
    """Thresholds required for a challenger to be eligible for promotion."""

    def __init__(
        self,
        min_brier_improvement_pct: float = 3.0,
        min_log_loss_improvement_pct: float = 3.0,
        min_eval_matches: int = 150,
    ) -> None:
        self.min_brier_improvement_pct = min_brier_improvement_pct
        self.min_log_loss_improvement_pct = min_log_loss_improvement_pct
        self.min_eval_matches = min_eval_matches

    def to_dict(self) -> Dict:
        return {
            "min_brier_improvement_pct": self.min_brier_improvement_pct,
            "min_log_loss_improvement_pct": self.min_log_loss_improvement_pct,
            "min_eval_matches": self.min_eval_matches,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "PromotionPolicy":
        return cls(
            min_brier_improvement_pct=d.get("min_brier_improvement_pct", 3.0),
            min_log_loss_improvement_pct=d.get("min_log_loss_improvement_pct", 3.0),
            min_eval_matches=d.get("min_eval_matches", 150),
        )


class ModelRecord:
    """Snapshot of a single model's state in the registry."""

    def __init__(
        self,
        model_id: str,
        name: str,
        role: ModelRole,
        artifact_paths: List[str],
        registered_at: str,
        metrics: Optional[Dict] = None,
        runtime_adapter: str = "ensemble",
    ) -> None:
        self.model_id = model_id
        self.name = name
        self.role = role
        self.artifact_paths = artifact_paths
        self.registered_at = registered_at
        self.metrics = metrics or {}
        self.runtime_adapter = runtime_adapter

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "role": self.role.value,
            "artifact_paths": self.artifact_paths,
            "registered_at": self.registered_at,
            "metrics": self.metrics,
            "runtime_adapter": self.runtime_adapter,
        }

    @classmethod
    def from_dict(cls, model_id: str, d: Dict) -> "ModelRecord":
        inferred_adapter = _infer_runtime_adapter(model_id=model_id, name=d.get("name", ""))
        return cls(
            model_id=model_id,
            name=d["name"],
            role=ModelRole(d["role"]),
            artifact_paths=d.get("artifact_paths", []),
            registered_at=d["registered_at"],
            metrics=d.get("metrics", {}),
            runtime_adapter=d.get("runtime_adapter", inferred_adapter),
        )

    def __repr__(self) -> str:
        return f"ModelRecord(id={self.model_id!r}, role={self.role.value}, name={self.name!r})"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class ModelRegistry:
    """
    Champion-Challenger Registry.

    Reads and writes ``data/model_registry.json``.  All mutations append to
    ``audit_trail``; entries are never removed.
    """

    def __init__(self, registry_path: Path = REGISTRY_PATH) -> None:
        self._path = Path(registry_path)
        self._state = self._load()

    # ------------------------------------------------------------------
    # Public read interface
    # ------------------------------------------------------------------

    def get_champion(self) -> ModelRecord:
        """Return the current champion.  Raises RuntimeError if none registered."""
        champion_id = self._state.get("current_champion")
        if not champion_id:
            raise RuntimeError("Registry has no champion registered.")
        return ModelRecord.from_dict(champion_id, self._state["models"][champion_id])

    def get_challengers(self) -> List[ModelRecord]:
        """Return all models currently in CHALLENGER role."""
        return [
            ModelRecord.from_dict(mid, data)
            for mid, data in self._state["models"].items()
            if data["role"] == ModelRole.CHALLENGER.value
        ]

    def get_all_models(self) -> List[ModelRecord]:
        """Return every model registered (any role)."""
        return [
            ModelRecord.from_dict(mid, data)
            for mid, data in self._state["models"].items()
        ]

    def get_audit_trail(self) -> List[Dict]:
        """Return an immutable copy of the full audit trail."""
        return list(self._state["audit_trail"])

    def get_policy(self) -> PromotionPolicy:
        """Return the current promotion policy."""
        return PromotionPolicy.from_dict(self._state["promotion_policy"])

    def get_runtime_adapter(self, model_id: str) -> str:
        """Return runtime adapter name for a model_id (e.g. ensemble, neural)."""
        model = self._state["models"].get(model_id)
        if model is None:
            raise ValueError(f"Model '{model_id}' not found in registry.")
        return model.get(
            "runtime_adapter",
            _infer_runtime_adapter(model_id=model_id, name=model.get("name", "")),
        )

    def get_runtime_roles(self) -> Dict[str, str]:
        """
        Return resolved runtime champion/challenger model IDs.

        Strategy:
        - champion_id = current_champion
        - challenger_id = first CHALLENGER model different from champion
        - if no challenger exists, challenger_id falls back to champion_id
        """
        champion = self.get_champion()
        challengers = self.get_challengers()
        challenger_id = next(
            (m.model_id for m in challengers if m.model_id != champion.model_id),
            champion.model_id,
        )
        return {
            "champion_id": champion.model_id,
            "challenger_id": challenger_id,
        }

    # ------------------------------------------------------------------
    # Promotion eligibility check (read-only — does NOT persist anything)
    # ------------------------------------------------------------------

    def is_eligible_for_promotion(
        self,
        challenger_id: str,
        challenger_metrics: Dict,
    ) -> Tuple[bool, str]:
        """
        Check whether a challenger meets the promotion policy criteria.

        Args:
            challenger_id: Registry key of the challenger model.
            challenger_metrics: Dict with keys ``brier_score``, ``log_loss``,
                ``n_eval_matches``.  Unknown keys are ignored.

        Returns:
            ``(True, "ok")`` when eligible.
            ``(False, reason)`` when not eligible, with a human-readable reason.
        """
        policy = self.get_policy()
        models = self._state["models"]

        if challenger_id not in models:
            return False, f"Model '{challenger_id}' not found in registry."

        if models[challenger_id]["role"] != ModelRole.CHALLENGER.value:
            return False, f"Model '{challenger_id}' is not a CHALLENGER."

        # --- Minimum evaluation window ---
        n_eval = challenger_metrics.get("n_eval_matches", 0)
        if n_eval < policy.min_eval_matches:
            return False, (
                f"Insufficient evaluation window: {n_eval} matches evaluated, "
                f"{policy.min_eval_matches} required."
            )

        champion_id = self._state.get("current_champion")
        champion_metrics = models.get(champion_id, {}).get("metrics", {}) if champion_id else {}

        # --- Brier score improvement ---
        champ_brier = champion_metrics.get("brier_score")
        chall_brier = challenger_metrics.get("brier_score")
        if champ_brier is not None and chall_brier is not None:
            threshold = champ_brier * (1.0 - policy.min_brier_improvement_pct / 100.0)
            if chall_brier > threshold:
                return False, (
                    f"Brier score {chall_brier:.4f} does not improve champion "
                    f"{champ_brier:.4f} by >= {policy.min_brier_improvement_pct}% "
                    f"(required <= {threshold:.4f})."
                )

        # --- Log-loss improvement ---
        champ_ll = champion_metrics.get("log_loss")
        chall_ll = challenger_metrics.get("log_loss")
        if champ_ll is not None and chall_ll is not None:
            threshold_ll = champ_ll * (1.0 - policy.min_log_loss_improvement_pct / 100.0)
            if chall_ll > threshold_ll:
                return False, (
                    f"Log-loss {chall_ll:.4f} does not improve champion "
                    f"{champ_ll:.4f} by >= {policy.min_log_loss_improvement_pct}% "
                    f"(required <= {threshold_ll:.4f})."
                )

        return True, "ok"

    # ------------------------------------------------------------------
    # Mutations (all writes go through _save)
    # ------------------------------------------------------------------

    def promote(
        self,
        challenger_id: str,
        metrics: Dict,
        reason: str,
    ) -> None:
        """
        Promote a challenger to champion.

        Atomically:
          1. Retires the current champion.
          2. Promotes the challenger to CHAMPION with the provided metrics.
          3. Appends RETIRED + PROMOTED audit events.
          4. Persists the registry JSON.

        Raises:
            ValueError: If challenger does not meet the promotion policy.
        """
        eligible, why = self.is_eligible_for_promotion(challenger_id, metrics)
        if not eligible:
            raise ValueError(f"Promotion rejected: {why}")

        now = _utcnow()
        models = self._state["models"]

        # 1. Retire current champion
        old_champion_id = self._state["current_champion"]
        models[old_champion_id]["role"] = ModelRole.RETIRED.value
        self._state["audit_trail"].append(
            {
                "event": "RETIRED",
                "model_id": old_champion_id,
                "from_role": ModelRole.CHAMPION.value,
                "timestamp": now,
                "superseded_by": challenger_id,
                "reason": reason,
            }
        )

        # 2. Promote challenger
        models[challenger_id]["role"] = ModelRole.CHAMPION.value
        models[challenger_id]["metrics"] = metrics
        self._state["current_champion"] = challenger_id
        self._state["audit_trail"].append(
            {
                "event": "PROMOTED",
                "model_id": challenger_id,
                "from_role": ModelRole.CHALLENGER.value,
                "to_role": ModelRole.CHAMPION.value,
                "timestamp": now,
                "metrics_at_promotion": metrics,
                "reason": reason,
            }
        )

        self._save()

    def preview_promotion(self, challenger_id: str, metrics: Dict) -> Dict:
        """Return a dry-run summary of a promotion attempt without mutating state."""
        eligible, why = self.is_eligible_for_promotion(challenger_id, metrics)
        current = self.get_champion()
        return {
            "eligible": eligible,
            "reason": why,
            "current_champion": current.model_id,
            "candidate_challenger": challenger_id,
            "candidate_metrics": metrics,
        }

    def rollback_last_promotion(self, reason: str) -> Dict:
        """
        Rollback the latest promotion by restoring the superseded champion.

        Behavior:
        - Finds latest PROMOTED event in audit trail.
        - Uses the related RETIRED event (same promotion cycle) to identify old champion.
        - Restores old champion to CHAMPION and demotes promoted model to CHALLENGER.
        - Appends ROLLED_BACK event to audit trail.
        """
        trail = self._state["audit_trail"]
        promoted_idx = next(
            (i for i in range(len(trail) - 1, -1, -1) if trail[i].get("event") == "PROMOTED"),
            None,
        )
        if promoted_idx is None:
            raise ValueError("No PROMOTED event found to rollback.")

        promoted_event = trail[promoted_idx]
        promoted_model_id = promoted_event["model_id"]

        retired_idx = next(
            (
                i
                for i in range(promoted_idx - 1, -1, -1)
                if trail[i].get("event") == "RETIRED"
                and trail[i].get("superseded_by") == promoted_model_id
            ),
            None,
        )
        if retired_idx is None:
            raise ValueError("Could not find paired RETIRED event for last promotion.")

        retired_event = trail[retired_idx]
        previous_champion_id = retired_event["model_id"]

        if previous_champion_id not in self._state["models"]:
            raise ValueError(f"Previous champion '{previous_champion_id}' not found in models.")
        if promoted_model_id not in self._state["models"]:
            raise ValueError(f"Promoted model '{promoted_model_id}' not found in models.")

        self._state["models"][previous_champion_id]["role"] = ModelRole.CHAMPION.value
        self._state["models"][promoted_model_id]["role"] = ModelRole.CHALLENGER.value
        self._state["current_champion"] = previous_champion_id

        event = {
            "event": "ROLLED_BACK",
            "timestamp": _utcnow(),
            "restored_champion": previous_champion_id,
            "demoted_model": promoted_model_id,
            "reason": reason,
            "source_promoted_event_index": promoted_idx,
            "source_retired_event_index": retired_idx,
        }
        self._state["audit_trail"].append(event)
        self._save()
        return event

    def register(
        self,
        model_id: str,
        name: str,
        role: ModelRole,
        artifact_paths: List[str],
        reason: str,
        metrics: Optional[Dict] = None,
        runtime_adapter: Optional[str] = None,
    ) -> None:
        """
        Add a new model to the registry.

        Raises:
            ValueError: If ``model_id`` already exists, or if registering a CHAMPION
                when one already exists.
        """
        if model_id in self._state["models"]:
            raise ValueError(f"Model '{model_id}' is already registered.")
        if role == ModelRole.CHAMPION and self._state.get("current_champion"):
            raise ValueError(
                "Cannot register a second CHAMPION. "
                "Retire the current champion first via promote()."
            )

        now = _utcnow()
        self._state["models"][model_id] = ModelRecord(
            model_id=model_id,
            name=name,
            role=role,
            artifact_paths=artifact_paths,
            registered_at=now,
            metrics=metrics or {},
            runtime_adapter=runtime_adapter or _infer_runtime_adapter(model_id=model_id, name=name),
        ).to_dict()

        if role == ModelRole.CHAMPION:
            self._state["current_champion"] = model_id

        self._state["audit_trail"].append(
            {
                "event": "REGISTERED",
                "model_id": model_id,
                "role": role.value,
                "timestamp": now,
                "reason": reason,
            }
        )

        self._save()

    def update_metrics(self, model_id: str, metrics: Dict) -> None:
        """
        Persist updated evaluation metrics for a model.

        Appends an EVALUATED event to the audit trail.
        """
        if model_id not in self._state["models"]:
            raise ValueError(f"Model '{model_id}' not found in registry.")
        self._state["models"][model_id]["metrics"] = metrics
        self._state["audit_trail"].append(
            {
                "event": "EVALUATED",
                "model_id": model_id,
                "timestamp": _utcnow(),
                "metrics": metrics,
            }
        )
        self._save()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> Dict:
        if self._path.exists():
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        # Return an empty-but-valid state; caller must bootstrap via register()
        return {
            "schema_version": SCHEMA_VERSION,
            "current_champion": None,
            "promotion_policy": PromotionPolicy().to_dict(),
            "models": {},
            "audit_trail": [],
        }

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_runtime_adapter(model_id: str, name: str) -> str:
    """Infer runtime adapter for backward compatibility when config is missing."""
    token = f"{model_id} {name}".lower()
    if "neural" in token or "mlp" in token:
        return "neural"
    return "ensemble"
