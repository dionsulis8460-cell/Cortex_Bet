"""
Módulo Unificado de Scanner de Oportunidades.

Regra de Negócio:
    Este módulo centraliza a lógica de scanning de jogos para garantir
    paridade entre CLI e Web (regra #3 do regras.md).
    
    Ambos main.py (CLI) e scanner_manager.py (Web) devem chamar
    scan_opportunities_core() para processar jogos.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Callable, Optional
import traceback

from src.scrapers.sofascore import SofaScoreScraper
from src.database.db_manager import DBManager
from src.models.model_v2 import ProfessionalPredictor
from src.analysis.prediction_engine import process_match_prediction
from src.models.neural_engine import NeuralChallenger # Shadow Mode

# Top 8 Ligas Monitoradas (IDs SofaScore)
TOP_LEAGUES = [325, 17, 8, 31, 35, 34, 23, 83, 390]  # BR, PL, LAL, BUN, SER, LIG, CL, POR, ChL


def process_scanned_matches(
    matches: List[Dict[str, Any]],
    db: DBManager,
    predictor: ProfessionalPredictor,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Processa uma lista de jogos brutos (API/Scraper), salva no banco e gera previsões.
    Extraído para permitir reuso pelo ScannerManager (Web).
    """
    results = []
    
    # Carrega histórico uma vez
    df_history = db.get_historical_data()
    if df_history.empty:
        if verbose:
            print("⚠️ Sem histórico no banco. Rode a atualização de temporadas primeiro.")
        return []
    
    total = len(matches)
    
    # Shadow Mode Initialization
    neural_engine = NeuralChallenger()
    
    
    for i, match in enumerate(matches):
        match_id = str(match['match_id'])
        home_name = match['home_team']
        away_name = match['away_team']
        
        if verbose:
            print(f"\n🔄 [{match_id}] {home_name} vs {away_name}")
        
        if progress_callback:
            # Scale progress 0-100 relative to this batch
            progress_callback(10 + int((i / total) * 80), f"Analisando {i+1}/{total}...")
        
        # Limpa predições antigas
        db.delete_predictions(match_id)
        
        try:
            # 3. Constrói match_data PADRONIZADO
            match_data = {
                'id': match_id,
                'tournament': match['tournament'],
                'tournament_id': match.get('tournament_id', 0),
                'season_id': match.get('season_id', 0),
                'round': match.get('round', 0),
                'status': match.get('status', 'scheduled'),
                'timestamp': match['timestamp'],
                'home_id': match['home_id'],
                'home_name': home_name,
                'away_id': match['away_id'],
                'away_name': away_name,
                'home_score': match.get('home_score', 0) or 0,
                'away_score': match.get('away_score', 0) or 0,
                'match_minute': match.get('status_description'),
                'home_position': match.get('home_position'),
                'away_position': match.get('away_position')
            }
            
            # 4. Salva partida no banco
            db.save_match(match_data)
            
            # --- CYBORG UPGRADE: INJECT NEURAL PARAMETERS ---
            # Antes da análise estatística, consultamos a IA para obter a "Vibe" do jogo
            try:
                neural_dist = neural_engine.get_neural_distributions(match_data, df_history)
                # Injeta no match_data para ser usado pelo process_match_prediction
                # O prediction_engine deve repassar isso para o StatisticalAnalyzer
                match_data['neural_params'] = neural_dist
                if verbose:
                    print(f"   🧠 Neural Params Injected: {neural_dist}")
            except Exception as e:
                print(f"   ⚠️ Neural Params Error: {e}")

            # 5. Processa análise via engine unificada
            result = process_match_prediction(match_data, predictor, df_history, db, neural_engine=neural_engine)
            
            if 'error' in result:
                if verbose:
                    print(f"   ⚠️ Erro na análise: {result['error']}")
                continue
            
            # 6. Formata resultado para retorno
            opportunity = {
                'match_id': match_id,
                'match': f"{home_name} vs {away_name}",
                'league': match['tournament'],
                'prediction': result['ml_prediction'],
                'confidence': result['confidence'] / 100.0,  # Normaliza para 0-1
                'bet': result['best_bet'],
                'status': match.get('status', 'scheduled'),
                'match_minute': match.get('status_description')
            }
            results.append(opportunity)
            
            if verbose:
                print(f"   ✅ {result['ml_prediction']:.1f} esc | {result['confidence']:.0f}% conf | 💾 Salvo!")

            # --- SHADOW MODE: NEURAL CHALLENGER ---
            try:
                # 1. Fetch the just-saved Statistical predictions to challenge
                conn_shadow = db.connect()
                cursor_shadow = conn_shadow.cursor()
                cursor_shadow.execute('''
                    SELECT prediction_label, prediction_value, confidence, market_group, category, odds 
                    FROM predictions 
                    WHERE match_id = ? AND model_version = 'Statistical'
                ''', (match_id,))
                
                math_picks = []
                rows = cursor_shadow.fetchall()
                if verbose:
                     print(f"   [DEBUG_SHADOW] Found {len(rows)} statistical predictions for match {match_id}")

                for row in rows:
                    if row[4] == 'Top7' or (row[4] and 'Suggestion' in row[4]): 
                        math_picks.append({
                            'Seleção': row[0],
                            'raw_line': row[1],
                            'Prob': row[2],
                            'Mercado': row[3],
                            'bet_side': 'Over' if 'Over' in row[0] or 'Mais' in row[0] else 'Under',
                            'Odd': row[5]
                        })
                
                # 2. Generate Shadow Predictions
                # Uses df_history for Volatility Analysis (Pre-Match rigor)
                shadow_preds = neural_engine.predict_match(match_data, math_picks, df_history)
                
                # 3. Save Shadow Predictions
                for pred in shadow_preds:
                    db.save_prediction(
                        match_id=pred['match_id'],
                        model_version='Neural_Challenger', 
                        value=pred['prediction_value'],
                        label=pred['prediction_label'],
                        confidence=pred['confidence'],
                        category=pred['category'],
                        market_group=pred['market_group'],
                        odds=pred['odds'],
                        feedback_text=pred['feedback_text'],
                        fair_odds=pred['fair_odds'],
                        verbose=False
                    )
                if verbose and shadow_preds:
                    print(f"   👻 Shadow Mode: Generated {len(shadow_preds)} neural variations.")
                    
            except Exception as e:
                if verbose:
                    print(f"   ⚠️ Shadow Mode Error: {e}")
            # --------------------------------------
                
        except Exception as e:
            if verbose:
                print(f"   ⚠️ Erro: {str(e)[:60]}")
            continue
            
    return results


def scan_opportunities_core(
    date_str: str,
    db: DBManager,
    predictor: ProfessionalPredictor,
    scraper: Optional[SofaScoreScraper] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    league_ids: List[int] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Função central de scanning de oportunidades.
    
    Args:
        date_str: Data no formato YYYY-MM-DD.
        db: Instância do DBManager para persistência.
        predictor: Instância do ProfessionalPredictor com modelo carregado.
        scraper: Instância opcional do SofaScoreScraper (será criada se None).
        progress_callback: Função opcional para reportar progresso (percent, message).
        league_ids: Lista opcional de IDs de ligas a filtrar (default: TOP_LEAGUES).
        verbose: Se True, imprime logs no console.
        
    Returns:
        Lista de dicionários com resultados das análises.
    """
    leagues = league_ids or TOP_LEAGUES
    results = []
    
    # Gerencia scraper próprio se não fornecido
    own_scraper = scraper is None
    if own_scraper:
        scraper = SofaScoreScraper(headless=True, verbose=verbose)
        scraper.start()
    
    try:
        if progress_callback:
            progress_callback(5, "Buscando jogos...")
        
        # 1. Busca jogos via API unificada
        matches = scraper.get_scheduled_matches(date_str, league_ids=leagues)
        
        if not matches:
            if verbose:
                print("❌ Nenhum jogo encontrado nas ligas monitoradas.")
            return []
        
        if verbose:
            print(f"📊 Encontrados {len(matches)} jogos nas Top Ligas.")
        
        # 1.5 Enrich matches with standings (team positions)
        if progress_callback:
            progress_callback(8, "Buscando classificação...")
        
        # Group matches by tournament to minimize API calls
        tournaments = {}
        for match in matches:
            t_id = match.get('tournament_id')
            s_id = match.get('season_id')
            if t_id and s_id:
                key = f"{t_id}_{s_id}"
                if key not in tournaments:
                    tournaments[key] = {'tournament_id': t_id, 'season_id': s_id, 'matches': []}
                tournaments[key]['matches'].append(match)
        
        # Fetch standings for each tournament
        for key, data in tournaments.items():
            try:
                standings = scraper.get_standings(data['tournament_id'], data['season_id'])
                if standings:
                    for match in data['matches']:
                        h_info = standings.get(match.get('home_id'))
                        a_info = standings.get(match.get('away_id'))
                        
                        if h_info:
                            match['home_position'] = h_info['position']
                        if a_info:
                            match['away_position'] = a_info['position']
                            
                    if verbose:
                        print(f"   ✅ Classificação obtida para {data['tournament_id']}")
            except Exception as e:
                if verbose:
                    print(f"   ⚠️ Erro ao buscar classificação {data['tournament_id']}: {e}")
                continue
        
        # 2. Processa jogos usando a nova função extraída
        results = process_scanned_matches(matches, db, predictor, progress_callback, verbose)
        
        if progress_callback:
            progress_callback(100, "Concluído!")
            
    except Exception as e:
        if verbose:
            print(f"❌ Erro no scanner: {e}")
            traceback.print_exc()
    finally:
        if own_scraper and scraper:
            scraper.stop()
    
    return results
