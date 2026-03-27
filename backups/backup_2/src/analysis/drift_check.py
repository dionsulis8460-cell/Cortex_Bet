
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.database.db_manager import DBManager
from src.ml.features_v2 import create_advanced_features

def check_drift():
    print("📊 Loading data for Drift Check...")
    db = DBManager()
    df_raw = db.get_historical_data()
    db.close()
    
    if df_raw.empty:
        print("❌ No data found.")
        return

    # Generate features
    print("🔧 Generating features...")
    X, y, timestamps, _ = create_advanced_features(df_raw)
    
    # 2. Strict Chronological Split (Same as Model V2)
    # Sort by timestamp
    data = pd.concat([X, y.rename('target'), timestamps.rename('timestamp')], axis=1)
    data = data.sort_values('timestamp')
    
    n_total = len(data)
    holdout_frac = 0.15
    n_holdout = int(n_total * holdout_frac)
    n_cv = n_total - n_holdout
    
    train_data = data.iloc[:n_cv]
    oot_data = data.iloc[n_cv:]
    
    print(f"📉 Split: Train={len(train_data)} | OOT={len(oot_data)}")
    
    # 3. Analyze Drift per Feature
    drift_results = []
    
    # Columns to check (exclude target/timestamp)
    feature_cols = [c for c in X.columns if c not in ['target', 'timestamp']]
    
    print(f"🧪 Checking Drift for {len(feature_cols)} features...")
    
    for col in feature_cols:
        if not pd.api.types.is_numeric_dtype(train_data[col]):
            continue
            
        train_vals = train_data[col].dropna()
        oot_vals = oot_data[col].dropna()
        
        train_mean = train_vals.mean()
        train_std = train_vals.std()
        oot_mean = oot_vals.mean()
        
        # PSI (Population Stability Index) or Z-Score Shift?
        # Let's use Z-Score of the shift: (Mean_OOT - Mean_Train) / Std_Train
        if train_std == 0:
            drift_score = 0
        else:
            drift_score = (oot_mean - train_mean) / train_std
            
        drift_results.append({
            'Feature': col,
            'Train_Mean': train_mean,
            'OOT_Mean': oot_mean,
            'Delta': oot_mean - train_mean,
            'Drift_Z': drift_score
        })
        
    df_drift = pd.DataFrame(drift_results)
    df_drift['Abs_Drift_Z'] = df_drift['Drift_Z'].abs()
    df_drift = df_drift.sort_values('Abs_Drift_Z', ascending=False)
    
    print("\n🚨 TOP 20 DRIFTING FEATURES (Highest Z-Score Shift):")
    pd.set_option('display.float_format', '{:.4f}'.format)
    print(df_drift[['Feature', 'Train_Mean', 'OOT_Mean', 'Delta', 'Drift_Z']].head(20))
    
    # Also Check Target Drift
    y_train = train_data['target'].mean()
    y_oot = oot_data['target'].mean()
    print(f"\n🎯 TARGET DRIFT: Train={y_train:.2f} | OOT={y_oot:.2f} | Delta={y_oot - y_train:.2f}")

if __name__ == "__main__":
    check_drift()
