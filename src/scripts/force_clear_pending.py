
import sys
import os
import sqlite3

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.database.db_manager import DBManager

def nuke_pending():
    print("☢️ INICIANDO OPERAÇÃO REMOÇÃO TOTAL DE PENDENTES (TOP 7) ☢️")
    db = DBManager()
    conn = db.connect()
    cursor = conn.cursor()
    
    # 1. Verificar quantos existem (Query exata do dashboard)
    query_dash = '''
        SELECT count(*)
        FROM predictions 
        WHERE category = 'Top7'
        AND (status IS NULL OR status NOT IN ('GREEN', 'RED', 'VOID'))
    '''
    cursor.execute(query_dash)
    count_before = cursor.fetchone()[0]
    print(f"📊 Contagem Inicial (Pendentes/Null): {count_before}")
    
    if count_before == 0:
        print("✅ O banco diz 0. Se você vê 14, pode ser cache do Streamlit ou outro banco.")
    else:
        # 2. Atualizar TODOS para VOID
        print(f"🧹 Varrendo {count_before} predições...")
        update_query = '''
            UPDATE predictions 
            SET status = 'VOID' 
            WHERE category = 'Top7' 
            AND (status IS NULL OR status NOT IN ('GREEN', 'RED'))
        '''
        cursor.execute(update_query)
        conn.commit()
        print("✅ UPDATE concluído!")
        
        # 3. Verificar novamente
        cursor.execute(query_dash)
        count_after = cursor.fetchone()[0]
        print(f"📊 Contagem Final: {count_after}")

    print("\n⚠️ IMPORTANTE: REINICIE O STREAMLIT (CTRL+C e 'streamlit run run_streamlit.py')")

if __name__ == "__main__":
    nuke_pending()
