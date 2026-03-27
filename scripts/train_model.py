import argparse
import sys
import os
import mlflow
import numpy as np
import pandas as pd
from datetime import datetime

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.database.db_manager import DBManager
from src.features.feature_store import FeatureStore
from src.models.model_v2 import ProfessionalPredictor
from src.training.trainer import train_model as legacy_train_mode # Compatibility
# from src.domain.bayesian import BayesianAnalytics # Uncomment when PyMC is fully configured

def train_pipeline(args):
    """
    Orchestrates the PhD-level training pipeline.
    1. Loads historical data from SQLite with Versioning (DVC concept).
    2. Trains the Bayesian/ML Hybrid Model.
    3. Logs metrics (RPS, MAE) and artifacts to MLflow.
    """
    print(f"🚀 Starting Training Pipeline: {args.experiment}")
    
    # 1. Data Ingestion
    db = DBManager()
    df = db.get_historical_data()
    db.close()
    
    if df.empty:
        print("⚠️ No historical data found in database. Cannot train.")
        return

    print(f"📊 Loaded {len(df)} historical matches for training.")

    # Feature Engineering (Canonical Path)
    print("🔧 Generating canonical features via FeatureStore...")
    try:
        feature_store = FeatureStore(db)
        X, y, timestamps = feature_store.get_training_features(df)
        print(f"   ✅ Features generated: {X.shape}")
    except Exception as exc:
        print(f"   ⚠️ Could not generate canonical training features: {exc}")
        return

    # 2. Experiment Tracking Setup
    mlflow.set_experiment(args.experiment)
    
    with mlflow.start_run(run_name=f"Run_{datetime.now().strftime('%Y-%m-%d_%H-%M')}") as run:
        # A. Log Parameters
        params = {
            "mode": "Full_Production" if args.optuna else "Fast_Check",
            "data_version": "v5.0.0",
            "n_matches": len(df),
            "optuna_trials": args.trials if args.optuna else 0
        }
        mlflow.log_params(params)

        predictor = ProfessionalPredictor()

        # B. OPTUNA (Hybrid Bayesian Optimization)
        if args.optuna:
            print(f"🔥 Starting Optuna Optimization ({args.trials} trials)...")
            best_params = predictor.optimize_hyperparameters(X, y, timestamps, n_trials=args.trials)
            mlflow.log_params(best_params) # Log best params found
            print(f"   ✅ Best Params: {best_params}")
        else:
            print("ℹ️ Skipping Optuna (Fast Mode). Use --optuna to enable.")

        # C. Training (Time Series Split)
        print("🚀 Training Final Model (Time Series Split)...")
        # Train and get metrics
        metrics = predictor.train_time_series_split(X, y, timestamps)
        
        # Log Metrics to MLflow
        mlflow.log_metrics({
            "rps": metrics.get('rps_test', 0),
            "mae": metrics.get('mae_test', 0),
            "roi": metrics.get('roi', 0),
            "win_rate": metrics.get('win_rate', 0)
        })
        
        print(f"📈 Final Metrics: RPS={metrics.get('rps_test'):.4f}, MAE={metrics.get('mae_test'):.4f}")
        
        # D. Save Model
        predictor.save_model()
        mlflow.sklearn.log_model(predictor.model, "model")
        
        # E. Save Production Calibrator (Scientific Standard)
        print("\n🌡️ Training Production Calibrator...")
        from src.scripts.save_production_calibrator import save_calibrator
        save_calibrator()
        
        print(f"✅ Training Pipeline Complete. Run ID: {run.info.run_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cortex Bet - PhD Training Pipeline")
    parser.add_argument("--experiment", type=str, default="Cortex_Default", help="Name of the MLflow experiment")
    parser.add_argument("--optuna", action="store_true", help="Enable Optuna Hyperparameter Optimization")
    parser.add_argument("--trials", type=int, default=20, help="Number of Optuna trials")
    
    args = parser.parse_args()
    
    train_pipeline(args)
