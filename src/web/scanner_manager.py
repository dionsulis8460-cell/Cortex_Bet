"""
CLASSIFICATION: MOVE TO LEGACY

Módulo de Scanner de Oportunidades para Interface Web.

Regra de Negócio:
    Utiliza a engine unificada (process_match_prediction) para garantir
    paridade com a interface CLI (regra #3 do regras.md).
"""

import sys
import os
from typing import List, Dict, Any, Optional, Callable

from src.database.db_manager import DBManager
from src.models.model_v2 import ProfessionalPredictor
from src.analysis.statistical import StatisticalAnalyzer


class ScannerManager:
    # Ligas Top: Brasil A/B, Premier, LaLiga, Bundesliga, Serie A, Ligue 1, Arg, Portugal
    TOP_LEAGUES = [325, 390, 17, 8, 31, 35, 34, 23, 83]
    
    def __init__(self, db_manager: Optional[DBManager] = None):
        self.db = db_manager or DBManager()
        self.predictor = ProfessionalPredictor()
        self.model_loaded = self.predictor.load_model()
        self.analyzer = StatisticalAnalyzer()

    def scan_day(self, date_str: str, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Escaneia jogos para uma data específica.
        
        Regra de Negócio:
            Utiliza a função unificada scan_opportunities_core para garantir
            paridade com a interface CLI (regra #3 do regras.md).
            
            Usa subprocess para evitar conflito de asyncio do Playwright com Streamlit.
        """
        import subprocess
        import json
        
        try:
            if progress_callback: 
                progress_callback(10, "Buscando agenda (Subprocesso)...")
            
            # Chama o script standalone que usa Playwright de forma isolada
            proxy_path = os.path.join(os.path.dirname(__file__), 'scraper_proxy.py')
            cmd = [sys.executable, proxy_path, date_str]
            
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if process.returncode != 0:
                print(f"Erro no subprocesso: {process.stderr}")
                return []
                
            try:
                matches = json.loads(process.stdout)
                if isinstance(matches, dict) and "error" in matches:
                    print(f"Erro no Scraper: {matches['error']}")
                    return []
            except json.JSONDecodeError:
                print(f"Erro ao decodificar JSON do scraper: {process.stdout}")
                return []

            if not matches:
                return []
                
            if progress_callback: 
                progress_callback(30, f"Encontrados {len(matches)} jogos. Analisando...")
            
            # Importa engine unificada (Lazy import para evitar circularidade se houver)
            from src.analysis.unified_scanner import process_scanned_matches
            
            # Delega processamento para módulo unificado
            process_scanned_matches(
                matches=matches,
                db=self.db,
                predictor=self.predictor,
                progress_callback=progress_callback,
                verbose=True
            )
            
            if progress_callback: 
                progress_callback(100, "Concluído!")
            
            # Retorna dados agrupados via banco
            return self.db.get_predictions_by_date(date_str)
            
        except Exception as e:
            print(f"Erro no scan_day: {e}")
            return []

    def get_dynamic_analysis(self, match_id: int) -> dict:
        """
        Gera análise estatística detalhada em tempo real para um match_id e SALVA no banco.
        Útil para predições antigas que não têm JSON/Feedback rico.
        """
        home_id, away_id = self.db.get_match_teams(match_id)
        if not home_id or not away_id:
            return {}
            
        try:
            # 1. Gera Features e Predição ML
            features_df = prepare_features_for_prediction(home_id, away_id, self.db)
            ml_prediction = float(self.predictor.predict(features_df)[0])
            
            # 2. Busca Histórico
            df_history = self.db.get_historical_data()
            df_home = df_history[(df_history['home_team_id'] == home_id) | (df_history['away_team_id'] == home_id)].copy()
            df_away = df_history[(df_history['home_team_id'] == away_id) | (df_history['away_team_id'] == away_id)].copy()
            
            for d in [df_home, df_away]:
                if not d.empty:
                    d['corners_ft'] = d['corners_home_ft'] + d['corners_away_ft']
                    d['corners_ht'] = d['corners_home_ht'] + d['corners_away_ht']
            
            # 3. Executa Analisador
            top_picks, suggestions, tactical_metrics = self.analyzer.analyze_match(
                df_home=df_home,
                df_away=df_away,
                ml_prediction=ml_prediction,
                advanced_metrics=features_df.iloc[0].to_dict() if not features_df.empty else None
            )
            
            # 4. SALVA as novas predições no banco
            self.db.delete_predictions(match_id) # Limpa para evitar overlaps
            
            # Salva o Score ML principal para o UI (Big Digit)
            confidence = int(top_picks[0]['probability'] * 100) if top_picks else 60
            fair_odds = 1 / (confidence / 100) if confidence > 0 else 2.0
            
            self.db.save_prediction(
                match_id=match_id,
                model_version='CORTEX_V2.1_CALIBRATED',
                value=ml_prediction,
                label='ML Prediction',
                confidence=confidence,
                category='Main',
                market_group='Corners',
                fair_odds=fair_odds,
                feedback_text=f"IA prevê {ml_prediction:.1f} cantos. Médias: Casa: {features_df.iloc[0].get('rolling_corners_home', 0):.1f}, Fora: {features_df.iloc[0].get('rolling_corners_away', 0):.1f}"
            )

            for pick in top_picks[:10]:
                 self.db.save_prediction(
                    match_id=match_id,
                    model_version='CORTEX_V2.1_CALIBRATED',
                    value=pick['line'],
                    label=pick['label'],
                    confidence=pick['probability'],
                    category='Suggestion',
                    market_group=pick['market'],
                    feedback_text=f"Probabilidade estatística de {int(pick['probability']*100)}% para este mercado."
                )

            return {
                "top_picks": top_picks,
                "suggestions": suggestions,
                "ml_prediction": ml_prediction
            }
        except Exception as e:
            print(f"Erro na análise dinâmica: {e}")
            return {}

    def get_stored_results(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Recupera predições já existentes no banco para uma data.
        """
        return self.db.get_predictions_by_date(date_str)
