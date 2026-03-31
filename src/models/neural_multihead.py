"""
src/models/neural_multihead.py
================================
Challenger Neural Multi-Head — Shadow Mode.

Prediz o vetor latente [home_1H, away_1H, home_2H, away_2H] usando
uma rede neural MLP com 4 cabeças independentes + trunk compartilhado.

REGRA CRÍTICA — Shadow Mode:
    Este modelo NUNCA aparece no output de produção diretamente.
    Seus outputs são:
    1. Logados na tabela shadow_predictions do banco.
    2. Avaliados periodicamente por WalkForwardValidator.
    3. Comparados contra o champion em SciEvaluator.

    Promoção ao champion requer critérios definidos em ModelRegistry
    e documentados em docs/governance.md.

Proibições:
    - NÃO fazer blend do output neural com o champion.
    - NÃO promover por sofisticação; apenas por ganho reproduzível e calibrado.
    - NÃO tratar como superior sem evidência walk-forward por família.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator

from src.models.base_predictor import BasePredictor


JOINT_TARGET_DISPLAY = ["home_1H", "away_1H", "home_2H", "away_2H"]


class NeuralMultiHead(BasePredictor):
    """
    Challenger neural com 4 cabeças de saída.

    Arquitetura:
        Trunk MLP compartilhado → 4 cabeças independentes de regressão.

    Implementação atual:
        Usa MLPRegressor da sklearn com MultiOutputRegressor interno
        (computacionalmente equivalente ao trunk+cabeças).

        Para Fase 4+: substituir por PyTorch com trunk compartilhado
        quando ganho em dados for demonstrado.

    Args:
        hidden_layer_sizes: Camadas ocultas do trunk.
        max_iter: Iterações de treino.
        random_state: Seed reproduzível.
    """

    MODEL_ID = "neural_multihead_v1"

    def __init__(
        self,
        hidden_layer_sizes: Tuple[int, ...] = (256, 128, 64),
        max_iter: int = 300,
        random_state: int = 42,
    ) -> None:
        self.hidden_layer_sizes = hidden_layer_sizes
        self.max_iter = max_iter
        self.random_state = random_state

        self.scaler = StandardScaler()
        self._model: Optional[MLPRegressor] = None
        self.feature_names_: List[str] = []
        self.is_fitted_: bool = False

    # ------------------------------------------------------------------
    # BasePredictor interface
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        return self.is_fitted_

    @property
    def version(self) -> str:
        return self.MODEL_ID

    def predict_lambda(self, features_df: pd.DataFrame) -> Tuple[float, float]:
        """
        Backward-compatible: retorna (λ_home_ft, λ_away_ft).
        Usa a soma dos componentes 1H+2H de cada time.

        NOTE: Este método não deve ser usado para output de produção.
        Use predict_joint_lambda() para o vetor completo.
        """
        if not self.is_fitted_:
            return 0.0, 0.0
        joint = self.predict_joint_lambda(features_df)
        l_home_ft = joint.get("home_ft", 0.0)
        l_away_ft = joint.get("away_ft", 0.0)
        return l_home_ft, l_away_ft

    # ------------------------------------------------------------------
    # Multi-head inference
    # ------------------------------------------------------------------

    def predict_joint_lambda(self, features_df: pd.DataFrame) -> Dict[str, float]:
        """
        Prediz o vetor latente [home_1H, away_1H, home_2H, away_2H].

        Returns:
            Dict com 9 lambdas — base e derivados (coerência garantida).
        """
        if not self.is_fitted_:
            return {k: 0.0 for k in JOINT_TARGET_DISPLAY}

        X = self._align_and_scale(features_df)
        preds = self._model.predict(X)[0]  # shape (4,)

        # Clamp: lambdas de escanteios realistas
        l_h1H = float(max(0.05, min(8.0, preds[0])))
        l_a1H = float(max(0.05, min(8.0, preds[1])))
        l_h2H = float(max(0.05, min(8.0, preds[2])))
        l_a2H = float(max(0.05, min(8.0, preds[3])))

        return {
            "home_1H": l_h1H,
            "away_1H": l_a1H,
            "home_2H": l_h2H,
            "away_2H": l_a2H,
            # Derivados — coerência por construção
            "home_ft": l_h1H + l_h2H,
            "away_ft": l_a1H + l_a2H,
            "total_1H": l_h1H + l_a1H,
            "total_2H": l_h2H + l_a2H,
            "ft_total": l_h1H + l_a1H + l_h2H + l_a2H,
        }

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, X: pd.DataFrame, Y: pd.DataFrame) -> "NeuralMultiHead":
        """
        Treina o modelo multi-head.

        Args:
            X: Features (output do FeatureStore).
            Y: Targets com colunas [home_1H, away_1H, home_2H, away_2H].
        """
        if not all(c in Y.columns for c in JOINT_TARGET_DISPLAY):
            raise ValueError(
                f"Y deve conter colunas: {JOINT_TARGET_DISPLAY}. "
                f"Encontrado: {list(Y.columns)}"
            )

        self.feature_names_ = list(X.columns)
        X_scaled = self.scaler.fit_transform(X)

        self._model = MLPRegressor(
            hidden_layer_sizes=self.hidden_layer_sizes,
            activation="relu",
            solver="adam",
            max_iter=self.max_iter,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=self.random_state,
            verbose=False,
        )
        self._model.fit(X_scaled, Y[JOINT_TARGET_DISPLAY].values)
        self.is_fitted_ = True
        print(f"[NeuralMultiHead] Treinado. Loss final: {self._model.loss_:.4f}")
        return self

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        joblib.dump(self, path)
        print(f"[NeuralMultiHead] Modelo salvo em: {path}")

    @classmethod
    def load(cls, path: str) -> "NeuralMultiHead":
        obj = joblib.load(path)
        if not isinstance(obj, NeuralMultiHead):
            raise TypeError(f"{path} não contém NeuralMultiHead")
        return obj

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _align_and_scale(self, features_df: pd.DataFrame) -> np.ndarray:
        df = features_df.copy()
        for col in self.feature_names_:
            if col not in df.columns:
                df[col] = 0.0
        return self.scaler.transform(df[self.feature_names_])
