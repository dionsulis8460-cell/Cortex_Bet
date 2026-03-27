
import sqlite3
import hashlib
import os
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager

def hash_password(password, salt=None):
    if not salt:
        salt = os.urandom(32)
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    # Return as HEX string to ensure safe storage in SQLite TEXT columns
    return (salt + key).hex()

def verify_password(stored_password, provided_password):
    # Backward compatibility: if stored is not hex (unlikely to work well), try validation
    try:
        # Expect hex string
        stored_bytes = bytes.fromhex(stored_password)
    except:
        # Fallback if somehow raw bytes (should not happen with new users)
        return False
        
    salt = stored_bytes[:32]
    key = stored_bytes[32:]
    new_key = hashlib.pbkdf2_hmac(
        'sha256',
        provided_password.encode('utf-8'),
        salt,
        100000
    )
    return key == new_key

def create_user(args):
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (args.username,))
        if cursor.fetchone():
            print(f"❌ Error: User '{args.username}' already exists.")
            return

        pwd_hash = hash_password(args.password)
        
        cursor.execute("""
            INSERT INTO users (username, password_hash, initial_bankroll, role)
            VALUES (?, ?, ?, ?)
        """, (args.username, pwd_hash, 0.0, 'user'))
        
        user_id = cursor.lastrowid
        
        # Initial Deposit if provided (optional arg, though plan said 0 start)
        # We enforce 0 start but allow manual deposit via deposit command preferably.
        # But let's stick to 0.
        
        print(f"✅ User '{args.username}' created successfully (ID: {user_id}).")
        conn.commit()
    except Exception as e:
        print(f"❌ Error creating user: {e}")
    finally:
        conn.close()

def list_users(args):
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, role, initial_bankroll, created_at FROM users")
    users = cursor.fetchall()
    
    print(f"{'ID':<5} {'Username':<15} {'Role':<10} {'Balance (Est)':<15}")
    print("-" * 50)
    for u in users:
        # Calculate current balance
        cursor.execute("""
            SELECT balance FROM bankroll_history 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (u[0],))
        res = cursor.fetchone()
        balance = res[0] if res else u[3] # Fallback to initial
        
        print(f"{u[0]:<5} {u[1]:<15} {u[2]:<10} R$ {balance:.2f}")
    
    conn.close()

def manage_finance(args):
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE username = ?", (args.username,))
        res = cursor.fetchone()
        if not res:
            print(f"❌ User '{args.username}' not found.")
            return
        
        user_id = res[0]
        amount = float(args.amount)
        
        # Get current balance
        cursor.execute("""
            SELECT balance FROM bankroll_history 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        res = cursor.fetchone()
        current_balance = res[0] if res else 0.0
        
        if args.action == 'withdraw':
            if current_balance < amount:
                print(f"❌ Insufficient funds. Balance: R$ {current_balance:.2f}, Request: R$ {amount:.2f}")
                return
            new_balance = current_balance - amount
            desc = f"Withdrawal by Admin"
            tx_type = 'WITHDRAW'
        else: # deposit
            new_balance = current_balance + amount
            desc = f"Deposit by Admin"
            tx_type = 'DEPOSIT'
            
        cursor.execute("""
            INSERT INTO bankroll_history (
                user_id, balance, transaction_type, amount, description
            ) VALUES (?, ?, ?, ?, ?)
        """, (user_id, new_balance, tx_type, amount if args.action == 'deposit' else -amount, desc))
        
        print(f"✅ {args.action.title()} successful! New Balance for {args.username}: R$ {new_balance:.2f}")
        conn.commit()
        
    except Exception as e:
        print(f"❌ Error processing transaction: {e}")
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Cortex Bet User Manager")
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Create User
    p_create = subparsers.add_parser('create', help='Create a new user')
    p_create.add_argument('username', help='Username')
    p_create.add_argument('--password', required=True, help='Password')
    p_create.set_defaults(func=create_user)
    
    # List Users
    p_list = subparsers.add_parser('list', help='List all users')
    p_list.set_defaults(func=list_users)
    
    # Deposit
    p_deposit = subparsers.add_parser('deposit', help='Deposit funds')
    p_deposit.add_argument('username', help='Username')
    p_deposit.add_argument('amount', type=float, help='Amount')
    p_deposit.set_defaults(func=manage_finance, action='deposit')
    
    # Withdraw
    p_withdraw = subparsers.add_parser('withdraw', help='Withdraw funds')
    p_withdraw.add_argument('username', help='Username')
    p_withdraw.add_argument('amount', type=float, help='Amount')
    p_withdraw.set_defaults(func=manage_finance, action='withdraw')

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
