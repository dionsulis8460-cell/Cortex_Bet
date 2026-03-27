import joblib
import os
from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np
from scipy.stats import poisson, nbinom

# TASK 2: FeatureStore is the single source of truth for inference features.
# neural_engine delegates here instead of duplicating dummy-row logic.
from src.features.feature_store import FeatureStore
from src.models.base_predictor import BasePredictor

class NeuralChallenger(BasePredictor):
    """
    The 'Challenger' Model.
    Now powered by a Trained Neural Network (MLPRegressor).
    """
    
    def __init__(self):
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
            
    @property
    def is_ready(self) -> bool:
        return self.is_trained

    @property
    def version(self) -> str:
        return "Neural_Challenger_MLP_v1.0"

    def filter_low_odds(self, predictions: List[Dict]) -> List[Dict]:
        """
        Filters predictions based on Odds/Probability risk management.
        Removes 'Junk Odds' (< 1.25) unless there is a huge edge.
        """
        filtered = []
        for pred in predictions:
            prob = pred['confidence']
            fair_odd = pred['fair_odds']
            
            # Floor Check: Odds below 1.15 are virtually unbettable (high risk/low reward)
            if fair_odd < 1.15:
                continue
                
            # Value Check: If Odd < 1.30, we demand stricter edge or high confidence
            if fair_odd < 1.30:
                # Only keep if very high confidence but valid
                if prob < 0.85: # If < 85% confident, 1.30 is bad value
                    continue
            
            filtered.append(pred)
        return filtered

    def _prepare_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Aligns input DataFrame to match the features expected by the trained model."""
        if hasattr(self.scaler, 'feature_names_in_'):
            expected_cols = self.scaler.feature_names_in_
            
            # Create a copy to avoid SettingWithCopyWarning
            df_aligned = features_df.copy()
            
            # Add any missing required columns with 0.0
            missing_cols = [c for c in expected_cols if c not in df_aligned.columns]
            if missing_cols:
                for c in missing_cols:
                    df_aligned[c] = 0.0
                    
            # Return only the expected columns in the exact order
            return df_aligned[expected_cols]
            
        return features_df

    def predict_lambda(self, features_df: pd.DataFrame) -> Tuple[float, float]:
        """
        [NEW] Predicts directly from pre-computed features (Feature Store integration).
        Implements BasePredictor.predict_lambda.
        Returns: (lambda_home, lambda_away)
        """
        if not self.is_trained:
            return 0.0, 0.0
            
        try:
            # 1. Scale
            X_input = self._prepare_features(features_df)
            X_scaled = self.scaler.transform(X_input)
            
            # 2. Predict
            prediction = self.model.predict(X_scaled)[0] # Shape (2,)
            
            # 3. Handle Multi-Output
            if isinstance(prediction, (list, np.ndarray)) and len(prediction) >= 2:
                l_home = float(prediction[0])
                l_away = float(prediction[1])
            else:
                # Fallback
                l_home = float(prediction) / 2
                l_away = float(prediction) / 2
                
            # 4. Clamp
            l_home = max(2.0, min(12.0, l_home))
            l_away = max(2.0, min(12.0, l_away))
            
            return l_home, l_away
        except Exception as e:
            print(f"[Neural] Feature Prediction Error: {e}")
            return 0.0, 0.0

        
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
                # TASK 2: Delegate to FeatureStore — single source of truth.
                # Previously this block duplicated dummy-row + create_advanced_features.
                h_id = match_stats.get('home_id')
                a_id = match_stats.get('away_id')

                features_vector = FeatureStore.build_match_features(
                    home_id=h_id,
                    away_id=a_id,
                    df_history=df_history,
                )

                # Scale and predict
                X_input = self._prepare_features(features_vector)
                X_scaled = self.scaler.transform(X_input)
                prediction = self.model.predict(X_scaled)[0]  # Shape (2,)

                if isinstance(prediction, (list, np.ndarray)) and len(prediction) >= 2:
                    l_home = float(prediction[0])
                    l_away = float(prediction[1])
                    neural_lambda = l_home + l_away
                else:
                    neural_lambda = float(prediction)

                neural_lambda = max(3.0, min(22.0, neural_lambda))
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
                
                # FIX: Minimum Variance Enforcement for Football (Corners are noisy)
                # Minimum CV of 0.15 (Coefficient of Variation)
                min_sigma2 = mu * 1.15 
                sigma2 = max(hist_var, min_sigma2) # Ensure we don't underestimate risk
                
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
                
                # P1-F FIX: Dynamic Blend instead of 60/40 hardcoded.
                # Se o MLP acha que a variância é muito alta (incerteza), dá mais peso à Estatística.
                # Se o MLP está confiante (equidispersion), ele domina a decisão.
                
                neural_weight = 0.5 + (0.35 * (mu / max(sigma2, mu))) # varia de 0.5 a 0.85 baseado em incerteza
                stat_weight = 1.0 - neural_weight
                
                final_prob = (neural_weight * neural_prob) + (stat_weight * stat_prob)
                final_prob = round(final_prob, 3)
            
            # Cap confidence at 90% to avoid arrogance (Label Smoothing effect)
            final_prob = min(0.90, final_prob)
            
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
            
        return self.filter_low_odds(predictions)

    def get_neural_distributions(self, match_stats: Dict[str, Any], df_history: pd.DataFrame) -> Dict[str, float]:
        """
        [DEPRECATED] Legacy method for the statistical engine.
        Use predict_distribution() via the BasePredictor interface.
        """
        if not self.is_trained or df_history is None or df_history.empty:
            return {'lambda_home': 0, 'lambda_away': 0, 'variance_factor': 1.0}

        try:
             h_id = match_stats.get('home_id')
             a_id = match_stats.get('away_id')

             features_vector = FeatureStore.build_match_features(
                 home_id=h_id,
                 away_id=a_id,
                 df_history=df_history,
             )
             return self.predict_distribution(features_vector)
             
        except Exception as e:
            print(f"[NeuralEngine] Dist Gen Error: {e}")
            return {'lambda_home': 0, 'lambda_away': 0, 'variance_factor': 1.0}

    def predict_distribution(self, features_df: pd.DataFrame) -> Dict[str, float]:
        """
        Generates full distributional parameters for the match.
        Implements BasePredictor.predict_distribution.
        
        Returns:
            Dict: {'lambda_home': float, 'lambda_away': float, 'variance_factor': float}
        """
        # TASK 2: Delegate to FeatureStore — removing the second duplicate of the
        # dummy-row + create_advanced_features block that existed here.
        if not self.is_ready or features_df is None or features_df.empty:
            return {'lambda_home': 0, 'lambda_away': 0, 'variance_factor': 1.0}

        try:
             # Scale 
             X_input = self._prepare_features(features_df)
             X_scaled = self.scaler.transform(X_input)

             # Note: predict_distribution() receives only features_df (no df_history in scope).
             # Variance is estimated from the prediction itself via overdispersion heuristic.
             
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
                 # We don't have df_history inside predict_distribution anymore (encapsulation),
                 # but we can check if the naive variance formula applies, or just return 1.0
                 # For now, default to equidispersion until we pass history into predictors globally.
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
