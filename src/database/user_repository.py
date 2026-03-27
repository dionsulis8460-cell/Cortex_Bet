"""
UserRepository - Repositório de Usuários e Apostas.

Regra de Negócio:
    Encapsula todo o CRUD de usuários, apostas e gestão de banca,
    extraído do monolítico DBManager para Single Responsibility.
"""

import re
import time
import sqlite3
from typing import Optional, Dict, Any, List
from werkzeug.security import generate_password_hash, check_password_hash


class UserRepository:
    """Repositório especializado em operações de usuários e apostas."""

    def __init__(self, db_manager):
        self._db = db_manager

    # ─── Authentication ─────────────────────────────────────────

    def verify_login(self, username, password):
        """Verifica credenciais de login."""
        conn = self._db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, role, initial_bankroll FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            return {
                "id": user[0],
                "username": user[1],
                "role": user[3],
                "bankroll": user[4]
            }
        return None

    def get_user_by_username(self, username):
        conn = self._db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, initial_bankroll FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "role": row[2], "bankroll": row[3]}
        return None

    def create_user(self, username, password, role='user', initial_bankroll=1000.0):
        """Cria um novo usuário (para seed/admin)."""
        conn = self._db.connect()
        cursor = conn.cursor()
        try:
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, initial_bankroll) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, initial_bankroll)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_user_password(self, username, password):
        conn = self._db.connect()
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
        conn.commit()

    def list_users(self):
        """Retorna lista de todos os usuários."""
        conn = self._db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, initial_bankroll FROM users")
        return cursor.fetchall()

    def delete_user(self, username):
        """Deleta um usuário pelo nome."""
        conn = self._db.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            if cursor.rowcount > 0:
                conn.commit()
                return True
            return False
        except Exception as e:
            return False

    # ─── Social Ranking ──────────────────────────────────────────

    def get_all_users_stats(self):
        """Retorna estatísticas de todos os usuários para o Social Ranking."""
        conn = self._db.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT id, username, initial_bankroll FROM users")
        users = cursor.fetchall()

        stats = []
        for u in users:
            uid, uname, ubank = u

            cursor.execute('''
                SELECT 
                    COUNT(*),
                    SUM(CASE WHEN status='GREEN' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status='GREEN' THEN possible_win - stake ELSE 
                        CASE WHEN status='RED' THEN -stake ELSE 0 END END) as profit,
                    SUM(stake)
                FROM bets
                WHERE user_id = ?
            ''', (uid,))

            bet_stats = cursor.fetchone()
            total_bets = bet_stats[0] or 0
            wins = bet_stats[1] or 0
            profit = bet_stats[2] or 0.0
            total_staked = bet_stats[3] or 0.0

            roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
            win_rate = (wins / total_bets * 100) if total_bets > 0 else 0.0

            stats.append({
                "username": uname,
                "total_bets": total_bets,
                "win_rate": win_rate,
                "profit": profit,
                "roi": roi,
                "bankroll": ubank + profit
            })

        return sorted(stats, key=lambda x: x['profit'], reverse=True)

    def get_user_h2h(self, username1: str, username2: str) -> dict:
        """Compara estatísticas de dois usuários (Head-to-Head)."""
        all_stats = self.get_all_users_stats()
        user1_stats = next((u for u in all_stats if u['username'] == username1), None)
        user2_stats = next((u for u in all_stats if u['username'] == username2), None)
        return {'user1': user1_stats, 'user2': user2_stats}

    # ─── Betting CRUD ────────────────────────────────────────────

    def save_bet(self, user_id, stake, total_odds, possible_win, bet_type, items):
        """Salva uma nova aposta no banco."""
        conn = self._db.connect()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO bets (user_id, timestamp, status, stake, total_odds, possible_win, bet_type)
                VALUES (?, ?, 'PENDING', ?, ?, ?, ?)
            ''', (user_id, int(time.time()), stake, total_odds, possible_win, bet_type))

            bet_id = cursor.lastrowid

            for item in items:
                cursor.execute('''
                    INSERT INTO bet_items (bet_id, match_id, prediction_label, odds, status)
                    VALUES (?, ?, ?, ?, 'PENDING')
                ''', (bet_id, item['match_id'], item['label'], item['odds']))

            conn.commit()
            return True, "Aposta registrada com sucesso!"
        except Exception as e:
            return False, f"Erro ao salvar aposta: {e}"

    def delete_bet(self, bet_id: int) -> bool:
        """Deleta uma aposta e seus itens relacionados."""
        conn = self._db.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM bet_items WHERE bet_id = ?", (bet_id,))
            cursor.execute("DELETE FROM bets WHERE id = ?", (bet_id,))
            conn.commit()
            print(f"✅ Aposta {bet_id} deletada com sucesso.")
            return True
        except Exception as e:
            print(f"❌ Erro ao deletar aposta {bet_id}: {e}")
            return False

    def get_bets_by_user(self, username, limit=10):
        """Retorna as últimas apostas de um usuário específico."""
        user = self.get_user_by_username(username)
        if not user:
            return []

        user_id = user['id']
        conn = self._db.connect()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, timestamp, status, stake, total_odds, possible_win, bet_type
            FROM bets
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))

        bets = []
        for row in cursor.fetchall():
            bets.append({
                'id': row[0],
                'timestamp': row[1],
                'status': row[2],
                'stake': row[3],
                'total_odds': row[4],
                'possible_win': row[5],
                'bet_type': row[6]
            })
        return bets

    def get_bet_items(self, bet_id: int) -> list:
        """Retorna os itens (seleções) de uma aposta específica."""
        conn = self._db.connect()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT bi.prediction_label, bi.odds, bi.status,
                   m.home_team_name, m.away_team_name, m.match_id
            FROM bet_items bi
            LEFT JOIN matches m ON bi.match_id = m.match_id
            WHERE bi.bet_id = ?
        ''', (bet_id,))

        items = []
        for row in cursor.fetchall():
            match_name = f"{row[3] or '?'} vs {row[4] or '?'}"
            items.append({
                'prediction_label': row[0],
                'odds': row[1],
                'status': row[2],
                'match_name': match_name,
                'match_id': row[5]
            })
        return items

    def get_betting_statistics(self, user_id=None) -> Dict[str, Any]:
        """
        Retorna estatísticas completas de apostas para a UI 'Minhas Apostas'.

        Regra de Negócio:
            Centraliza todos os dados necessários para a interface de gestão de banca.
        """
        conn = self._db.connect()
        cursor = conn.cursor()

        stats = {
            'saldo': 0.0,
            'roi': 0.0,
            'taxa_acerto': 0.0,
            'total_apostas': 0,
            'ganhas': 0,
            'perdidas': 0,
            'pendentes': 0,
            'bets': [],
            'weekly_stats': [],
            'market_stats': {}
        }

        try:
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'GREEN' THEN 1 ELSE 0 END) as ganhas,
                    SUM(CASE WHEN status = 'RED' THEN 1 ELSE 0 END) as perdidas,
                    SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pendentes
                FROM bets
                WHERE (? IS NULL OR user_id = ?)
            ''', (user_id, user_id))
            row = cursor.fetchone()
            if row:
                stats['total_apostas'] = row[0] or 0
                stats['ganhas'] = row[1] or 0
                stats['perdidas'] = row[2] or 0
                stats['pendentes'] = row[3] or 0

            total_resolved = stats['ganhas'] + stats['perdidas']
            if total_resolved > 0:
                stats['taxa_acerto'] = (stats['ganhas'] / total_resolved) * 100

            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN status = 'GREEN' THEN possible_win ELSE 0 END) as ganhos,
                    SUM(CASE WHEN status IN ('GREEN', 'RED') THEN stake ELSE 0 END) as investido,
                    SUM(stake) as total_stake
                FROM bets
                WHERE (? IS NULL OR user_id = ?)
            ''', (user_id, user_id))
            row = cursor.fetchone()
            if row:
                ganhos = row[0] or 0
                investido = row[1] or 0
                total_stake = row[2] or 0
                stats['saldo'] = ganhos - investido + total_stake
                if investido > 0:
                    stats['roi'] = ((ganhos - investido) / investido) * 100

            cursor.execute('''
                SELECT 
                    strftime('%W', datetime(timestamp, 'unixepoch')) as week,
                    SUM(CASE WHEN status = 'GREEN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'RED' THEN 1 ELSE 0 END) as losses
                FROM bets
                WHERE (? IS NULL OR user_id = ?) AND status IN ('GREEN', 'RED')
                GROUP BY week
                ORDER BY week ASC
                LIMIT 12
            ''', (user_id, user_id))

            stats['weekly_stats'] = [
                {'week': f"Semana {row[0]}", 'wins': row[1], 'losses': row[2]}
                for row in cursor.fetchall()
            ]

            cursor.execute('''
                SELECT id, timestamp, status, stake, total_odds, possible_win, bet_type
                FROM bets
                WHERE (? IS NULL OR user_id = ?)
                ORDER BY timestamp DESC
                LIMIT 50
            ''', (user_id, user_id))
            bets = cursor.fetchall()

            for bet in bets:
                bet_id = bet[0]
                cursor.execute('''
                    SELECT bi.match_id, bi.prediction_label, bi.odds, bi.status, m.home_team_name, m.away_team_name
                    FROM bet_items bi
                    LEFT JOIN matches m ON bi.match_id = m.match_id
                    WHERE bi.bet_id = ?
                ''', (bet_id,))
                items = cursor.fetchall()

                stats['bets'].append({
                    'id': bet_id,
                    'timestamp': bet[1],
                    'status': bet[2],
                    'stake': bet[3],
                    'total_odds': bet[4],
                    'possible_win': bet[5],
                    'bet_type': bet[6],
                    'items': [
                        {
                            'match_id': item[0],
                            'prediction_label': item[1],
                            'odds': item[2],
                            'status': item[3],
                            'match_name': f"{item[4]} vs {item[5]}" if item[4] and item[5] else "Jogo Desconhecido"
                        }
                        for item in items
                    ]
                })

            cursor.execute('''
                SELECT 
                    market_group,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'GREEN' THEN 1 ELSE 0 END) as wins
                FROM predictions
                WHERE category = 'Top7' AND status IN ('GREEN', 'RED')
                GROUP BY market_group
            ''')
            for row in cursor.fetchall():
                market = row[0] or 'Outro'
                stats['market_stats'][market] = {
                    'total': row[1],
                    'wins': row[2],
                    'rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
                }

        except Exception as e:
            print(f"Erro ao calcular betting stats: {e}")

        return stats

    def reset_all_betting_history(self) -> bool:
        """Remove todo o histórico de apostas e itens, resetando a banca para zero."""
        conn = self._db.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM bet_items")
            cursor.execute("DELETE FROM bets")
            cursor.execute("UPDATE users SET initial_bankroll = 0.0")

            conn.commit()
            print("✨ Histórico de apostas resetado com sucesso (Banca = R$ 0.00).")
            return True
        except Exception as e:
            print(f"❌ Erro ao resetar histórico de apostas: {e}")
            conn.rollback()
            return False

    # ─── Bet Verification ────────────────────────────────────────

    def check_bets_debug(self) -> None:
        """
        Verifica o status das apostas registradas baseado no status dos seus itens.
        Uma aposta é GREEN se todos os itens forem GREEN.
        Uma aposta é RED se algum item for RED.
        """
        print("DEBUG: Entered check_bets function")
        conn = self._db.connect()
        cursor = conn.cursor()

        # 1. Atualiza bet_items baseado nas predictions verificadas
        cursor.execute('''
            UPDATE bet_items
            SET status = (
                SELECT p.status 
                FROM predictions p 
                WHERE p.match_id = bet_items.match_id 
                  AND p.prediction_label = bet_items.prediction_label
                LIMIT 1
            )
            WHERE status = 'PENDING'
              AND EXISTS (
                SELECT 1 FROM predictions p 
                WHERE p.match_id = bet_items.match_id 
                  AND p.prediction_label = bet_items.prediction_label
                  AND p.status IN ('GREEN', 'RED')
              )
        ''')

        # 1.1 Robust Verification Fallback for still-pending items
        cursor.execute('''
            SELECT bi.id, bi.match_id, bi.prediction_label, 
                   s.corners_home_ft, s.corners_away_ft, s.corners_home_ht, s.corners_away_ht
            FROM bet_items bi
            JOIN matches m ON bi.match_id = m.match_id
            JOIN match_stats s ON m.match_id = s.match_id
            WHERE bi.status = 'PENDING' AND m.status = 'finished'
        ''')
        pending_items = cursor.fetchall()
        print(f"DEBUG: check_bets pending_items count = {len(pending_items)}")

        for item in pending_items:
            item_id, m_id, label, h_ft, a_ft, h_ht, a_ht = item
            h_ft, a_ft, h_ht, a_ht = h_ft or 0, a_ft or 0, h_ht or 0, a_ht or 0

            try:
                label_lower = label.lower()

                match_val = re.search(r'(?:over|under|mais|menos)\s*(\d+\.?\d*)', label_lower)

                if match_val:
                    line = float(match_val.group(1))
                else:
                    all_nums = re.findall(r'(\d+\.?\d*)', label)
                    if not all_nums:
                        continue
                    line = float(all_nums[-1])

                is_home = any(k in label_lower for k in ['casa', 'home', 'mandante'])
                is_away = any(k in label_lower for k in ['vis.', 'vis ', 'away', 'visitante'])
                is_1t = any(k in label_lower for k in ['1t', 'ht'])
                is_2t = any(k in label_lower for k in ['2t', '2st', ' st'])

                if is_home:
                    val_to_check = h_ht if is_1t else (h_ft - h_ht if is_2t else h_ft)
                elif is_away:
                    val_to_check = a_ht if is_1t else (a_ft - a_ht if is_2t else a_ft)
                else:
                    val_to_check = (h_ht + a_ht) if is_1t else ((h_ft - h_ht) + (a_ft - a_ht) if is_2t else h_ft + a_ft)

                is_correct = False
                if 'over' in label_lower:
                    is_correct = val_to_check > line
                elif 'under' in label_lower:
                    is_correct = val_to_check < line

                item_status = 'GREEN' if is_correct else 'RED'
                print(f"DEBUG: Label='{label}', Line={line}, Val={val_to_check}, Correct={is_correct}")
                cursor.execute("UPDATE bet_items SET status = ? WHERE id = ?", (item_status, item_id))
            except Exception as e:
                print(f"DEBUG ERROR: {e}")
                continue

        # 2. Atualiza status da aposta principal
        cursor.execute('''
            UPDATE bets
            SET status = 'RED'
            WHERE status = 'PENDING'
              AND id IN (SELECT bet_id FROM bet_items WHERE status = 'RED')
        ''')

        cursor.execute('''
            UPDATE bets
            SET status = 'GREEN'
            WHERE status = 'PENDING'
              AND NOT EXISTS (SELECT 1 FROM bet_items WHERE bet_id = bets.id AND status != 'GREEN')
              AND EXISTS (SELECT 1 FROM bet_items WHERE bet_id = bets.id)
        ''')

        conn.commit()
        print("✅ Verificação de apostas concluída.")

    def check_bets(self):
        """Verifica e atualiza o status das apostas pendentes."""
        conn = self._db.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT id, bet_type FROM bets WHERE status = 'PENDING'")
        pending_bets = cursor.fetchall()

        if not pending_bets:
            return 0

        resolved_count = 0

        for bet_id, bet_type in pending_bets:
            cursor.execute('''
                SELECT bi.id, bi.match_id, bi.prediction_label, bi.status
                FROM bet_items bi
                WHERE bi.bet_id = ?
            ''', (bet_id,))
            items = cursor.fetchall()

            items_statuses = []
            item_updates_needed = False

            for item in items:
                item_id, match_id, label, status = item

                if status in ('GREEN', 'RED', 'VOID'):
                    items_statuses.append(status)
                    continue

                cursor.execute("SELECT status, home_score, away_score FROM matches WHERE match_id = ?", (match_id,))
                match_row = cursor.fetchone()

                if not match_row:
                    items_statuses.append(status)
                    continue

                match_status = match_row[0]

                if match_status in ('postponed', 'canceled', 'adiado', 'cancelado'):
                    new_status = 'VOID'
                    cursor.execute("UPDATE bet_items SET status = ? WHERE id = ?", (new_status, item_id))
                    items_statuses.append(new_status)
                    item_updates_needed = True
                    continue

                if match_status != 'finished':
                    items_statuses.append('PENDING')
                    continue

                cursor.execute("SELECT corners_home_ft, corners_away_ft FROM match_stats WHERE match_id = ?", (match_id,))
                stats_row = cursor.fetchone()

                if not stats_row:
                    items_statuses.append('PENDING')
                    continue

                corners_ft = (stats_row[0] or 0) + (stats_row[1] or 0)

                new_status = 'RED'
                label_lower = label.lower()

                line_match = re.search(r'(\d+\.?\d*)', label)
                line = float(line_match.group(1)) if line_match else 0.0

                if 'over' in label_lower or 'mais' in label_lower:
                    if corners_ft > line:
                        new_status = 'GREEN'
                elif 'under' in label_lower or 'menos' in label_lower:
                    if corners_ft < line:
                        new_status = 'GREEN'

                cursor.execute("UPDATE bet_items SET status = ? WHERE id = ?", (new_status, item_id))
                items_statuses.append(new_status)
                item_updates_needed = True

            if item_updates_needed:
                conn.commit()

            final_status = 'PENDING'

            if 'PENDING' in items_statuses:
                final_status = 'PENDING'
            elif 'RED' in items_statuses:
                final_status = 'RED'
            elif all(s == 'GREEN' or s == 'VOID' for s in items_statuses):
                if all(s == 'VOID' for s in items_statuses):
                    final_status = 'VOID'
                else:
                    final_status = 'GREEN'

            if final_status != 'PENDING':
                cursor.execute("UPDATE bets SET status = ? WHERE id = ?", (final_status, bet_id))
                resolved_count += 1

        conn.commit()
        return resolved_count
