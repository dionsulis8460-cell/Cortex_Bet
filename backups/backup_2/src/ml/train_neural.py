
import sys
import os
import joblib
import pandas as pd
import numpy as np
import optuna
from sklearn.neural_network import MLPRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score


# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# FIX: Force UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.database.db_manager import DBManager
from src.ml.features_v2 import create_advanced_features

def objective(trial, X_train, y_train, X_test, y_test):
    """
    Optuna Objective Function: Evaluates a set of hyperparameters.
    Multi-Output version: predicts [Home, Away] simultaneously.
    """
    # 1. Hyperparameter Space (Grid Search)
    
    # Layers: Try different depths and widths
    n_layers = trial.suggest_int('n_layers', 1, 3)
    layers = []
    for i in range(n_layers):
        layers.append(trial.suggest_int(f'n_units_l{i}', 16, 128))
    
    # Regularization (Alpha)
    alpha = trial.suggest_float('alpha', 1e-5, 1e-1, log=True)
    
    # Learning Rate Init
    lr_init = trial.suggest_float('learning_rate_init', 1e-4, 1e-2, log=True)
    
    # 2. Build Multi-Output Model
    base_mlp = MLPRegressor(
        hidden_layer_sizes=tuple(layers),
        activation='relu',
        solver='adam',
        alpha=alpha,
        batch_size=32,
        learning_rate='adaptive',
        learning_rate_init=lr_init,
        max_iter=300, # Less iter for optimization speed
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=10,
        random_state=42
    )
    
    model = MultiOutputRegressor(base_mlp)
    
    # 3. Train
    model.fit(X_train, y_train)
    
    # 4. Evaluate (Minimize MAE averaged across Home and Away)
    y_pred = model.predict(X_test)
    mae_home = mean_absolute_error(y_test.iloc[:, 0], y_pred[:, 0])
    mae_away = mean_absolute_error(y_test.iloc[:, 1], y_pred[:, 1])
    mae = (mae_home + mae_away) / 2  # Average MAE
    
    return mae

def train_neural_model():
    print("🧠 Starting Neural Network Training with Optuna Optimization...")
    
    # 1. Load Data
    db = DBManager()
    df_history = db.get_historical_data()
    db.close()
    
    if df_history.empty:
        print("❌ No historical data found!")
        return
        
    print(f"📊 Loaded {len(df_history)} historical matches.")
    
    # 2. Feature Engineering (Deep Features)
    print("⚙️ Generating Deep Features (using features_v2)...")
    X, y, timestamps, _ = create_advanced_features(df_history)
    
    valid_indices = X.dropna().index
    X = X.loc[valid_indices]
    y = y.loc[valid_indices]
    
    print(f"✅ Features ready. Training samples: {len(X)} | Features: {X.shape[1]}")
    
    # ==========================================================================
    # EMERGENCY FIX: Multi-Output MLP (Home + Away Training)
    # ==========================================================================
    # PROBLEMA ANTERIOR:
    #   y = corners_home_ft + corners_away_ft  # SÓ TOTAL
    #   MLP nunca aprendia: "Mandante forte em casa" ou "Visitante defende bem fora"
    #   Resultado: R² = -0.0078 (pior que baseline)
    #
    # SOLUÇÃO:
    #   Treinar 2 saídas: [Home Corners, Away Corners]
    #   MLP aprende dinâmica separada de cada time
    #
    # Referência Acadêmica:
    #   Spyromitros-Xioufis et al. (2016) - "Multi-Target Regression via 
    #   Input Space Expansion: Application to Football Score Prediction"
    # ==========================================================================
    
    # Create Multi-Output target
    y_multi = pd.DataFrame({
        'home': df_history.loc[valid_indices, 'corners_home_ft'],
        'away': df_history.loc[valid_indices, 'corners_away_ft']
    }, index=valid_indices)
    
    print(f"✅ Multi-Output Target: Home={y_multi['home'].mean():.2f} | Away={y_multi['away'].mean():.2f}")
    
    # 3. Preprocessing
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Split (Multi-Output)
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_multi, test_size=0.2, random_state=42, shuffle=False)
    
    # 4. Optuna Optimization
    print("🔍 Optimizing Hyperparameters (This may take a moment)...")
    study = optuna.create_study(direction='minimize')
    study.optimize(lambda trial: objective(trial, X_train, y_train, X_test, y_test), n_trials=20) # 20 trials for speed
    
    print("\n🏆 Best Hyperparameters:")
    print(study.best_params)
    print(f"   Best MAE: {study.best_value:.4f}")
    
    # 5. Retrain Best Model
    print("\n🏋️‍♂️ Retraining Final Model with Best Params...")
    best_params = study.best_params
    
    # Reconstruct layers tuple from best_params
    n_layers = best_params['n_layers']
    best_layers = tuple([best_params[f'n_units_l{i}'] for i in range(n_layers)])
    
    base_mlp = MLPRegressor(
        hidden_layer_sizes=best_layers,
        activation='relu',
        solver='adam',
        alpha=best_params['alpha'],
        batch_size=32,
        learning_rate='adaptive',
        learning_rate_init=best_params['learning_rate_init'],
        max_iter=1000, # Full training
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20,
        random_state=42,
        verbose=True
    )
    
    final_model = MultiOutputRegressor(base_mlp)
    
    final_model.fit(X_train, y_train)
    
    # 6. Final Evaluation (Multi-Output)
    y_pred = final_model.predict(X_test)
    
    # Calculate metrics for each output
    mae_home = mean_absolute_error(y_test.iloc[:, 0], y_pred[:, 0])
    mae_away = mean_absolute_error(y_test.iloc[:, 1], y_pred[:, 1])
    mae_avg = (mae_home + mae_away) / 2
    
    r2_home = r2_score(y_test.iloc[:, 0], y_pred[:, 0])
    r2_away = r2_score(y_test.iloc[:, 1], y_pred[:, 1])
    r2_avg = (r2_home + r2_away) / 2
    
    print("\n🔬 Final Validation Results (Multi-Output):")
    print(f"   Home: MAE={mae_home:.4f} | R²={r2_home:.4f}")
    print(f"   Away: MAE={mae_away:.4f} | R²={r2_away:.4f}")
    print(f"   Average: MAE={mae_avg:.4f} | R²={r2_avg:.4f}")
    
    if r2_avg > 0:
        print("   ✅ Model is learning patterns (R² > 0)!")
    else:
        print("   ⚠️ Model struggling to beat baseline (R² <= 0). More data needed.")

    # 7. Save
    model_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
    os.makedirs(model_dir, exist_ok=True)
    
    model_path = os.path.join(model_dir, 'neural_challenger_mlp.joblib')
    scaler_path = os.path.join(model_dir, 'neural_scaler.joblib')
    
    joblib.dump(final_model, model_path)
    joblib.dump(scaler, scaler_path)
    
    print(f"\n💾 Optimized Model saved to: {model_path}")

if __name__ == "__main__":
    train_neural_model()
