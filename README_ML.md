# Cortex Bet: ML and Statistical Engine

This document explains the machine learning, statistical and calibration layers that drive Cortex Bet's predictions, and how to train the system for production use.

---

## 1. Production Modeling Scope

The system predicts pre-live corners across **9 derived markets**, all generated from a single joint distribution:

```
Latent vector:  Y = [home_1H, away_1H, home_2H, away_2H]

Derived markets (coherent by construction):
  FT total  = home_1H + away_1H + home_2H + away_2H
  1T total  = home_1H + away_1H
  2T total  = home_2H + away_2H
  FT home   = home_1H + home_2H
  FT away   = away_1H + away_2H
  1T home   = home_1H
  1T away   = away_1H
  2T home   = home_2H
  2T away   = away_2H
```

This guarantees that FT = 1H + 2H for every team and total. No market is derived by naive subtraction or heuristic scaling.

### Model Architecture

- **Champion (production)**: `JointCornersModel` — 4 independent LightGBM Poisson regressors, one per component of Y. Located in `src/ml/joint_model.py`.
- **Challenger (shadow only)**: `NeuralMultiHead` — PyTorch multi-head network with 4 Poisson output heads. Located in `src/models/neural_multihead.py`. Logs predictions to `data/shadow_logs/challenger_shadow.jsonl` but **never** contributes to the final output.
- **Market Translator**: `MarketTranslator` in `src/ml/market_translator.py` — takes the 4 lambda values from the champion, runs 20,000 bivariate Poisson Monte Carlo simulations, and produces probability distributions for all 9 markets.
- **Per-Market Calibrators**: `PerMarketCalibrator` in `src/ml/per_market_calibrator.py` — 9 isotonic regression calibrators (one per market family). Uses hierarchical pooling when sample size < 100.

### Canonical Feature Engineering

Feature generation is centralized in `FeatureStore` for both training and inference to avoid train/serve skew.

The pipeline processes temporal and contextual features, including:

- **EMA Trends**: Exponential Moving Averages of corners (last 5, 10, 20 games).
- **Home/Away Specialization**: Separate metrics for team performance based on venue.
- **Defensive Resistance**: Corners conceded by opponents.
- **Momentum Metrics**: Real-time pressure based on dangerous attacks and shots.
- **Joint Targets**: `create_joint_targets()` in `src/ml/features_v2.py` extracts the 4-component target vector from match data.

---

## 2. How to Train the AI for Production

Training the joint multimercado model is **required** for the scientific Top 7 to work. Without it, the scanner falls back to legacy single-market predictions.

### Step-by-step

```bash
# 1. Activate the virtual environment
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # Linux/Mac

# 2. Train the joint multimercado model (recommended method)
#    Via CLI interactive menu:
python src/main.py
#    Select option 8: "Train Joint Multimercado Model"
#
#    Or via the legacy script (trains single-market champion only):
python scripts/train_model.py

# 3. After training, run the scanner
python scripts/run_scanner.py --date tomorrow

# 4. Start the dashboard to see results
python start_system.py
```

### What happens during joint training (option 8)

The `JointTrainer` pipeline (`src/training/joint_trainer.py`) executes:

1. **Feature extraction**: loads all matches from the database, calls `FeatureStore` and `create_joint_targets()` to build the feature matrix with 4-component targets.
2. **Walk-forward temporal validation**: splits data chronologically into expanding windows. Each fold trains on past data only, predicts the next window, and collects out-of-fold (OOF) probabilities. No future leakage.
3. **Model fitting**: trains 4 LightGBM Poisson regressors (one per lambda component) on the full training set.
4. **Market translation**: the `MarketTranslator` converts the 4 lambdas into 9 market probability distributions via Monte Carlo simulation.
5. **Per-family calibration**: fits 9 isotonic regression calibrators on the OOF predictions, grouped by market family. Small families use hierarchical pooling.
6. **Scientific evaluation**: `SciEvaluator` computes Brier score, log loss, RPS, ECE, MAE, sharpness and coverage — reported separately per market family.
7. **Model registration**: saves the trained model, calibrators and evaluation report to the model registry.

### What happens during the scanner

After training, when `run_scanner.py` executes:

1. Each match goes through `ManagerAI.predict_match()` — champion only (no blend).
2. The `ScientificSelectionStrategy` computes a scientific score for each prediction:
   ```
   score = calibrated_prob * (1 - uncertainty_penalty) * family_stability
   ```
3. Top 7 picks are selected by this score — ranked by calibrated probability, penalized by uncertainty, weighted by stability per market family.
4. Each prediction carries `scientific_meta`: score, expected corners, uncertainty (sigma), 90% confidence interval, calibrated probability, and stability.
5. The dashboard displays all of this in the match cards and Top 7 panel.

### Training schedule recommendation

- **Full retrain**: after each new season starts or every 2-3 months.
- **Incremental update**: after accumulating 200+ new resolved matches.
- **Validation**: always check `scripts/check_model_health.py` after training.

---

## 3. Statistical Layer

For each match, the statistical layer works through the joint distribution:

1. **Joint Lambda Prediction**: the champion predicts 4 lambda values (home_1H, away_1H, home_2H, away_2H).
2. **Bivariate Poisson Simulation**: `MarketTranslator` runs 20,000 Monte Carlo draws from independent Poisson distributions per component. Overdispersion is captured naturally by the variance in the lambda predictions across the feature space.
3. **9-Market Derivation**: all markets are computed by aggregating the simulated components. Coherence is guaranteed by construction.
4. **Per-Family Calibration**: each market family has its own calibrator. The system does not assume calibration — it measures and corrects it.

### Policy without real odds

The system does **not** have a historical odds feed. Therefore:

- Output is interpreted as **calibrated probability + uncertainty**, not as proven value bet.
- The user can manually insert odds in the interface for point comparison with the model's fair probability.
- Without user-provided odds, the system ranks by scientific score only — never claims which market is "economically best".

---

## 4. Top 7 Scientific Ranking

The Top 7 is the primary output for the user. It presents the 7 best opportunities across all scanned matches, ranked scientifically.

### Ranking formula

```
scientific_score = calibrated_prob * (1 - uncertainty_penalty) * family_stability
```

Where:
- `calibrated_prob`: post-calibration probability for the specific market line.
- `uncertainty_penalty`: normalized standard deviation of the predicted distribution. Higher uncertainty reduces the score.
- `family_stability`: how consistent the model is for that market family across leagues and time windows. Range 0-1.

### What the user sees per pick

| Field | Description |
|---|---|
| Scientific Score | Composite ranking value (0-1) |
| E[Corners] | Expected corner count for this market |
| Uncertainty (σ) | Standard deviation of the prediction |
| CI 90% | 90% confidence interval for corner count |
| P(calibrated) | Calibrated probability for the over/under line |
| Stability | Model reliability for this market family |

The Top 7 gives the user **options** — it is not binary. The user chooses which picks to bet on with real money based on the scientific data displayed.

---

## 5. Evaluation Protocol

Evaluation follows strict temporal splits (walk-forward) and reports per market family.

### Primary metrics

- **Brier Score**: measures calibration quality of probability predictions.
- **Log Loss**: penalizes confident wrong predictions severely.
- **RPS (Ranked Probability Score)**: measures full distribution quality against outcomes.
- **ECE (Expected Calibration Error)**: gap between predicted confidence and observed frequency.

### Secondary metrics

- **MAE**: average error in expected corner count.
- **Sharpness**: concentration of predicted distributions (sharper = more informative).
- **Coverage**: proportion of outcomes within the predicted confidence interval.
- **Stability**: consistency of metrics across leagues and time periods.
- **Hit rate**: tracked as auxiliary only, never used for model selection.

### Minimum reporting cuts

- By league
- By season
- By market family (FT total, 1T total, 2T total, FT home, FT away, 1T home, 1T away, 2T home, 2T away)

---

## 6. Champion Promotion Policy

The challenger (neural multi-head) can only replace the champion if:

1. It beats the champion on walk-forward evaluation across all primary metrics.
2. Calibration improves or stays stable per market family.
3. No material degradation in any individual family (global gain with 1T/2T regression is not automatic promotion).
4. Results are reproducible across at least 2 evaluation runs.

Promotion is executed via `scripts/model_registry_cli.py promote`.

---

## 7. Serving and Governance

- Official backend: FastAPI in `src/api/server.py`.
- Official frontend: Next.js in `web_app`.
- Canonical joint training: CLI option 8 in `src/main.py` → `JointTrainer`.
- Legacy single-market training: `scripts/train_model.py`.
- Neural challenger training: `src/ml/train_neural.py` (shadow only).
- Canonical inference: `scripts/run_scanner.py`.
- Registry operations: `scripts/model_registry_cli.py`.
- Health monitoring: `scripts/check_model_health.py` and `/api/model-health`.
- Governance rules: `docs/governance.md`.

---

## 8. UTC and Regional Settings

The system is optimized for **UTC-3 (Brasil)**. All performance metrics and scanner logic explicitly handle the -3 hour offset to ensure games from late-night Brazil don't leak into the wrong calendar day.
