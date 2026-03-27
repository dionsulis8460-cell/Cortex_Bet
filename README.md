# Cortex Bet

Cortex Bet is a soccer pre-live corner prediction system focused on a simple, testable and auditable architecture. The operational scope is currently prioritized for total full-time over/under corner markets.

## Key Features

- **Official HTTP Backend**: FastAPI server in `src/api/server.py`.
- **Official Frontend**: Next.js app in `web_app`.
- **Canonical Feature Source**: unified feature extraction through `FeatureStore`.
- **Canonical Inference Path**: scanner and prediction flow orchestrated by `ManagerAI` with registry-driven champion resolution.
- **Model Governance**: JSON-backed model registry with policy-based promotion, dry-run and rollback.
- **Operational Health**: model health endpoint and CLI check with calibration/drift-proxy alerts.

## Architecture

- **Frontend (official)**: `web_app` (Next.js).
- **Backend (official)**: `src/api/server.py` (FastAPI).
- **Core Domain**: Python modules under `src/` with contract tests.
- **Operational Automation**: `scripts/`.
- **Research-only Experiments**: `research/`.
- **Artifacts**: generated outputs under `artifacts/` or data/model files, excluded when appropriate by `.gitignore`.

## Getting Started

1. **Setup environment**: use the workspace virtual environment `.venv`.
2. **Train canonical pipeline**:
   - `python scripts/train_model.py`
   - `python src/ml/train_neural.py`
3. **Run scanner**: `python scripts/run_scanner.py --date tomorrow`.
4. **Check model registry**: `python scripts/model_registry_cli.py status`.
5. **Check model health**: `python scripts/check_model_health.py`.

## Documentation

- `README_ML.md`: machine learning and statistical methodology.
- `docs/architecture.md`: current architecture and target principles.
- `docs/decision_log.md`: refactor decisions by phase.
- `docs/refactor_audit.md`: incremental audit trail and residual risks.
