"""
CLASSIFICATION: MOVE TO RESEARCH

Audit Calibration ECE.
Calculates Expected Calibration Error for Multi-Threshold Calibrator on OOT data.
Not part of production runtime paths.
"""

import sys
import os
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.calibration import calibration_curve

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager
from src.ml.features_v2 import create_advanced_features
from src.models.model_v2 import ProfessionalPredictor
from src.ml.calibration import MultiThresholdCalibrator

def calculate_ece(prob_pred, y_true, n_bins=10):
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (prob_pred >= bin_edges[i]) & (prob_pred < bin_edges[i+1])
        if mask.sum() > 0:
            acc = y_true[mask].mean()
            conf = prob_pred[mask].mean()
            ece += np.abs(acc - conf) * (mask.sum() / len(y_true))
    return ece

def audit_calibration():
    print("\n" + "="*80)
    print("📊 AUDIT: CALIBRATION ECE CHECKS (MULTI-THRESHOLD)")
    print("="*80)
    
    # 1. Load Data
    db = DBManager()
    df = db.get_historical_data()
    X, y, timestamps, _ = create_advanced_features(df)
    
    # 2. OOT Split (Standard 80/20 or check against production split)
    # Using 80/20 to match save_production_calibrator logic
    n = len(X)
    idx_split = int(n * 0.80)
    
    X_test = X.iloc[idx_split:]
    y_test = y.iloc[idx_split:]
    ts_test = timestamps.iloc[idx_split:]
    
    print(f"Dataset Size: {n}. OOT Test Size: {len(X_test)}")
    
    # 3. Load Model and Generate Predictions
    model = ProfessionalPredictor()
    if not model.load_model():
        print("❌ Model not found. Please train model first.")
        sys.exit(1)
        
    print("Generating model predictions on OOT set...")
    preds = model.predict(X_test)
    
    # 4. Load Calibrator
    calib_path = "data/calibrator_temperature.pkl"
    if not os.path.exists(calib_path):
        print(f"❌ Calibrator not found at {calib_path}")
        sys.exit(1)
        
    calibrator = MultiThresholdCalibrator() # dummy
    try:
        calibrator.load(calib_path)
    except Exception as e:
        print(f"❌ Failed to load calibrator: {e}")
        # Could be type mismatch if we haven't run save_production_calibrator yet
        sys.exit(1)
        
    if not hasattr(calibrator, 'calibrators') or not calibrator.calibrators:
        print("❌ Loaded calibrator seems invalid (missing 'calibrators' dict). Run save_production_calibrator.py first.")
        sys.exit(1)
        
    # 5. Calculate ECE per Threshold
    thresholds = sorted(calibrator.thresholds)
    print(f"\nEvaluating thresholds: {thresholds}")
    
    results = []
    
    for t in thresholds:
        print(f"\n--- Threshold {t} ---")
        # Ground Truth Binary
        y_binary = (y_test > t).astype(int)
        
        # Predicted Probabilities (Calibrated)
        # MultiThresholdCalibrator.predict_proba does NOT support vectorization natively based on my impl?
        # My impl calls cal.predict_proba which MIGHT support vectorization if CalibratedConfidence does.
        # CalibratedConfidence.predict_proba uses self.calibrator.predict_proba(X). 
        # If X is array, it works.
        # My MultiThresholdCalibrator.predict_proba(ml_prediction, ...) takes float?
        # Let's check implementation. 
        # def predict_proba(self, ml_prediction: float, ...)
        # It takes `ml_prediction` hinted as float. But I used `X = np.array([[ml_prediction]])` inside `CalibratedConfidence`.
        # If I pass an array to `predict_proba`, `X = np.array([[ml_prediction]])` creates a 3D array if input is 1D array?
        # `np.array([[1, 2, 3]])` is shape (1, 3).
        # We need shape (N, 1).
        
        # I should probably vector-enable `predict_proba` or just loop here.
        # For audit script, looping is fine.
        
        probs = []
        for p in preds:
            probs.append(calibrator.predict_proba(float(p), threshold=t, use_poisson=True))
        probs = np.array(probs)
        
        # Calculate ECE
        ece = calculate_ece(probs, y_binary)
        print(f"ECE: {ece:.4f}")
        
        results.append({'threshold': t, 'ece': ece})
        
    # Summary
    print("\n" + "="*80)
    print("📢 SUMMARY RESULTS")
    print(f"{'Threshold':<10} | {'ECE':<10} | {'Status'}")
    print("-" * 40)
    
    for r in results:
        ece = r['ece']
        if ece < 0.05: status = "✅ Excellent"
        elif ece < 0.10: status = "✅ Good"
        elif ece < 0.15: status = "⚠️ Acceptable"
        else: status = "❌ Poor"
        print(f"{r['threshold']:<10} | {ece:.4f}     | {status}")

if __name__ == "__main__":
    audit_calibration()
