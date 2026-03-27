"""CLI utilities for ModelRegistry operations.

Supports:
- status
- promote (with --dry-run)
- rollback
- update-metrics
- register
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.model_registry import ModelRegistry, ModelRole


def _print_json(payload: Dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _parse_metrics(args: argparse.Namespace) -> Dict:
    return {
        "brier_score": args.brier_score,
        "log_loss": args.log_loss,
        "n_eval_matches": args.n_eval_matches,
    }


def cmd_status(registry: ModelRegistry, args: argparse.Namespace) -> int:
    champion = registry.get_champion()
    challengers = registry.get_challengers()
    payload = {
        "current_champion": champion.model_id,
        "current_champion_adapter": registry.get_runtime_adapter(champion.model_id),
        "challengers": [m.model_id for m in challengers],
        "audit_trail_size": len(registry.get_audit_trail()),
    }
    _print_json(payload)
    return 0


def cmd_promote(registry: ModelRegistry, args: argparse.Namespace) -> int:
    metrics = _parse_metrics(args)
    if args.dry_run:
        preview = registry.preview_promotion(args.challenger_id, metrics)
        _print_json({"mode": "dry-run", **preview})
        return 0 if preview["eligible"] else 2

    registry.promote(args.challenger_id, metrics=metrics, reason=args.reason)
    _print_json({
        "mode": "apply",
        "status": "promoted",
        "new_champion": registry.get_champion().model_id,
    })
    return 0


def cmd_rollback(registry: ModelRegistry, args: argparse.Namespace) -> int:
    event = registry.rollback_last_promotion(reason=args.reason)
    _print_json({
        "status": "rolled_back",
        "restored_champion": event["restored_champion"],
        "demoted_model": event["demoted_model"],
    })
    return 0


def cmd_update_metrics(registry: ModelRegistry, args: argparse.Namespace) -> int:
    registry.update_metrics(args.model_id, _parse_metrics(args))
    _print_json({"status": "metrics_updated", "model_id": args.model_id})
    return 0


def cmd_register(registry: ModelRegistry, args: argparse.Namespace) -> int:
    role = ModelRole(args.role)
    artifact_paths: List[str] = args.artifact_path or []
    registry.register(
        model_id=args.model_id,
        name=args.name,
        role=role,
        artifact_paths=artifact_paths,
        reason=args.reason,
        metrics=_parse_metrics(args),
        runtime_adapter=args.runtime_adapter,
    )
    _print_json({"status": "registered", "model_id": args.model_id, "role": role.value})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Model registry CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Show champion/challenger status")
    p_status.set_defaults(func=cmd_status)

    p_promote = sub.add_parser("promote", help="Promote challenger")
    p_promote.add_argument("--challenger-id", required=True)
    p_promote.add_argument("--brier-score", type=float, required=True)
    p_promote.add_argument("--log-loss", type=float, required=True)
    p_promote.add_argument("--n-eval-matches", type=int, required=True)
    p_promote.add_argument("--reason", required=True)
    p_promote.add_argument("--dry-run", action="store_true")
    p_promote.set_defaults(func=cmd_promote)

    p_rollback = sub.add_parser("rollback", help="Rollback last promotion")
    p_rollback.add_argument("--reason", required=True)
    p_rollback.set_defaults(func=cmd_rollback)

    p_metrics = sub.add_parser("update-metrics", help="Update model metrics")
    p_metrics.add_argument("--model-id", required=True)
    p_metrics.add_argument("--brier-score", type=float, required=True)
    p_metrics.add_argument("--log-loss", type=float, required=True)
    p_metrics.add_argument("--n-eval-matches", type=int, required=True)
    p_metrics.set_defaults(func=cmd_update_metrics)

    p_register = sub.add_parser("register", help="Register model without code changes")
    p_register.add_argument("--model-id", required=True)
    p_register.add_argument("--name", required=True)
    p_register.add_argument("--role", required=True, choices=[r.value for r in ModelRole])
    p_register.add_argument("--artifact-path", action="append")
    p_register.add_argument("--runtime-adapter", choices=["ensemble", "neural"], default=None)
    p_register.add_argument("--reason", required=True)
    p_register.add_argument("--brier-score", type=float, default=None)
    p_register.add_argument("--log-loss", type=float, default=None)
    p_register.add_argument("--n-eval-matches", type=int, default=None)
    p_register.set_defaults(func=cmd_register)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    registry = ModelRegistry()
    return args.func(registry, args)


if __name__ == "__main__":
    raise SystemExit(main())
