"""
Database migration script to create Bankroll Management tables
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DBManager
import sqlite3

def create_bankroll_tables():
    """Create user_bets and bankroll_history tables"""
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    print("[*] Creating Bankroll Management tables...")
    
    # User Bets Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            match_id INTEGER,
            prediction_id INTEGER,
            bet_label TEXT NOT NULL,
            bet_line REAL,
            stake REAL NOT NULL,
            house_odd REAL,
            fair_odd REAL,
            status TEXT DEFAULT 'PENDING',
            profit REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            settled_at TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches (match_id),
            FOREIGN KEY (prediction_id) REFERENCES predictions (id)
        )
    ''')
    
    # Bet Slips Table (for multiple bets grouped together)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bet_slips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            slip_type TEXT DEFAULT 'SINGLE',
            total_stake REAL NOT NULL,
            calculated_odd REAL,
            manual_odd REAL,
            final_odd REAL,
            potential_return REAL,
            actual_return REAL DEFAULT 0,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            settled_at TIMESTAMP
        )
    ''')
    
    # Link table for bets in slips
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS slip_bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slip_id INTEGER NOT NULL,
            bet_id INTEGER NOT NULL,
            FOREIGN KEY (slip_id) REFERENCES bet_slips (id),
            FOREIGN KEY (bet_id) REFERENCES user_bets (id)
        )
    ''')
    
    # Bankroll History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bankroll_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
            balance REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            slip_id INTEGER,
            bet_id INTEGER,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (slip_id) REFERENCES bet_slips (id),
            FOREIGN KEY (bet_id) REFERENCES user_bets (id)
        )
    ''')
    
    # Initialize starting balance if needed
    cursor.execute("SELECT COUNT(*) FROM bankroll_history")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO bankroll_history (balance, transaction_type, amount, description)
            VALUES (1000.0, 'DEPOSIT', 1000.0, 'Initial balance')
        ''')
        print("[OK] Initialized starting balance: R$ 1000.00")
    
    conn.commit()
    conn.close()
    
    print("[OK] Bankroll tables created successfully!")
    print("[*] Tables: user_bets, bet_slips, slip_bets, bankroll_history")

if __name__ == '__main__':
    try:
        create_bankroll_tables()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
