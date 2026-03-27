"""
SelectionStrategy - Estratégia de Seleção de Apostas.

Regra de Negócio:
    Filtra, ordena e seleciona as melhores apostas (Top N)
    com base em confiança mínima e ranking.
"""

from typing import List, Dict, Any

# Domain Models (Single Source of Truth)
from src.domain.models import PredictionResult, BettingPick
    
class SelectionStrategy:
    """
    The 'Manager AI'.
    Responsible for Filtering, Sorting, and Selecting the Best Bets (Top 7).
    
    Principles:
    1. Value Betting (Price > Cost) - Placeholder for now.
    2. Confidence Thresholding.
    3. Portfolio Management (Top N limit).
    """
    
    def __init__(self, min_confidence: float = 0.60):
        self.min_confidence = min_confidence
        
    def evaluate_candidates(self, candidates: List[Dict[str, Any]]) -> List[BettingPick]:
        """
        Takes a list of raw prediction results and returns ranked Picks.
        
        Args:
            candidates: List of dicts containing {match_id, result: PredictionResult, match_name}
        """
        picks = []
        
        for cand in candidates:
            res: PredictionResult = cand['result']
            
            # 1. Filter: Minimum Confidence
            # We relax this slightly for high-value potential, but default 60%
            if res.consensus_confidence < self.min_confidence:
                continue
                
            # 2. Ranking Score
            # Currently just confidence, but can include Edge vs Market
            rank_score = res.consensus_confidence 
            
            pick = BettingPick(
                match_id=cand['match_id'],
                match_name=cand['match_name'],
                selection=res.best_bet,
                line=res.line_val,
                probability=res.consensus_confidence,
                fair_odd=1.0/res.consensus_confidence if res.consensus_confidence > 0 else 0,
                raw_score=res.final_prediction,
                rank_score=rank_score
            )
            picks.append(pick)
            
        # 3. Sort by Rank (Desc)
        picks.sort(key=lambda x: x.rank_score, reverse=True)
        
        return picks

    def select_top_n(self, picks: List[BettingPick], n: int = 7) -> List[BettingPick]:
        """Truncates the list to the Top N picks."""
        return picks[:n]
