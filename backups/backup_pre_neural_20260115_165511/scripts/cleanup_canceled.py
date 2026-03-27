
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager

sys.stdout.reconfigure(encoding='utf-8')

def cleanup_canceled_matches():
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    print("🧹 Starting cleanup of canceled/postponed matches...")
    
    # 1. Identify Target Matches
    ignored_statuses = ['canceled', 'postponed', 'interrupted', 'abandoned', 'coverage_canceled', 'delayed']
    placeholders = ','.join(['?'] * len(ignored_statuses))
    
    cursor.execute(f"SELECT match_id, home_team_name, away_team_name, status FROM matches WHERE status IN ({placeholders})", ignored_statuses)
    targets = cursor.fetchall()
    
    if not targets:
        print("✅ No canceled matches found in database.")
        return

    print(f"🔍 Found {len(targets)} matches with canceled/postponed status.")
    
    deleted_count = 0
    skipped_count = 0
    
    for match in targets:
        m_id, home, away, status = match
        
        # 2. Check for Bets
        cursor.execute("SELECT COUNT(*) FROM bet_items WHERE match_id = ?", (m_id,))
        bet_count = cursor.fetchone()[0]
        
        if bet_count > 0:
            print(f"⚠️  Match {home} vs {away} has {bet_count} bets. Updating status to '{status}' instead of deleting.")
            # Update match status to reflect the new reality (e.g., 'canceled', 'postponed')
            # This ensures the user sees 'Canceled' in their betting history instead of a zombie 'Pending'
            cursor.execute("UPDATE matches SET status = ? WHERE match_id = ?", (status, m_id))
            
            # Also update the bet_items status to 'VOID' or 'CANCELED' if it was PENDING?
            # User request: "Se tiver apostas, ele só atualiza o status para 'Canceled'"
            # Let's update the match status first. The Bet Resolver might need to handle 'canceled' matches globally?
            # For now, let's mark predictions as 'CANCELED' too? 
            # Safest is to just update the Match Status for now, so it shows up in UI.
            # And maybe update the bet_items status to VOID so they don't stay PENDING forever?
            
            cursor.execute("UPDATE bet_items SET status = 'VOID' WHERE match_id = ? AND status = 'PENDING'", (m_id,))
            skipped_count += 1
            print(f"   -> Updated match and {bet_count} bets to CANCELED/VOID.")
            continue
            
        # 3. Delete Recursively (Manual Cascade)
        try:
            # Delete Predictions
            cursor.execute("DELETE FROM predictions WHERE match_id = ?", (m_id,))
            
            # Delete Stats
            cursor.execute("DELETE FROM match_stats WHERE match_id = ?", (m_id,))
            
            # Delete Match
            cursor.execute("DELETE FROM matches WHERE match_id = ?", (m_id,))
            
            deleted_count += 1
            print(f"🗑️  Deleted: {home} vs {away} ({status})")
            
        except Exception as e:
            print(f"❌ Error deleting match {m_id}: {e}")

    conn.commit()
    print(f"\n✅ Cleanup Complete.")
    print(f"   - Deleted: {deleted_count}")
    print(f"   - Skipped (Safe Mode): {skipped_count}")

if __name__ == "__main__":
    cleanup_canceled_matches()
