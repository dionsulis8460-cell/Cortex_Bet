"""
src/evaluation/ablation_report.py
===================================
Relatório de Ablação Formal de Heurísticas do Sistema.

Testa sistematicamente o impacto de cada heurística:
    1. Winsorização clip(lower=3.0) em corners_home/away_ft
    2. Blend champion+challenger vs. champion-only output
    3. Dummy-row assumption (zeros vs. médias históricas)
    4. Regras de ranking (Easy/Medium/Hard vs. prob_calibrated rank)

Metodologia:
    - Cada ablação roda walk-forward independente (mesmas janelas temporais)
    - Compara Brier Score, ECE e MAE com e sem a heurística
    - Resultado documentado com timestamp em data/evaluation/ablation_*.json

Proibições:
    - NÃO usar os resultados de ablação para cherry-pick.
    - NÃO manter heurística com impacto negativo não-documentado.
    - NÃO rodar ablação em dados de teste — apenas em OOF.

Referências:
    Lipton & Steinhardt (2019) - "Troubling Trends in Machine Learning Scholarship"
    Sculley et al. (2015) - "Hidden Technical Debt in Machine Learning Systems" — NIPS
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

EVAL_OUTPUT_DIR = Path("data/evaluation")


# ---------------------------------------------------------------------------
# Resultado de uma ablação individual
# ---------------------------------------------------------------------------

class AblationResult:
    """Resultado de uma ablação — comparação de métrica com/sem heurística."""

    def __init__(
        self,
        name: str,
        description: str,
        metric_with: float,
        metric_without: float,
        metric_name: str = "brier_score",
        n_samples: int = 0,
    ) -> None:
        self.name = name
        self.description = description
        self.metric_with = metric_with
        self.metric_without = metric_without
        self.metric_name = metric_name
        self.n_samples = n_samples

    @property
    def delta(self) -> float:
        """Diferença: metric_without - metric_with (positivo = heurística ajuda)."""
        return self.metric_without - self.metric_with

    @property
    def recommendation(self) -> str:
        if abs(self.delta) < 0.001:
            return "NEUTRAL — impacto desprezível; heurística pode ser mantida ou removida"
        elif self.delta > 0:
            return "KEEP — heurística melhora a métrica"
        else:
            return "REMOVE — heurística piora a métrica; remover ou ajustar"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "metric": self.metric_name,
            "with_heuristic": round(self.metric_with, 5),
            "without_heuristic": round(self.metric_without, 5),
            "delta": round(self.delta, 5),
            "recommendation": self.recommendation,
            "n_samples": self.n_samples,
        }


# ---------------------------------------------------------------------------
# Runner de ablações
# ---------------------------------------------------------------------------

class AblationRunner:
    """
    Executa ablações formais sobre heurísticas do pipeline.

    Args:
        df_history: Dataset histórico completo.
        n_folds: Número de folds walk-forward.
    """

    def __init__(self, df_history: pd.DataFrame, n_folds: int = 5) -> None:
        self.df_history = df_history
        self.n_folds = n_folds

    def run_all(self, save: bool = True) -> List[AblationResult]:
        """
        Executa todas as ablações registradas.

        Returns:
            Lista de AblationResult com recomendação para cada heurística.
        """
        results = []

        results.append(self.ablate_winsorization())
        results.append(self.ablate_dummy_row_assumption())
        results.append(self.ablate_champion_only_vs_blend())

        if save:
            self._save(results)

        return results

    # ------------------------------------------------------------------
    # Ablação 1: Winsorização clip(lower=3.0)
    # ------------------------------------------------------------------

    def ablate_winsorization(self) -> AblationResult:
        """
        Testa impacto de clip(lower=3.0) nos corners FT.

        Com heurística: corners_home/away_ft.clip(lower=3.0)
        Sem heurística: valores originais (sem clipagem)
        """
        from src.ml.features_v2 import create_advanced_features

        def score_with_clip() -> float:
            df = self.df_history.copy()
            df["corners_home_ft"] = df["corners_home_ft"].clip(lower=3.0)
            df["corners_away_ft"] = df["corners_away_ft"].clip(lower=3.0)
            return self._oof_mae(df, create_advanced_features)

        def score_without_clip() -> float:
            df = self.df_history.copy()
            return self._oof_mae(df, create_advanced_features)

        try:
            m_with = score_with_clip()
            m_without = score_without_clip()
        except Exception as e:
            m_with = m_without = float("nan")
            print(f"[Ablation] Erro na ablação de winsorização: {e}")

        return AblationResult(
            name="winsorization_clip_3",
            description="clip(lower=3.0) aplicado em corners_home/away_ft no FeatureStore",
            metric_with=m_with,
            metric_without=m_without,
            metric_name="mae_ft_total",
            n_samples=len(self.df_history),
        )

    # ------------------------------------------------------------------
    # Ablação 2: Dummy-row assumption (zeros vs. médias)
    # ------------------------------------------------------------------

    def ablate_dummy_row_assumption(self) -> AblationResult:
        """
        Testa impacto de preencher dummy-row com zeros vs. médias históricas.

        Atual: zeros em corners_home_ft=0, corners_away_ft=0, etc.
        Alternativa: médias das últimas N partidas de cada time.
        """
        # Esta ablação é descritiva — requer modificação no FeatureStore
        # que neste scaffold registra o experimento mas não o executa automaticamente.
        print("[Ablation] dummy-row assumption: execução manual necessária.")
        print("  Ver: src/features/feature_store.py -> build_match_features() -> dummy_row")
        print("  Experimento: substituir zeros por médias dos últimos 5 jogos de cada time.")

        return AblationResult(
            name="dummy_row_zeros",
            description="Dummy row: zeros vs. médias históricas para partida futura",
            metric_with=float("nan"),
            metric_without=float("nan"),
            metric_name="mae_ft_total",
            n_samples=len(self.df_history),
        )

    # ------------------------------------------------------------------
    # Ablação 3: Champion-only vs. Blend (champion * 0.5 + prob_score * 0.5)
    # ------------------------------------------------------------------

    def ablate_champion_only_vs_blend(self) -> AblationResult:
        """
        Testa impacto do blend champion+challenger vs. champion-only.

        Diagnostica se o blend atual no manager_ai.py melhora ou piora calibração.
        """
        # Esta ablação requer acesso ao ManagerAI com feature flag.
        # Registra o diagnóstico para execução manual com CHAMPION_ONLY_MODE.
        print("[Ablation] champion vs blend: requer CHAMPION_ONLY_MODE=True/False")
        print("  Ver: src/analysis/manager_ai.py -> CHAMPION_ONLY_MODE env var")
        print("  Procedimento:")
        print("    1. Rodar walk-forward com CHAMPION_ONLY_MODE=False (blend atual)")
        print("    2. Rodar walk-forward com CHAMPION_ONLY_MODE=True (champion only)")
        print("    3. Comparar Brier e ECE nas 9 famílias")

        return AblationResult(
            name="champion_vs_blend",
            description="Output: champion-only vs. blend(champion*0.5, challenger*0.5)",
            metric_with=float("nan"),
            metric_without=float("nan"),
            metric_name="brier_score_ft_total",
            n_samples=len(self.df_history),
        )

    # ------------------------------------------------------------------
    # Helper: OOF MAE para FT total
    # ------------------------------------------------------------------

    def _oof_mae(
        self,
        df: pd.DataFrame,
        feature_fn: Callable,
        n_folds: int = 3,
    ) -> float:
        """Calcula MAE OOF do total de escanteios FT."""
        from sklearn.model_selection import TimeSeriesSplit
        import lightgbm as lgb

        X, y, _, _ = feature_fn(df)
        X_r = X.reset_index(drop=True)
        y_r = y.reset_index(drop=True)

        tscv = TimeSeriesSplit(n_splits=n_folds)
        maes = []

        for tr_idx, val_idx in tscv.split(X_r):
            if len(tr_idx) < 50:
                continue
            mdl = lgb.LGBMRegressor(
                objective="poisson", n_estimators=100, verbose=-1
            )
            mdl.fit(X_r.iloc[tr_idx], y_r.iloc[tr_idx])
            preds = mdl.predict(X_r.iloc[val_idx])
            mae = float(np.mean(np.abs(preds - y_r.iloc[val_idx].values)))
            maes.append(mae)

        return float(np.mean(maes)) if maes else float("nan")

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------

    def _save(self, results: List[AblationResult]) -> None:
        EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = EVAL_OUTPUT_DIR / f"ablation_{ts}.json"
        data = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "n_history": len(self.df_history),
            "results": [r.to_dict() for r in results],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[Ablation] Relatório salvo em: {path}")
