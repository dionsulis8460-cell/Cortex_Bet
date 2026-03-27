
import sys
import os
from pathlib import Path
from datetime import datetime

# Force UTF-8 for Windows Consoles
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager

def list_pending():
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    print("🔍 Searching for matches with status 'notstarted'...")
    
    cursor.execute("""
        SELECT match_id, home_team_name, away_team_name, start_timestamp, status, match_minute 
        FROM matches 
        WHERE status = 'notstarted'
        ORDER BY start_timestamp
    """)
    
    bets = cursor.fetchall()
    
    if not bets:
        print("✅ No pending bets found.")
    else:
        print(f"found {len(bets)} pending bets:")
        for match in bets:
            mid, h, a, ts, status, minute = match
            try:
                dt = datetime.fromtimestamp(int(ts))
            except:
                dt = ts
            print(f"[{mid}] {dt} | {h} vs {a} | Status: {status} ({minute})")

    print("\n🔍 Checking distinct match statuses in DB:")
    cursor.execute("SELECT DISTINCT status, COUNT(*) FROM matches GROUP BY status")
    for row in cursor.fetchall():
        print(f" - {row[0]}: {row[1]}")

if __name__ == "__main__":
    list_pending()
