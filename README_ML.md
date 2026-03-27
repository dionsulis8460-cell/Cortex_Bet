# Cortex Bet: AI & Statistical Engine (V6 Pro)

This document explains the inner workings of the machine learning and statistical layers that drive Cortex Bet's predictions.

## 1. The ML Model: AI V6 Pro (V2.1 Calibrated)

The core predictor is a Gradient Boosted model (XGBoost/LightGBM) optimized for corner prediction.

### Feature Engineering

We process over 140 features for each match, including:

- **EMA Trends**: Exponential Moving Averages of corners (last 5, 10, 20 games).
- **Home/Away Specialization**: Separate metrics for team performance based on venue.
- **Defensive Resistance**: Corners conceded by opponents.
- **Momentum Metrics**: Real-time pressure based on dangerous attacks and shots.

### Calibration (Temperature Scaling)

Unlike standard models that provide "raw scores", V6 Pro uses a **Multi-Threshold Temperature Scaling** calibrator. This ensures that a confidence score of 70% actually results in a win 70% of the time, making it reliable for bankroll management.

## 2. Statistical Engine: Monte Carlo Simulation

For every match, we run a hybrid statistical analysis:

1. **Hybrid Lambda (λ)**: We combine the ML prediction (70% weight) with historical statistical averages (30% weight) to determine the "Expected Rate" of corners.
2. **Distribution Selection**:
   - **Poisson**: Used when variance equals mean (standard games).
   - **Negative Binomial**: Used when variance > mean (high volatility games).
3. **Simulation**: We run **10,000 simulations** of the match to build a probability distribution.
4. **Fair Odas Calculation**: `Fair Odd = 1 / Probability`.

## 3. Evaluation Metrics

We use three primary metrics to monitor AI health:

- **Win Rate**: Percentage of correct predictions.
- **RPS (Ranked Probability Score)**: Measures how close the predicted probability was to the actual outcome.
- **ECE (Expected Calibration Error)**: Measures the gap between predicted confidence and observed accuracy.
- **MAE (Mean Absolute Error)**: Average difference between predicted corner count and real outcome.

## 4. UTC & Regional Settings

The system is optimized for **UTC-3 (Brasil)**. All performance metrics and scanner logic explicitly handle the -3 hour offset to ensure games from late-night Brazil don't leak into the wrong calendar day.
