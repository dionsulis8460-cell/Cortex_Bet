
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager

sys.stdout.reconfigure(encoding='utf-8')

def delete_hamburg():
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    match_id = 14062169 # Hamburger SV vs Bayer 04 Leverkusen
    
    print(f"🗑️  Attempting to delete Match ID {match_id}...")
    
    # Check if exists
    cursor.execute("SELECT home_team_name, away_team_name, status FROM matches WHERE match_id = ?", (match_id,))
    match = cursor.fetchone()
    
    if not match:
        print("❌ Match not found. Already deleted?")
        return

    print(f"   Found: {match[0]} vs {match[1]} (Status: {match[2]})")
    
    try:
        # Delete related data first
        cursor.execute("DELETE FROM predictions WHERE match_id = ?", (match_id,))
        cursor.execute("DELETE FROM match_stats WHERE match_id = ?", (match_id,))
        cursor.execute("DELETE FROM bet_items WHERE match_id = ?", (match_id,)) # Caution: User said no bets, but safety first
        
        # Delete match
        cursor.execute("DELETE FROM matches WHERE match_id = ?", (match_id,))
        
        conn.commit()
        print("✅ Match deleted successfully.")
        
    except Exception as e:
        print(f"❌ Error deleting: {e}")

if __name__ == "__main__":
    delete_hamburg()
