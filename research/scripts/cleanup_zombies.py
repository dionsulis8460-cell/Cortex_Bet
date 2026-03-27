
"""
CLASSIFICATION: MOVE TO RESEARCH

Research-only maintenance script for pending prediction cleanup.
Not part of production runtime paths.
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.database.db_manager import DBManager

def clean_zombies():
    print("🧟 Caçando predições zumbis (Pending > 48h)...")
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    # Data de corte: 2 dias atrás
    cutoff = datetime.now() - timedelta(days=2)
    cutoff_ts = int(cutoff.timestamp())
    
    # 1. Identificar Zumbis (predictions pending de jogos MUITO antigos)
    query = '''
        SELECT p.id, m.start_timestamp, m.home_team_name, m.away_team_name, p.prediction_label
        FROM predictions p
        JOIN matches m ON p.match_id = m.match_id
        WHERE p.status NOT IN ('GREEN', 'RED')
        AND m.start_timestamp < ?
    '''
    cursor.execute(query, (cutoff_ts,))
    zombies = cursor.fetchall()
    
    if not zombies:
        print("✅ Nenhuma predição zumbi encontrada. Seu banco está limpo!")
        return

    print(f"⚠️ Encontradas {len(zombies)} predições antigas travadas como 'PENDING':")
    for z in zombies:
        ts = datetime.fromtimestamp(z[1]).strftime('%Y-%m-%d')
        print(f" - [{ts}] {z[2]} vs {z[3]} ({z[4]})")
    
    confirm = input(f"\nDeseja marcar essas {len(zombies)} predições como 'VOID' (Anuladas)? (s/n): ")
    if confirm.lower() == 's':
        ids = [z[0] for z in zombies]
        cursor.execute(f"UPDATE predictions SET status = 'VOID' WHERE id IN ({','.join(map(str, ids))})")
        conn.commit()
        print("✅ Zumbis anulados. O Dashboard deve normalizar.")
    else:
        print("Operação cancelada.")

if __name__ == "__main__":
    clean_zombies()
