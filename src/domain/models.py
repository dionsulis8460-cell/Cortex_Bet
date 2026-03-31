"""
Domain Models - Cortex Bet V3.

Módulo centralizado com todas as dataclasses de domínio do sistema.
Single Source of Truth para evitar duplicação de modelos entre camadas.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

import pandas as pd


# ============================================================================
# Entidades Base
# ============================================================================

@dataclass(frozen=True)
class Team:
    """Entidade imutável representando um time."""
    id: int
    name: str
    league: str


@dataclass
class MatchStats:
    """
    Estatísticas detalhadas de uma partida.

    Regra de Negócio:
        Armazena métricas de jogo usadas para feature engineering
        e análise estatística (Monte Carlo, Poisson).
    """
    corners_home: int = 0
    corners_away: int = 0
    goals_home: int = 0
    goals_away: int = 0
    possession_home: float = 0.5
    possession_away: float = 0.5


@dataclass
class Prediction:
    """Previsão genérica de um modelo."""
    model_version: str
    predicted_value: float
    confidence: float
    fair_odds: float
    raw_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Match:
    """
    Entidade principal representando uma partida de futebol.

    Regra de Negócio:
        Agrega dados do time, placar, estatísticas e previsões
        em uma estrutura unificada.
    """
    id: int
    home_team: Team
    away_team: Team
    timestamp: datetime
    status: str  # 'scheduled', 'inprogress', 'finished'
    current_score: Dict[str, int] = field(default_factory=lambda: {"home": 0, "away": 0})
    stats: Optional[MatchStats] = None
    predictions: List[Prediction] = field(default_factory=list)

    @property
    def total_corners(self) -> int:
        if self.stats:
            return self.stats.corners_home + self.stats.corners_away
        return 0


# ============================================================================
# Resultado de Previsão (ex-ManagerAI)
# ============================================================================

@dataclass
class PredictionResult:
    """
    Resultado padronizado da previsão do ManagerAI.

    Regra de Negócio:
        Encapsula o output completo do pipeline de previsão, incluindo
        valores do Ensemble (LightGBM+RF Stacking), Neural Challenger (MLP),
        confiança consensual, e mercados alternativos do Statistical Analyzer.
    """
    match_id: int
    home_team: str
    away_team: str

    # Decisões
    final_prediction: float
    line_val: float
    best_bet: str
    is_over: bool

    # Confidências
    ensemble_confidence: float
    neural_confidence: float
    consensus_confidence: float

    # Valores dos Componentes
    ensemble_raw: float
    neural_raw: float  # Total corners (lambda)

    # Fairness
    fair_odds: float
    ev_percentage: float

    # Metadata
    features: pd.DataFrame = field(default_factory=pd.DataFrame)
    feedback_text: str = ""

    # Statistical Engine Outputs
    alternative_markets: List[Dict] = field(default_factory=list)
    suggestions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário (API/JSON)."""
        return {
            'match_id': self.match_id,
            'prediction': self.best_bet,
            'line': self.line_val,
            'confidence': self.consensus_confidence,
            'ensemble_val': self.ensemble_raw,
            'neural_val': self.neural_raw,
            'fair_odds': self.fair_odds,
            'ev': self.ev_percentage,
            'feedback': self.feedback_text,
            'alternative_markets': self.alternative_markets,
            'suggestions': self.suggestions
        }


# ============================================================================
# Seleção de Apostas (ex-SelectionStrategy)
# ============================================================================

@dataclass
class BettingPick:
    """
    Aposta ranqueada pelo Manager AI.

    Regra de Negócio:
        Representa uma seleção filtrada e ordenada por rank_score.
        Usada pelo SelectionStrategy para selecionar Top N picks.
    """
    match_id: int
    match_name: str
    selection: str   # Ex: "Over 9.5"
    line: float
    probability: float
    fair_odd: float
    raw_score: float
    rank_score: float  # Para ordenação

    # --- Scientific fields (Phase 2) ---
    league: str = ""
    market_family: str = "ft_total"
    uncertainty: float = 0.0       # std da distribuição MC
    ece_local: float = 0.0         # ECE estimado da família (do calibrador)
    stability_score: float = 0.0   # 1 - cv (coeficiente de variação normalizado)
    ci_90_low: float = 0.0         # Intervalo de credibilidade 90% — limite inferior
    ci_90_high: float = 0.0        # Intervalo de credibilidade 90% — limite superior
    expected_corners: float = 0.0  # E[X] do mercado
    market_distributions: Dict[str, Any] = field(default_factory=dict)  # 9 mercados derivados
