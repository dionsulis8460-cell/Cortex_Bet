"""
src/training/walk_forward_validator.py
========================================
Validação Temporal Rolling Walk-Forward.

Protocolo científico de avaliação sem data leakage:
    - Ordenação temporal estrita
    - Sem shuffle (dados de treino sempre anteriores aos de validação)
    - Avaliação por liga, por temporada e por família de mercado
    - Out-of-fold probabilities para calibração pós-treino

Integra com:
    - JointCornersModel (champion) e NeuralMultiHead (challenger)
    - MarketTranslator para derivação dos 9 mercados
    - SciEvaluator para cálculo de métricas
    - PerMarketCalibrator para ajuste de calibração com OOF probs

Proibições:
    - NÃO usar TimeSeriesSplit com shuffle.
    - NÃO usar dados futuros como features de treino.
    - NÃO reportar métricas só em FT total — SEMPRE por família.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

EVAL_OUTPUT_DIR = Path("data/evaluation")


# ---------------------------------------------------------------------------
# Gerador de splits
# ---------------------------------------------------------------------------

def temporal_splits(
    df: pd.DataFrame,
    n_splits: int = 5,
    min_train_size: int = 200,
    timestamp_col: str = "start_timestamp",
) -> Generator[Tuple[pd.DataFrame, pd.DataFrame, Dict], None, None]:
    """
    Gera splits temporais (train, val) com metadados de fold.

    Args:
        df: DataFrame histórico.
        n_splits: Número de folds.
        min_train_size: Mínimo de amostras no treino.
        timestamp_col: Coluna de timestamp.

    Yields:
        (df_train, df_val, meta_dict) — com info de datas do fold.
    """
    df_sorted = df.sort_values(timestamp_col).reset_index(drop=True)
    tscv = TimeSeriesSplit(n_splits=n_splits, min_train_size=min_train_size)

    for fold_i, (tr_idx, val_idx) in enumerate(tscv.split(df_sorted)):
        df_tr = df_sorted.iloc[tr_idx].copy()
        df_val = df_sorted.iloc[val_idx].copy()

        # Converte timestamps para display
        def ts_to_str(ts_val) -> str:
            try:
                return pd.to_datetime(ts_val, unit="s").strftime("%Y-%m-%d")
            except Exception:
                return str(ts_val)

        meta = {
            "fold": fold_i + 1,
            "train_size": len(df_tr),
            "val_size": len(df_val),
            "train_start": ts_to_str(df_tr[timestamp_col].min()),
            "train_end": ts_to_str(df_tr[timestamp_col].max()),
            "val_start": ts_to_str(df_val[timestamp_col].min()),
            "val_end": ts_to_str(df_val[timestamp_col].max()),
        }
        yield df_tr, df_val, meta


# ---------------------------------------------------------------------------
# Walk-Forward Validator
# ---------------------------------------------------------------------------

class WalkForwardValidator:
    """
    Executa validação walk-forward completa para um modelo de escanteios.

    Args:
        n_splits: Número de folds de validação.
        min_train_size: Mínimo de amostras por fold de treino.
        n_simulations: Simulações Monte Carlo no MarketTranslator.
        random_state: Seed para reprodutibilidade.
    """

    def __init__(
        self,
        n_splits: int = 5,
        min_train_size: int = 200,
        n_simulations: int = 10_000,
        random_state: int = 42,
    ) -> None:
        self.n_splits = n_splits
        self.min_train_size = min_train_size
        self.n_simulations = n_simulations
        self.random_state = random_state

    def run(
        self,
        df_history: pd.DataFrame,
        train_and_predict_fn: Callable[
            [pd.DataFrame, pd.DataFrame], List[Dict[str, Any]]
        ],
        model_id: str,
        save: bool = True,
    ) -> Dict[str, Any]:
        """
        Executa o walk-forward completo.

        Args:
            df_history: Dataset histórico completo (ordenado temporalmente internamente).
            train_and_predict_fn: Função que recebe (df_train, df_val) e retorna
                lista de registros para avaliação. Cada registro deve ter:
                {
                    match_id: int,
                    family: str,
                    line: float,
                    prob_over: float,
                    y_actual: float,
                    expected: float,
                    league_id: str | None,
                    season: str | None,
                    samples: np.ndarray | None,
                }
            model_id: ID do modelo sendo validado.
            save: Salvar relatório em disco.

        Returns:
            Dict com relatório completo (métricas por família, por liga, por fold).
        """
        from src.evaluation.sci_evaluator import SciEvaluator

        evaluator = SciEvaluator()
        all_records: List[Dict[str, Any]] = []
        fold_summaries = []

        print(f"\n[WalkForwardValidator] Modelo: {model_id}")
        print(f"  Splits: {self.n_splits} | Min train: {self.min_train_size}")

        for df_train, df_val, meta in temporal_splits(
            df_history, self.n_splits, self.min_train_size
        ):
            print(f"\n  [{meta['fold']}/{self.n_splits}] "
                  f"Treino: {meta['train_start']} → {meta['train_end']} "
                  f"({meta['train_size']} jogos) | "
                  f"Val: {meta['val_start']} → {meta['val_end']} "
                  f"({meta['val_size']} jogos)")
            try:
                fold_records = train_and_predict_fn(df_train, df_val)
            except Exception as e:
                print(f"  [WARN] Fold {meta['fold']} falhou: {e}")
                continue

            all_records.extend(fold_records)

            # Métricas por fold (apenas ft_total para monitoramento rápido)
            fold_ft = [r for r in fold_records if r.get("family") == "ft_total"]
            if fold_ft:
                import numpy as _np
                probs_ft = _np.array([r["prob_over"] for r in fold_ft])
                labels_ft = _np.array([float(r["y_actual"] > r.get("line", 9.5)) for r in fold_ft])
                from src.evaluation.sci_evaluator import brier_score as _bs
                bs_ft = _bs(probs_ft, labels_ft)
                print(f"    ft_total Brier (fold): {bs_ft:.4f}")
                fold_summaries.append({**meta, "ft_total_brier": round(bs_ft, 5)})

        if not all_records:
            raise ValueError("[WalkForwardValidator] Nenhum registro gerado.")

        # Avaliação final agregada
        report = evaluator.evaluate(all_records, model_id=model_id)

        print(f"\n[WalkForwardValidator] Resultado final ({len(all_records)} registros):")
        print(report.summary_dataframe().to_string(index=False))

        result = {
            "model_id": model_id,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "n_records": len(all_records),
            "fold_summaries": fold_summaries,
            "metrics_by_family": {
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

        if save:
            self._save(result, model_id)

        return result

    def _save(self, result: Dict, model_id: str) -> None:
        EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = EVAL_OUTPUT_DIR / f"walkforward_{model_id}_{ts}.json"
        with open(path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n[WalkForwardValidator] Relatório salvo: {path}")
