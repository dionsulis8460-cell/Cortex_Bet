import sys
import os
import argparse
from datetime import datetime, timedelta

# Extrair root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.database.db_manager import DBManager
from src.scrapers.sofascore import SofaScoreScraper
import json

def load_leagues_config() -> list:
    """Carrega a lista de ligas configuradas do arquivo 'clubes_sofascore.json'."""
    try:
        config_path = os.path.join(project_root, 'data', 'clubes_sofascore.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [l['torneio'] for l in data.get('competicoes', [])]
    except Exception as e:
        print(f"Erro ao carregar config de ligas: {e}")
        return []

def main():
    print("Iniciando busca dos últimos 2 meses (60 dias) para todos os campeonatos no CLI...")
    db = DBManager()
    scraper = SofaScoreScraper(headless=True)
    
    try:
        scraper.start()
        
        leagues = load_leagues_config()
        print(f"Ligas configuradas: {leagues}")
        
        league_ids = []
        for league in leagues:
            t_id = scraper.get_tournament_id(league)
            if t_id:
                league_ids.append(t_id)
        
        print(f"IDs das ligas encontrados: {league_ids}")
        if not league_ids:
            print("Nenhum ID de liga encontrado. Abortando.")
            return

        matches_found = 0
        now = datetime.now()
        
        for i in range(60, -1, -1):
            target_date = now - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')
            print(f"\n--- Buscando jogos para {date_str} ---")
            
            matches = scraper.get_scheduled_matches(date_str, league_ids)
            for m in matches:
                if m['status'] == 'finished':
                    try:
                        match_data = {
                            'id': m['match_id'],
                            'tournament': m['tournament'],
                            'tournament_id': m['tournament_id'],
                            'season_id': m['season_id'],
                            'round': 0,
                            'status': m['status'],
                            'timestamp': m['timestamp'],
                            'home_id': m['home_id'],
                            'home_name': m['home_team'],
                            'away_id': m['away_id'],
                            'away_name': m['away_team'],
                            'home_score': m['home_score'],
                            'away_score': m['away_score']
                        }
                        db.save_match(match_data)
                        
                        print(f" Coletando estatísticas para {m['home_team']} vs {m['away_team']}...")
                        stats = scraper.get_match_stats(m['match_id'])
                        db.save_stats(m['match_id'], stats)
                        matches_found += 1
                    except Exception as e:
                        print(f" Erro ao processar o jogo {m.get('match_id')}: {e}")

        print(f"\n✅ Busca concluída! {matches_found} jogos finalizados coletados nos últimos 2 meses.")
        
    except Exception as e:
        print(f"Erro critico: {e}")
    finally:
        scraper.stop()
        db.close()

if __name__ == "__main__":
    main()
