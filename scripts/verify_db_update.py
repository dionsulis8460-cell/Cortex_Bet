import sys
import os
import sqlite3
import pandas as pd

# Add project root
sys.path.append(os.getcwd())

def verify_target_price():
    # DB path based on db_manager.py default
    db_path = os.path.join(os.getcwd(), 'data', 'football_data.db')
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}, trying alternative...")
        db_path = os.path.join(os.getcwd(), 'football_data.db')
        
    print(f"Connecting to DB: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get latest predictions
    print("\nChecking Latest Predictions for Target Price...")
    query = """
    SELECT match_id, prediction_label, confidence, feedback_text, created_at 
    FROM predictions 
    WHERE category = 'Professional'
    ORDER BY created_at DESC 
    LIMIT 5
    """
    
    rows = cursor.execute(query).fetchall()
    
    found_target = False
    
    for row in rows:
        match_id, label, conf, text, created_at = row
        print(f"\n--- Match {match_id} ({label}) [{created_at}] ---")
        print(f"\n--- Match {match_id} ({label}) ---")
        print(f"Confidence: {conf}")
        if "Target Price" in text:
            print("[OK] 'Target Price' found in feedback!")
            print(text.split('\n')[-2:]) # Show last lines
            found_target = True
        else:
            print("[FAIL] 'Target Price' NOT found.")
            print(text)
            
    conn.close()
    
    if found_target:
        print("\nVERIFICATION SUCCESS: Target Price logic is active.")
    else:
        print("\nVERIFICATION FAILED: No Target Price found.")

if __name__ == "__main__":
    verify_target_price()
