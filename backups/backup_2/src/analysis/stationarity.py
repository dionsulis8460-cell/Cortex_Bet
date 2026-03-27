
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.database.db_manager import DBManager
from src.ml.features_v2 import create_advanced_features

try:
    from statsmodels.tsa.stattools import adfuller
except ImportError:
    print("❌ statsmodels not installed. Please run: pip install statsmodels")
    sys.exit(1)

def check_stationarity():
    print("📊 Loading data for Stationarity Check...")
    db = DBManager()
    df_raw = db.get_historical_data()
    db.close()
    
    if df_raw.empty:
        print("❌ No data found.")
        return

    # Generate features
    print("🔧 Generating features...")
    # Use features_v2 logic
    X, y, timestamps, _ = create_advanced_features(df_raw)
    
    # Drop NaNs for statistical test (ADF requires clean series)
    X_clean = X.dropna()
    print(f"📉 Data shape after cleaning: {X_clean.shape}")
    
    if len(X_clean) < 100:
        print("⚠️ Warning: Not enough data for reliable stationarity test.")
    
    print(f"\n🧪 Running Augmented Dickey-Fuller (ADF) Test on {len(X_clean.columns)} features...")
    print("   Criteria: p-value < 0.05 => Stationary (Keep)")
    print("             p-value >= 0.05 => Non-Stationary (Risk of Overfitting - Random Walk)\n")
    
    results = []
    
    for col in X_clean.columns:
        # Skip non-numeric
        if not pd.api.types.is_numeric_dtype(X_clean[col]):
            continue
            
        series = X_clean[col].values
        
        # Check for constant columns (ADF fails on constant)
        if np.all(series == series[0]):
             results.append({'Feature': col, 'p-value': 1.0, 'Status': '❌ Constant', 'ADF Statistic': 0})
             continue
             
        try:
            # autolag='AIC' chooses optimal lag
            # regression='c' (constant only) is standard for this check
            res = adfuller(series, autolag='AIC', regression='c')
            p_value = res[1]
            adf_stat = res[0]
            
            status = "✅ Stationary" if p_value < 0.05 else "⚠️ Non-Stationary"
            results.append({'Feature': col, 'p-value': p_value, 'Status': status, 'ADF Statistic': adf_stat})
            
        except Exception as e:
            # print(f"Error processing {col}: {e}")
            results.append({'Feature': col, 'p-value': 999.0, 'Status': f'❌ Error: {str(e)[:20]}', 'ADF Statistic': 0})

    # Create DataFrame report
    df_res = pd.DataFrame(results).sort_values('p-value', ascending=False)
    
    # Save to CSV for full inspection
    df_res.to_csv('stationarity_report.csv', index=False)
    print("\n💾 Detailed report saved to 'stationarity_report.csv'")
    
    # Display Riskier Features (Top 30 Non-Stationary)
    print("\n🚨 TOP 30 RISKIEST FEATURES (Highest p-value / Non-Stationary):")
    
    pd.set_option('display.float_format', '{:.4f}'.format)
    # Force pandas to show more rows/cols
    pd.set_option('display.max_rows', 50)
    
    print(df_res[df_res['p-value'] >= 0.05].head(30)[['Feature', 'p-value', 'Status']])
    
    print("\n✅ SAFE FEATURES (Top 10 Stationary samples):")
    print(df_res[df_res['p-value'] < 0.01].head(10)[['Feature', 'p-value', 'Status']])
    
    # Summary
    n_total = len(df_res)
    n_fail = len(df_res[df_res['p-value'] >= 0.05])
    print(f"\n📋 SUMMARY: {n_fail}/{n_total} features are Non-Stationary ({n_fail/n_total:.1%})")
    
    if n_fail > 0:
        print("\n💡 RECOMMENDATION:")
        print("   1. Rolling Means/Sums often behave like Random Walks if not differenced.")
        print("   2. Consider replacing rolling_mean() with rolling_mean().diff() or ratio vs league avg.")

if __name__ == "__main__":
    check_stationarity()
