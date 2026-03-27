import sqlite3
import os
import sys

# DB path
db_path = os.path.join(os.getcwd(), 'data', 'football_data.db')
if not os.path.exists(db_path): db_path = 'football_data.db'

print(f"Checking DB: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check latest Top 7 predictions
print("\n--- Verifying Latest Top 7 Predictions ---")
query = """
SELECT match_id, prediction_label, fair_odds, odds, confidence
FROM predictions 
WHERE category='Top7' 
ORDER BY created_at DESC 
LIMIT 14
"""

rows = cursor.execute(query).fetchall()

failed = False
for row in rows:
    mid, label, fair, odd, conf = row
    
    # Logic: If Odd < 1.25 (and it's not a value bet which we can't verify easily without EV field here, but assuming odd=fair if no bookmaker), it's junk.
    # The filter was: FairOdd < 1.25 and not IsBookmaker.
    # In DB, if no bookmaker, odd usually equals fair_odds.
    
    is_junk = (odd < 1.25)
    
    status = "[FAIL]" if is_junk else "[OK]"
    if is_junk: failed = True
    
    print(f"{status} Match {mid}: {label:20} | Odd: {odd:.2f} | Fair: {fair:.2f} | Conf: {conf:.1%}")

if failed:
    print("\n[ERROR] Found Junk Odds (<1.25) in Top 7!")
    sys.exit(1)
    
print("\n[SUCCESS] Top 7 list is clean of junk odds.")
conn.close()
