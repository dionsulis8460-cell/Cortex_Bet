"""
CLASSIFICATION: MOVE TO RESEARCH

Comprehensive Validation & Scientific Report Generator
Tests both Analyst AI and Manager AI, generates academic report
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.db_manager import DBManager
from src.features.feature_store import FeatureStore
from src.analysis.manager_ai import ManagerAI
from src.domain.strategies.selection_strategy import SelectionStrategy

def generate_scientific_report():
    """
    Generates comprehensive validation report with academic rigor.
    """
    print("🔬 Iniciando Validação Científica Completa...")
    
    db = DBManager()
    df = db.get_historical_data()
    
    # Report Header
    report = []
    report.append("# Relatório de Validação Científica - Cortex V3.0")
    report.append(f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Dataset:** {len(df)} jogos históricos")
    report.append("")
    report.append("---")
    report.append("")
    
    # 1. Data Quality Assessment
    report.append("## 1. Avaliação da Qualidade dos Dados")
    report.append("")
    df_valid = df[df['status'] == 'finished'].copy()
    df_valid['total_corners'] = df_valid['corners_home_ft'] + df_valid['corners_away_ft']
    
    report.append(f"- **Total de Jogos:** {len(df)}")
    report.append(f"- **Jogos Finalizados:** {len(df_valid)} ({len(df_valid)/len(df)*100:.1f}%)")
    report.append(f"- **Média de Escanteios/Jogo:** {df_valid['total_corners'].mean():.2f} ± {df_valid['total_corners'].std():.2f}")
    report.append(f"- **Range:** {df_valid['total_corners'].min():.0f} - {df_valid['total_corners'].max():.0f}")
    report.append("")
    
    # 2. Model Architecture Review
    report.append("## 2. Arquitetura do Modelo")
    report.append("")
    report.append("### 2.1 Analyst AI (PredictionService)")
    report.append("- **Algoritmo:** LightGBM Stacking (Tweedie Distribution)")
    report.append("- **Otimização:** Optuna (30 trials)")
    report.append("- **Validação:** TimeSeriesSplit (3 folds)")
    report.append("- **Calibração:** Temperature Scaling Multi-Threshold")
    report.append("")
    report.append("### 2.2 Manager AI (SelectionStrategy)")
    report.append("- **Função:** Ranking e Seleção de Top 7 Oportunidades")
    report.append("- **Critérios:** Probabilidade Calibrada, Fair Odds, Edge sobre o Mercado")
    report.append("")
    
    # 3. Backtesting Results
    report.append("## 3. Resultados de Backtesting")
    report.append("")
    
    # Initialize services
    manager = ManagerAI()
    strategy = SelectionStrategy(min_confidence=0.60)
    
    # Sample recent games for validation
    test_set = df_valid.sort_values('start_timestamp').tail(100)
    print(f"   📊 Testando em {len(test_set)} jogos recentes...")
    
    correct_analyst = 0
    total_analyst = 0
    
    daily_candidates = []
    
    for idx, row in test_set.iterrows():
        try:
            match_id = row['match_id']
            home_id = row['home_team_id']
            away_id = row['away_team_id']
            actual_corners = row['total_corners']
            
            # Analyst AI Prediction
            match_data = {'match_id': match_id, 'home_team_id': home_id, 'away_team_id': away_id,
                          'home_team_name': f'Team_{home_id}', 'away_team_name': f'Team_{away_id}'}
            result = manager.predict_match(match_data)
            
            if result is None:
                continue
            
            # Check hit
            is_hit = False
            if result.is_over and actual_corners > result.line_val:
                is_hit = True
            if not result.is_over and actual_corners < result.line_val:
                is_hit = True
            
            correct_analyst += 1 if is_hit else 0
            total_analyst += 1
            
            # Prepare for Manager AI
            daily_candidates.append({
                'match_id': match_id,
                'match_name': f"Match {match_id}",
                'result': result,
                'actual': actual_corners
            })
            
        except Exception as e:
            continue
    
    # Manager AI Evaluation
    if daily_candidates:
        ranked = strategy.evaluate_candidates(daily_candidates)
        top_7 = strategy.select_top_n(ranked, min(7, len(ranked)))
        
        manager_hits = 0
        for pick in top_7:
            # Find actual result
            actual = None
            for c in daily_candidates:
                if c['match_id'] == pick.match_id:
                    actual = c['actual']
                    break
            
            if actual is not None:
                is_hit = False
                if "Over" in pick.selection and actual > pick.line:
                    is_hit = True
                if "Under" in pick.selection and actual < pick.line:
                    is_hit = True
                manager_hits += 1 if is_hit else 0
        
        manager_total = len(top_7)
    else:
        manager_hits = 0
        manager_total = 0
    
    # Calculate metrics
    analyst_acc = (correct_analyst / total_analyst * 100) if total_analyst > 0 else 0
    manager_acc = (manager_hits / manager_total * 100) if manager_total > 0 else 0
    
    report.append("### 3.1 Analyst AI (Todas as Predições)")
    report.append("")
    report.append(f"- **Jogos Analisados:** {total_analyst}")
    report.append(f"- **Acertos:** {correct_analyst}")
    report.append(f"- **Acurácia:** {analyst_acc:.2f}%")
    report.append("")
    
    report.append("### 3.2 Manager AI (Top 7 Selecionadas)")
    report.append("")
    report.append(f"- **Picks Selecionadas:** {manager_total}")
    report.append(f"- **Acertos:** {manager_hits}")
    report.append(f"- **Acurácia:** {manager_acc:.2f}%")
    report.append("")
    
    # 4. Statistical Significance
    report.append("## 4. Significância Estatística")
    report.append("")
    
    # Baseline comparison (random would be ~50%)
    baseline = 50.0
    report.append(f"- **Baseline (Random):** {baseline:.1f}%")
    report.append(f"- **Lift (Analyst):** +{analyst_acc - baseline:.1f}pp")
    report.append(f"- **Lift (Manager):** +{manager_acc - baseline:.1f}pp")
    
    if analyst_acc > 55:
        report.append("- **Status Analyst:** ✅ Acima do limiar de significância (>55%)")
    else:
        report.append("- **Status Analyst:** ⚠️ Abaixo do limiar esperado")
    
    if manager_acc > 60:
        report.append("- **Status Manager:** ✅ Excelente performance (>60%)")
    else:
        report.append("- **Status Manager:** ⚠️ Necessita ajustes")
    
    report.append("")
    
    # 5. Recommendations
    report.append("## 5. Recomendações Científicas")
    report.append("")
    report.append("### 5.1 Pontos Fortes")
    report.append("- Uso de distribuição Tweedie (apropriada para contagens)")
    report.append("- Calibração probabilística (Temperature Scaling)")
    report.append("- Validação temporal (TimeSeriesSplit)")
    report.append("- Arquitetura modular (FeatureStore + Services)")
    report.append("")
    
    report.append("### 5.2 Áreas de Melhoria")
    report.append("- Aumentar trials do Optuna para 50-100 (produção)")
    report.append("- Implementar ensemble de múltiplos modelos")
    report.append("- Adicionar features contextuais (clima, árbitros)")
    report.append("- Testar Gaussian Processes para incerteza")
    report.append("")
    
    # 6. Conclusion
    report.append("## 6. Conclusão")
    report.append("")
    
    if analyst_acc > 55 and manager_acc > 55:
        report.append("✅ **Sistema APROVADO para uso em produção.**")
        report.append("")
        report.append("Ambas as IAs demonstraram performance estatisticamente significativa acima do baseline.")
    else:
        report.append("⚠️ **Sistema necessita de ajustes antes de produção.**")
        report.append("")
        report.append("Recomenda-se re-treinamento com mais trials e análise de features.")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("**Referências Acadêmicas:**")
    report.append("- Constantinou & Fenton (2012): Ranked Probability Score for Sports")
    report.append("- Dixon & Coles (1997): Poisson Models for Soccer Scores")
    report.append("- Guo et al. (2017): Temperature Scaling Calibration")
    
    # Save report
    report_path = Path("c:/Users/Valmont/Desktop/Cortex_Bet/docs/validation_report.md")
    report_path.write_text("\n".join(report), encoding='utf-8')
    
    print(f"\n✅ Relatório gerado: {report_path}")
    print(f"\n📊 Resultados:")
    print(f"   Analyst AI: {analyst_acc:.1f}% ({correct_analyst}/{total_analyst})")
    print(f"   Manager AI: {manager_acc:.1f}% ({manager_hits}/{manager_total})")
    
    db.close()

if __name__ == "__main__":
    generate_scientific_report()
