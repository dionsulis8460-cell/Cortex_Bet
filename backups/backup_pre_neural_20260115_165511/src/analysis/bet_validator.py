"""
Bet Validator - Automatically validates bets when matches finish

Run this periodically (e.g., via cron job or after match updates)
"""
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager


def validate_pending_bets():
    """Check all pending bets and validate against match results"""
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    print("[*] Starting bet validation...")
    
    # Get all pending bets with match results
    cursor.execute("""
        SELECT 
            ub.id,
            ub.match_id,
            ub.bet_label,
            ub.bet_line,
            ub.stake,
            ub.house_odd,
            ms.corners_home_ft,
            ms.corners_away_ft,
            ms.corners_home_ht,
            ms.corners_away_ht,
            m.status
        FROM user_bets ub
        JOIN matches m ON ub.match_id = m.match_id
        LEFT JOIN match_stats ms ON m.match_id = ms.match_id
        WHERE ub.status = 'PENDING' AND m.status = 'finished'
    """)
    
    pending_bets = cursor.fetchall()
    validated_count = 0
    
    for bet in pending_bets:
        (bet_id, match_id, label, line, stake, house_odd, 
         corners_home_ft, corners_away_ft, corners_home_ht, corners_away_ht, match_status) = bet
        
        # Skip if no corner data available
        if corners_home_ft is None or corners_away_ft is None:
            print(f"[SKIP] Bet#{bet_id}: No corner data for match#{match_id}")
            continue
        
        # Parse bet label and determine if won
        is_correct = validate_bet_logic(
            label, line, 
            corners_home_ft, corners_away_ft,
            corners_home_ht, corners_away_ht
        )
        
        if is_correct is None:
            print(f"[SKIP] Bet#{bet_id}: Unable to parse bet label '{label}'")
            continue
        
        # Calculate profit
        if is_correct:
            profit = stake * (house_odd - 1)
            status = 'GREEN'
        else:
            profit = -stake
            status = 'RED'
        
        # Update bet
        cursor.execute("""
            UPDATE user_bets
            SET status = ?, profit = ?, settled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, profit, bet_id))
        
        # Get current balance
        cursor.execute("SELECT balance FROM bankroll_history ORDER BY created_at DESC LIMIT 1")
        current_balance = cursor.fetchone()[0]
        new_balance = current_balance + profit
        
        # Record bankroll transaction
        cursor.execute("""
            INSERT INTO bankroll_history (
                balance, transaction_type, amount, bet_id, description
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            new_balance,
            'BET_SETTLED',
            profit,
            bet_id,
            f"Bet settled: {status}"
        ))
        
        validated_count += 1
        print(f"[{status}] Bet#{bet_id}: {label} - Profit: R$ {profit:.2f}")
    
    conn.commit()
    conn.close()
    
    print(f"[OK] Validated {validated_count} bets")
    return validated_count


def validate_bet_logic(label: str, line: float, 
                      corners_home_ft: int, corners_away_ft: int,
                      corners_home_ht: int, corners_away_ht: int) -> bool:
    """
    Validate if bet is correct based on match results
    
    Returns:
        True if bet won, False if lost, None if unable to parse
    """
    label_lower = label.lower()
    total_ft = corners_home_ft + corners_away_ft
    total_ht = (corners_home_ht or 0) + (corners_away_ht or 0)
    total_2h = total_ft - total_ht
    
    # Skip non-bet labels (metadata/analysis fields)
    if 'tactical' in label_lower or 'analysis' in label_lower or 'data' in label_lower:
        return None
    
    # Parse bet type - USE WORD BOUNDARIES to avoid substring collisions
    # CRITICAL: '1t' should NOT match 'total', '2t' should NOT match 'bettor', etc.
    import re
    
    # Check for specific team first (more specific patterns)
    if re.search(r'\b(casa|home)\b', label_lower):
        actual = corners_home_ft
    elif re.search(r'\b(vis|away|visitante)\b', label_lower):
        actual = corners_away_ft
    # Check for time periods (1T, 2T, HT) with word boundaries
    elif re.search(r'\b(1t|1h|ht|primeiro)\b', label_lower):
        actual = total_ht
    elif re.search(r'\b(2t|2h|segundo)\b', label_lower):
        actual = total_2h
    # Explicit full-time total keywords
    elif re.search(r'\b(total|both|jogo|completo)\b', label_lower):
        actual = total_ft
    # DEFAULT: Bare "Over X.X" or "Under X.X" → assume Full-Time Total
    elif 'over' in label_lower or 'under' in label_lower:
        actual = total_ft
    else:
        return None  # Unable to parse
    
    # Determine Over/Under
    if 'over' in label_lower:
        return actual > line
    elif 'under' in label_lower:
        return actual < line
    else:
        return None  # Unable to determine


if __name__ == '__main__':
    try:
        count = validate_pending_bets()
        print(f"\n[SUCCESS] Validation complete: {count} bets processed")
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
