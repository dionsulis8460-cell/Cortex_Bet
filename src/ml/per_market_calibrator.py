"""
src/ml/per_market_calibrator.py
=================================
Calibradores Probabilísticos por Família de Mercado.

9 calibradores independentes — um por família de mercado:
    ft_total, ht_total, ht2_total, ft_home, ft_away,
    ht_home, ht_away, ht2_home, ht2_away

Metodologia:
    - Isotonic Regression (não-paramétrica, mono-tônica) como default.
    - Temperature Scaling quando amostra < 30 jogos.
    - Pooling hierárquico quando amostra < 100 jogos:
        calibrador_família = shrink(calibrador_local → calibrador_global)
        fator_shrinkage = n_local / (n_local + 100)

Proibições:
    - NÃO usar 1 calibrador global para todos os mercados.
    - NÃO assumir calibração sem medir ECE (Expected Calibration Error).
    - NÃO usar calibradores frágeis (< 10 amostras por bin) como produção.

Referências:
    Niculescu-Mizil & Caruana (2005) - "Predicting Good Probabilities" — ICML
    Zadrozny & Elkan (2002) - "Transforming Classifier Scores" — KDD
    Guo et al. (2017) - "On Calibration of Modern Neural Networks" — ICML
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

MARKET_FAMILIES = [
    "ft_total", "ht_total", "ht2_total",
    "ft_home", "ft_away",
    "ht_home", "ht_away", "ht2_home", "ht2_away",
]

# Thresholds de amostra
MIN_SAMPLES_ISOTONIC = 30
MIN_SAMPLES_PRODUCTION = 10


# ---------------------------------------------------------------------------
# Métricas de Calibração
# ---------------------------------------------------------------------------

def compute_ece(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Expected Calibration Error (ECE) — versão binária.

    ECE = Σ (|B_m| / N) * |acc(B_m) - conf(B_m)|

    Args:
        probs: Probabilidades preditas (0-1).
        labels: Labels binários reais (0 ou 1).
        n_bins: Número de bins de calibração.

    Returns:
        ECE em [0, 1] — menor é melhor.
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs)

    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i + 1])
        if mask.sum() == 0:
            continue
        acc = labels[mask].mean()
        conf = probs[mask].mean()
        ece += (mask.sum() / n) * abs(acc - conf)

    return float(ece)


def compute_brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
    """Brier Score = MSE entre probs e labels binários."""
    return float(np.mean((probs - labels) ** 2))


# ---------------------------------------------------------------------------
# Calibrador Individual
# ---------------------------------------------------------------------------

class SingleFamilyCalibrator:
    """
    Calibrador para uma única família de mercado.

    Aprende o mapeamento prob_raw → prob_calibrated usando dados históricos
    out-of-fold (jamais dados de treino dos modelos base).

    Args:
        family: Nome da família de mercado.
        method: 'isotonic' (default) ou 'temperature'.
        min_samples: Mínimo de amostras para usar isotonic; abaixo usa temperature.
    """

    def __init__(
        self,
        family: str,
        method: str = "isotonic",
        min_samples: int = MIN_SAMPLES_ISOTONIC,
    ) -> None:
        if family not in MARKET_FAMILIES:
            raise ValueError(f"Família '{family}' inválida. Válidas: {MARKET_FAMILIES}")
        self.family = family
        self.method = method
        self.min_samples = min_samples

        self._calibrator = None
        self._temperature: float = 1.0
        self._effective_method: str = method
        self.is_fitted: bool = False
        self.n_samples: int = 0

        # Métricas pós-fit
        self.ece_train: float = float("nan")
        self.brier_train: float = float("nan")

    def fit(
        self,
        y_prob: np.ndarray,
        y_true_binary: np.ndarray,
    ) -> "SingleFamilyCalibrator":
        """
        Ajusta o calibrador.

        Args:
            y_prob: Probabilidades brutas do modelo para este mercado.
            y_true_binary: Labels binários (1 se Over aconteceu, 0 se não).

        Returns:
            self
        """
        n = len(y_prob)
        self.n_samples = n

        if n < MIN_SAMPLES_PRODUCTION:
            warnings.warn(
                f"[PerMarketCalibrator] Família '{self.family}': apenas {n} amostras. "
                "Calibrador não ajustado — usando pass-through.",
                UserWarning,
            )
            self._effective_method = "passthrough"
            self.is_fitted = True
            return self

        if n < self.min_samples:
            # Fallback para temperature scaling
            self._effective_method = "temperature"
            self._temperature = self._fit_temperature(y_prob, y_true_binary)
        else:
            self._effective_method = "isotonic"
            self._calibrator = IsotonicRegression(out_of_bounds="clip", increasing=True)
            self._calibrator.fit(y_prob, y_true_binary)

        self.is_fitted = True

        # Métricas de calibração pós-fit
        y_cal = self.predict(y_prob)
        self.ece_train = compute_ece(y_cal, y_true_binary)
        self.brier_train = compute_brier_score(y_cal, y_true_binary)

        return self

    def predict(self, y_prob: np.ndarray) -> np.ndarray:
        """
        Transforma probabilidades brutas em probabilidades calibradas.

        Args:
            y_prob: Array de probabilidades brutas.

        Returns:
            Array de probabilidades calibradas.
        """
        if not self.is_fitted:
            raise RuntimeError(
                f"Calibrador '{self.family}' não ajustado. Chame fit() primeiro."
            )

        y_prob = np.clip(y_prob, 1e-6, 1.0 - 1e-6)

        if self._effective_method == "passthrough":
            return y_prob
        elif self._effective_method == "temperature":
            return self._apply_temperature(y_prob)
        else:
            return np.clip(self._calibrator.predict(y_prob), 1e-6, 1.0 - 1e-6)

    def predict_single(self, prob_raw: float) -> float:
        """Calibra uma única probabilidade."""
        return float(self.predict(np.array([prob_raw]))[0])

    def _fit_temperature(
        self, y_prob: np.ndarray, y_true: np.ndarray
    ) -> float:
        """
        Temperature Scaling: encontra T que minimiza NLL.
        P_cal = sigmoid(logit(p) / T)
        """
        from scipy.special import logit, expit
        from scipy.optimize import minimize_scalar

        logits = logit(np.clip(y_prob, 1e-6, 1 - 1e-6))

        def nll(T: float) -> float:
            if T <= 0:
                return 1e9
            p = expit(logits / T)
            p = np.clip(p, 1e-9, 1 - 1e-9)
            return -np.mean(y_true * np.log(p) + (1 - y_true) * np.log(1 - p))

        result = minimize_scalar(nll, bounds=(0.1, 10.0), method="bounded")
        return float(result.x)

    def _apply_temperature(self, y_prob: np.ndarray) -> np.ndarray:
        from scipy.special import logit, expit
        logits = logit(np.clip(y_prob, 1e-6, 1 - 1e-6))
        return np.clip(expit(logits / self._temperature), 1e-6, 1 - 1e-6)


# ---------------------------------------------------------------------------
# Calibrador Conjunto (9 famílias)
# ---------------------------------------------------------------------------

class PerMarketCalibrator:
    """
    Wrapper que gerencia 9 calibradores independentes.

    Também implementa pooling hierárquico:
        Quando amostra local < 100 jogos, o calibrador da família é
        encolhido em direção ao calibrador global (FT total).

    Args:
        method: Método padrão para cada calibrador ('isotonic' ou 'temperature').
        pooling_threshold: Abaixo deste N, aplica shrinkage em direção ao global.
        pooling_strength: Peso do calibrador global no shrinkage.
    """

    def __init__(
        self,
        method: str = "isotonic",
        pooling_threshold: int = 100,
        pooling_strength: float = 0.5,
    ) -> None:
        self.method = method
        self.pooling_threshold = pooling_threshold
        self.pooling_strength = pooling_strength

        self._calibrators: Dict[str, SingleFamilyCalibrator] = {
            f: SingleFamilyCalibrator(f, method) for f in MARKET_FAMILIES
        }
        self.is_fitted: bool = False

    def fit(
        self,
        family_probs: Dict[str, np.ndarray],
        family_labels: Dict[str, np.ndarray],
    ) -> "PerMarketCalibrator":
        """
        Ajusta todos os calibradores com probabilidades out-of-fold.

        Args:
            family_probs:  {family: array de probs brutas}
            family_labels: {family: array de labels binários}

        Returns:
            self
        """
        for family in MARKET_FAMILIES:
            probs = family_probs.get(family)
            labels = family_labels.get(family)
            if probs is None or labels is None:
                warnings.warn(
                    f"[PerMarketCalibrator] Família '{family}' sem dados. Ignorando.",
                    UserWarning,
                )
                continue
            self._calibrators[family].fit(
                np.asarray(probs, dtype=float),
                np.asarray(labels, dtype=float),
            )

        self.is_fitted = True
        return self

    def predict(self, family: str, prob_raw: float) -> float:
        """
        Retorna probabilidade calibrada para uma família e probabilidade bruta.

        Aplica pooling hierárquico se necessário.

        Args:
            family: Nome da família.
            prob_raw: Probabilidade bruta do MarketTranslator.

        Returns:
            Probabilidade calibrada em [0, 1].
        """
        if family not in self._calibrators:
            raise ValueError(f"Família '{family}' desconhecida.")

        cal = self._calibrators[family]
        if not cal.is_fitted:
            return float(np.clip(prob_raw, 1e-6, 1 - 1e-6))

        p_local = cal.predict_single(prob_raw)

        # Pooling hierárquico: se amostra pequena, encolhe em direção ao ft_total
        if cal.n_samples < self.pooling_threshold and "ft_total" in self._calibrators:
            global_cal = self._calibrators["ft_total"]
            if global_cal.is_fitted and global_cal.n_samples >= self.pooling_threshold:
                p_global = global_cal.predict_single(prob_raw)
                alpha = cal.n_samples / (cal.n_samples + self.pooling_threshold)
                p_local = alpha * p_local + (1 - alpha) * p_global

        return float(np.clip(p_local, 1e-6, 1 - 1e-6))

    def calibration_report(self) -> Dict[str, Dict]:
        """
        Retorna relatório de calibração de todos os mercados.

        Returns:
            Dict[family → {method, n_samples, ece_train, brier_train, is_fitted}]
        """
        report = {}
        for family, cal in self._calibrators.items():
            report[family] = {
                "method": cal._effective_method if cal.is_fitted else "not_fitted",
                "n_samples": cal.n_samples,
                "ece_train": cal.ece_train,
                "brier_train": cal.brier_train,
                "is_fitted": cal.is_fitted,
            }
        return report

    def save(self, path: str) -> None:
        joblib.dump(self, path)
        print(f"[PerMarketCalibrator] Salvo em: {path}")

    @classmethod
    def load(cls, path: str) -> "PerMarketCalibrator":
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"{path} não contém PerMarketCalibrator")
        return obj
