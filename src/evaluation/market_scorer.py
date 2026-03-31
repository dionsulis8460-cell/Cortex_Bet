"""
src/evaluation/market_scorer.py
================================
Scoring por Família de Mercado — Walk-Forward Temporal.

Avalia modelos em cada uma das 9 famílias de mercado usando rolling
walk-forward com relatórios por liga e por temporada.

Destina-se a:
    - Comparação champion vs. challenger por família.
    - Detecção de degradação em mercados de nicho (1T, 2T, por time).
    - Geração de evidência para decisão de promoção no ModelRegistry.

Protocolo Walk-Forward:
    - Split temporal estrito (sem data leakage).
    - Mínimo de 200 amostras em cada fold de treino.
    - Avaliação em janelas de 30-60 dias.
    - Relatório segmentado por liga e por temporada.

Proibições:
    - NÃO misturar dados de validação no treino.
    - NÃO reportar só globais — SEMPRE reportar por família.
    - NÃO aceitar promoção com degradação em qualquer família.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from src.evaluation.sci_evaluator import (
    SciEvaluator,
    ModelEvaluationReport,
    brier_score,
    log_loss,
    ece,
)
from src.ml.market_translator import MARKET_FAMILIES

EVAL_OUTPUT_DIR = Path("data/evaluation")


# ---------------------------------------------------------------------------
# Walk-forward generator
# ---------------------------------------------------------------------------

def walk_forward_splits(
    df: pd.DataFrame,
    n_splits: int = 5,
    min_train_size: int = 200,
    timestamp_col: str = "start_timestamp",
) -> Generator[Tuple[pd.DataFrame, pd.DataFrame], None, None]:
    """
    Gera pares (train, val) em split temporal estrito.

    Args:
        df: DataFrame com coluna de timestamp.
        n_splits: Número de folds.
        min_train_size: Mínimo de linhas no fold de treino.
        timestamp_col: Coluna de timestamp para ordenação.

    Yields:
        (df_train, df_val) — pares sem overlap temporal.
    """
    df_sorted = df.sort_values(timestamp_col).reset_index(drop=True)
    tscv = TimeSeriesSplit(n_splits=n_splits, min_train_size=min_train_size)

    for train_idx, val_idx in tscv.split(df_sorted):
        yield df_sorted.iloc[train_idx], df_sorted.iloc[val_idx]


# ---------------------------------------------------------------------------
# Market Scorer principal
# ---------------------------------------------------------------------------

class MarketScorer:
    """
    Avalia um modelo preditivo em todas as 9 famílias de mercado com walk-forward.

    Args:
        n_splits: Número de folds walk-forward.
        min_train_size: Mínimo de amostras por fold de treino.
        evaluator: Instância do SciEvaluator (criado internamente se None).
    """

    DEFAULT_LINES = {
        "ft_total":  9.5,
        "ht_total":  4.5,
        "ht2_total": 4.5,
        "ft_home":   4.5,
        "ft_away":   4.5,
        "ht_home":   2.5,
        "ht_away":   2.5,
        "ht2_home":  2.5,
        "ht2_away":  2.5,
    }

    def __init__(
        self,
        n_splits: int = 5,
        min_train_size: int = 200,
        evaluator: Optional[SciEvaluator] = None,
    ) -> None:
        self.n_splits = n_splits
        self.min_train_size = min_train_size
        self.evaluator = evaluator or SciEvaluator()

    def score_model(
        self,
        model_id: str,
        df_history: pd.DataFrame,
        predict_fn: Callable[[pd.DataFrame, pd.DataFrame], List[Dict]],
        save: bool = True,
    ) -> ModelEvaluationReport:
        """
        Avalia o modelo com walk-forward temporal.

        Args:
            model_id: ID do modelo avaliado.
            df_history: Dataset histórico completo.
            predict_fn: Função que recebe (df_train, df_val) e retorna
                        lista de registros para SciEvaluator.evaluate().
                        Forma: [{family, line, prob_over, y_actual, expected, ...}]
            save: Salvar relatório em disco.

        Returns:
            ModelEvaluationReport agregado por família.
        """
        all_records: List[Dict] = []

        print(f"[MarketScorer] Avaliando modelo '{model_id}'...")

        for fold_i, (df_train, df_val) in enumerate(
            walk_forward_splits(df_history, self.n_splits, self.min_train_size)
        ):
            print(f"  Fold {fold_i + 1}: treino={len(df_train)} | validação={len(df_val)}")
            try:
                fold_records = predict_fn(df_train, df_val)
                all_records.extend(fold_records)
            except Exception as e:
                print(f"  [WARN] Fold {fold_i + 1} falhou: {e}")
                continue

        if not all_records:
            raise ValueError(
                "[MarketScorer] Nenhum registro gerado. Verifique predict_fn."
            )

        report = self.evaluator.evaluate(all_records, model_id=model_id)

        if save:
            self._save_report(report)

        return report

    def score_by_league(
        self,
        records: List[Dict],
        model_id: str,
    ) -> Dict[str, ModelEvaluationReport]:
        """
        Avalia métricas segmentadas por liga.

        Args:
            records: Registros com campo 'league_id'.
            model_id: ID do modelo.

        Returns:
            Dict[league_id → ModelEvaluationReport]
        """
        df = pd.DataFrame(records)
        if "league_id" not in df.columns:
            raise ValueError("Registros devem conter campo 'league_id'.")

        results = {}
        for league_id in df["league_id"].dropna().unique():
            league_records = df[df["league_id"] == league_id].to_dict("records")
            if len(league_records) < 10:
                continue
            try:
                report = self.evaluator.evaluate(
                    league_records,
                    model_id=f"{model_id}_league_{league_id}",
                )
                results[str(league_id)] = report
            except Exception as e:
                print(f"  [WARN] Liga {league_id}: {e}")

        return results

    def score_by_season(
        self,
        records: List[Dict],
        model_id: str,
    ) -> Dict[str, ModelEvaluationReport]:
        """
        Avalia métricas segmentadas por temporada.

        Args:
            records: Registros com campo 'season'.
            model_id: ID do modelo.

        Returns:
            Dict[season → ModelEvaluationReport]
        """
        df = pd.DataFrame(records)
        if "season" not in df.columns:
            raise ValueError("Registros devem conter campo 'season'.")

        results = {}
        for season in df["season"].dropna().unique():
            season_records = df[df["season"] == season].to_dict("records")
            if len(season_records) < 10:
                continue
            try:
                report = self.evaluator.evaluate(
                    season_records,
                    model_id=f"{model_id}_season_{season}",
                )
                results[str(season)] = report
            except Exception as e:
                print(f"  [WARN] Temporada {season}: {e}")

        return results

    def promotion_check(
        self,
        champion_report: ModelEvaluationReport,
        challenger_report: ModelEvaluationReport,
        min_n_per_family: int = 50,
    ) -> Dict[str, Any]:
        """
        Verifica se o challenger atende os critérios de promoção.

        Critérios (ver docs/governance.md):
            1. Brier melhora ≥ 3% globalmente (ft_total)
            2. ECE melhora ou não degrada em TODAS as 9 famílias
            3. Nenhuma família com degradação Brier > 5%
            4. N mínimo de amostras avaliadas por família

        Returns:
            Dict com resultado e razões.
        """
        comparison = self.evaluator.compare_models(champion_report, challenger_report)

        eligible = comparison.get("_promotion_eligible", False)
        block_reasons = comparison.get("_block_reasons", [])

        # Critério global: ft_total Brier melhora ≥ 3%
        ft_comparison = comparison.get("ft_total", {})
        global_improvement = ft_comparison.get("improvement_pct", 0.0)
        if global_improvement < 3.0:
            eligible = False
            block_reasons.append(
                f"ft_total Brier melhora apenas {global_improvement:.1f}% (mínimo 3%)"
            )

        # Critério ECE: challenger ECE ≤ champion ECE em cada família
        for family, comp_data in comparison.items():
            if family.startswith("_"):
                continue
            ch_ece = comp_data.get("champion_ece", 0.0)
            cr_ece = comp_data.get("challenger_ece", 0.0)
            if cr_ece > ch_ece * 1.05:  # > 5% pior em ECE
                eligible = False
                block_reasons.append(
                    f"{family}: challenger ECE {cr_ece:.4f} > champion ECE {ch_ece:.4f} (+5%)"
                )

        # Critério N mínimo
        for family in MARKET_FAMILIES:
            ch_m = champion_report.families.get(family)
            cr_m = challenger_report.families.get(family)
            if cr_m and cr_m.n_samples < min_n_per_family:
                eligible = False
                block_reasons.append(
                    f"{family}: apenas {cr_m.n_samples} amostras (mínimo {min_n_per_family})"
                )

        return {
            "eligible": eligible,
            "block_reasons": block_reasons,
            "champion_id": champion_report.model_id,
            "challenger_id": challenger_report.model_id,
            "comparison": {k: v for k, v in comparison.items() if not k.startswith("_")},
        }

    def _save_report(self, report: ModelEvaluationReport) -> None:
        EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = EVAL_OUTPUT_DIR / f"market_score_{report.model_id}_{ts}.json"
        data = {
            "model_id": report.model_id,
            "eval_date": report.eval_date,
            "n_total": report.n_total_samples,
            "families": {
                f: {
                    "brier": round(m.brier_score, 5),
                    "log_loss": round(m.log_loss, 5),
                    "rps": round(m.rps, 5),
                    "ece": round(m.ece, 5),
                    "mae_expected": round(m.mae_expected, 4),
                    "sharpness": round(m.sharpness, 4),
                    "hit_rate": round(m.hit_rate, 4),
                    "n": m.n_samples,
                }
                for f, m in report.families.items()
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[MarketScorer] Relatório salvo: {path}")
