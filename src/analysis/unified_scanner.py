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
# [NEW] Manager AI Integration
from src.analysis.manager_ai import ManagerAI, PredictionResult
from src.domain.strategies.selection_strategy import SelectionStrategy

# Top 8 Ligas Monitoradas (IDs SofaScore)
TOP_LEAGUES = [325, 17, 8, 31, 35, 34, 23, 83, 390]  # BR, PL, LAL, BUN, SER, LIG, CL, POR, ChL


def process_scanned_matches(
    matches: List[Dict[str, Any]],
    db: DBManager,
    manager: ManagerAI,
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
    
    # Shadow Mode Initialization removed (handled by Manager AI)
    
    
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
            
            # 5. Processa análise via Manager AI (Unificado)
            # manager.predict_match queries the DB/FeatureStore, so match needed to be saved first.
            result = manager.predict_match(int(match_id), match_metadata=match_data)
            
            # 6. Formata resultado para retorno
            opportunity = {
                'match_id': match_id,
                'match': f"{home_name} vs {away_name}",
                'league': match['tournament'],
                'prediction': result.final_prediction,
                'confidence': result.consensus_confidence,
                'bet': result.best_bet,
                'line_val': result.line_val, 
                'raw_score': result.ensemble_raw,
                'status': match.get('status', 'scheduled'),
                'match_minute': match.get('status_description')
            }
            results.append(opportunity)
            
            # Persist Prediction (Main Line)
            db.save_prediction(
                match_id=int(result.match_id),
                model_version='CORTEX_V3_ENSEMBLE',
                value=result.line_val,
                label=result.best_bet,
                confidence=result.consensus_confidence,
                odds=1.90, # Placeholder
                category='Main',
                market_group='Corners',
                feedback_text=result.feedback_text,
                fair_odds=result.fair_odds,
                verbose=False
            )

            # Persist Alternative Markets (Statistical Tops)
            if hasattr(result, 'alternative_markets') and result.alternative_markets:
                if verbose: print(f"   💾 Saving {len(result.alternative_markets)} alternative markets...")
                for alt in result.alternative_markets:
                    # alt structure from statistical.py:
                    # {'Mercado': 'JOGO COMPLETO', 'Seleção': 'Total Over 9.5', 'Prob': 0.65, ...}
                    try:
                        db.save_prediction(
                            match_id=int(result.match_id),
                            model_version='STATISTICAL_MC',
                            value=alt.get('raw_line', 0.0),
                            label=alt['Seleção'],
                            confidence=alt['Prob'],
                            odds=alt.get('Odd', 0.0),
                            category='Alternative', # Shows in 'Alternative Markets' tab
                            market_group=alt.get('market_type', 'Corners'),
                            feedback_text=f"Monte Carlo Prob: {alt['Prob']:.1%}",
                            fair_odds=alt.get('FairOdd', 0.0),
                            verbose=False
                        )
                    except Exception as ex:
                        if verbose: print(f"     ⚠️ Failed to save alt: {ex}")

            if verbose:
                print(f"   ✅ {result.final_prediction:.1f} esc | {result.consensus_confidence*100:.0f}% conf | 💾 Salvo!")

            # --------------------------------------
                
        except Exception as e:
            if verbose:
                print(f"   ⚠️ Erro: {str(e)[:60]}")
            continue
            
    return results


def scan_opportunities_core(
    date_str: str,
    db: DBManager,
    manager: Optional[ManagerAI] = None, # Renamed and optional (can auto-init)
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
        manager: Instância do ManagerAI (se None, cria uma nova).
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
    own_scraper = False
    if scraper is None:
        own_scraper = True
        scraper = SofaScoreScraper(headless=True, verbose=verbose)
        scraper.start()

    # Ensure Manager AI
    if manager is None:
        if verbose: print("⚙️ Inicializando Manager AI...")
        manager = ManagerAI(db)
    
    try:
        if progress_callback:
            progress_callback(5, "Buscando jogos...")
        
        # 1. Busca jogos via API unificada
        matches = scraper.get_scheduled_matches(date_str, league_ids=leagues)
        
        if not matches:
            if verbose:
                print("❌ Nenhum jogo encontrado nas ligas monitoradas.")
            return []
            
        # Filter out canceled, postponed, or abandoned matches
        valid_matches = []
        invalid_statuses = ['canceled', 'postponed', 'abandoned', 'canc', 'postp', 'aban', 'adiado', 'cancelado']
        for match in matches:
            status_desc = str(match.get('status_description', '')).lower()
            status_type = str(match.get('status', '')).lower()
            
            if any(s in status_desc for s in invalid_statuses) or any(s in status_type for s in invalid_statuses):
                if verbose:
                    print(f"🚫 Ignorando {match.get('home_team')} vs {match.get('away_team')} (Status: {match.get('status_description') or match.get('status')})")
                continue
            valid_matches.append(match)
            
        matches = valid_matches
        
        if not matches:
            if verbose:
                print("❌ Nenhum jogo válido encontrado nas ligas monitoradas (todos cancelados ou adiados).")
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
        results = process_scanned_matches(matches, db, manager, progress_callback, verbose)
        
        # --- PHASE 2: MANAGER AI (TOP 7 SELECTION) ---
        try:
             if results:
                 if verbose: print(f"\n🧠 Manager AI: Selecionando Top 7 de {len(results)} jogos...")
                 
                 strategy = SelectionStrategy(min_confidence=0.60)
                 import pandas as pd # Needed for dummy features
                 
                 # 1. Adapt results to Strategy Format
                 candidates = []
                 for r in results:
                     try:
                         # Ensure we have all needed keys
                         if 'prediction' in r and 'confidence' in r and 'line_val' in r:
                            is_over = 'Over' in r['bet'] or 'Mais' in r['bet']
                            
                            # Reconstruct strongly-typed object (Manager already returned this structure but we converted to dict)
                            # Actually, for Top 7 strategy we can use the dict fields directly if Strategy supports it
                            # But Strategy expects candidates with 'result': PredictionResult
                            
                            res = PredictionResult(
                                match_id=int(r['match_id']),
                                home_team="", # Lazy
                                away_team="",
                                final_prediction=float(r['raw_score']),
                                best_bet=r['bet'],
                                line_val=float(r['line_val']),
                                consensus_confidence=float(r['confidence']),
                                is_over=is_over,
                                ensemble_confidence=0, neural_confidence=0, ensemble_raw=0, neural_raw=0, fair_odds=0, ev_percentage=0 # Dummy
                            )
                            candidates.append({
                                'match_id': r['match_id'], 
                                'match_name': r['match'], 
                                'result': res
                            })
                     except Exception as e:
                         pass

                 # 2. Execute Strategy
                 ranked_picks = strategy.evaluate_candidates(candidates)
                 top_7 = strategy.select_top_n(ranked_picks, 7)
                 
                 if verbose:
                     print(f"   🏆 Top 7 Selecionados ({len(top_7)}):")
                 
                 # 3. Save to DB (Global Top 7)
                 for i, pick in enumerate(top_7, 1):
                     if verbose:
                         print(f"      {i}. {pick.match_name}: {pick.selection} ({pick.probability:.1%})")
                         
                     db.save_prediction(
                         match_id=int(pick.match_id),
                         model_version='CORTEX_MANAGER_V3',
                         value=pick.line,
                         label=pick.selection,
                         confidence=pick.probability,
                         odds=1.90, # Placeholder until scraping is piped through
                         category='Top7', # Critical for UI
                         market_group='Corners',
                         feedback_text=f"Autoselected by Manager AI (Rank #{i})",
                         fair_odds=pick.fair_odd,
                         verbose=False
                     )
                     
        except Exception as e:
            if verbose: print(f"⚠️ Manager AI Error: {e}")
            import traceback
            traceback.print_exc()

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
