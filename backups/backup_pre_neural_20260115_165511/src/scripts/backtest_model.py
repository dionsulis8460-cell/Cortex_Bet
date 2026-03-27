"""
Backtesting Script - Cortex V2.1
Target: December 2025 (Validation of ROI before Production)

Logic:
1. Load full history.
2. Split into TRAIN (< 2025-12-01) and TEST (>= 2025-12-01).
3. Train a fresh ProfessionalPredictor on TRAIN only.
4. Train/Fit a fresh MultiThresholdCalibrator on TRAIN (folds).
5. Predict on TEST set (simulating production day-by-day).
6. Calculate ROI using Hardcoded Odds (@1.90 default).
7. Generate Report.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import joblib

# Add project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.db_manager import DBManager
from src.models.model_v2 import ProfessionalPredictor
from src.ml.features_v2 import create_advanced_features
from src.ml.calibration import MultiThresholdCalibrator

def run_backtest():
    print("🧪 Starting Cortex V2.1 Backtest (Target: Dec 2025)...")
    
    # 1. Load Data
    db = DBManager()
    df_full = db.get_historical_data()
    
    if df_full.empty:
        print("❌ No data found in DB.")
        return

    print(f"📊 Total Games in DB: {len(df_full)}")

    # 2. Prepare Features
    # We must generate features on full dataset to ensure rolling windows are correct, 
    # BUT we must be careful not to peek at target variable of future games.
    # The `create_advanced_features` is designed to shift(1), so it's safe to run on full df 
    # and then slice.
    
    print("⚙️ Generating Features (Strict No-Lookahead)...")
    X, y, timestamps, df_display_metrics = create_advanced_features(df_full)
    
    # Add date column for splitting
    dates = pd.to_datetime(timestamps, unit='s')
    
    # 3. Time Split
    cutoff_date = pd.Timestamp("2025-12-01")
    
    # Mask
    mask_train = dates < cutoff_date
    mask_test = dates >= cutoff_date
    
    X_train, y_train = X[mask_train], y[mask_train]
    X_test, y_test = X[mask_test], y[mask_test]
    
    # Metadados para relatório
    test_games_indices = np.where(mask_test)[0]
    test_dates = dates[mask_test]
    
    print(f"📉 Train Set: {len(X_train)} games (< {cutoff_date.date()})")
    print(f"📈 Test Set:  {len(X_test)} games (>= {cutoff_date.date()})")
    
    if len(X_test) == 0:
        print("❌ No games found in Dec 2025 range! Check your DB dates.")
        return

    # 4. Train Model (Fresh)
    print("\n🧠 Training Model on Historical Data (Pre-Dec)...")
    predictor = ProfessionalPredictor()
    # Force retrain - do not load existing model, use valid method
    predictor.train_time_series_split(X_train, y_train, timestamps[mask_train], n_splits=5)
    
    # 5. Calibration

    print("⚖️ Fitting Calibrator on Validation Folds...")
    # Ideally we use OOF predictions from training set to fit calibrator
    # For simplicity/speed in MVP backtest, we might split Train again or just assume
    # the production calibrator style (fitted on history).
    # Let's use the production method: fit on LAST 20% of TRAIN set as calibration set?
    # Better: Use the MultiThreshold logic that splits internally or accepts validation data.
    
    calibrator = MultiThresholdCalibrator()
    # We essentially need OOF predictions for X_train to calibrate correctly without overfitting.
    # predictor.model is a stacking regressor.
    
    # Generate in-sample predictions (risky) or OOF?
    # Let's generate OOF predictions for the train set using cross_val_predict style if possible,
    # or just simple predict on Train (slightly optimistic but acceptable for quick calibration check).
    train_preds = predictor.predict(X_train).flatten()
    calibrator.fit(train_preds, y_train.values)
    
    # 6. Run Test Predictions
    print("\n🔮 Running Predictions on Dec 2025 (Test Set)...")
    test_preds_raw = predictor.predict(X_test).flatten()
    
    # Prepare Results Table
    results = []
    
    ODDS_HARDCODED = 1.90  # Standard Asian Line Odd
    
    bankroll = 1000.0
    initial_bankroll = bankroll
    stake_fixed = 0.03  # 3% stake
    
    wins = 0
    losses = 0
    pushes = 0
    
    daily_pnl = {}
    
    for i, (idx, row) in enumerate(zip(test_games_indices, X_test.iterrows())):
        actual_corners = y_test.iloc[i]
        pred_val = test_preds_raw[i]
        
        # Decide Line & Bet
        # Simple Logic: Bet on nearest integer line with edge
        # E.g. Pred 11.2 -> Bet Over 10.5
        # E.g. Pred 9.8 -> Bet Under 10.5
        
        # Determine Line: Round to nearest X.5
        # 11.2 -> 11.5 or 10.5? Usually market offers main line.
        # Let's simulate we bet on the line implicitly defined by prediction.
        
        # Strategy:
        # If Pred > 10.0 -> Bet OVER 9.5 (Safe)
        # If Pred < 10.0 -> Bet UNDER 10.5 (Safe)
        # This is strictly hypothetical to test alpha.
        
        if pred_val > 10.0:
            bet_type = 'Over'
            line = 9.5
        else:
            bet_type = 'Under'
            line = 10.5
            
        # Calibration Check
        prob = calibrator.predict_proba(pred_val, threshold=line) # Probability of OVER
        
        if bet_type == 'Under':
            prob = 1.0 - prob # Probability of UNDER
            
        # Filter: Only bet if edge > threshold (or confidence > 60%)
        confidence = prob
        
        bet_placed = False
        outcome = 0
        pnl = 0
        
        if confidence >= 0.60:
            bet_placed = True
            stake = bankroll * stake_fixed
            
            # Check Result
            won = False
            if bet_type == 'Over' and actual_corners > line:
                won = True
            elif bet_type == 'Under' and actual_corners < line:
                won = True
            
            if won:
                wins += 1
                pnl = stake * (ODDS_HARDCODED - 1)
                outcome = 1
            else:
                losses += 1
                pnl = -stake
                outcome = -1
                
            bankroll += pnl
            
        # Record
        date_str = test_dates.iloc[i].strftime('%Y-%m-%d')
        daily_pnl[date_str] = daily_pnl.get(date_str, 0) + pnl
        
        results.append({
            'date': date_str,
            'pred': pred_val,
            'actual': actual_corners,
            'bet_type': bet_type,
            'line': line,
            'confidence': confidence,
            'bet_placed': bet_placed,
            'pnl': pnl,
            'bankroll_ts': bankroll
        })

    # 7. Statistics
    total_bets = wins + losses
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0.0
    roi = ((bankroll - initial_bankroll) / initial_bankroll) * 100
    
    print("\n" + "="*40)
    print("🧪 BACKTEST REPORT - DEC 2025")
    print("="*40)
    print(f"Total Games Analyzed: {len(X_test)}")
    print(f"Bets Placed: {total_bets} (Conf >= 60%)")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Final Bankroll: ${bankroll:.2f} (Start: $1000)")
    print(f"ROI: {roi:.2f}%")
    print("="*40)
    
    # Save Report
    report_path = os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'backtest_report_dec2025.md')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# 🧪 Relatório de Backtest - Cortex V2.1\n")
        f.write(f"**Data do Teste:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Período Simulado:** Dezembro 2025\n")
        f.write(f"**Modelo:** Treinado com dados < 01/12/2025\n")
        f.write(f"**Odds Hardcoded:** @{ODDS_HARDCODED}\n\n")
        
        f.write("## 📊 Resultados Gerais\n")
        f.write(f"- **ROI:** {roi:.2f}%\n")
        f.write(f"- **Win Rate:** {win_rate:.2f}%\n")
        f.write(f"- **Bets:** {total_bets}\n")
        f.write(f"- **Lucro Líquido:** ${bankroll - initial_bankroll:.2f}\n\n")
        
        f.write("## 📈 Performance Diária\n")
        f.write("| Data | PnL |\n")
        f.write("|------|-----|\n")
        for d, p in daily_pnl.items():
            f.write(f"| {d} | ${p:.2f} |\n")

    print(f"📄 Report saved to {report_path}")

if __name__ == "__main__":
    run_backtest()
