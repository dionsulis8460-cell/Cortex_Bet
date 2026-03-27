
import sys
import os
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager

def validate_bet_logic(label: str, line: float, 
                      corners_home_ft: int, corners_away_ft: int,
                      corners_home_ht: int, corners_away_ht: int) -> str:
    """
    Validate if bet is GREEN/RED based on match results.
    Returns: 'GREEN', 'RED', or None (unable to parse)
    """
    label_lower = label.lower()
    total_ft = corners_home_ft + corners_away_ft
    total_ht = (corners_home_ht or 0) + (corners_away_ht or 0)
    total_2h = total_ft - total_ht
    
    # Skip non-bet labels
    if 'tactical' in label_lower or 'analysis' in label_lower:
        return None
    
    actual = None
    
    # 1. Determine the metric (Who/When)
    if re.search(r'\b(casa|home)\b', label_lower):
        actual = corners_home_ft
        # Handle "Home 1T" or "Home 2T" logic if needed, but usually markets are FT
        if re.search(r'\b(1t|1h|ht)\b', label_lower):
            actual = corners_home_ht
    elif re.search(r'\b(vis|away|visitante)\b', label_lower):
        actual = corners_away_ft
        if re.search(r'\b(1t|1h|ht)\b', label_lower):
            actual = corners_away_ht
    elif re.search(r'\b(1t|1h|ht|primeiro)\b', label_lower):
        actual = total_ht
    elif re.search(r'\b(2t|2h|segundo)\b', label_lower):
        actual = total_2h
    elif re.search(r'\b(total|both|jogo|completo)\b', label_lower):
        actual = total_ft
    elif 'over' in label_lower or 'under' in label_lower:
        actual = total_ft # Default to Full Time Total
    
    if actual is None:
        return 'VOID' # Can't determine metric -> Void for safety
        
    # 2. Compare with Line
    # Extract line if passed as 0.0 (sometimes happens with bad parsing elsewhere)
    if line == 0.0:
        match = re.search(r'(?:over|under)\s*(\d+\.?\d*)', label_lower)
        if match:
            line = float(match.group(1))
            
    if 'over' in label_lower:
        return 'GREEN' if actual > line else 'RED'
    elif 'under' in label_lower:
        return 'GREEN' if actual < line else 'RED'
        
    return 'VOID'


def resolve_pending_bets():
    """Main function to resolve user bets"""
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    print("[BetResolver] Starting scan for pending user bets...")
    
    # 1. Get ALL Pending Bet Items from Finished Matches
    # Note: We need to verify if the match is truly finished
    cursor.execute("""
        SELECT 
            bi.id, bi.bet_id, bi.match_id, bi.prediction_label, bi.odds,
            ms.corners_home_ft, ms.corners_away_ft, 
            ms.corners_home_ht, ms.corners_away_ht,
            m.status
        FROM bet_items bi
        JOIN matches m ON bi.match_id = m.match_id
        LEFT JOIN match_stats ms ON m.match_id = ms.match_id
        WHERE bi.status = 'PENDING' 
          AND m.status IN ('finished', 'ended', 'closed')
    """)
    
    items = cursor.fetchall()
    items_resolved = 0
    
    for item in items:
        (item_id, bet_id, match_id, label, odds, 
         home_ft, away_ft, home_ht, away_ht, match_status) = item
         
        # Check if stats are available
        if home_ft is None or away_ft is None:
            # Maybe use momentum/fallback or keep pending
            continue
            
        # Extract line from label (assuming stored line logic is brittle, re-parse is safer)
        # Using regex to get the number from "Over 10.5"
        line = 0.0
        import re
        # Smart Extraction Logic (Matches prediction_engine.py)
        # 1. Keyword Priority: Look for number AFTER Over/Under/Mais/Menos
        match = re.search(r'(?:over|under|mais|menos)\s*(\d+\.?\d*)', label, re.IGNORECASE)
        if match:
            line = float(match.group(1))
        else:
            # 2. Decimal Priority: Look for numbers with dots (e.g. 6.5, 3.25)
            # This avoids picking up integer '1' from '1T', '1X2' if the line is decimal
            match = re.search(r'(\d+\.\d+)', label)
            if match:
                line = float(match.group(1))
            else:
                # 3. Fallback: First number found (Risky, but last resort)
                match = re.search(r'(\d+\.?\d*)', label)
                if match:
                    line = float(match.group(1))
            
        new_status = validate_bet_logic(
            label, line, 
            home_ft, away_ft, 
            home_ht or 0, away_ht or 0  # HT might be None
        )
        
        if new_status:
            cursor.execute("UPDATE bet_items SET status = ? WHERE id = ?", (new_status, item_id))
            items_resolved += 1
            print(f"   > Resolved Item #{item_id} ({label}): {new_status}")
            
    conn.commit()
    print(f"[BetResolver] Resolved {items_resolved} items.")
    
    # 2. Update Parent Bets (Aggregation)
    # Check bets that are PENDING but might have all items resolved
    cursor.execute("""
        SELECT id, user_id, stake, total_odds 
        FROM bets 
        WHERE status = 'PENDING'
    """)
    
    pending_parent_bets = cursor.fetchall()
    bets_resolved_count = 0
    
    for bet in pending_parent_bets:
        bet_id, user_id, stake, total_odds = bet
        
        # Check all child items
        cursor.execute("SELECT status FROM bet_items WHERE bet_id = ?", (bet_id,))
        item_statuses = [r[0] for r in cursor.fetchall()]
        
        if not item_statuses:
            continue # Ghost bet?
            
        if 'PENDING' in item_statuses:
            continue # Still waiting for some leg
            
        # All items resolved -> Determine final status
        final_status = 'PENDING'
        
        if 'RED' in item_statuses:
            final_status = 'RED'
            payout = 0.0
            profit = -stake
        elif all(s == 'GREEN' or s == 'VOID' for s in item_statuses):
            # Recalculate Odds if there are VOIDs
            # Simplified: Treat VOID as odd 1.0
            # (In a real system we would recalculate total_odds excluding voids)
            if all(s == 'VOID' for s in item_statuses):
                final_status = 'VOID'
                payout = stake
                profit = 0.0
            else:
                final_status = 'GREEN'
                payout = stake * total_odds
                profit = payout - stake
        else:
            # Should not happen (e.g. mix of VOID and RED is covered by RED check)
            final_status = 'RED'
            payout = 0.0
            profit = -stake
            
        # UPDATE BET
        cursor.execute("""
            UPDATE bets 
            SET status = ?, possible_win = ? 
            WHERE id = ?
        """, (final_status, payout, bet_id))
        
        # HANDLE MONEY (Update User Balance)
        if final_status in ('GREEN', 'VOID'):
             # Add payout to user balance
             cursor.execute("""
                INSERT INTO bankroll_history (user_id, balance, transaction_type, amount, description)
                SELECT ?, 
                       (SELECT balance FROM bankroll_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 1) + ?, 
                       ?, ?, ?
             """, (user_id, user_id, payout, 'PAYOUT', payout, f"Bet {bet_id} {final_status}"))
             
             # Also update users table helper column (Skip if not exists)
             # cursor.execute("UPDATE users SET current_bankroll = current_bankroll + ? WHERE id = ?", (payout, user_id))
             
        bets_resolved_count += 1
        print(f"   >>> Bet #{bet_id} Settled: {final_status} | Payout: {payout}")
        
    conn.commit()
    conn.close()
    print(f"[BetResolver] Fully settled {bets_resolved_count} bets.")
    return bets_resolved_count

if __name__ == "__main__":
    resolve_pending_bets()
