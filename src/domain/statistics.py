import numpy as np
from scipy.stats import poisson
from typing import Tuple

class StatisticalModels:
    """
    Core statistical models for football analytics (PhD Level implementations).
    """
    
    @staticmethod
    def calculate_poisson_probability(lambda_val: float, k: int) -> float:
        """Calculates Poisson probability for k events given lambda."""
        return poisson.pmf(k, lambda_val)

    @staticmethod
    def calculate_over_under_probability(lambda_val: float, line: float) -> Tuple[float, float]:
        """
        Calculates Over/Under probabilities for a given line using Poisson distribution.
        Returns: (Prob Over, Prob Under)
        """
        prob_under = poisson.cdf(np.floor(line), lambda_val)
        prob_over = 1 - prob_under
        return prob_over, prob_under

    @staticmethod
    def calculate_exact_score_probability(lambda_home: float, lambda_away: float, max_val: int = 20) -> np.ndarray:
        """
        Calculates an exact score matrix (e.g., for goals or corners).
        """
        home_probs = poisson.pmf(np.arange(max_val), lambda_home)
        away_probs = poisson.pmf(np.arange(max_val), lambda_away)
        return np.outer(home_probs, away_probs)
