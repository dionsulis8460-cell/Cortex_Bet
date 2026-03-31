"""
src/evaluation/sci_evaluator.py
=================================
Avaliador Científico — Métricas Primárias e Secundárias por Família de Mercado.

Métricas Primárias (obrigatórias):
    1. Brier Score — calibração de probabilidade binária
    2. Log Loss — scoring probabilístico
    3. RPS (Ranked Probability Score) — para distribuição discreta
    4. ECE (Expected Calibration Error) — reliability

Métricas Secundárias:
    5. MAE do valor esperado E[X] vs. X_real
    6. Sharpness — quão "perto de 0 ou 1" são as probs
    7. Estabilidade — variância de Brier por liga/temporada
    8. Cobertura de intervalos — frequência de X_real dentro de CI
    9. Hit Rate — APENAS auxiliar, nunca como métrica principal

Proibições:
    - NÃO usar hit rate como métrica principal de avaliação.
    - NÃO comparar modelos apenas por acurácia simples.
    - NÃO usar métricas de uma família para julgar outra.
    - NÃO promover modelo com degradação em qualquer família.

Referências:
    Brier (1950) - "Verification of Forecasts" — Monthly Weather Review
    Gneiting & Raftery (2007) - "Strictly Proper Scoring Rules" — JASA
    DeGroot & Fienberg (1983) - "The Comparison and Evaluation of Forecasters" — The Statistician
    Guo et al. (2017) - "On Calibration of Modern Neural Networks" — ICML
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Dataclasses de resultado
# ---------------------------------------------------------------------------

@dataclass
class FamilyMetrics:
    """Métricas para uma única família de mercado."""
    family: str
    line: float
    n_samples: int

    # Primárias
    brier_score: float
    log_loss: float
    rps: float
    ece: float

    # Secundárias
    mae_expected: float        # MAE entre E[X] do modelo e X real
    sharpness: float           # Média de max(p, 1-p)
    hit_rate: float            # Apenas auxiliar
    coverage_90: float         # P(X_real dentro do CI 90%)

    # Segmentação
    league_stability: float = float("nan")   # std(Brier por liga)
    season_stability: float = float("nan")   # std(Brier por temporada)


@dataclass
class ModelEvaluationReport:
    """Relatório completo de avaliação de um modelo."""
    model_id: str
    eval_date: str
    n_total_samples: int
    families: Dict[str, FamilyMetrics] = field(default_factory=dict)

    def summary_dataframe(self) -> pd.DataFrame:
        rows = []
        for fam, m in self.families.items():
            rows.append({
                "family": m.family,
                "line": m.line,
                "n": m.n_samples,
                "brier": round(m.brier_score, 4),
                "log_loss": round(m.log_loss, 4),
                "rps": round(m.rps, 4),
                "ece": round(m.ece, 4),
                "mae_expected": round(m.mae_expected, 3),
                "sharpness": round(m.sharpness, 4),
                "hit_rate": round(m.hit_rate, 3),
                "coverage_90": round(m.coverage_90, 3),
                "league_stability": round(m.league_stability, 4)
                    if not np.isnan(m.league_stability) else "n/a",
            })
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Métricas individuais
# ---------------------------------------------------------------------------

def brier_score(probs: np.ndarray, labels: np.ndarray) -> float:
    """Brier Score = E[(p - y)^2]. Menor é melhor."""
    return float(np.mean((probs - labels) ** 2))


def log_loss(probs: np.ndarray, labels: np.ndarray, eps: float = 1e-7) -> float:
    """Binary cross-entropy. Menor é melhor."""
    p = np.clip(probs, eps, 1 - eps)
    return float(-np.mean(labels * np.log(p) + (1 - labels) * np.log(1 - p)))


def ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """
    Expected Calibration Error — binning uniforme de confiança.
    ECE = Σ |B_m|/N * |acc(B_m) - conf(B_m)|
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    total_ece = 0.0
    n = len(probs)
    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i + 1])
        if mask.sum() == 0:
            continue
        acc = labels[mask].mean()
        conf = probs[mask].mean()
        total_ece += (mask.sum() / n) * abs(acc - conf)
    return float(total_ece)


def rps_binary(prob_over: np.ndarray, labels_over: np.ndarray) -> float:
    """
    Ranked Probability Score para mercado binário Over/Under.
    RPS = 0.5 * E[(F1 - O1)^2 + (F2 - O2)^2]
    onde F = CDF da previsão, O = CDF observada.

    Para binário: RPS = 0.5 * [(p - y)^2 + ((1-p) - (1-y))^2]
                      = (p - y)^2 = Brier Score neste caso.
    """
    return brier_score(prob_over, labels_over)


def sharpness(probs: np.ndarray) -> float:
    """
    Sharpness = quão afastadas de 0.5 são as probabilidades.
    Higher = mais confiante (não necessariamente correto).
    = E[max(p, 1-p)]
    """
    return float(np.mean(np.maximum(probs, 1 - probs)))


def interval_coverage(
    samples: Optional[np.ndarray],
    y_true: float,
    level: float = 0.90,
) -> float:
    """
    Cobertura de intervalo de credibilidade.
    Retorna 1.0 se y_true dentro do CI, 0.0 caso contrário.
    """
    if samples is None or len(samples) == 0:
        return float("nan")
    alpha = (1 - level) / 2
    lower = float(np.quantile(samples, alpha))
    upper = float(np.quantile(samples, 1 - alpha))
    return float(lower <= y_true <= upper)


# ---------------------------------------------------------------------------
# Evaluator principal
# ---------------------------------------------------------------------------

class SciEvaluator:
    """
    Avalia um modelo em todas as 9 famílias de mercado com protocolo científico.

    Uso típico:
        evaluator = SciEvaluator()
        report = evaluator.evaluate(predictions_df, model_id="joint_v1")
        print(report.summary_dataframe())

    Args:
        n_bins_ece: Número de bins para ECE.
    """

    FAMILY_DEFAULT_LINES = {
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

    def __init__(self, n_bins_ece: int = 10) -> None:
        self.n_bins_ece = n_bins_ece

    def evaluate(
        self,
        records: List[Dict],
        model_id: str,
        eval_date: Optional[str] = None,
    ) -> ModelEvaluationReport:
        """
        Avalia o modelo a partir de uma lista de registros.

        Args:
            records: Lista de dicts com campos:
                {
                  family: str,
                  line: float,
                  prob_over: float,        # probabilidade bruta ou calibrada
                  y_actual: float,        # valor real observado
                  expected: float,        # E[X] do modelo
                  samples: array | None,  # amostras MC (para coverage)
                  league_id: str | None,
                  season: str | None,
                }
            model_id: Identificador do modelo avaliado.
            eval_date: Data da avaliação (ISO8601).

        Returns:
            ModelEvaluationReport com métricas por família.
        """
        from datetime import datetime, timezone
        if eval_date is None:
            eval_date = datetime.now(tz=timezone.utc).isoformat()

        df = pd.DataFrame(records)
        if df.empty:
            raise ValueError("[SciEvaluator] Nenhum registro fornecido.")

        report = ModelEvaluationReport(
            model_id=model_id,
            eval_date=eval_date,
            n_total_samples=len(df),
        )

        for family, line in self.FAMILY_DEFAULT_LINES.items():
            sub = df[(df["family"] == family) & (df["line"] == line)]
            if sub.empty:
                continue

            probs = sub["prob_over"].values.astype(float)
            y_bin = (sub["y_actual"].values > line).astype(float)
            expected = sub["expected"].values.astype(float)
            y_actual = sub["y_actual"].values.astype(float)

            # Primárias
            bs = brier_score(probs, y_bin)
            ll = log_loss(probs, y_bin)
            rps_ = rps_binary(probs, y_bin)
            ece_ = ece(probs, y_bin, self.n_bins_ece)

            # Secundárias
            mae_exp = float(np.mean(np.abs(expected - y_actual)))
            sharp = sharpness(probs)
            hit = float(np.mean((probs > 0.5) == y_bin.astype(bool)))

            # Coverage (se samples disponíveis)
            samples_col = sub.get("samples") if hasattr(sub, "get") else sub["samples"] if "samples" in sub.columns else None
            coverages = []
            if samples_col is not None:
                for idx, row in sub.iterrows():
                    s = row.get("samples") if isinstance(row, dict) else row["samples"] if "samples" in row.index else None
                    cov = interval_coverage(s, float(row["y_actual"]))
                    if not np.isnan(cov):
                        coverages.append(cov)
            coverage_90 = float(np.mean(coverages)) if coverages else float("nan")

            # Estabilidade por liga
            league_stability = float("nan")
            if "league_id" in sub.columns and sub["league_id"].notna().any():
                league_briers = []
                for lg in sub["league_id"].dropna().unique():
                    lg_mask = sub["league_id"] == lg
                    if lg_mask.sum() >= 5:
                        lb = brier_score(
                            sub.loc[lg_mask, "prob_over"].values.astype(float),
                            (sub.loc[lg_mask, "y_actual"].values > line).astype(float),
                        )
                        league_briers.append(lb)
                if len(league_briers) > 1:
                    league_stability = float(np.std(league_briers))

            report.families[family] = FamilyMetrics(
                family=family,
                line=line,
                n_samples=len(sub),
                brier_score=bs,
                log_loss=ll,
                rps=rps_,
                ece=ece_,
                mae_expected=mae_exp,
                sharpness=sharp,
                hit_rate=hit,
                coverage_90=coverage_90 if not np.isnan(coverage_90) else float("nan"),
                league_stability=league_stability,
            )

        return report

    def compare_models(
        self,
        champion_report: ModelEvaluationReport,
        challenger_report: ModelEvaluationReport,
    ) -> Dict[str, Dict]:
        """
        Compara champion e challenger por família.

        Returns:
            Dict com resultado da comparação:
            {family: {metric: (champion_val, challenger_val, winner)}}

        Regras de promoção (ver docs/governance.md):
            - Challenger só promovido se superar TODAS as famílias
            - Degradação > 5% em qualquer família = bloqueio de promoção
        """
        result = {}
        promotion_blocked = False
        block_reasons = []

        for family in self.FAMILY_DEFAULT_LINES:
            ch_m = champion_report.families.get(family)
            cr_m = challenger_report.families.get(family)
            if ch_m is None or cr_m is None:
                continue

            ch_brier = ch_m.brier_score
            cr_brier = cr_m.brier_score
            improvement_pct = (ch_brier - cr_brier) / ch_brier * 100 if ch_brier > 0 else 0

            winner = "challenger" if cr_brier < ch_brier else "champion" if cr_brier > ch_brier else "tie"

            # Verifica degradação material (> 5% pior)
            if improvement_pct < -5.0:
                promotion_blocked = True
                block_reasons.append(
                    f"{family}: challenger PIOR em {-improvement_pct:.1f}% Brier"
                )

            result[family] = {
                "champion_brier": ch_brier,
                "challenger_brier": cr_brier,
                "improvement_pct": improvement_pct,
                "champion_ece": ch_m.ece,
                "challenger_ece": cr_m.ece,
                "winner": winner,
            }

        result["_promotion_eligible"] = not promotion_blocked
        result["_block_reasons"] = block_reasons
        return result
