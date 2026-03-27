"""
PredictionRepository - Repositório de Previsões.

Regra de Negócio:
    Encapsula todo o CRUD de previsões e feedback loop,
    extraído do monolítico DBManager para Single Responsibility.
"""

import re
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List


class PredictionRepository:
    """Repositório especializado em operações de previsões e análise."""

    def __init__(self, db_manager):
        self._db = db_manager

    def save_prediction(self, match_id: int, model_version: str, value: float, label: str,
                        confidence: float, category: str = None, market_group: str = None,
                        odds: float = 0.0, feedback_text: str = None, fair_odds: float = 0.0,
                        raw_model_score: float = None, verbose: bool = False) -> None:
        """
        Salva ou atualiza uma predição gerada pelo modelo.

        Regra de Negócio:
            Evita duplicatas verificando match_id + label + category.
        """
        conn = self._db.connect()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id FROM predictions 
                WHERE match_id = ? AND prediction_label = ? AND category = ?
            ''', (match_id, label, category))

            existing = cursor.fetchone()
            if existing:
                cursor.execute('''
                    UPDATE predictions 
                    SET prediction_value = ?, confidence = ?, odds = ?, model_version = ?, 
                        feedback_text = ?, fair_odds = ?, raw_model_score = ?, status = 'PENDING'
                    WHERE id = ?
                ''', (value, confidence, odds, model_version, feedback_text, fair_odds, raw_model_score, existing[0]))
            else:
                cursor.execute('''
                    INSERT INTO predictions (
                        match_id, model_version, prediction_value, prediction_label, 
                        confidence, category, market_group, odds, feedback_text, fair_odds, raw_model_score, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                ''', (match_id, model_version, value, label, confidence, category, market_group, odds, feedback_text, fair_odds, raw_model_score))

            conn.commit()
            if verbose:
                print(f"✅ Predição salva/atualizada: {label} ({category})")
        except Exception as e:
            print(f"Erro ao salvar predição: {e}")

    def delete_predictions(self, match_id: int) -> None:
        """Remove predições existentes para uma partida."""
        conn = self._db.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM predictions WHERE match_id = ?", (match_id,))
            conn.commit()
        except Exception as e:
            print(f"Erro ao limpar predições antigas: {e}")

    def check_predictions(self) -> None:
        """
        Verifica se predições passadas acertaram (Feedback Loop).

        Regra de Negócio:
            - Total Mandante → usa corners_home_ft
            - Total Visitante → usa corners_away_ft  
            - Jogo Completo / outros → usa soma total
            - 1º Tempo → usa corners_*_ht
            - 2º Tempo → usa corners_*_ft - corners_*_ht
        """
        conn = self._db.connect()
        cursor = conn.cursor()

        query = '''
            SELECT p.id, p.match_id, p.prediction_value, p.prediction_label, p.market_group,
                   s.corners_home_ft, s.corners_away_ft, s.corners_home_ht, s.corners_away_ht
            FROM predictions p
            JOIN matches m ON p.match_id = m.match_id
            LEFT JOIN match_stats s ON m.match_id = s.match_id
            WHERE m.status = 'finished'
              AND s.corners_home_ft IS NOT NULL
              AND p.prediction_label != 'Tactical Analysis Data'
        '''

        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            return

        print(f"Verificando {len(rows)} predições pendentes...")

        for row in rows:
            pred_id, match_id, pred_val, pred_label, market_group, h_corners_ft, a_corners_ft, h_corners_ht, a_corners_ht = row

            h_corners_ft = h_corners_ft or 0
            a_corners_ft = a_corners_ft or 0
            h_corners_ht = h_corners_ht or 0
            a_corners_ht = a_corners_ht or 0

            market_group_lower = (market_group or '').lower()

            if 'mandante' in market_group_lower or 'home' in market_group_lower:
                corners_value = h_corners_ft
            elif 'visitante' in market_group_lower or 'away' in market_group_lower:
                corners_value = a_corners_ft
            elif '1' in market_group_lower or 'ht' in market_group_lower or 'primeiro' in market_group_lower:
                corners_value = h_corners_ht + a_corners_ht
            elif '2' in market_group_lower or 'segundo' in market_group_lower:
                corners_value = (h_corners_ft - h_corners_ht) + (a_corners_ft - a_corners_ht)
            else:
                corners_value = h_corners_ft + a_corners_ft

            is_over = 'over' in pred_label.lower() if pred_label else False
            is_under = 'under' in pred_label.lower() if pred_label else False

            line = None
            if pred_label:
                match = re.search(r'(?:over|under)\s*(\d+\.?\d*)', pred_label.lower())
                if match:
                    line = float(match.group(1))
                else:
                    matches = re.findall(r'(\d+\.?\d*)', pred_label)
                    if matches:
                        line = float(matches[-1])

            is_correct = False
            if line is not None:
                if is_over:
                    is_correct = corners_value > line
                elif is_under:
                    is_correct = corners_value < line

            status = 'GREEN' if is_correct else 'RED'
            cursor.execute("UPDATE predictions SET is_correct = ?, status = ? WHERE id = ?", (is_correct, status, pred_id))

        conn.commit()
        print("Verificacao de predicoes concluida.")

    def get_win_rate_stats(self) -> dict:
        """Calcula estatísticas de Win Rate das predições."""
        conn = self._db.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE is_correct IS NOT NULL OR status IN ('GREEN', 'RED')
        """)
        total = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE is_correct = 1 OR status = 'GREEN'
        """)
        correct = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE (is_correct IS NOT NULL OR status IN ('GREEN', 'RED')) 
            AND (confidence > 0.75 OR confidence > 75)
        """)
        total_top7 = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE (is_correct = 1 OR status = 'GREEN') 
            AND (confidence > 0.75 OR confidence > 75)
        """)
        correct_top7 = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COUNT(*) FROM predictions 
            WHERE status = 'PENDING' OR status IS NULL
        """)
        pending = cursor.fetchone()[0] or 0

        win_rate = correct / total if total > 0 else 0.0
        win_rate_top7 = correct_top7 / total_top7 if total_top7 > 0 else 0.0

        return {
            'total': total,
            'correct': correct,
            'win_rate': win_rate,
            'total_top7': total_top7,
            'correct_top7': correct_top7,
            'win_rate_top7': win_rate_top7,
            'pending': pending
        }

    def clear_finished_predictions(self) -> int:
        """Remove todas as predições com status 'GREEN' ou 'RED'."""
        conn = self._db.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM predictions WHERE status IN ('GREEN', 'RED')")
            count = cursor.rowcount
            conn.commit()
            print(f"🧹 Limpeza concluída: {count} predições removidas.")
            return count
        except Exception as e:
            print(f"❌ Erro ao limpar predições: {e}")
            return 0

    def fix_existing_predictions_values(self) -> int:
        """Corrige previsões antigas salvas com prediction_value=0."""
        conn = self._db.connect()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, prediction_label 
            FROM predictions 
            WHERE (prediction_value IS NULL OR prediction_value = 0) 
              AND prediction_label IS NOT NULL
        ''')

        rows = cursor.fetchall()

        if not rows:
            print("✅ Nenhuma previsão precisa de correção.")
            return 0

        fixed_count = 0
        for pred_id, label in rows:
            match = re.search(r'(\d+\.?\d*)', label or '')
            if match:
                line_value = float(match.group(1))
                cursor.execute("UPDATE predictions SET prediction_value = ? WHERE id = ?", (line_value, pred_id))
                fixed_count += 1

        conn.commit()
        print(f"✅ {fixed_count} previsões corrigidas.")
        return fixed_count

    def get_predictions_by_date(self, date_str: str) -> list:
        """
        Busca jogos e suas predições para uma data específica (YYYY-MM-DD).
        Retorna estrutura agrupada e enriquecida por match_id.
        """
        conn = self._db.connect()
        cursor = conn.cursor()

        brt = timezone(timedelta(hours=-3))
        dt_start = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=brt)
        start_ts = int(dt_start.timestamp())
        dt_end = dt_start.replace(hour=23, minute=59, second=59)
        end_ts = int(dt_end.timestamp())

        query = '''
            SELECT m.match_id, m.home_team_name, m.away_team_name, m.tournament_name,
                   p.prediction_label, p.confidence, p.fair_odds, p.prediction_value,
                   p.feedback_text, m.start_timestamp, m.home_score, m.away_score, 
                   m.round, p.model_version, p.market_group, m.status, p.status,
                   m.match_minute, p.raw_model_score, p.category,
                   m.home_league_position, m.away_league_position
            FROM matches m
            LEFT JOIN predictions p ON m.match_id = p.match_id
            WHERE m.start_timestamp BETWEEN ? AND ?
            ORDER BY m.match_id, p.confidence DESC
        '''

        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()

        matches_dict = {}
        for row in rows:
            match_id = row[0]
            if match_id not in matches_dict:
                matches_dict[match_id] = {
                    "id": match_id,
                    "match_name": f"{row[1]} vs {row[2]}",
                    "tournament": row[3],
                    "timestamp": row[9],
                    "home_score": row[10],
                    "away_score": row[11],
                    "round": row[12],
                    "status": row[15],
                    "match_minute": row[17],
                    "ml_score": None,
                    "predictions": [],
                    "max_confidence": 0,
                    "home_position": row[20],
                    "away_position": row[21]
                }

            if row[4]:  # prediction_label
                pred_data = {
                    "prediction_label": row[4],
                    "confidence": int(row[5] * 100) if row[5] is not None and row[5] <= 1 else int(row[5] or 0),
                    "fair_odds": row[6],
                    "prediction_value": row[7],
                    "feedback_text": row[8] or "Nenhum detalhe disponível.",
                    "model_version": row[13],
                    "market_group": row[14] or "Geral",
                    "status": row[16],
                    "raw_model_score": row[18],
                    "category": row[19]
                }

                if row[13] == 'CORTEX_V2.1_CALIBRATED' and matches_dict[match_id]["ml_score"] is None:
                    matches_dict[match_id]["ml_score"] = row[18] or row[7]

                matches_dict[match_id]["predictions"].append(pred_data)
                matches_dict[match_id]["max_confidence"] = max(matches_dict[match_id]["max_confidence"], pred_data["confidence"])

        # Fallback para ml_score
        for m_id in matches_dict:
            if matches_dict[m_id]["ml_score"] is None and matches_dict[m_id]["predictions"]:
                pref = next((p for p in matches_dict[m_id]["predictions"] if p['model_version'] == 'CORTEX_V2.1_CALIBRATED'), None)
                if pref:
                    matches_dict[m_id]["ml_score"] = pref.get('raw_model_score') or pref['prediction_value']
                else:
                    matches_dict[m_id]["ml_score"] = matches_dict[m_id]["predictions"][0].get('raw_model_score') or matches_dict[m_id]["predictions"][0]['prediction_value']

        results = list(matches_dict.values())
        results.sort(key=lambda x: x["max_confidence"], reverse=True)

        return results

    def get_match_analysis(self, match_id) -> Optional[dict]:
        """Busca dados detalhados de um jogo e suas predições pelo match_id."""
        conn = self._db.connect()
        cursor = conn.cursor()

        query = '''
            SELECT m.match_id, m.home_team_name, m.away_team_name, m.tournament_name,
                   p.prediction_label, p.confidence, p.fair_odds, p.prediction_value,
                   p.feedback_text, m.start_timestamp, m.home_score, m.away_score, 
                   m.round, p.model_version, p.market_group, m.status, p.status,
                   s.corners_home_ft, s.corners_away_ft, s.corners_home_ht, s.corners_away_ht,
                   m.home_team_id, m.away_team_id, m.home_league_position, m.away_league_position,
                   p.category
            FROM matches m
            LEFT JOIN predictions p ON m.match_id = p.match_id
            LEFT JOIN match_stats s ON m.match_id = s.match_id
            WHERE m.match_id = ?
            ORDER BY p.confidence DESC
        '''

        cursor.execute(query, (match_id,))
        rows = cursor.fetchall()

        if not rows:
            return None

        first = rows[0]
        match_data = {
            "id": match_id,
            "match_name": f"{first[1]} vs {first[2]}",
            "home_team": first[1],
            "away_team": first[2],
            "home_team_id": first[21],
            "away_team_id": first[22],
            "home_position": first[23],
            "away_position": first[24],
            "tournament": first[3],
            "timestamp": first[9],
            "home_score": first[10],
            "away_score": first[11],
            "round": first[12],
            "status": first[15],
            "ml_score": None,
            "predictions": [],
            "stats": {
                "corners_home_ft": first[17],
                "corners_away_ft": first[18],
                "corners_home_ht": first[19],
                "corners_away_ht": first[20]
            }
        }

        for row in rows:
            if row[4]:  # prediction_label
                pred_data = {
                    "prediction_label": row[4],
                    "confidence": int(row[5] * 100) if row[5] is not None and row[5] <= 1 else int(row[5] or 0),
                    "fair_odds": row[6],
                    "prediction_value": row[7],
                    "feedback_text": row[8] or "Nenhum detalhe disponível.",
                    "model_version": row[13],
                    "market_group": row[14] or "Geral",
                    "status": row[16] or 'PENDING',
                    "category": row[25]
                }

                if row[13] == 'CORTEX_V2.1_CALIBRATED' and match_data["ml_score"] is None and row[7] is not None:
                    match_data["ml_score"] = row[7]

                match_data["predictions"].append(pred_data)

        if match_data["ml_score"] is None and match_data["predictions"]:
            match_data["ml_score"] = match_data["predictions"][0]["prediction_value"]

        return match_data

    def get_dashboard_stats(self, user_id: int = None) -> dict:
        """
        Retorna estatísticas agregadas para a Dashboard 'Visão Estratégica'.

        Regra de Negócio:
            - Lucro Líquido: Calculado a partir das apostas do usuário
            - Assertividade: % de acertos nas previsões TOP7 (Global)
            - GREENs/REDs/Aguardando: Contagem de previsões TOP7
            - Acurácia ML: Erro absoluto médio (Global)
        """
        conn = self._db.connect()
        cursor = conn.cursor()

        stats = {
            'total_matches': 0,
            'greens_top7': 0,
            'reds_top7': 0,
            'pending_top7': 0,
            'assertivity': 0.0,
            'net_profit': 0.0,
            'ml_accuracy': 0.0,
            'model_version': 'CORTEX_V2.1_CALIBRATED',
            'total_features': 45
        }

        try:
            cursor.execute('SELECT COUNT(*) FROM matches')
            stats['total_matches'] = cursor.fetchone()[0] or 0

            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN status = 'GREEN' THEN 1 ELSE 0 END) as greens,
                    SUM(CASE WHEN status = 'RED' THEN 1 ELSE 0 END) as reds,
                    SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending
                FROM predictions 
                WHERE category = 'Top7'
            ''')
            row = cursor.fetchone()
            if row:
                stats['greens_top7'] = row[0] or 0
                stats['reds_top7'] = row[1] or 0
                stats['pending_top7'] = row[2] or 0

            total_resolved = stats['greens_top7'] + stats['reds_top7']
            if total_resolved > 0:
                stats['assertivity'] = (stats['greens_top7'] / total_resolved) * 100

            query_profit = '''
                SELECT 
                    SUM(CASE WHEN status = 'GREEN' THEN possible_win - stake ELSE 0 END) -
                    SUM(CASE WHEN status = 'RED' THEN stake ELSE 0 END) as net,
                    SUM(CASE WHEN status IN ('GREEN', 'RED') THEN stake ELSE 0 END) as invested
                FROM bets
                WHERE (? IS NULL OR user_id = ?)
            '''
            cursor.execute(query_profit, (user_id, user_id))
            profit_row = cursor.fetchone()
            stats['net_profit'] = profit_row[0] if profit_row and profit_row[0] else 0.0
            stats['total_invested'] = profit_row[1] if profit_row and profit_row[1] else 0.0

            cursor.execute('''
                SELECT AVG(ABS(p.prediction_value - (s.corners_home_ft + s.corners_away_ft))) as mae
                FROM predictions p
                JOIN match_stats s ON p.match_id = s.match_id
                WHERE p.model_version = 'ML_V10' 
                AND p.status IN ('GREEN', 'RED')
            ''')
            mae_row = cursor.fetchone()
            if mae_row and mae_row[0]:
                stats['ml_accuracy'] = round(mae_row[0], 2)

        except Exception as e:
            print(f"Erro ao calcular stats do dashboard: {e}")

        return stats
