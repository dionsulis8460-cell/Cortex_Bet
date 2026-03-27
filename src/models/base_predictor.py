"""
src/models/base_predictor.py
============================
Abstract base class defining the common interface for all predictors in
Cortex_Bet.

Every model (Ensemble, Neural, future Dixon-Coles, etc.) must implement:
  - predict_lambda()  → expected corner counts (λ_home, λ_away)
  - predict_distribution() → full distributional parameters for the statistical engine

This enforces a contract that allows ManagerAI to treat all predictors
polymorphically, and makes it trivial to swap, add, or benchmark models.

Design Pattern: Template Method / Strategy
References:
  - Gamma et al. (1994) — "Design Patterns: Elements of Reusable OO Software"
  - Sculley et al. (2015) — "Hidden Technical Debt in ML Systems" (NIPS):
    standardised interfaces prevent "glue code" debt in ML pipelines.
"""

from __future__ import annotations

import abc
from typing import Dict, Tuple

import pandas as pd
import numpy as np


class BasePredictor(abc.ABC):
    """
    Abstract base class for all corner-prediction models.

    Subclasses MUST implement ``predict_lambda`` and ``predict_distribution``.
    They MAY override ``is_ready`` if they have non-trivial readiness checks
    (e.g. model file not found on disk).

    Concrete implementations:
        - ``ProfessionalPredictor`` (src/ml/model_v2.py)
            Stacking ensemble: LightGBM + XGBoost + CatBoost + Ridge meta-learner.
        - ``NeuralChallenger`` (src/analysis/neural_engine.py)
            MLPRegressor predicting (λ_home, λ_away) directly (multi-output).
    """

    # ------------------------------------------------------------------
    # Required interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def predict_lambda(
        self, features: pd.DataFrame
    ) -> Tuple[float, float]:
        """
        Predict expected corner counts for a single match.

        Args:
            features: Single-row DataFrame produced by
                      ``FeatureStore.build_match_features()``.

        Returns:
            Tuple ``(lambda_home, lambda_away)`` — the Poisson rate parameters
            for each team.  Both values must be positive finite floats.

        Notes:
            The *total* expected corners is simply ``lambda_home + lambda_away``.
            Implementations should clamp outputs to a plausible range
            (e.g. 2.0 – 12.0 per team) to avoid degenerate distributions.
        """
        ...

    @abc.abstractmethod
    def predict_distribution(
        self, features: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Return full distributional parameters for use by the statistical engine.

        Args:
            features: Single-row DataFrame produced by
                      ``FeatureStore.build_match_features()``.

        Returns:
            Dictionary with **at least** these keys:

            .. code-block:: python

                {
                    "lambda_home":     float,  # Poisson rate — home team
                    "lambda_away":     float,  # Poisson rate — away team
                    "variance_factor": float,  # Overdispersion ratio (≥ 1.0)
                }

            ``variance_factor = 1.0`` means Poisson equidispersion.
            ``variance_factor > 1.0`` means Negative-Binomial territory
            (overdispersed), which is common in football corner data.

        Notes:
            The statistical engine (``StatisticalAnalyzer``) reads these values
            to parameterise its Monte Carlo simulation, so the dictionary must
            be well-defined under all circumstances (no NaN, no Inf).
        """
        ...

    # ------------------------------------------------------------------
    # Optional hooks with sensible defaults
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """
        Returns ``True`` if the model is loaded and ready to make predictions.

        Override this in subclasses that load artifacts from disk
        (e.g. ``self.is_trained`` in ``NeuralChallenger``).
        """
        return True

    @property
    def version(self) -> str:
        """Human-readable version string.  Override in each subclass."""
        return "BasePredictor/unknown"

    # ------------------------------------------------------------------
    # Convenience helpers (concrete — do NOT override)
    # ------------------------------------------------------------------

    def predict_total(self, features: pd.DataFrame) -> float:
        """
        Convenience method: total expected corners = λ_home + λ_away.

        Args:
            features: Single-row feature DataFrame.

        Returns:
            float: Expected total corners for the match.
        """
        lh, la = self.predict_lambda(features)
        return lh + la

    def __repr__(self) -> str:
        status = "ready" if self.is_ready else "not ready"
        return f"<{self.__class__.__name__} version={self.version!r} status={status}>"
