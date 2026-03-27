"""
Bankroll API backend handler (V3 - Multi-User Support)
"""
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager


def get_current_balance(cursor, user_id):
    """Get current bankroll balance for specific user"""
    cursor.execute("""
        SELECT balance FROM bankroll_history 
        WHERE user_id = ?
        ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Fallback to initial bankroll if no history
    cursor.execute("SELECT initial_bankroll FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    return user_row[0] if user_row else 0.0


def get_bet_history(cursor, user_id):
    """Get all user bets with items (Multi-Bet support)"""
    # 1. Fetch parent bets for USER
    cursor.execute("""
        SELECT 
            id, status, stake, total_odds, possible_win, bet_type, created_at
        FROM bets
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (user_id,))
    parent_rows = cursor.fetchall()
    
    bets = []
    for row in parent_rows:
        bet_id, status, stake, total_odds, possible_win, bet_type, created_at = row
        
        # 2. Fetch items for this bet
        cursor.execute("""
            SELECT 
                bi.prediction_label, bi.odds, bi.status, 
                m.home_team_name, m.away_team_name
            FROM bet_items bi
            LEFT JOIN matches m ON bi.match_id = m.match_id
            WHERE bi.bet_id = ?
        """, (bet_id,))
        
        items_rows = cursor.fetchall()
        
        bet_items = []
        
        for item in items_rows:
            label, odds, item_status, home, away = item
            match_name = f"{home} vs {away}" if home and away else "Match Info N/A"
            bet_items.append({
                'label': label,
                'odds': odds,
                'status': item_status,
                'match': match_name
            })
        
        # Construct summary label
        if len(bet_items) > 1:
            main_label = f"Multiple ({len(bet_items)})"
            match_summary = "Multiple Matches"
        elif len(bet_items) == 1:
            main_label = bet_items[0]['label']
            match_summary = bet_items[0]['match']
        else:
            main_label = "Empty Bet"
            match_summary = "N/A"

        profit = (possible_win - stake) if status == 'GREEN' else (-stake if status == 'RED' else 0)

        bets.append({
            'id': bet_id,
            'label': main_label,
            'match_name': match_summary, 
            'stake': stake,
            'house_odd': total_odds,
            'fair_odd': 0,
            'status': status,
            'profit': profit,
            'created_at': created_at,
            'items': bet_items,
            # Backward compat fields
            'home_team': bet_items[0]['match'].split(' vs ')[0] if bet_items else '',
            'away_team': bet_items[0]['match'].split(' vs ')[1] if bet_items and ' vs ' in bet_items[0]['match'] else '',
        })
    
    return bets


def place_bet(cursor, conn, bet_data, user_id):
    """Place a new bet (Single or Multiple)"""
    
    # 1. Parse Input
    stake = float(bet_data['stake'])
    total_odds = float(bet_data.get('house_odd', 1.0))
    items = bet_data.get('items', [])
    
    # Check Balance
    current_balance = get_current_balance(cursor, user_id)
    if current_balance < stake:
        return {'error': f'Insufficient funds. Balance: R$ {current_balance:.2f}'}

    # Validation
    if not items:
        # Fallback for old single-bet format
        if 'match_id' in bet_data:
            items = [{
                'match_id': bet_data['match_id'],
                'label': bet_data['label'],
                'odd': bet_data.get('house_odd', 1.0)
            }]
        else:
            return {'error': 'No bet items provided'}

    possible_win = stake * total_odds
    bet_type = 'MULTIPLE' if len(items) > 1 else 'SINGLE'
    
    # 2. Insert Parent Bet
    cursor.execute("""
        INSERT INTO bets (
            user_id, timestamp, status, stake, total_odds, possible_win, bet_type
        ) VALUES (?, ?, 'PENDING', ?, ?, ?, ?)
    """, (
        user_id,
        int(datetime.now().timestamp()),
        stake,
        total_odds,
        possible_win,
        bet_type
    ))
    bet_id = cursor.lastrowid
    
    # 3. Insert Bet Items
    for item in items:
        cursor.execute("""
            INSERT INTO bet_items (
                bet_id, match_id, prediction_label, odds, status
            ) VALUES (?, ?, ?, ?, 'PENDING')
        """, (
            bet_id,
            item['match_id'],
            item['label'],
            item.get('odd', 1.0)
        ))
    
    # 4. Update Balance
    new_balance = current_balance - stake
    
    cursor.execute("""
        INSERT INTO bankroll_history (
            user_id, balance, transaction_type, amount, bet_id, description
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        new_balance,
        'BET_PLACED',
        -stake,
        bet_id,
        f"Bet placed: {bet_type} ({len(items)} items)"
    ))
    
    conn.commit()
    
    return {
        'bet_id': bet_id,
        'new_balance': new_balance
    }


def delete_bet(cursor, conn, bet_id, user_id):
    """Delete a bet and refund"""
    # 1. Get bet details from BETS table (Validate Owner)
    cursor.execute("SELECT stake, status FROM bets WHERE id = ? AND user_id = ?", (bet_id, user_id))
    row = cursor.fetchone()
    
    if not row:
        return {'error': 'Bet not found or access denied'}
        
    stake, status = row
    
    # 2. Refund if PENDING
    if status == 'PENDING':
        balance = get_current_balance(cursor, user_id)
        new_balance = balance + stake
        
        cursor.execute("""
            INSERT INTO bankroll_history (
                user_id, balance, transaction_type, amount, bet_id, description
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            new_balance,
            'REFUND',
            stake,
            bet_id,
            f"Refund: Bet {bet_id} deleted"
        ))
    else:
        new_balance = get_current_balance(cursor, user_id)

    # 3. Delete
    try:
        cursor.execute("DELETE FROM bet_items WHERE bet_id = ?", (bet_id,))
    except:
        pass
        
    cursor.execute("DELETE FROM bets WHERE id = ?", (bet_id,))
    conn.commit()
    
    return {'success': True, 'new_balance': new_balance}


def get_stats(cursor, user_id):
    """Get advanced user stats (ROI, Winrate)"""
    # Fetch all bets
    bets = get_bet_history(cursor, user_id)
    
    # Calculate Deposits
    cursor.execute("SELECT SUM(amount) FROM bankroll_history WHERE user_id = ? AND transaction_type = 'DEPOSIT'", (user_id,))
    total_deposits = cursor.fetchone()[0] or 0.0
    
    # Calculate Withdrawals
    cursor.execute("SELECT SUM(ABS(amount)) FROM bankroll_history WHERE user_id = ? AND transaction_type = 'WITHDRAW'", (user_id,))
    total_withdrawals = cursor.fetchone()[0] or 0.0

    current_balance = get_current_balance(cursor, user_id)
    
    # ROI = (Liquid Profit) / Investment
    # Profit = (Balance + Withdrawals) - Deposits
    net_profit = (current_balance + total_withdrawals) - total_deposits
    roi = (net_profit / total_deposits * 100) if total_deposits > 0 else 0.0

    total_bets = len(bets)
    wins = sum(1 for b in bets if b['status'] == 'GREEN')
    pending = sum(1 for b in bets if b['status'] == 'PENDING')
    
    return {
        'total_bets': total_bets,
        'wins': wins,
        'pending': pending,
        'total_profit': net_profit, 
        'roi': roi,
        'win_rate': (wins / (total_bets - pending) * 100) if (total_bets - pending) > 0 else 0,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals
    }




def get_leaderboard(cursor):
    """Get leaderboard stats for all users"""
    # 1. Get all users
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()
    
    leaderboard = []
    
    for user_row in users:
        uid, username = user_row
        stats = get_stats(cursor, uid) # Re-use get_stats logic
        
        # Add to list if they have activity (optional, or just show all)
        leaderboard.append({
            'username': username,
            'roi': stats['roi'],
            'profit': stats['total_profit'],
            'win_rate': stats['win_rate'],
            'wins': stats['wins'],    # Added wins count
            'Total Bets': stats['total_bets']
        })
    
    # Sort Criteria (User Request: "Rank por aposta acertadas"):
    # 1. Total Wins (High to Low) - PRIMARY
    # 2. Profit (High to Low) - Tie Breaker
    # 3. Win Rate (High to Low) - Tie Breaker
    leaderboard.sort(key=lambda x: (x['wins'], x['profit'], x['win_rate']), reverse=True)
    return leaderboard


def get_public_feed(cursor, limit=50):
    """Get recent bets from all users for social feed"""
    # Fetch recent bets with user info
    cursor.execute("""
        SELECT 
            b.id, b.status, b.stake, b.total_odds, b.possible_win, b.bet_type, b.created_at,
            u.username
        FROM bets b
        JOIN users u ON b.user_id = u.id
        ORDER BY b.created_at DESC
        LIMIT ?
    """, (limit,))
    
    bets_rows = cursor.fetchall()
    
    feed = []
    for row in bets_rows:
        bet_id, status, stake, total_odds, possible_win, bet_type, created_at, username = row
        
        # Calculate profit
        profit = (possible_win - stake) if status == 'GREEN' else (-stake if status == 'RED' else 0)
        
        # Fetch bet items
        cursor.execute("""
            SELECT 
                bi.prediction_label, bi.odds,
                m.home_team_name, m.away_team_name
            FROM bet_items bi
            LEFT JOIN matches m ON bi.match_id = m.match_id
            WHERE bi.bet_id = ?
        """, (bet_id,))
        
        items_rows = cursor.fetchall()
        items = []
        for item_row in items_rows:
            label, odds, home, away = item_row
            match_name = f"{home} vs {away}" if home and away else "Match Info N/A"
            items.append({
                'match': match_name,
                'label': label,
                'odds': odds
            })
        
        feed.append({
            'bet_id': bet_id,
            'username': username,
            'stake': stake,
            'total_odds': total_odds,
            'possible_win': possible_win,
            'status': status,
            'profit': profit,
            'created_at': created_at,
            'bet_type': bet_type,
            'items': items
        })
    
    return feed


def manage_funds(cursor, conn, user_id, amount, transaction_type):
    """Handle Deposit and Withdrawal"""
    # Verify balance for withdrawal
    current_balance = get_current_balance(cursor, user_id)
    
    if transaction_type == 'WITHDRAW':
        if current_balance < amount:
            return {'error': f'Insufficient funds. Available: R$ {current_balance:.2f}'}
        new_balance = current_balance - amount
        desc = "Withdrawal via Web"
    elif transaction_type == 'DEPOSIT':
        new_balance = current_balance + amount
        desc = "Deposit via Web"
    else:
        return {'error': 'Invalid transaction type'}

    cursor.execute("""
        INSERT INTO bankroll_history (
            user_id, balance, transaction_type, amount, description
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        new_balance,
        transaction_type,
        amount if transaction_type == 'DEPOSIT' else -amount,
        desc
    ))
    conn.commit()
    return {'success': True, 'new_balance': new_balance}


def auth_user(cursor, username, password):
    """Authenticate user and return ID"""
    cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    # ... (rest of auth_user same as before)

    
    if not row:
        return {'error': 'User not found'}
        
    user_id, stored_hash = row
    
    try:
        # Convert Hex String back to bytes
        # This assumes verify_password in user_manager now stores hex
        if isinstance(stored_hash, str):
            try:
                stored_hash_bytes = bytes.fromhex(stored_hash)
            except ValueError:
                # Fallback: maybe it's legacy raw bytes that got latin-1 decoded?
                # This is messy. Best to rely on hex going forward.
                stored_hash_bytes = stored_hash.encode('latin-1') 
        else:
             stored_hash_bytes = stored_hash
             
        salt = stored_hash_bytes[:32]
        key = stored_hash_bytes[32:]
        new_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        if key == new_key:
            return {'success': True, 'userId': user_id, 'username': username}
        else:
            return {'error': 'Invalid password'}
    except Exception as e:
        return {'error': f'Auth error: {str(e)}'}


def main():
    try:
        method = sys.argv[1] if len(sys.argv) > 1 else 'GET'
        
        # ... (Previous args parsing logic) ...
        # Parsing User ID safely
        try:
             # If called like: python script.py GET balance <user_id>
             if len(sys.argv) > 3 and sys.argv[3].isdigit():
                 user_id = int(sys.argv[3])
             else:
                 user_id = 1
        except:
            user_id = 1

        db = DBManager()
        conn = db.connect()
        cursor = conn.cursor()
        
        if method == 'AUTH':
            # Args: AUTH <username> <password>
            username = sys.argv[2]
            password = sys.argv[3]
            result = auth_user(cursor, username, password)
            print(json.dumps(result))

        elif method == 'TRANSACTION':
            # Args: TRANSACTION <user_id> <type> <amount>
            # type: DEPOSIT or WITHDRAW
            user_id = int(sys.argv[2])
            tx_type = sys.argv[3].upper()
            amount = float(sys.argv[4])
            
            result = manage_funds(cursor, conn, user_id, amount, tx_type)
            print(json.dumps(result))

        elif method == 'LEADERBOARD':
            result = get_leaderboard(cursor)
            print(json.dumps({'leaderboard': result}))

        elif method == 'PUBLIC_FEED':
            # Args: PUBLIC_FEED [limit]
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            result = get_public_feed(cursor, limit)
            print(json.dumps({'feed': result}))

        elif method == 'GET':
            data_type = sys.argv[2] if len(sys.argv) > 2 else 'all'
            
            if data_type == 'balance':
                balance = get_current_balance(cursor, user_id)
                print(json.dumps({'balance': balance}))
            elif data_type == 'history':
                bets = get_bet_history(cursor, user_id)
                print(json.dumps({'bets': bets}))
            else:  # 'all'
                balance = get_current_balance(cursor, user_id)
                bets = get_bet_history(cursor, user_id)
                stats = get_stats(cursor, user_id)
                
                print(json.dumps({
                    'balance': balance,
                    'bets': bets,
                    'stats': stats
                }))
        
        elif method == 'POST':
            # Payload: {"items": [...], "stake": 10, "userId": 1}
            bet_data = json.loads(sys.argv[2])
            
            # Prefer userId from payload if available
            uid = bet_data.get('userId', user_id)
            
            result = place_bet(cursor, conn, bet_data, uid)
            print(json.dumps(result))

        elif method == 'DELETE':
            bet_id = int(sys.argv[2])
            # We need user_id passed in args or payload. 
            # DELETE calls usually: python script.py DELETE <bet_id> <user_id>
            # Let's support an extra arg for user_id
            if len(sys.argv) > 3:
                user_id = int(sys.argv[3])
                
            result = delete_bet(cursor, conn, bet_id, user_id)
            print(json.dumps(result))
        
        conn.close()
        
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
