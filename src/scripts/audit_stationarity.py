"""
Audit Stationarity.
Runs Augmented Dickey-Fuller test on all features to identify non-stationary ones.
"""

import sys
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager
from src.ml.features_v2 import create_advanced_features

def audit_stationarity():
    print("\n" + "="*80)
    print("📊 AUDIT: FEATURE STATIONARITY CHECKS (ADF TEST)")
    print("="*80)
    
    # 1. Load Data
    print("📂 Loading historical data...")
    db = DBManager()
    df = db.get_historical_data()
    
    # Generate features
    # Note: create_advanced_features ALREADY drops non-stationary features if they are in the blacklist.
    # To audit properly, we should ideally check BEFORE dropping.
    # However, create_advanced_features logic is:
    # 1. Generate ALL features.
    # 2. SPRINT 9.5: Drop NON_STATIONARY_FEATURES.
    # We want to see if there are NEW non-stationary features or if the list is correct.
    # Ideally we'd inspect X BEFORE the drop, but we can't easily hook into the function.
    # So we will check the OUTPUT X. If standard X contains non-stationary, it's a finding.
    
    X, y, timestamps, _ = create_advanced_features(df)
    
    print(f"Analyzing {X.shape[1]} features across {X.shape[0]} samples...")
    
    non_stationary = []
    
    # Limit to top 50 features if too many? No, do all.
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            continue
            
        series = X[col].dropna()
        if len(series) < 50:
            print(f"⚠️ {col}: Too few samples ({len(series)})")
            continue
            
        try:
            # ADF Test
            # Null Hypothesis: Unit root present (Non-Stationary)
            # Alternate Hypothesis: Stationary
            result = adfuller(series, autolag='AIC')
            p_value = result[1]
            
            if p_value >= 0.05:
                # Fail to reject Null -> Non-Stationary
                non_stationary.append({'feature': col, 'p_value': p_value})
                # print(f"❌ {col:<40} p={p_value:.4f} (Non-Stationary)")
            else:
                pass
                # print(f"✅ {col:<40} p={p_value:.4f}")
                
        except Exception as e:
            print(f"⚠️ {col}: Error in ADF - {e}")
            
    # Report
    print("\n" + "-"*80)
    if non_stationary:
        print(f"❌ Found {len(non_stationary)} NON-STATIONARY features (p >= 0.05):")
        # Sort by p-value desc
        non_stationary.sort(key=lambda x: x['p_value'], reverse=True)
        
        for item in non_stationary:
            print(f"   - {item['feature']:<50} p={item['p_value']:.4f}")
            
        print("\n📝 ACTION: Add these to NON_STATIONARY_FEATURES list in src/ml/features_v2.py")
        
        # Generate python list for easy copy-paste
        print("\nCopy-Paste Block:")
        print("NEW_BLACKLIST = [")
        for item in non_stationary:
            print(f"    '{item['feature']}',")
        print("]")
    else:
        print("✅ All features passed Stationarity Audit (ADF p < 0.05)!")
        
    print("="*80)

if __name__ == "__main__":
    audit_stationarity()
