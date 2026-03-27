"""Online model health monitoring and alert generation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

from src.models.model_registry import ModelRegistry


ECE_WARNING_THRESHOLD = 0.10
ECE_CRITICAL_THRESHOLD = 0.15


def _extract_ece_values(file_path: Path) -> List[float]:
    if not file_path.exists():
        return []
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    return [float(x) for x in re.findall(r"ECE\s*=\s*([0-9]*\.?[0-9]+)", text)]


def _mean(values: List[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def get_model_health_snapshot() -> Dict:
    registry = ModelRegistry()
    champion = registry.get_champion()

    ece_v2_path = Path("data/ece_metrics_v2.txt")
    ece_legacy_path = Path("data/ece_metrics.txt")

    ece_v2_values = _extract_ece_values(ece_v2_path)
    ece_legacy_values = _extract_ece_values(ece_legacy_path)

    mean_ece_v2 = _mean(ece_v2_values)
    mean_ece_legacy = _mean(ece_legacy_values)

    alerts: List[Dict] = []

    if mean_ece_v2 is None:
        alerts.append({"severity": "warning", "type": "calibration", "message": "No ECE v2 metrics file found."})
    else:
        if mean_ece_v2 >= ECE_CRITICAL_THRESHOLD:
            alerts.append({
                "severity": "critical",
                "type": "calibration",
                "message": f"ECE v2 mean={mean_ece_v2:.4f} >= {ECE_CRITICAL_THRESHOLD:.2f}",
            })
        elif mean_ece_v2 >= ECE_WARNING_THRESHOLD:
            alerts.append({
                "severity": "warning",
                "type": "calibration",
                "message": f"ECE v2 mean={mean_ece_v2:.4f} >= {ECE_WARNING_THRESHOLD:.2f}",
            })

    # Drift proxy: sudden calibration delta between legacy and v2 reports.
    if mean_ece_v2 is not None and mean_ece_legacy is not None:
        delta = mean_ece_v2 - mean_ece_legacy
        if abs(delta) >= 0.05:
            alerts.append({
                "severity": "warning",
                "type": "drift_proxy",
                "message": f"ECE delta between v2 and legacy reports is {delta:+.4f}",
            })

    champ_metrics = champion.metrics or {}
    if champ_metrics.get("brier_score") is None or champ_metrics.get("log_loss") is None:
        alerts.append({
            "severity": "info",
            "type": "registry",
            "message": "Champion metrics are incomplete (brier/log_loss missing).",
        })

    return {
        "champion": champion.model_id,
        "champion_runtime_adapter": registry.get_runtime_adapter(champion.model_id),
        "ece_v2_mean": mean_ece_v2,
        "ece_legacy_mean": mean_ece_legacy,
        "alert_count": len(alerts),
        "alerts": alerts,
    }
