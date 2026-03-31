"""
ScientificScorer — Motor de Score Científico para Top 7.

Substitui o ranking heurístico baseado apenas em confiança.
O score combina:
    1. P_calibrada   — probabilidade calibrada (peso principal)
    2. Uncertainty    — penalidade por alta incerteza (std da distribuição)
    3. Stability      — consistência da família de mercado por liga

Diretriz de governança (docs/governance.md):
    - Sem odd real: ranquear por P_calibrada, estabilidade e incerteza.
    - Sem afirmação econômica — apenas ranking probabilístico.
    - Top 7 existe como opção ao usuário (não binário), não como critério final.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import math

from src.domain.models import PredictionResult, BettingPick


# ---------------------------------------------------------------------------
# Pesos do score (podem ser ajustados após ablação)
# ---------------------------------------------------------------------------

W_PROB = 0.60        # Peso da probabilidade calibrada
W_UNCERTAINTY = 0.25 # Peso (penalidade) da incerteza
W_STABILITY = 0.15   # Peso da estabilidade por família


def compute_scientific_score(
    probability: float,
    uncertainty: float,
    expected_value: float,
    stability: float = 1.0,
) -> float:
    """
    Calcula o score científico para ranking.

    Args:
        probability: P_calibrada (0 a 1).
        uncertainty: Desvio padrão da distribuição MC.
        expected_value: E[X] — usado para normalizar incerteza.
        stability: Estabilidade da família (1 - cv normalizado). 0 a 1.

    Returns:
        Score composto (0 a 1). Maior = melhor.
    """
    # Coeficiente de variação normalizado (0 = muito incerto, 1 = concentrado)
    if expected_value > 0:
        cv = min(uncertainty / expected_value, 2.0) / 2.0  # normaliza para [0, 1]
        uncertainty_penalty = 1.0 - cv
    else:
        uncertainty_penalty = 0.5

    score = (
        W_PROB * probability
        + W_UNCERTAINTY * uncertainty_penalty
        + W_STABILITY * stability
    )

    return round(min(max(score, 0.0), 1.0), 4)


class ScientificSelectionStrategy:
    """
    Substitui o SelectionStrategy heurístico por ranking científico.

    Filtra, ordena e seleciona Top N picks usando:
        - P_calibrada como componente principal
        - Penalidade de incerteza (std / E[X])
        - Estabilidade por família de mercado

    Compatível com interface legada (evaluate_candidates + select_top_n).
    """

    def __init__(self, min_confidence: float = 0.55) -> None:
        self.min_confidence = min_confidence

    def evaluate_candidates(
        self,
        candidates: List[Dict[str, Any]],
        market_data: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> List[BettingPick]:
        """
        Avalia candidatos e atribui score científico.

        Args:
            candidates: [{match_id, match_name, result: PredictionResult}, ...]
            market_data: Opcional. Dict[match_id -> {
                'distributions': Dict[family -> {expected, std, prob_over, ci_90}],
                'league': str,
                'stability': float,
            }]

        Returns:
            Lista de BettingPick ranqueados por scientific_score.
        """
        picks: List[BettingPick] = []
        market_data = market_data or {}

        for cand in candidates:
            res: PredictionResult = cand['result']

            if res.consensus_confidence < self.min_confidence:
                continue

            match_id = cand['match_id']
            mdata = market_data.get(int(match_id), {})

            # Extrair dados científicos se disponíveis
            distributions = mdata.get('distributions', {})
            league = mdata.get('league', cand.get('league', ''))
            stability = mdata.get('stability', 0.7)  # default conservador

            # Encontrar família do mercado principal
            family = _infer_family_from_bet(res.best_bet)
            family_dist = distributions.get(family, {})

            expected = family_dist.get('expected', res.final_prediction)
            std = family_dist.get('std', expected * 0.3 if expected > 0 else 1.0)
            prob = family_dist.get('prob_over', res.consensus_confidence) if 'Over' in res.best_bet else family_dist.get('prob_under', res.consensus_confidence)
            ci_90 = family_dist.get('ci_90', (max(0, expected - 2 * std), expected + 2 * std))
            ece = family_dist.get('ece', 0.10)

            # Score científico
            rank_score = compute_scientific_score(
                probability=res.consensus_confidence,
                uncertainty=std,
                expected_value=expected,
                stability=stability,
            )

            fair_odd = round(1.0 / res.consensus_confidence, 2) if res.consensus_confidence > 0 else 0.0

            # Montar distributions serializáveis para o frontend
            serialized_markets = {}
            for fam, fdist in distributions.items():
                serialized_markets[fam] = {
                    'expected': round(fdist.get('expected', 0), 2),
                    'std': round(fdist.get('std', 0), 2),
                    'prob_over': round(fdist.get('prob_over', 0), 4),
                    'prob_under': round(fdist.get('prob_under', 0), 4),
                    'fair_odd_over': round(1.0 / max(fdist.get('prob_over', 0.01), 0.01), 2),
                    'fair_odd_under': round(1.0 / max(fdist.get('prob_under', 0.01), 0.01), 2),
                    'ci_90': fdist.get('ci_90', [0, 0]),
                    'line': fdist.get('line', 0),
                }

            pick = BettingPick(
                match_id=cand['match_id'],
                match_name=cand['match_name'],
                selection=res.best_bet,
                line=res.line_val,
                probability=res.consensus_confidence,
                fair_odd=fair_odd,
                raw_score=res.final_prediction,
                rank_score=rank_score,
                league=league,
                market_family=family,
                uncertainty=round(std, 2),
                ece_local=round(ece, 4),
                stability_score=round(stability, 2),
                ci_90_low=round(ci_90[0], 1),
                ci_90_high=round(ci_90[1], 1),
                expected_corners=round(expected, 1),
                market_distributions=serialized_markets,
            )
            picks.append(pick)

        # Ordenar por score científico (desc)
        picks.sort(key=lambda x: x.rank_score, reverse=True)
        return picks

    def select_top_n(self, picks: List[BettingPick], n: int = 7) -> List[BettingPick]:
        """Retorna os Top N picks."""
        return picks[:n]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_family_from_bet(bet_label: str) -> str:
    """Infere a família de mercado a partir do label da aposta."""
    lower = bet_label.lower()

    if any(x in lower for x in ['1t', '1h', 'ht ']):
        if any(x in lower for x in ['home', 'casa']):
            return 'ht_home'
        if any(x in lower for x in ['away', 'vis', 'fora']):
            return 'ht_away'
        return 'ht_total'

    if any(x in lower for x in ['2t', '2h', 'st ']):
        if any(x in lower for x in ['home', 'casa']):
            return 'ht2_home'
        if any(x in lower for x in ['away', 'vis', 'fora']):
            return 'ht2_away'
        return 'ht2_total'

    if any(x in lower for x in ['home', 'casa']):
        return 'ft_home'
    if any(x in lower for x in ['away', 'vis', 'fora']):
        return 'ft_away'

    return 'ft_total'
