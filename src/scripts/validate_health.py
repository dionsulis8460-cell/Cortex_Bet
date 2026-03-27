import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.database.db_manager import DBManager
from src.analysis.manager_ai import ManagerAI
from src.analysis.statistical import Colors

def run_health_check(limit=300):
    print(f"\n{Colors.CYAN}🏥 AI HEALTH CHECK - SYSTEM VALIDATION (Last {limit} Games){Colors.RESET}")
    print("="*80)
    
    db = DBManager()
    
    # 1. Load Last N Finished Matches
    print("📊 Loading historical data...")
    df = db.get_historical_data()
    
    # Filter finished
    df_valid = df[df['status'] == 'finished'].copy()
    
    # Sort by timestamp descending (newest first) and take top N
    df_valid = df_valid.sort_values('start_timestamp', ascending=False).head(limit)
    
    # Create datetime column for display
    df_valid['start_timestamp_dt'] = pd.to_datetime(df_valid['start_timestamp'], unit='s')
    
    # Re-sort to ascending for simulation (Past -> Present)
    df_test = df_valid.sort_values('start_timestamp', ascending=True)
    
    print(f"   Matches loaded: {len(df_test)}")
    print(f"   Period: {df_test['start_timestamp_dt'].min()} to {df_test['start_timestamp_dt'].max()}")
    print("-" * 80)
    
    # 2. Initialize Manager AI
    try:
        manager = ManagerAI(db)
        print("✅ ManagerAI initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to init ManagerAI: {e}")
        return

    # 3. Validation Loop
    results = []
    
    # Trackers
    engine_stats = {
        'Ensemble': {'correct': 0, 'total': 0},
        'Neural': {'correct': 0, 'total': 0},
        'Consensus': {'correct': 0, 'total': 0},
        'Top7': {'correct': 0, 'total': 0}
    }
    
    print(f"\n🚀 Running Inference on {len(df_test)} matches...")
    
    for _, row in tqdm(df_test.iterrows(), total=len(df_test)):
        match_id = int(row['match_id'])
        actual_corners = row['corners_home_ft'] + row['corners_away_ft']
        
        try:
            # Predict using ManagerAI
            # result is a PredictionResult object
            pred = manager.predict_match(match_id)
            
            # --- EVALUATE ENSEMBLE ---
            # Ensemble Raw is approximate total corners.
            # We need a line to grade it against. Let's use the generated line_val.
            ens_line = pred.line_val
            ens_pred_val = pred.ensemble_raw
            ens_is_over = ens_pred_val > ens_line
            
            ens_hit = False
            if ens_is_over and actual_corners > ens_line: ens_hit = True
            if not ens_is_over and actual_corners < ens_line: ens_hit = True
            
            engine_stats['Ensemble']['total'] += 1
            if ens_hit: engine_stats['Ensemble']['correct'] += 1
            
            # --- EVALUATE NEURAL ---
            # Neural also produces raw total
            neu_pred_val = pred.neural_raw
            neu_is_over = neu_pred_val > ens_line # Grade against same line for consistency? Or its own implicit line?
            # Let's say if Neural predicts 10.0 and Line is 10.5, it likes Under.
            
            neu_hit = False
            if neu_is_over and actual_corners > ens_line: neu_hit = True
            if not neu_is_over and actual_corners < ens_line: neu_hit = True
            
            engine_stats['Neural']['total'] += 1
            if neu_hit: engine_stats['Neural']['correct'] += 1
            
            # --- EVALUATE CONSENSUS (Final Prediction) ---
            # This is what the Manager decided
            con_hit = False
            if pred.is_over and actual_corners > pred.line_val: con_hit = True
            if not pred.is_over and actual_corners < pred.line_val: con_hit = True
            
            engine_stats['Consensus']['total'] += 1
            if con_hit: engine_stats['Consensus']['correct'] += 1
            
            # --- EVALUATE TOP 7 (High Confidence) ---
            if pred.consensus_confidence >= 0.65: # Threshold for "Good Bet"
                engine_stats['Top7']['total'] += 1
                if con_hit: engine_stats['Top7']['correct'] += 1
                
        except Exception as e:
            # print(f"Error on {match_id}: {e}")
            pass
            
    # 4. Report
    print("\n" + "="*60)
    print("📊 HEALTH REPORT (Performance vs Actuals)")
    print("="*60)
    
    def print_stat(name, stats):
        acc = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
        icon = "✅" if acc > 55 else "⚠️" if acc > 50 else "❌"
        print(f"{icon} {name:15s}: {acc:6.2f}% ({stats['correct']}/{stats['total']})")
        
    print_stat("Ensemble V3", engine_stats['Ensemble'])
    print_stat("Neural V1", engine_stats['Neural'])
    print_stat("Consensus", engine_stats['Consensus'])
    print("-" * 60)
    print_stat("🔥 Top Picks (>65%)", engine_stats['Top7'])
    
    print("="*60)
    
    if engine_stats['Top7']['total'] > 0:
        top7_acc = (engine_stats['Top7']['correct'] / engine_stats['Top7']['total'] * 100)
        if top7_acc > 60:
            print(f"{Colors.GREEN}✅ SYSTEM STATUS: HEALTHY (Top Picks > 60%){Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}⚠️ SYSTEM STATUS: NEEDS TUNING (Top Picks < 60%){Colors.RESET}")
    else:
        print("ℹ️ Not enough High Confidence picks to grade system health.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=300, help='Number of games to check')
    args = parser.parse_args()
    
    run_health_check(args.limit)
