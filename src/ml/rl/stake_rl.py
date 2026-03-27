import numpy as np

class StakeRLBranch:
    """
    Reinforcement Learning logic for dynamic Stake Management (PhD Level).
    Instead of fixed Kelly, an agent learns to adjust betting units
    based on model uncertainty, historical drawdown, and league-specific variance.
    """
    
    def __init__(self, initial_bankroll=1000):
        self.bankroll = initial_bankroll
        self.history = []

    def calculate_optimal_stake(self, model_prob, fair_odds, current_odds):
        """
        Policy function to determine stake size.
        In a real RL implementation, this would be a forward pass through a 
        Neural Network (DQN/PPO) trained on historical betting episodes.
        """
        edge = (model_prob * current_odds) - 1
        
        if edge <= 0:
            return 0.0
            
        # Standard Kelly as baseline
        kelly_fraction = edge / (current_odds - 1)
        
        # RL Adjustment Factor (Placeholder for agent policy)
        # The agent reduces stake if the recent variance is high
        adjustment = np.clip(1.0 - (self._get_recent_variance() * 5), 0.2, 1.0)
        
        return kelly_fraction * adjustment * self.bankroll * 0.1 # Max 10% of bankroll

    def _get_recent_variance(self):
        # Calculates variance of the last 10 bets to detect "cold streaks"
        if len(self.history) < 10:
            return 0.0
        return np.var(self.history[-10:])

    def update_state(self, bet_result):
        self.history.append(bet_result)
        self.bankroll += bet_result
