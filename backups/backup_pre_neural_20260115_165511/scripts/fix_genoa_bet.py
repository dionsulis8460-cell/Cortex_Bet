
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager
from src.analysis.bet_resolver import resolve_pending_bets

# FIX: Force UTF-8 encoding for Windows Consoles to support emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass 


def fix_genoa_bet():
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    print("🔍 Searching for the incorrect bet...")
    
    # Find bet item
    # Match: Genoa vs Cagliari
    # Incorrect Label: Vis. Over 3.5
    # Status: RED (assumed)
    
    
    # Update: JOIN with matches to find by team names
    cursor.execute("""
        SELECT bi.id, bi.bet_id, bi.match_id, bi.prediction_label, bi.status 
        FROM bet_items bi
        JOIN matches m ON bi.match_id = m.match_id
        WHERE (m.home_team_name LIKE '%Genoa%' OR m.away_team_name LIKE '%Genoa%')
        AND (m.home_team_name LIKE '%Cagliari%' OR m.away_team_name LIKE '%Cagliari%')
        AND bi.prediction_label LIKE '%Over 3.5%'
    """)
    
    item = cursor.fetchone()
    
    if not item:
        print("❌ Bet not found! Please check parameters.")
        return

    item_id, bet_id, match_id, old_label, old_status = item
    print(f"✅ Found Item #{item_id} (Bet #{bet_id})")
    print(f"   Label: {old_label}")
    print(f"   Status: {old_status}")
    
    # Update Label and Reset Status
    new_label = old_label.replace("3.5", "2.5")
    print(f"🛠️  Fixing label to: {new_label}")
    
    # 1. Update Item
    cursor.execute("""
        UPDATE bet_items 
        SET prediction_label = ?, status = 'PENDING' 
        WHERE id = ?
    """, (new_label, item_id))
    
    # 2. Reset Parent Bet to PENDING so resolver picks it up
    print(f"   Resetting Parent Bet #{bet_id} to PENDING...")
    cursor.execute("UPDATE bets SET status = 'PENDING' WHERE id = ?", (bet_id,))
    
    conn.commit()
    conn.close()
    
    print("🔄 Re-running Bet Resolver to settle correctly...")
    resolve_pending_bets()
    print("✅ Done! Check your balance.")

if __name__ == "__main__":
    fix_genoa_bet()
