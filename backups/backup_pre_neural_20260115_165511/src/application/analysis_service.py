from typing import List, Optional
import logging
from src.domain.models import Match, Team, Prediction
from src.domain.statistics import StatisticalModels
from src.domain.bayesian import BayesianAnalytics

class MatchAnalysisService:
    """
    Orchestrates the analysis of matches by combining data infrastructure
    and statistical modeling.
    """
    
    def __init__(self, repository, ml_model):
        self.repository = repository
        self.ml_model = ml_model
        self.logger = logging.getLogger(__name__)

    async def analyze_match(self, match_id: int) -> Optional[Match]:
        """
        Full analysis pipeline for a single match.
        """
        self.logger.info(f"Starting analysis for match {match_id}")
        
        # 1. Fetch data from repository
        match_data = await self.repository.get_match_by_id(match_id)
        if not match_data:
            self.logger.warning(f"Match {match_id} not found in repository.")
            return None

        # 2. ML Inference (Point Estimate)
        prediction_result = self.ml_model.predict(match_data)
        
        # 3. Apply Statistical Layer (Uncertainty & Probs)
        # Using PhD-level Bayesian Inference (Injected logic)
        prob_over = 0.5 # Default fallback
        
        # Future: Call BayesianAnalytics.estimate_team_strengths here
        # For now, we use the Poisson distribution with lambda from ML
        prob_over, prob_under = StatisticalModels.calculate_over_under_probability(
            lambda_val=prediction_result['expected_value'],
            line=10.5
        )
        
        # 4. Create Prediction Domain Object
        prediction = Prediction(
            model_version=self.ml_model.version,
            predicted_value=prediction_result['expected_value'],
            confidence=prediction_result['confidence'],
            fair_odds=1.0 / prob_over if prob_over > 0 else 999.0,
            raw_score=prediction_result.get('expected_value'),
            metadata={"prob_over": prob_over, "prob_under": prob_under}
        )
        
        match_data.predictions.append(prediction)
        
        # 5. Persist and Return
        await self.repository.save_match(match_data)
        return match_data
