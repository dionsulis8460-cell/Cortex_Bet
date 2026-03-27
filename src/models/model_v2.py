"""
Modelo Profissional de ML para Previsão de Escanteios - Versão 2.1

Changes v2.1:
    - StackingRegressor (Sklearn) substituindo pesos manuais.
    - RPS (Ranked Probability Score) como métrica de validação.
    - Synthetic Odds Generator (Naive Market Simulation).
    - Imputação e Pipeline robustos.

Autor: Refatoração baseada em feedback de Cientista de Dados Sênior
Data: 2025-12-17
"""

import lightgbm as lgb
from typing import Tuple, Dict
import xgboost as xgb
from catboost import CatBoostRegressor
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from scipy.stats import poisson
import optuna

# Sklearn ecosystem
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import StackingRegressor, RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.model_selection import TimeSeriesSplit

# Imbalanced Learning: SMOTE removido na v2.1 (instável para regressão)

# =====================================================================
# SPRINT 9, TAREFA 3.1: Focal Weighting (Fase 3)
# =====================================================================
# Importa FocalLoss para calcular sample weights baseados em dificuldade
# Baseado em Lin et al. (2017) - "Focal Loss for Dense Object Detection" - ICCV
# Adaptação: Usa focal term (1-p)^γ como sample weight para Tweedie regression
# Agora padrão na v2.1

class TimeAwareStacking(BaseEstimator, RegressorMixin):
    """
    Implementação manual de Stacking para Séries Temporais.
    Evita o erro de 'cross_val_predict only works for partitions' do sklearn
    e garante zero data leakage (Forward Chaining).
    """
    def __init__(self, base_estimators, final_estimator, n_splits=3):
        self.base_estimators = base_estimators
        self.final_estimator = final_estimator
        self.n_splits = n_splits
        self.trained_base_models_ = []
        self.trained_final_model_ = None

    def fit(self, X, y, sample_weight=None):
        """
        Treina o Stacking com suporte a sample weights (Sprint 9, Fase 3).
        
        Args:
            X: Features
            y: Target
            sample_weight: Sample weights (opcional, para Focal Weighting)
        """
        # 1. Gerar OOF (Out-of-Fold) Predictions usando TimeSeriesSplit
        # As primeiras amostras (do primeiro split de treino) não terão previsão
        # e portanto não serão usadas para treinar o meta-modelo.
        
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        meta_features = []
        meta_targets = []
        
        # Garante índices resetados para facilitar slices
        X = X.reset_index(drop=True)
        y = y.reset_index(drop=True)
        if sample_weight is not None:
            sample_weight = pd.Series(sample_weight).reset_index(drop=True)
        
        print(f"      🔨 Stacking Interno ({self.n_splits} splits)...")
        
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # Sample weights para este fold
            w_tr = sample_weight.iloc[train_idx] if sample_weight is not None else None
            
            fold_preds = []
            for name, model in self.base_estimators:
                # Clone para não afetar o modelo original
                from sklearn.base import clone
                cloned_model = clone(model)
                
                # Tenta passar sample_weight se o modelo suportar
                # Pipelines geralmente não propagam sample_weight corretamente
                from sklearn.pipeline import Pipeline
                if w_tr is not None and not isinstance(cloned_model, Pipeline):
                    try:
                        cloned_model.fit(X_tr, y_tr, sample_weight=w_tr)
                    except (TypeError, ValueError) as e:
                        # Modelo não suporta sample_weight ou há erro de propagação
                        cloned_model.fit(X_tr, y_tr)
                else:
                    cloned_model.fit(X_tr, y_tr)
                
                pred = cloned_model.predict(X_val)
                fold_preds.append(pred)
            
            # Stack das previsões desse fold (n_samples, n_models)
            fold_meta_X = np.column_stack(fold_preds)
            meta_features.append(fold_meta_X)
            meta_targets.append(y_val)
            
        # 2. Treinar Meta-Learner
        if meta_features:
            X_meta_train = np.vstack(meta_features)
            y_meta_train = np.concatenate(meta_targets)
            
            self.trained_final_model_ = self.final_estimator
            self.trained_final_model_.fit(X_meta_train, y_meta_train)
        else:
            raise ValueError("Não foi possível gerar dados para o Meta-Learner. Dados insuficientes?")

        # 3. Retreinar Base Models em TODO o dataset (com sample weights se disponível)
        self.trained_base_models_ = []
        for name, model in self.base_estimators:
            from sklearn.base import clone
            from sklearn.pipeline import Pipeline
            final_base = clone(model)
            
            # Tenta passar sample_weight (skip para Pipelines)
            if sample_weight is not None and not isinstance(final_base, Pipeline):
                try:
                    final_base.fit(X, y, sample_weight=sample_weight)
                except (TypeError, ValueError):
                    final_base.fit(X, y)
            else:
                final_base.fit(X, y)
            
            self.trained_base_models_.append(final_base)
            
        return self

    def predict(self, X):
        # 1. Gerar previsões dos base models
        base_preds = []
        for model in self.trained_base_models_:
            base_preds.append(model.predict(X))
            
        # 2. Formatar para o Meta-Learner
        X_meta = np.column_stack(base_preds)
        
        # 3. Previsão final
        return self.trained_final_model_.predict(X_meta)


from src.models.base_predictor import BasePredictor

class ProfessionalPredictor(BasePredictor):
    """
    Ensemble Profissional (Stacking) para previsão de escanteios.
    Usa LightGBM e Random Forest como base, e Linear Regression como Meta-Learner.
    """
    
    def __init__(self, model_path: str = "data/corner_model_v2_professional.pkl"):
        self.model_path = Path(model_path)
        self.model = None # Stacking Regressor
        self.feature_names = None
        
        # LightGBM Params (Tweedie / Compound Poisson)
        self.lgbm_params = {
            'objective': 'tweedie',
            'tweedie_variance_power': 1.5,
            'metric': 'mae',
            'n_estimators': 300,
            'learning_rate': 0.015,
            'num_leaves': 31,
            'max_depth': 5,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'verbose': -1,
            # P1-D FIX: Parâmetros is_unbalance e scale_pos_weight foram removidos
            # porque são excludentes e não afetam regressão (objective='tweedie').
        }
        
        # =====================================================================
        # ENSEMBLE EXPANSION: XGBoost e CatBoost (Semana 3-4 do Roadmap)
        # =====================================================================
        # XGBoost Params (Count:Poisson - Similar ao Tweedie)
        # Referência: Chen & Guestrin (2016) - "XGBoost: A Scalable Tree Boosting System"
        self.xgb_params = {
            'objective': 'count:poisson',  # Distribuição Poisson para contagens
            'n_estimators': 300,
            'learning_rate': 0.015,
            'max_depth': 5,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'n_jobs': -1,
            'verbosity': 0,
            'enable_categorical': True # Fix for ValueError with category columns
        }
        
        # CatBoost Params (Poisson Loss)
        # Referência: Prokhorenkova et al. (2018) - "CatBoost: unbiased boosting with categorical features"
        self.catboost_params = {
            'loss_function': 'Poisson',    # Otimizado para contagens (corners)
            'iterations': 300,
            'learning_rate': 0.015,
            'depth': 5,
            'subsample': 0.8,
            'random_state': 42,
            'thread_count': -1,
            'verbose': 0
        }

    def _calculate_rps(self, y_true, y_pred):
        """
        Calcula Ranked Probability Score (RPS) assumindo distribuição Poisson.
        RPS é a métrica 'Padrão Ouro' para modelos probabilísticos em esportes.
        Menor é melhor.
        """
        rps_list = []
        y_true_vals = y_true.values if hasattr(y_true, 'values') else y_true
        y_pred_vals = y_pred
        
        # Vectorized implementation approximation or loop
        # Loop is safer for variable max outcomes
        for obs, mu in zip(y_true_vals, y_pred_vals):
            # Limita avaliação até 20 escanteios (probabilidade residual desprezível)
            max_outcomes = 25
            outcomes = np.arange(max_outcomes)
            
            # Cumulative Probabilities do Modelo (CDF)
            cdf_model = poisson.cdf(outcomes, mu)
            
            # Cumulative Probabilities do Real (Heaviside Step Function)
            # 0 se k < obs, 1 se k >= obs
            cdf_obs = (outcomes >= obs).astype(int) 
            
            # P1-A FIX: Divisor correto do RPS é (N_outcomes - 1)
            # Fórmula padrão de Epstein (1969): Soma((CDF_m - CDF_o)^2) / (J - 1)
            rps = np.sum((cdf_model - cdf_obs) ** 2) / (max_outcomes - 1)
            rps_list.append(rps)
            
        return np.mean(rps_list)

    def _generate_synthetic_odds(self, X: pd.DataFrame, vig: float = 0.075) -> pd.DataFrame:
        """
        Gera Odds Sintéticas baseadas em um modelo 'Naive' (Média Simples).
        Simula um Bookmaker mediano para fins de backtesting.
        
        Args:
            X: Features (usaremos médias móveis simples como proxy do Bookmaker)
            vig: Margem da casa (Juice). Padrão 7.5%.
        """
        # Bookmaker Naive usa apenas a média recente (ema_5g)
        # Se não tiver, usa média da liga (aprox 9.5)
        if 'home_ema_corners_5g' in X.columns and 'away_ema_corners_5g' in X.columns:
            naive_pred = (X['home_ema_corners_5g'] + X['away_ema_corners_5g']) / 2 + \
                         (X['home_ema_corners_5g'] + X['away_ema_corners_5g']) # Soma dos dois
            # Ops, a feature é average individual, então total = home + away
            naive_pred = (X['home_ema_corners_5g'] + X['away_ema_corners_5g']).fillna(9.5)
        else:
            naive_pred = np.full(len(X), 9.5)
            
        synthetic_data = []
        
        for pred in naive_pred:
            # Bookmaker define a linha no inteiro mais próximo ou .5
            line = round(pred) - 0.5 
            if line < 0.5: line = 0.5
            
            # Probabilidade Real (sem vig)
            prob_under = poisson.cdf(line, pred)
            prob_over = 1 - prob_under
            
            # Aplica Vig (Juice)
            # Probabilidade Implícita = Prob Real * (1 + vig)
            imp_prob_over = prob_over * (1 + vig/2)
            imp_prob_under = prob_under * (1 + vig/2)
            
            # Converte para Odds Decimais
            odd_over = 1 / imp_prob_over if imp_prob_over > 0 else 1.01
            odd_under = 1 / imp_prob_under if imp_prob_under > 0 else 1.01
            
            synthetic_data.append({
                'LINE': line,
                'O_ODDS': round(odd_over, 2),
                'U_ODDS': round(odd_under, 2),
                'is_synthetic': True
            })
            
        return pd.DataFrame(synthetic_data, index=X.index)

    def train_time_series_split(self, X: pd.DataFrame, y: pd.Series, timestamps: pd.Series, odds: pd.Series = None, n_splits: int = 5, holdout_frac: float = 0.0) -> dict:
        self.feature_names = X.columns.tolist()
        
        # Ordenação Temporal
        data = pd.DataFrame({'timestamp': timestamps, 'target': y})
        data = pd.concat([X, data], axis=1).sort_values('timestamp')
        
        # Split Holdout (Strict Chronological)
        n_total = len(data)
        n_holdout = int(n_total * holdout_frac)
        n_cv = n_total - n_holdout
        
        cv_data = data.iloc[:n_cv]
        holdout_data = data.iloc[n_cv:] if n_holdout > 0 else pd.DataFrame()
        
        # Dados para CV loop
        X_sorted = cv_data[self.feature_names]
        y_sorted = cv_data['target']
        
        print(f"📊 Dataset Split: CV={len(cv_data)} | Holdout={len(holdout_data)} ({holdout_frac*100:.1f}%)")
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        metrics = {'mae': [], 'rmse': [], 'rps': [], 'roi': [], 'win_rate': []}
        
        print(f"\n🚀 TREINAMENTO ENSEMBLE STACKING (V3.0 - Multi-Model) - {n_splits} SPLITS")
        print(f"   Modelos Base: LightGBM + XGBoost + CatBoost")
        print(f"   Meta-Learner: Ridge Regression (Weighted Voting)")
        print(f"   Métrica Validação: RPS & ROI (Synthetic Odds)")
        
        # FIX: CatBoost needs explicit cat_features list for categorical data
        cat_features = X.select_dtypes(include=['category', 'object']).columns.tolist()
        if cat_features:
            print(f"      🐱 CatBoost: Detected categorical features: {cat_features}")
        
        # Prepare params with specific cat_features for this dataset
        cb_params = self.catboost_params.copy()
        if cat_features:
            cb_params['cat_features'] = cat_features

        # Definição do Ensemble Stacking (3 Modelos)
        # Base Learners: LightGBM, XGBoost, CatBoost
        estimators = [
            ('lgbm', lgb.LGBMRegressor(**self.lgbm_params)),
            ('xgb', xgb.XGBRegressor(**self.xgb_params)),
            ('catboost', CatBoostRegressor(**cb_params))
        ]
        
        # Audit Fix 5.4: Non-negative weights — prevents physically invalid negatives.
        # All base models predict positive corner counts, so a negative weight has no
        # statistical interpretation. LinearRegression(positive=True) enforces this constraint.
        # Reference: Gneiting & Raftery (2007) — proper scoring for ensemble combination.
        final_estimator = LinearRegression(positive=True)
        
        self.model = TimeAwareStacking(
            base_estimators=estimators,
            final_estimator=final_estimator,
            n_splits=3 # CV interno
        )
        
        fold = 0
        for train_idx, test_idx in tscv.split(X_sorted):
            fold += 1
            X_train, X_test = X_sorted.iloc[train_idx], X_sorted.iloc[test_idx]
            y_train, y_test = y_sorted.iloc[train_idx], y_sorted.iloc[test_idx]
            
            print(f"\n📂 FOLD {fold}/{n_splits} | Train: {len(X_train)} | Test: {len(X_test)}")
            
            # =====================================================================
            # AUDIT FIX (Phase 1): FOCAL WEIGHTING DISABLED
            # =====================================================================
            # REMOVED: Focal Sample Weighting (Sprint 9, Tarefa 3.1)
            #
            # Rationale (PhD Audit):
            #   Focal Loss was designed for object detection (finding small objects),
            #   NOT for regression. The "difficulty" concept doesn't translate well:
            #   - A 6-corner game isn't "easy", it's just a different regime (defensive)
            #   - Giving weight=0 to low-scoring games causes model amnesia on those regimes
            #   - Result: 46% Win Rate on days dominated by defensive matches
            #
            # Impact of Removal:
            #   - Model learns ALL regimes uniformly (6-corner games = 12-corner games)
            #   - Expected: Win Rate stabilizes above 75% across all match types
            #
            # Alternative (Future):
            #   If we want regime-specific modeling, use Quantile Regression
            #   (predict 10th, 50th, 90th percentiles) instead of sample weighting.
            # =====================================================================
            
            sample_weights = None  # Uniform weighting (all samples equally important)
            
            print(f"      ⚖️ Uniform Weighting: All regimes treated equally (Focal disabled)")
            
            # Train model
            self.model.fit(X_train, y_train)
            
            # Predict
            preds = self.model.predict(X_test)
            
            # Metrics
            mae = mean_absolute_error(y_test, preds)
            rmse = np.sqrt(mean_squared_error(y_test, preds))
            rps = self._calculate_rps(y_test, preds)
            
            # ROI Simulation (Synthetic Odds se não houver reais)
            odds_test = self._generate_synthetic_odds(X_test)
            
            biz_metrics = self._evaluate_profitability(y_test, preds, odds_test, verbose=False)
            
            metrics['mae'].append(mae)
            metrics['rmse'].append(rmse)
            metrics['rps'].append(rps)
            metrics['roi'].append(biz_metrics['roi'])
            metrics['win_rate'].append(biz_metrics['win_rate'])
            
            # MUDANÇA (Sprint 5): RPS é a métrica principal
            print(f"   ✅ RPS: {rps:.4f} | MAE: {mae:.4f} | ROI (Synth): {biz_metrics['roi']:.2f}")

        # =====================================================================
        # SPRINT 9: OOT (Out-Of-Time) Validation Report
        # =====================================================================
        oot_metrics = {}
        if not holdout_data.empty:
            print(f"\n🔒 VALIDANDO NO COFRE (Last {len(holdout_data)} games)...")
            
            # 1. Treina no set de CV completo
            X_cv_full = cv_data[self.feature_names]
            y_cv_full = cv_data['target']
            # Re-aplica lógica de Focal Weights para o treino final do CV
            # AUDIT FIX (P0-A): Removido focal weighting inconsistente do OOT.
            final_sample_weights = None

            if final_sample_weights is not None:
                self.model.fit(X_cv_full, y_cv_full, sample_weight=final_sample_weights)
            else:
                self.model.fit(X_cv_full, y_cv_full)
                
            # 2. Avalia no Holdout (Futuro desconhecido)
            X_holdout = holdout_data[self.feature_names]
            y_holdout = holdout_data['target']
            
            
            
            preds_oot = self.model.predict(X_holdout)
            
            rps_oot = self._calculate_rps(y_holdout, preds_oot)
            mae_oot = mean_absolute_error(y_holdout, preds_oot)
            
            # Odds sintéticas para OOT
            odds_oot = self._generate_synthetic_odds(X_holdout)
            biz_oot = self._evaluate_profitability(y_holdout, preds_oot, odds_oot, verbose=False)
            
            print(f"   🛑 RPS (OOT): {rps_oot:.4f} (CV Avg: {np.mean(metrics['rps']):.4f})")
            print(f"   🛑 MAE (OOT): {mae_oot:.4f}")
            print(f"   🛑 ROI (OOT): {biz_oot['roi']:.2f}")
            
            delta_rps = rps_oot - np.mean(metrics['rps'])
            if delta_rps > 0.02:
                print(f"   ⚠️ ALERTA: Overfitting detectado (Delta RPS +{delta_rps:.4f})")
            else:
                print(f"   ✅ Modelo Robusto (Delta RPS {delta_rps:.4f})")
            
            oot_metrics = {
                'rps_oot': rps_oot,
                'mae_oot': mae_oot,
                'roi_oot': biz_oot['roi']
            }

        # Retrain on Full Data (CV + Holdout) for Production
        # Para produção, usamos TODO o conhecimento disponível
        X_total = data[self.feature_names]
        y_total = data['target']
        
        total_weights = None
        
        self.model.fit(X_total, y_total, sample_weight=total_weights)
        self.save_model()
        
        # Retorno prioriza RPS
        return {
            'rps_test': np.mean(metrics['rps']), 
            'mae_test': np.mean(metrics['mae']),
            'rmse_test': np.mean(metrics['rmse']),
            'roi': np.mean(metrics['roi']),
            'win_rate': np.mean(metrics['win_rate']),
            'total_bets': 0,
            'roi_percent': np.mean(metrics['roi']) * 100,
            **oot_metrics
        }

    @property
    def is_ready(self) -> bool:
        return self.model is not None

    @property
    def version(self) -> str:
        return "Professional_Ensemble_v2.1"

    def predict_lambda(self, features: pd.DataFrame) -> Tuple[float, float]:
        """
        Implements BasePredictor.predict_lambda.
        Because this model currently predicts the TOTAL match corners,
        we naively split the expectation 50/50 between Home and Away.
        """
        total = float(self.predict(features)[0])
        # Clamp to reasonable values
        total = max(4.0, min(24.0, total))
        
        # N9 FIX: Utiliza a proporção dinâmica baseada nas médias dos times se disponível
        # Caso contrário, fallback para a proporção empírica de 55/45 (Dixon & Coles 1997)
        try:
            if 'home_avg_corners_general' in features.columns and 'away_avg_corners_general' in features.columns:
                h_avg = float(features['home_avg_corners_general'].iloc[0])
                a_avg = float(features['away_avg_corners_general'].iloc[0])
                if h_avg + a_avg > 0:
                    h_ratio = h_avg / (h_avg + a_avg)
                    return total * h_ratio, total * (1 - h_ratio)
        except Exception:
            pass
            
        return total * 0.55, total * 0.45

    def predict_distribution(self, features: pd.DataFrame) -> Dict[str, float]:
        """
        Implements BasePredictor.predict_distribution.
        """
        l_home, l_away = self.predict_lambda(features)
        
        # ProfessionalPredictor assumes Poisson (equidispersion) implicitly 
        # because of how it currently models the counts without variance tracking
        return {
            'lambda_home': l_home,
            'lambda_away': l_away,
            'variance_factor': 1.0  # Strict Poisson
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("Modelo não treinado.")
        
        # DEFENSIVE CHECK: Garante que X é um DataFrame, não Series
        if isinstance(X, pd.Series):
            X = X.to_frame().T
        elif not isinstance(X, pd.DataFrame):
            raise TypeError(f"X deve ser DataFrame ou Series, recebido: {type(X)}")


        
        # 1. Recuperação de Feature Names (Robustez para modelos legados)
        if self.feature_names is None:
            try:
                # Tenta extrair do modelo LightGBM base dentro do Stacking
                if hasattr(self.model, 'trained_base_models_') and len(self.model.trained_base_models_) > 0:
                    lgbm_model = self.model.trained_base_models_[0]
                    if hasattr(lgbm_model, 'feature_name'):
                        self.feature_names = lgbm_model.feature_name()
            except:
                pass

        # 2. Filtragem e Reordenação
        if self.feature_names:
            # Pega apenas as colunas que o modelo espera, na ordem correta
            # Preenche com 0 colunas que faltarem (segurança)
            existing_cols = set(X.columns)
            missing_cols = [c for c in self.feature_names if c not in existing_cols]
            
            if missing_cols:
                X = X.copy()
                for col in missing_cols:
                    # Se pediram para desconsiderar 20g (removido do features_v2),
                    # usamos a versão de 10g como proxy (Smart Fill). 
                    # Isso mantém o modelo estável sem inventariar dados 0.0 extremos.
                    if '20g' in col:
                        proxy_col = col.replace('20g', '10g')
                        if proxy_col in existing_cols:
                            X[col] = X[proxy_col]
                        else:
                            X[col] = 0.0
                    else:
                        X[col] = 0.0
            
            # Garante ordem exata para o LightGBM
            X_filtered = X[self.feature_names]
            
            preds = self.model.predict(X_filtered)
            return preds
            
        # Fallback se não soubermos os nomes (pode causar erro de shape se X tiver metadata)
        preds = self.model.predict(X)
        return preds

    def _evaluate_profitability(self, y_true, y_pred, odds_df, verbose=True):
        """Avalia lucratividade contra odds (Reais ou Sintéticas)."""
        profit = 0
        bets = 0
        hits = 0
        
        y_true = y_true.values if hasattr(y_true, 'values') else y_true
        
        for i in range(len(y_true)):
            obs = y_true[i]
            pred = y_pred[i]
            
            # Pega odds do dataframe alinhado
            # odds_df deve ter mesmo index ou resetado. 
            # Aqui assumimos alinhamento por posição (iloc) para simplificar dentro do loop
            line = odds_df.iloc[i]['LINE']
            odd_over = odds_df.iloc[i]['O_ODDS']
            odd_under = odds_df.iloc[i]['U_ODDS']
            
            # Prob do Modelo (Poisson)
            prob_over_model = 1 - poisson.cdf(line, pred)
            prob_under_model = poisson.cdf(line, pred)
            
            # Valor esperado (Kelly Criterion Simplificado)
            # Aposta se Edge > 5%
            edge_over = prob_over_model * odd_over - 1
            edge_under = prob_under_model * odd_under - 1
            
            stake = 0
            outcome = 0
            
            if edge_over > 0.05:
                stake = 1 # Flat stake for simplicity in validation metrics
                bets += 1
                if obs > line:
                    outcome = (odd_over - 1)
                    hits += 1
                else:
                    outcome = -1
            elif edge_under > 0.05:
                stake = 1
                bets += 1
                if obs <= line:
                    outcome = (odd_under - 1)
                    hits += 1
                else:
                    outcome = -1
            
            profit += outcome
            
        roi = profit / bets if bets > 0 else 0
        win_rate = hits / bets if bets > 0 else 0
        
        return {'roi': roi, 'win_rate': win_rate, 'total_bets': bets, 'profit': profit, 'roi_percent': roi*100}

    def save_model(self):
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model,
            'feature_names': self.feature_names
        }, self.model_path)
        print(f"💾 Modelo Stacking salvo em {self.model_path}")

    def load_model(self) -> bool:
        if not self.model_path.exists():
            return False
        try:
            import sys
            import src.models.model_v2
            # Alias for backward compatibility with models saved under the old path
            sys.modules['src.ml.model_v2'] = src.models.model_v2

            data = joblib.load(self.model_path)
            self.model = data['model']
            self.feature_names = data['feature_names']
            print("✅ Modelo Stacking carregado.")
            return True
        except Exception as e:
            print(f"Erro ao carregar modelo: {e}")
            return False

    def get_feature_importance(self) -> pd.DataFrame:
        """
        Extrai importância das features do modelo LightGBM base.
        """
        if self.model is None or not hasattr(self.model, 'trained_base_models_'):
            return pd.DataFrame()
        
        # Tenta encontrar o LightGBM entre os modelos base treinados
        # Assumindo que o primeiro modelo é o LGBM (como definido no init)
        try:
            lgbm_model = self.model.trained_base_models_[0]
            if hasattr(lgbm_model, 'feature_importances_'):
                imp = lgbm_model.feature_importances_
                return pd.DataFrame({
                    'feature': self.feature_names, 
                    'importance': imp
                }).sort_values('importance', ascending=False)
        except Exception as e:
            print(f"Erro ao extrair feature importance: {e}")
            
        return pd.DataFrame()

    def optimize_hyperparameters(self, X, y, timestamps, n_trials=20):
        """
        Otimiza os hiperparâmetros do LightGBM (Base Model) usando Optuna.
        Foca no modelo principal do Stacking (Gradient Boosting).
        """
        # Configura verbosidade do Optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        
        print(f"\n🔥 Iniciando Otimização com Optuna ({n_trials} trials)...")
        print("   Focando em: LightGBM (Tweedie/Poisson)")

        # Prepara e ordena os dados COM PRECISÃO TOTAL (Usa todo o histórico disponível)
        # Fix: Construct DataFrame directly with dict to avoid .rename() scalar error
        local_df = pd.DataFrame({
            **{col: X[col].reset_index(drop=True) for col in X.columns},
            'target': y.reset_index(drop=True),
            'ts': timestamps.reset_index(drop=True)
        }).sort_values('ts')
        
        X_sorted = local_df[X.columns]
        y_sorted = local_df['target']
        
        # 🧪 Restaura TimeSeriesSplit Professional (3 splits para validação robusta)
        tscv = TimeSeriesSplit(n_splits=3)

        def objective(trial):
            """
            Função objetivo do Optuna para otimização de hiperparâmetros.
            
            Regra de Negócio (Sprint 5, Tarefa 1.3):
                Modificado para otimizar RPS (Ranked Probability Score) em vez de MSE.
                RPS é mais apropriado para modelos probabilísticos em esportes, pois
                penaliza previsões extremas de forma mais adequada que MAE/MSE.
            
            Referência Acadêmica:
                Constantinou & Fenton (2012): "Solving the Problem of Inadequate 
                Scoring Rules for Assessing Probabilistic Football Forecast Models"
            
            Métrica:
                RPS = Σ(CDF_modelo - CDF_real)² / N_outcomes
                Menor é melhor (0 = perfeito)
            """
            param = {
                'objective': 'tweedie',
                'tweedie_variance_power': trial.suggest_float('tweedie_variance_power', 1.1, 1.9),
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
                'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.1, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 20, 150),
                'max_depth': trial.suggest_int('max_depth', 3, 15),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1
            }
            
            # MUDANÇA CRÍTICA (Sprint 5): RPS em vez de MSE
            rps_scores = []
            for train_idx, val_idx in tscv.split(X_sorted):
                X_tr, X_val = X_sorted.iloc[train_idx], X_sorted.iloc[val_idx]
                y_tr, y_val = y_sorted.iloc[train_idx], y_sorted.iloc[val_idx]
                
                model = lgb.LGBMRegressor(**param)
                model.fit(X_tr, y_tr)
                preds = model.predict(X_val)
                
                # Calcula RPS usando método existente
                rps = self._calculate_rps(y_val, preds)
                rps_scores.append(rps)
            
            score = np.mean(rps_scores)
            
            # Visualização: mostra RPS em vez de MSE
            print(f"   📊 [AutoML] Trial {trial.number+1}/{n_trials} | RPS: {score:.4f} | Est: {param['n_estimators']}")
                
            return score

        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials)

        print(f"\n✅ Melhores parâmetros encontrados: {study.best_params}")
        print(f"📊 Melhor RPS: {study.best_value:.4f}")
        
        # Atualiza params do objeto
        self.lgbm_params.update(study.best_params)
        
        return study.best_params

    def train_global_and_finetune(self, X, y, timestamps, tournament_ids=None, odds=None):
        """
        Wrapper para compatibilidade com pipeline de Transfer Learning.
        
        Regra de Negócio:
            Transfer Learning foi desativado para o Stacking V2.1 devido à 
            complexidade de fine-tuning em ensemble. Esta função redireciona 
            para o treinamento global padrão.
            
        Args:
            X: Features DataFrame.
            y: Target Series.
            timestamps: Series com timestamps para ordenação temporal.
            tournament_ids: Ignorado nesta versão.
            odds: Series com odds para backtesting.
            
        Returns:
            dict: Métricas do treinamento.
        """
        print("⚠️ Transfer Learning desativado para Stacking nesta versão. Treinando Global.")
        return self.train_time_series_split(X, y, timestamps, odds)

# Função auxiliar para retrocompatibilidade
def prepare_improved_features(df: pd.DataFrame) -> tuple:
    """
    Wrapper para o novo módulo de features.
    
    Mantido para retrocompatibilidade com código existente.
    Recomenda-se usar diretamente features_v2.create_advanced_features().
    
    Args:
        df: DataFrame com dados históricos.
    
    Returns:
        tuple: (X, y, timestamps)
    """
    from src.ml.features_v2 import create_advanced_features
    X, y, df_features = create_advanced_features(df)
    return X, y, df_features['start_timestamp']
