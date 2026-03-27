import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm

# Add project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.db_manager import DBManager
from src.analysis.manager_ai import ManagerAI
from src.domain.models import BettingPick
from src.domain.strategies.selection_strategy import SelectionStrategy

def run_backtest():
    print("🚀 Iniciando Backtest do Sistema (Cortex V3.0)...")
    
    db = DBManager()
    
    # 1. Carregar Histórico Completo (12k+ jogos)
    print("📊 Carregando histórico estatístico...")
    df = db.get_historical_data()
    print(f"   Total de jogos no banco: {len(df)}")
    
    # Filtra jogos finalizados com stats
    df_valid = df[df['status'] == 'finished'].copy()
    df_valid['total_corners'] = df_valid['corners_home_ft'] + df_valid['corners_away_ft']
    
    print(f"   Jogos finalizados válidos para teste: {len(df_valid)}")
    
    # 2. Inicializar Serviços
    manager = ManagerAI()
    strategy = SelectionStrategy(min_confidence=0.60)
    
    # 3. Setup do Loop
    results_analyst = [] # Hit rate do modelo puro
    results_manager = [] # Hit rate das Top 7 Picks
    
    # Simula dias recentes (ex: últimos 500 jogos para economizar tempo no teste inicial)
    # Se quiser testar TUDO, remova o .tail()
    test_set = df_valid.sort_values('start_timestamp') # Full Test (12k games)
    print(f"   ⚡ Executando inferência em {len(test_set)} jogos (Histórico Completo)...")
    
    correct_analyst = 0
    total_analyst = 0
    
    predictions_buffer = [] # Para o Manager AI processar em lote
    
    # Agrupa por DIA para simular o comportamento do Manager (que vê o dia todo)
    test_set['date'] = pd.to_datetime(test_set['start_timestamp'], unit='s').dt.date
    daily_groups = test_set.groupby('date')
    
    manager_hits = 0
    manager_total = 0
    
    for date, group in tqdm(daily_groups, desc="Simulando Dias"):
        
        daily_candidates = []
        
        for _, row in group.iterrows():
            # A. Analyst AI
            match_id = row['match_id']
            home_id = row['home_team_id']
            away_id = row['away_team_id']
            
            try:
                # Simula previsão
                match_data = {'match_id': match_id, 'home_team_id': home_id, 'away_team_id': away_id,
                              'home_team_name': f'Team_{home_id}', 'away_team_name': f'Team_{away_id}'}
                result = manager.predict_match(match_data)
                
                if result is None:
                    continue
                    
                # Verifica acerto do Analyst (Ex: Over 9.5 vs Realidade)
                actual_corners = row['total_corners']
                line = result.line_val
                pick_over = result.is_over
                
                is_hit = False
                if pick_over and actual_corners > line: is_hit = True
                if not pick_over and actual_corners < line: is_hit = True
                
                correct_analyst += 1 if is_hit else 0
                total_analyst += 1
                
                # Guarda para o Manager
                daily_candidates.append({
                    'match_id': match_id,
                    'match_name': f"Match {match_id}",
                    'result': result
                })
                
            except Exception as e:
                # print(f"Erro no jogo {match_id}: {e}")
                pass
                
        # B. Manager AI (Final do Dia)
        if daily_candidates:
            ranked = strategy.evaluate_candidates(daily_candidates)
            top_7 = strategy.select_top_n(ranked, 7)
            
            for pick in top_7:
                # Verifica se o Pick (Top 7) bateu
                # Precisamos buscar o resultado real de novo
                actual = test_set[test_set['match_id'] == pick.match_id].iloc[0]['total_corners']
                
                is_hit = False
                if "Over" in pick.selection and actual > pick.line: is_hit = True
                if "Under" in pick.selection and actual < pick.line: is_hit = True
                
                manager_hits += 1 if is_hit else 0
                manager_total += 1
                
    # 4. Relatório Final
    print("\n" + "="*50)
    print("📈 RELATÓRIO DE SAÚDE DO SISTEMA (BACKTEST)")
    print("="*50)
    
    acc_analyst = (correct_analyst / total_analyst * 100) if total_analyst > 0 else 0
    acc_manager = (manager_hits / manager_total * 100) if manager_total > 0 else 0
    
    print(f"🧠 Analyst AI (Todas as previsões):")
    print(f"   Jogos Analisados: {total_analyst}")
    print(f"   Acertos: {correct_analyst}")
    print(f"   Acurácia: {acc_analyst:.2f}%")
    
    print(f"\n👔 Manager AI (Top 7 Picks):")
    print(f"   Picks Selecionadas: {manager_total}")
    print(f"   Acertos: {manager_hits}")
    print(f"   Acurácia: {acc_manager:.2f}%")
    
    print("="*50)
    if acc_manager > 55.0:
        print("✅ O sistema está SAUDÁVEL (Acurácia Global > 55%).")
    else:
        print("⚠️ O sistema precisa de AJUSTES (Acurácia Global < 55%).")
        
    db.close()

if __name__ == "__main__":
    run_backtest()
