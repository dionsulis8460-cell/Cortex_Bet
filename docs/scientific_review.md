# Scientific Code Review & Technical Audit (V3.0)

**Project:** Cortex_Bet (Sports Analytics Engine)  
**Date:** 05 Feb 2026  
**Reviewer:** Senior Data Scientist (PhD, Agentic AI)  
**Version:** V3.0 (Ensemble Architecture)

---

## 1. Executive Summary

The **Cortex_Bet** system has evolved into a sophisticated **Dual-Engine Architecture**, combining an ensemble of Gradient Boosted Decision Trees (GBDTs) with a Neural Network "Challenger".

The implementation of **Ensemble V3.0** (LightGBM + XGBoost + CatBoost) with **Ridge Stacking** represents a significant leap in maturity, moving from a single-model prototype to a robust, professional-grade prediction system.

However, the audit reveals a **Complexity Gap**: the system runs two parallel AI engines (`ProfessionalPredictor` vs `NeuralChallenger`) with overlapping feature pipelines and unclear hierarchy. While individually strong, their integration is brittle.

**Verdict:** **Scientifically Robust (A-)** but **Architecturally Complex (B)**. The next phase must focus on **Convergence**—binding the two engines into a single, cohesive workflow.

---

## 2. Scientific Strengths (State of the Art Alignment)

### ✅ 2.1. Ensemble Diversity (Dietterich, 2000)
The new **Analyst AI** (`model_v2.py`) implements a textbook "Heterogeneous Ensemble":
*   **LightGBM (Tweedie):** Captures compound poisson distributions.
*   **XGBoost (Poisson):** Robust count modeling.
*   **CatBoost (Poisson):** Excellent handling of categorical features.
*   **Ridge Meta-Learner:** Automatically learns optimal weights via Cross-Validation, avoiding human bias/heuristic weights.

### ✅ 2.2. Distributional Robustness (Karlis & Ntzoufras, 2003)
The `NeuralChallenger` (`neural_engine.py`) correctly identifies **Overdispersion** ($\sigma^2 > \mu$) and dynamically switches:
*   **Equidispersion ($\sigma^2 \approx \mu$):** Uses **Poisson**.
*   **Overdispersion ($\sigma^2 \gg \mu$):** Uses **Negative Binomial**.
This prevents underestimating risk in chaotic games, a common failure mode in sports modeling.

### ✅ 2.3. Temporal Integrity (Forward Chaining)
The use of `TimeSeriesSplit` for cross-validation ensures **Zero Data Leakage**. The model never trains on future games to predict past ones, a critical requirement for valid ROI estimation.

### ✅ 2.4. Probabilistic Calibration via Temperature Scaling
The post-hoc calibration in `focal_calibration.py` (minimizing NLL) ensures that a 70% confidence score aligns with a 70% empirical win rate, essential for the Kelly Criterion and risk management.

---

## 3. Critical Weaknesses & Architectural Debt

### ❌ 3.1. The "Dual-Engine" Confusion
*   **Issue:** The system has two "Brains" that don't speak to each other efficiently:
    *   **Main:** `ProfessionalPredictor` (Ensemble) → Predicts single line (Over/Under).
    *   **Secondary:** `NeuralChallenger` (MLP) → Predicts multi-markets.
*   **Risk:** Users might receive conflicting signals without a clear "Tie-Breaker" logic. The codebase treats them as separate silos.

### ❌ 3.2. Redundant Feature Engineering
*   **Files:** `features_v2.py` is called independently by both engines.
*   **Inefficiency:** The complex 117-feature generation runs **twice** for every match.
*   **Recommendation:** Implement a **Feature Store** (in-memory or Redis) to compute once and serve both models.

### ❌ 3.3. Manual "Manager AI"
*   **Gap:** The "Manager AI" (Selection Strategy) described in documentation serves as the "Best Bet" selector, but its logic is scattered across scripts rather than formalized in a class.
*   **Risk:** "Top 7 Picks" logic might vary between CLI (`unified_scanner.py`) and Web App if not centralized.

---

## 4. Recommendations for "PhD Pro" Evolution

### 🚀 Phase 1: Convergence (Immediate)
1.  **Unified Prediction Object:** Create a standard `PredictionResult` class that contains:
    *   Ensemble Prediction (Main)
    *   Neural Shadow Prediction (Challenger)
    *   Consensus Score (Agreement metric)
2.  **Centralized Manager:** Formalize `ManagerAI` class that takes inputs from both engines and applies the "Filter & Select" logic consistently.

### 🔬 Phase 2: Scientific Upgrade
1.  **Gaussian Processes (GP):** As noted in the Roadmap, implement GPs for uncertainty estimation. The current ensemble gives a point estimate; GPs give a full probability surface, useful for "Safe Bets".
2.  **Bivariate Correction:** Enhance `bivariate_poisson` in `statistical.py` with a rolling covariance window on residuals, improving "Match Openness" modeling.

### 🛠 Phase 3: Infrastructure
1.  **Async API:** Move inference to background workers (Celery/FastAPI BackgroundTasks) to reduce API latency <100ms.
2.  **Data Versioning (DVC):** Version control the SQLite datasets to reproduce past training states perfectly.

---

**Signed:**
*Dr. Antigravity*
*Agentic AI Code Reviewer*
