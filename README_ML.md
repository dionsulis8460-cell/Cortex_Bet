# Cortex Bet: ML and Statistical Engine

This document explains the inner workings of the machine learning and statistical layers that drive Cortex Bet's predictions.

## 1. Production Modeling Scope

The production scope is currently pre-live total full-time over/under corner prediction. Runtime selection uses a model registry with one active champion and formal promotion policy.

- Current champion: `neural_challenger_v1` (runtime adapter: `neural`)
- Previous champion (retired): `ensemble_v1` (runtime adapter: `ensemble`)
- Challenger policy: candidates should be maintained in `research/` and only promoted after reproducible evaluation.

### Canonical Feature Engineering

Feature generation is centralized in `FeatureStore` for both training and inference to avoid train/serve skew.

The pipeline processes temporal and contextual features, including:

- **EMA Trends**: Exponential Moving Averages of corners (last 5, 10, 20 games).
- **Home/Away Specialization**: Separate metrics for team performance based on venue.
- **Defensive Resistance**: Corners conceded by opponents.
- **Momentum Metrics**: Real-time pressure based on dangerous attacks and shots.

### Calibration

Model confidence is calibrated with a production calibrator so that predicted probabilities track empirical frequencies.

## 2. Statistical Layer

For each match, the statistical layer combines model outputs with historical context and distributional assumptions.

1. **Hybrid Lambda (λ)**: We combine the ML prediction (70% weight) with historical statistical averages (30% weight) to determine the "Expected Rate" of corners.
2. **Distribution Selection**:
   - **Poisson**: Used when variance equals mean (standard games).
   - **Negative Binomial**: Used when variance > mean (high volatility games).
3. **Simulation**: We run **10,000 simulations** of the match to build a probability distribution.
4. **Fair Odds Calculation**: `Fair Odd = 1 / Probability`.

## 3. Evaluation Protocol

Evaluation must follow temporal splits and include probabilistic quality, calibration and corner expectation error.

Primary metrics:

- **RPS (Ranked Probability Score)**: Measures how close the predicted probability was to the actual outcome.
- **ECE (Expected Calibration Error)**: Measures the gap between predicted confidence and observed accuracy.
- **MAE (Mean Absolute Error)**: Average difference between predicted corner count and real outcome.

Secondary metrics:

- ROI / yield / drawdown can be tracked, but never used as the only model selection criterion.

Minimum reporting cuts:

- By league
- By season

## 4. Serving and Governance

- Official backend: FastAPI in `src/api/server.py`.
- Official frontend: Next.js in `web_app`.
- Canonical training entrypoint: `scripts/train_model.py`.
- Canonical neural auxiliary training: `src/ml/train_neural.py`.
- Canonical inference entrypoint: `scripts/run_scanner.py`.
- Registry operations: `scripts/model_registry_cli.py`.
- Health monitoring: `scripts/check_model_health.py` and `/api/model-health`.

## 5. UTC and Regional Settings

The system is optimized for **UTC-3 (Brasil)**. All performance metrics and scanner logic explicitly handle the -3 hour offset to ensure games from late-night Brazil don't leak into the wrong calendar day.
