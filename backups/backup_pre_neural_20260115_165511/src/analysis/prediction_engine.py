import time
import pandas as pd
from typing import Dict, Any, List
import numpy as np
from src.database.db_manager import DBManager
from src.ml.features_v2 import prepare_features_for_prediction
from src.analysis.statistical import StatisticalAnalyzer

def process_match_prediction(
    match_data: Dict[str, Any], 
    predictor: Any, 
    df_history: pd.DataFrame, 
    db: DBManager, 
    home_pos: int = None, 
    away_pos: int = None
) -> Dict[str, Any]:
    """
    Lógica central de previsão e persistência (Atualizado para ML V2).
    Compartilhada entre 'Analisar Jogo' (Web) e 'Scanner' (CLI).
    """
    home_name = match_data['home_name']
    away_name = match_data['away_name']
    home_id = match_data['home_id']
    away_id = match_data['away_id']
    match_id = match_data['id']
    
    # 0. Safety Check: Se o jogo é no futuro, força status 'notstarted'
    # Isso corrige bugs onde a API retorna 'finished' incorretamente
    if match_data.get('timestamp', 0) > time.time() + 300: # 5 min tolerance
        match_data['status'] = 'notstarted'
    
    # 1. Salvar o jogo ANTES de tentar calcular features.
    try:
        db.save_match(match_data)
    except Exception as e:
        return {'error': f'Erro ao salvar dados básicos: {e}'}

    # 2. Preparar Features (V2)
    try:
        # Garante colunas corretas (compatibilidade)
        if 'home_score' in df_history.columns and 'goals_ft_home' not in df_history.columns:
            df_history['goals_ft_home'] = df_history['home_score']
        if 'away_score' in df_history.columns and 'goals_ft_away' not in df_history.columns:
            df_history['goals_ft_away'] = df_history['away_score']

        # Usa o db_manager passado para gerar features
        features_df = prepare_features_for_prediction(
            home_id=home_id,
            away_id=away_id,
            db_manager=db,
            window_long=5
        )
    except Exception as e:
        return {'error': f'Erro ao gerar features V2: {e}'}
    
    if features_df is None or features_df.empty:
        return {'error': f'Histórico insuficiente para {home_name} ou {away_name}'}
    
    # Recupera médias para exibição
    try:
        home_games = df_history[(df_history['home_team_id'] == home_id) | (df_history['away_team_id'] == home_id)].tail(5)
        away_games = df_history[(df_history['home_team_id'] == away_id) | (df_history['away_team_id'] == away_id)].tail(5)
        
        h_corners = []
        for _, g in home_games.iterrows():
            h_corners.append(g['corners_home_ft'] if g['home_team_id'] == home_id else g['corners_away_ft'])
            
        a_corners = []
        for _, g in away_games.iterrows():
            a_corners.append(g['corners_home_ft'] if g['home_team_id'] == away_id else g['corners_away_ft'])
            
        h_avg = sum(h_corners)/len(h_corners) if h_corners else 0
        a_avg = sum(a_corners)/len(a_corners) if a_corners else 0
    except:
        h_avg, a_avg = 0, 0

    # 3. Previsão ML (Professional V2)
    try:
        pred_array = predictor.predict(features_df)
        ml_prediction = float(pred_array[0])
    except Exception as e:
        return {'error': f'Erro na inferência ML V2: {e}'}
        
    # 3.1 Define Best Bet e Linha (Antecipado para uso na calibração)
    if ml_prediction > 10.0:
        best_bet = 'Over 9.5'
        line_val = 9.5
        is_over = True
    else:
        best_bet = 'Under 10.5'
        line_val = 10.5
        is_over = False
    
    # 4. Confiança Calibrada (Probabilística - Sprint 10 Multi-Threshold)
    # Regra de Negócio: Usa MultiThresholdCalibrator para buscar probabilidade exata
    # da linha escolhida (ex: P(Over 9.5) ou P(Under 10.5)).
    
    try:
        from src.ml.calibration import MultiThresholdCalibrator
        from pathlib import Path
        
        import os
        # Robust absolute path
        calibrator_path = Path(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'calibrator_temperature.pkl'))
        
        if calibrator_path.exists():
            # Usa calibrador treinado (Multi-Threshold Temperature Scaling)
            calibrator = MultiThresholdCalibrator() # dummy init
            calibrator.load(str(calibrator_path))
            
            # Obtém P(Over Line)
            p_over = calibrator.predict_proba(ml_prediction, threshold=line_val, use_poisson=True)
            
            if is_over:
                confidence = p_over
            else:
                confidence = 1.0 - p_over
                
            calib_source = f"Multi-Threshold TS (Line {line_val})"
        else:
            # Fallback: Calibração baseada em Poisson (conservadora)
            from scipy.stats import poisson
            
            # P(Over Line) via Poisson
            p_over = 1 - poisson.cdf(line_val, ml_prediction)
            
            if is_over:
                confidence = p_over
            else:
                confidence = 1.0 - p_over
                
            calib_source = "Poisson Fallback (Conservative)"
            
            print("⚠️ Calibrador não encontrado. Usando Poisson como fallback.")
            print("   Execute: python src/scripts/save_production_calibrator.py")
    
    except Exception as e:
        # Fallback seguro: confiança moderada
        print(f"⚠️ Erro ao carregar calibrador: {e}")
        confidence = 0.60
        calib_source = "Error Fallback"
    
    # Clip para evitar 1.0 ou 0.0 extremos
    confidence = float(np.clip(confidence, 0.05, 0.95))

    
    # Fair Odds logic
    fair_odd = 1.0 / confidence if confidence > 0 else 0.0
    
    # Placeholder for Future Scraping
    def compare_with_market_odds(fair_odd: float, market_odd: float) -> float:
        """
        Placeholder para comparação com odds reais (Sprint 12+).
        Retorna o EV (Expected Value) ou None se sem odds.
        """
        if not market_odd: return None
        return (confidence * market_odd) - 1

    # Feedback Text Generation
    # Sprint 10: Ajuste de níveis de confiança para realidade calibrada
    conf_level = "Alta" if confidence >= 0.60 else "Média" if confidence >= 0.50 else "Baixa"
    
    feedback_text = f"🎯 Previsão: {ml_prediction:.1f} escanteios\n"
    feedback_text += f"📊 Confiança Calibrada: {confidence*100:.1f}% ({conf_level})\n"
    feedback_text += f"Scientific Calibration: {calib_source}"
    
    if home_pos and away_pos:
        feedback_text += f"\n🏆 Confronto: {home_name} ({home_pos}º) vs {away_name} ({away_pos}º)"
        
    if h_avg > 0 and a_avg > 0:
        feedback_text += f"\n⚽ Médias: {home_name} (casa): {h_avg:.1f} | {away_name} (fora): {a_avg:.1f}"
    
    feedback_text += f"\n💰 Odd Justa: @{fair_odd:.2f}"

    # 5. Salvar Previsão ML
    db.save_prediction(
        match_id=match_id,
        model_version='CORTEX_V2.1_CALIBRATED',
        value=ml_prediction,
        label=best_bet,
        confidence=confidence,
        odds=1.85,
        category='Professional',
        market_group='Corners',
        feedback_text=feedback_text,
        fair_odds=fair_odd,
        raw_model_score=ml_prediction,  # ← FIX Bug #1: Salva Lambda puro (12.5)
        verbose=False
    )
    
    # 6. Análise Estatística (Top 7 & Sugestões)
    advanced_metrics = {}
    try:
        analyzer = StatisticalAnalyzer()
        
        # Helper para preparar stats do histórico
        def prepare_team_df(games, team_id):
            data = []
            for _, row in games.iterrows():
                is_home = row['home_team_id'] == team_id
                data.append({
                    'corners_ft': row['corners_home_ft'] if is_home else row['corners_away_ft'],
                    'corners_ht': row['corners_home_ht'] if is_home else row['corners_away_ht'],
                    'corners_2t': (row['corners_home_ft'] - row['corners_home_ht']) if is_home else (row['corners_away_ft'] - row['corners_away_ht']),
                    'shots_ht': row['shots_ot_home_ht'] if is_home else row['shots_ot_away_ht']
                })
            return pd.DataFrame(data)

        if not home_games.empty and not away_games.empty:
            df_h_stats = prepare_team_df(home_games, home_id)
            df_a_stats = prepare_team_df(away_games, away_id)

            # Extrai métricas avançadas
            if not features_df.empty:
                try:
                    advanced_metrics['home_avg_corners_general'] = float(features_df['home_avg_corners_general'].iloc[0])
                    advanced_metrics['away_avg_corners_general'] = float(features_df['away_avg_corners_general'].iloc[0])
                    advanced_metrics['home_volatility'] = float(features_df['home_std_corners_general'].iloc[0])
                    advanced_metrics['away_volatility'] = float(features_df['away_std_corners_general'].iloc[0])
                    advanced_metrics['home_attack_adv'] = float(features_df['home_attack_adv'].iloc[0])
                    advanced_metrics['away_attack_adv'] = float(features_df['away_attack_adv'].iloc[0])
                    
                    advanced_metrics['home_avg_corners_home'] = float(features_df['home_avg_corners_home'].iloc[0])
                    advanced_metrics['away_avg_corners_away'] = float(features_df['away_avg_corners_away'].iloc[0])
                    advanced_metrics['home_avg_corners_conceded_home'] = float(features_df['home_avg_corners_conceded_home'].iloc[0])
                    advanced_metrics['away_avg_corners_conceded_away'] = float(features_df['away_avg_corners_conceded_away'].iloc[0])
                    advanced_metrics['home_avg_corners_h2h'] = float(features_df['home_avg_corners_h2h'].iloc[0])
                    advanced_metrics['away_avg_corners_h2h'] = float(features_df['away_avg_corners_h2h'].iloc[0])
                    
                    # Attack Momentum (Revised V3 - Robust)
                    if 'home_avg_momentum_general' in features_df.columns:
                        advanced_metrics['home_momentum'] = float(features_df['home_avg_momentum_general'].iloc[0])
                    else:
                        advanced_metrics['home_momentum'] = 0.0
                        
                    if 'away_avg_momentum_general' in features_df.columns:
                        advanced_metrics['away_momentum'] = float(features_df['away_avg_momentum_general'].iloc[0])
                    else:
                        advanced_metrics['away_momentum'] = 0.0
                        
                    if 'home_momentum_diff_5g' in features_df.columns:
                        advanced_metrics['momentum_diff'] = float(features_df['home_momentum_diff_5g'].iloc[0])
                    else:
                        advanced_metrics['momentum_diff'] = 0.0

                except Exception as e:
                    print(f"Erro metrics: {e}")

            # Extract Odds
            scraped_odds = match_data.get('corner_odds', {})

            # Executa análise estatística (Passing Calibrator from Scope)
            top_picks, suggestions, tactical_metrics = analyzer.analyze_match(
                df_h_stats, df_a_stats, 
                ml_prediction=ml_prediction, 
                match_name=f"{home_name} vs {away_name}",
                advanced_metrics=advanced_metrics,
                scraped_odds=scraped_odds,
                calibrator=calibrator if 'calibrator' in locals() else None
            )
            
            # Persiste Análise Tática para Mirroring na Web
            if tactical_metrics:
                import json
                db.save_prediction(
                    match_id=match_id,
                    model_version='CORTEX_V2.1',
                    value=0.0,
                    label='Tactical Analysis Data',
                    confidence=1.0,
                    category='TacticalAnalysis',
                    feedback_text=json.dumps(tactical_metrics)
                )
            
            # Função extract_line_value REMOVIDA (Substituída por Dados Estruturados)
            
            # Salva Top 7
            for pick in top_picks[:7]:
                # Usa dado estruturado confiável (sem regex)
                line_val = pick.get('raw_line', 0.0) 
                db.save_prediction(match_id, 'Statistical', line_val, pick['Seleção'], pick['Prob'], odds=pick['Odd'], category='Top7', market_group=pick['Mercado'])

            # Salva Sugestões
            for level, pick in suggestions.items():
                if pick:
                    # Usa dado estruturado confiável
                    line_val = pick.get('raw_line', 0.0)
                    db.save_prediction(match_id, 'Statistical', line_val, pick['Seleção'], pick['Prob'], odds=pick['Odd'], category=f"Suggestion_{level}", market_group=pick['Mercado'])
                    
    except Exception as e:
        print(f"Erro na análise estatística: {e}")
    
    return {
        'match_name': f"{home_name} vs {away_name}",
        'ml_prediction': round(ml_prediction, 1),
        'raw_model_score': round(ml_prediction, 1),
        'confidence': round(confidence * 100, 1),
        'calibrated_probability': round(confidence * 100, 1),
        'fair_odd': round(fair_odd, 2), # Explicit field requested
        'calibration_source': calib_source,
        'best_bet': best_bet,
        'home_avg_corners': round(h_avg, 1),
        'away_avg_corners': round(a_avg, 1),
        'match_id': match_id,
        'advanced_metrics': advanced_metrics
    }
