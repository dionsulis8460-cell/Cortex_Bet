
"""
CLASSIFICATION: MOVE TO RESEARCH

Research-only pending predictions debug listing.
Not part of production runtime paths.
"""

import sys
import os
import sqlite3
import pandas as pd
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.database.db_manager import DBManager

def list_pending():
    print("🔍 [DEBUG DEEP] Listando predições...")
    db = DBManager()
    conn = db.connect()
    
    # 1. Check Total Pending (Status check)
    query_broad = '''
        SELECT count(*) FROM predictions 
        WHERE status NOT IN ('GREEN', 'RED')
    '''
    total_suspicious = pd.read_sql_query(query_broad, conn).iloc[0,0]
    print(f"📊 Total com status != GREEN/RED: {total_suspicious}")

    # 2. Check Specific Dashboard Query Logic
    query_dash = '''
        SELECT p.id, m.start_timestamp, m.home_team_name, m.away_team_name, p.prediction_label, p.status, p.category
        FROM predictions p
        JOIN matches m ON p.match_id = m.match_id
        WHERE p.category = 'Top7'
        AND (p.status IS NULL OR p.status NOT IN ('GREEN', 'RED'))
    '''
    df = pd.read_sql_query(query_dash, conn)
    
    if df.empty:
        print("❌ Query exata do Dashboard retornou 0 linhas.")
        print("   Verifying category distribution...")
        cat_df = pd.read_sql_query("SELECT category, count(*) FROM predictions GROUP BY category", conn)
        print(cat_df.to_string())
    else:
        print(f"⚠️ Query do Dashboard encontrou {len(df)} linhas:")
        df['match_date'] = pd.to_datetime(df['start_timestamp'], unit='s') - pd.Timedelta(hours=3)
        print(df[['id', 'match_date', 'home_team_name', 'away_team_name', 'category', 'status']].to_string())

if __name__ == "__main__":
    list_pending()
