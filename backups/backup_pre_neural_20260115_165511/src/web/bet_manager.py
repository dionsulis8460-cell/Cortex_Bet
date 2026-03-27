"""
Módulo de Gerenciamento de Apostas e Gestão de Banca.

Este módulo implementa a lógica para:
- Cálculo de odds acumuladas para múltiplas (parlays).
- Sugestão de Stake usando o Critério de Kelly.
- Validação e persistência de apostas no banco de dados.
"""

import math
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.database.db_manager import DBManager

class BetManager:
    """
    Gerencia a lógica de registro e sugestão de apostas.
    """
    
    def __init__(self, db_manager: Optional[DBManager] = None):
        self.db = db_manager or DBManager()

    def calculate_kelly(self, probability: float, odds: float, fraction: float = 0.25, bankroll: float = 1000.0) -> Dict[str, Any]:
        """
        Calcula a sugestão de aposta baseada no Critério de Kelly.
        
        Args:
            probability: Probabilidade estimada (0.0 - 1.0)
            odds: Odd oferecida pela casa
            fraction: Multiplicador de segurança (default 0.25 - "Quarter Kelly")
            bankroll: Valor atual da banca
            
        Returns:
            Dict com a porcentagem e o valor sugerido.
        """
        if odds <= 1.0 or probability <= 0:
            return {"percentage": 0.0, "amount": 0.0, "ev": -100.0}
            
        b = odds - 1
        p = probability
        q = 1 - p
        
        # Fórmula de Kelly: (bp - q) / b
        f = (b * p - q) / b
        
        # Ajuste fracionário e cap de segurança (max 5% da banca)
        suggested_pct = max(0, f * fraction)
        suggested_pct = min(suggested_pct, 0.05) 
        
        amount = bankroll * suggested_pct
        ev = (p * odds - 1) * 100
        
        return {
            "percentage": round(suggested_pct * 100, 2),
            "amount": round(amount, 2),
            "ev": round(ev, 2)
        }

    def calculate_parlay_odds(self, odds_list: List[float]) -> float:
        """
        Calcula a odd total de uma múltipla.
        """
        if not odds_list:
            return 0.0
        
        total_odds = 1.0
        for o in odds_list:
            total_odds *= o
            
        return round(total_odds, 2)

    def save_bet(self, stake: float, bet_type: str, items: List[Dict[str, Any]], user_id: int, custom_total_odds: Optional[float] = None) -> int:
        """
        Salva uma aposta no banco de dados vinculada a um usuário.
        Args:
            stake: Valor apostado
            bet_type: 'SINGLE' ou 'MULTIPLE'
            items: Lista de itens (match_id, prediction_label, odds)
            user_id: ID do usuário
            custom_total_odds: Opcional. Se fornecido, substitui o cálculo automático das odds.
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        try:
            if custom_total_odds:
                total_odds = custom_total_odds
            else:
                total_odds = self.calculate_parlay_odds([item['odds'] for item in items])
                
            possible_win = stake * total_odds
            timestamp = int(datetime.now().timestamp())
            
            # Insere a aposta principal
            cursor.execute('''
                INSERT INTO bets (user_id, timestamp, stake, total_odds, possible_win, bet_type, status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            ''', (user_id, timestamp, stake, total_odds, possible_win, bet_type))
            
            bet_id = cursor.lastrowid
            
            # Insere os itens da aposta
            for item in items:
                cursor.execute('''
                    INSERT INTO bet_items (bet_id, match_id, prediction_label, odds, status)
                    VALUES (?, ?, ?, ?, 'PENDING')
                ''', (bet_id, item['match_id'], item['prediction_label'], item['odds']))
                
            conn.commit()
            return bet_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.db.close()

    def get_bankroll(self, user_id: int) -> float:
        """
        Calcula a banca atual do usuário.
        Initial Bankroll + Lucro/Prejuízo Realizado.
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Pega saldo inicial
        cursor.execute("SELECT initial_bankroll FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        initial = row[0] if row else 1000.0
        
        # Pega lucro/prejuízo
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN status = 'GREEN' THEN possible_win - stake ELSE 
                    CASE WHEN status = 'RED' THEN -stake ELSE 0 END END)
            FROM bets
            WHERE user_id = ?
        ''', (user_id,))
        profit_row = cursor.fetchone()
        profit = profit_row[0] if profit_row and profit_row[0] else 0.0
        
        return initial + profit 
