import joblib
import os
from typing import Dict, List, Any
import pandas as pd
import numpy as np
from scipy.stats import poisson, nbinom

from src.ml.features_v2 import create_advanced_features

class NeuralChallenger:
    """
    The 'Challenger' Model.
    Now powered by a Trained Neural Network (MLPRegressor).
    """
    
    def __init__(self):
        self.version = "Neural_Challenger_MLP_v1.0"
        self.min_confidence = 0.55
        
        # Load Model Artifacts
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_path, '..', '..', 'models', 'neural_challenger_mlp.joblib')
            scaler_path = os.path.join(base_path, '..', '..', 'models', 'neural_scaler.joblib')
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.is_trained = True
                print(f"[Neural] Loaded Trained Model v1.0")
            else:
                print("[Neural] Warning: Model artifacts not found. Using fallback.")
                self.is_trained = False
        except Exception as e:
            print(f"[Neural] Error loading model: {e}")
            self.is_trained = False
        
    def predict_match(self, match_stats: Dict[str, Any], statistical_probs: List[Dict], df_history: pd.DataFrame = None) -> List[Dict]:
        """
        Generates predictions using the Trained Neural Network.
        
        Args:
            match_stats: Basic match metadata.
            statistical_probs: Statistical model picks (for challenging).
            df_history: Historical data (Required for feature generation).
        """
        predictions = []
        neural_lambda = None
        feature_context = "Neural: Insufficient Data"
        
        # --- 1. REAL INFERENCE (MLP Predicts Expected Corners) ---
        if self.is_trained and df_history is not None and not df_history.empty:
            try:
                # A. Generate Features for this single match context
                # Filter relevant history
                h_id = match_stats.get('home_id')
                a_id = match_stats.get('away_id')
                
                relevant_games = df_history.loc[
                    (df_history['home_team_id'] == h_id) | (df_history['away_team_id'] == h_id) |
                    (df_history['home_team_id'] == a_id) | (df_history['away_team_id'] == a_id)
                ].copy()
                
                if not relevant_games.empty:
                    # Create Dummy Row for prediction
                    import time
                    dummy_row = pd.DataFrame([{
                        'match_id': 999999999,
                        'start_timestamp': int(time.time()) + 86400,
                        'home_team_id': h_id, 'away_team_id': a_id,
                        'corners_home_ft': 0, 'corners_away_ft': 0,
                        'shots_ot_home_ft': 0, 'shots_ot_away_ft': 0,
                        'home_score': 0, 'away_score': 0,
                        'corners_home_ht': 0, 'corners_away_ht': 0,
                        'dangerous_attacks_home': 0, 'dangerous_attacks_away': 0,
                        'tournament_id': match_stats.get('tournament_id', 'Unknown'),
                        'tournament_name': 'Prediction'
                    }])
                    df_combined = pd.concat([relevant_games, dummy_row], ignore_index=True)
                    
                    # Generate Features (Pipeline)
                    X, _, _, _ = create_advanced_features(df_combined)
                    
                    # Extract last row (current match)
                    features_vector = X.iloc[[-1]] # Keep as DataFrame for scaler
                    
                    # B. Scale Features
                    X_scaled = self.scaler.transform(features_vector)
                    
                    # C. Predict Output (Multi-Output: [Home, Away])
                    prediction = self.model.predict(X_scaled)[0] # Shape (2,)
                    
                    # Handle Multi-Output (Sum for Total Corners context)
                    if isinstance(prediction, (list, np.ndarray)) and len(prediction) >= 2:
                        l_home = float(prediction[0])
                        l_away = float(prediction[1])
                        neural_lambda = l_home + l_away
                    else:
                        # Fallback for old single-output models (if any)
                        neural_lambda = float(prediction)
                        
                    # Clamp reasonable values (e.g. 5 to 20)
                    neural_lambda = max(5.0, min(20.0, neural_lambda))
                    
                    feature_context = f"Neural Expected: {neural_lambda:.2f} corners"
                    
            except Exception as e:
                print(f"[NeuralEngine] Inference Error: {e}")
                neural_lambda = None


        # --- 2. CHALLENGE LOGIC (Probabilistic) ---
        # Scientific Upgrade: Check for Overdispersion (Variance > Mean)
        # If Overdispersed -> Negative Binomial (Better for corners)
        # If Equidispersed -> Poisson (Simpler)
        
        hist_var = 0.0
        if df_history is not None and not df_history.empty:
            # Quick variance check on recent games
            try:
                 h_id = match_stats.get('home_id')
                 a_id = match_stats.get('away_id')
                 recent = df_history[
                    (df_history['home_team_id'].isin([h_id, a_id])) | 
                    (df_history['away_team_id'].isin([h_id, a_id]))
                 ].head(20) # Last 20 games combined
                 if not recent.empty:
                     # Calculate variance of total corners
                     total_corners = recent['corners_home_ft'] + recent['corners_away_ft']
                     hist_var = total_corners.var()
            except:
                hist_var = 0.0

        for pick in statistical_probs:
            stat_prob = pick.get('Prob', 0.5)
            line = pick.get('raw_line', 0.5)
            market_type = pick.get('Mercado', '') 
            side = 'Over' if ('Over' in pick.get('Seleção', '') or 'Mais' in pick.get('Seleção', '')) else 'Under'
            
            final_prob = stat_prob # Fallback
            
            if neural_lambda is not None:
                k = int(line) # Floor (e.g., 10.5 -> 10)
                
                # Distribution Selection (Scientific Rigor)
                mu = neural_lambda
                sigma2 = max(hist_var, mu) # Variance usually > Mean in football
                
                if sigma2 > mu:
                    # Overdispersion -> Negative Binomial
                    # Conversion from Mean/Var to n/p
                    # Var = n * (1-p) / p^2
                    # Mean = n * (1-p) / p
                    # -> p = Mean / Var
                    # -> n = Mean^2 / (Var - Mean)
                    
                    p_nb = mu / sigma2
                    n_nb = (mu ** 2) / (sigma2 - mu)
                    
                    dist_model = "NegBinom"
                    if side == 'Over':
                        neural_prob = 1 - nbinom.cdf(k, n_nb, p_nb)
                    else:
                        neural_prob = nbinom.cdf(k, n_nb, p_nb)
                else:
                    # Equidispersion -> Poisson
                    dist_model = "Poisson"
                    if side == 'Over':
                        neural_prob = 1 - poisson.cdf(k, mu)
                    else:
                        neural_prob = poisson.cdf(k, mu)
                
                # Update context if not set detailed
                if "Dist" not in feature_context:
                    feature_context += f" | {dist_model} (Var {sigma2:.1f})"
                
                # Blend: 60% Neural, 40% Statistical
                final_prob = (0.6 * neural_prob) + (0.4 * stat_prob)
                final_prob = round(final_prob, 3)
            
            predictions.append({
                'match_id': match_stats.get('id'),
                'model_version': self.version,
                'prediction_value': line,
                'prediction_label': pick.get('Seleção'),
                'confidence': final_prob,
                'category': 'Neural_Shadow',
                'market_group': market_type,
                'odds': pick.get('Odd', 0),
                'feedback_text': feature_context,
                'fair_odds': round(1/final_prob, 2) if final_prob > 0 else 0
            })
            
        return predictions

    def get_neural_distributions(self, match_stats: Dict[str, Any], df_history: pd.DataFrame) -> Dict[str, float]:
        """
        Generates full distributional parameters for the match.
        Used by the Statistical Engine for Neural-Guided Calculations.
        
        Returns:
            Dict: {'lambda_home': float, 'lambda_away': float, 'variance_factor': float}
        """
        # 1. Total Lambda (Already existing logic, extracted)
        neural_lambda = None
        
        # We need to rerun the feature gen logic or refactor. 
        # For safety/speed, let's keep it self-contained here or reuse if possible.
        # Ideally, predict_match should call this, but predict_match is legacy shadow mode.
        # We'll duplicate the inference logic cleanly here for the new unified flow.
        
        if not self.is_trained or df_history is None or df_history.empty:
             return {'lambda_home': 0, 'lambda_away': 0, 'variance_factor': 1.0}
             
        try:
             # Feature Gen (Same as predict_match)
             h_id = match_stats.get('home_id')
             a_id = match_stats.get('away_id')
             
             relevant_games = df_history.loc[
                (df_history['home_team_id'] == h_id) | (df_history['away_team_id'] == h_id) |
                (df_history['home_team_id'] == a_id) | (df_history['away_team_id'] == a_id)
             ].copy()
             
             if relevant_games.empty:
                 return {'lambda_home': 0, 'lambda_away': 0, 'variance_factor': 1.0}

             import time
             dummy_row = pd.DataFrame([{
                'match_id': 999999999,
                'start_timestamp': int(time.time()) + 86400,
                'home_team_id': h_id, 'away_team_id': a_id,
                'corners_home_ft': 0, 'corners_away_ft': 0,
                'shots_ot_home_ft': 0, 'shots_ot_away_ft': 0,
                'home_score': 0, 'away_score': 0,
                'corners_home_ht': 0, 'corners_away_ht': 0,
                'dangerous_attacks_home': 0, 'dangerous_attacks_away': 0,
                'tournament_name': 'Prediction',
                'tournament_id': match_stats.get('tournament_id', 'Unknown')
             }])
             df_combined = pd.concat([relevant_games, dummy_row], ignore_index=True)
             
             X, _, _, df_display = create_advanced_features(df_combined)
             
             if X.empty:
                return {'lambda_home': 0, 'lambda_away': 0, 'variance_factor': 1.0}

             features_vector = X.iloc[[-1]]
             X_scaled = self.scaler.transform(features_vector)
             
             # =================================================================
             # EMERGENCY FIX: Multi-Output MLP (Direct Home/Away Prediction)
             # =================================================================
             # ANTES: total_lambda = model.predict() → Split via heurística
             # AGORA: prediction = [lambda_home, lambda_away] direto da rede
             # =================================================================
             
             prediction = self.model.predict(X_scaled)[0]  # Shape: (2,)
             
             lambda_home = float(prediction[0])
             lambda_away = float(prediction[1])
             total_lambda = lambda_home + lambda_away
             
             # Clamp reasonable values
             lambda_home = max(2.0, min(12.0, lambda_home))
             lambda_away = max(2.0, min(12.0, lambda_away))
             total_lambda = lambda_home + lambda_away
             
             # 3. Estimate Variance Factor (Overdispersion)
             # If recent games were high variance, we expect high variance.
             # Simple heuristic: Variance = Mean * Factor
             
             hist_var = 0.0
             hist_mean = 0.0
             try:
                 recent = relevant_games.tail(20)
                 total_corners = recent['corners_home_ft'] + recent['corners_away_ft']
                 hist_var = total_corners.var()
                 hist_mean = total_corners.mean()
             except:
                 pass
                 
             variance_factor = 1.0
             if hist_mean > 0 and hist_var > hist_mean:
                 # Calculate observed overdispersion ratio
                 # Damping factor: Don't assume full chaos matches history immediately
                 raw_factor = hist_var / hist_mean
                 variance_factor = 1.0 + (raw_factor - 1.0) * 0.5 # 50% damping
                 
             return {
                 'lambda_home': lambda_home,
                 'lambda_away': lambda_away,
                 'variance_factor': variance_factor
             }
             
        except Exception as e:
            print(f"[NeuralEngine] Dist Gen Error: {e}")
            return {'lambda_home': 0, 'lambda_away': 0, 'variance_factor': 1.0}
