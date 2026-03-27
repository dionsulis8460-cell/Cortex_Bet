"""
Testes Unitários dos Repositórios.

Valida a decomposição do DBManager em repositórios especializados
usando banco de dados SQLite in-memory.

Executar: python -m pytest tests/test_repositories.py -v
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.db_manager import DBManager


@pytest.fixture
def db():
    """Cria DBManager in-memory com tabelas e dados de teste."""
    manager = DBManager(db_path=":memory:")

    conn = manager.connect()
    cursor = conn.cursor()

    # Fixtures: jogo de teste
    cursor.execute('''
        INSERT INTO matches (match_id, home_team_id, away_team_id, home_team_name, away_team_name,
                             tournament_name, start_timestamp, status, home_score, away_score, round)
        VALUES (1001, 10, 20, 'Flamengo', 'Palmeiras', 'Brasileirão', ?, 'finished', 2, 1, '10')
    ''', (int(time.time()) - 3600,))

    cursor.execute('''
        INSERT INTO match_stats (match_id, corners_home_ft, corners_away_ft, corners_home_ht, corners_away_ht)
        VALUES (1001, 7, 5, 3, 2)
    ''')

    # Fixture: predição
    cursor.execute('''
        INSERT INTO predictions (match_id, model_version, prediction_value, prediction_label,
                                 confidence, category, market_group, odds, status)
        VALUES (1001, 'TEST_V1', 11.5, 'Over 11.5', 0.75, 'Top7', 'Jogo Completo', 1.85, 'PENDING')
    ''')

    # Fixture: usuário
    cursor.execute('''
        INSERT INTO users (username, password_hash, role, initial_bankroll)
        VALUES ('test_user', 'pbkdf2:sha256:dummy_hash', 'user', 1000.0)
    ''')

    conn.commit()
    yield manager


class TestMatchRepository:
    """Testes do MatchRepository."""

    def test_get_match_teams(self, db):
        home_id, away_id = db.matches.get_match_teams(1001)
        assert home_id == 10
        assert away_id == 20

    def test_get_match_teams_not_found(self, db):
        result = db.matches.get_match_teams(9999)
        assert result == (None, None)

    def test_save_match(self, db):
        match_data = {
            'id': 2001,
            'home_id': 30,
            'away_id': 40,
            'home_name': 'Santos',
            'away_name': 'São Paulo',
            'tournament': 'Brasileirão',
            'tournament_id': 325,
            'season_id': 2025,
            'timestamp': int(time.time()),
            'status': 'scheduled',
            'round': '15',
            'home_score': 0,
            'away_score': 0,
        }
        db.matches.save_match(match_data)

        home_id, away_id = db.matches.get_match_teams(2001)
        assert home_id == 30
        assert away_id == 40


class TestPredictionRepository:
    """Testes do PredictionRepository."""

    def test_save_prediction_new(self, db):
        db.predictions.save_prediction(
            match_id=1001,
            model_version='TEST_V2',
            value=10.5,
            label='Under 10.5',
            confidence=0.80,
            category='Top7',
            market_group='Jogo Completo',
            odds=1.90
        )
        # Verifica que foi salva
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE match_id=1001")
        count = cursor.fetchone()[0]
        assert count == 2  # Original + nova

    def test_save_prediction_update_existing(self, db):
        # Salva com mesma label/category → deve atualizar
        db.predictions.save_prediction(
            match_id=1001,
            model_version='TEST_V1_UPDATED',
            value=12.0,
            label='Over 11.5',
            confidence=0.90,
            category='Top7',
            market_group='Jogo Completo'
        )
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT confidence FROM predictions WHERE match_id=1001 AND prediction_label='Over 11.5'")
        conf = cursor.fetchone()[0]
        assert conf == 0.90

    def test_delete_predictions(self, db):
        db.predictions.delete_predictions(1001)
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE match_id=1001")
        assert cursor.fetchone()[0] == 0

    def test_get_win_rate_stats(self, db):
        stats = db.predictions.get_win_rate_stats()
        assert 'total' in stats
        assert 'pending' in stats
        assert stats['pending'] >= 1  # Temos 1 PENDING

    def test_check_predictions(self, db):
        """Verifica que check_predictions resolve predições de jogos finalizados."""
        db.predictions.check_predictions()

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM predictions WHERE match_id=1001 AND prediction_label='Over 11.5'")
        status = cursor.fetchone()[0]
        # 7+5=12 total corners, Over 11.5 → GREEN
        assert status == 'GREEN'

    def test_get_dashboard_stats(self, db):
        stats = db.predictions.get_dashboard_stats()
        assert 'total_matches' in stats
        assert 'assertivity' in stats
        assert stats['total_matches'] >= 1


class TestUserRepository:
    """Testes do UserRepository."""

    def test_get_user_by_username(self, db):
        user = db.users.get_user_by_username('test_user')
        assert user is not None
        assert user['username'] == 'test_user'
        assert user['bankroll'] == 1000.0

    def test_get_user_not_found(self, db):
        user = db.users.get_user_by_username('nonexistent')
        assert user is None

    def test_create_user(self, db):
        result = db.users.create_user('new_user', 'secret123', 'user', 500.0)
        assert result is True

        user = db.users.get_user_by_username('new_user')
        assert user is not None
        assert user['bankroll'] == 500.0

    def test_create_duplicate_user(self, db):
        result = db.users.create_user('test_user', 'password', 'user')
        assert result is False  # IntegrityError

    def test_list_users(self, db):
        users = db.users.list_users()
        assert len(users) >= 1

    def test_delete_user(self, db):
        db.users.create_user('temp_user', 'pass123')
        result = db.users.delete_user('temp_user')
        assert result is True

        user = db.users.get_user_by_username('temp_user')
        assert user is None

    def test_save_and_get_bets(self, db):
        user = db.users.get_user_by_username('test_user')
        user_id = user['id']

        items = [{'match_id': 1001, 'label': 'Over 11.5', 'odds': 1.85}]
        success, msg = db.users.save_bet(user_id, 10.0, 1.85, 18.50, 'simple', items)
        assert success is True

        bets = db.users.get_bets_by_user('test_user', limit=5)
        assert len(bets) >= 1
        assert bets[0]['stake'] == 10.0

    def test_get_all_users_stats(self, db):
        stats = db.users.get_all_users_stats()
        assert len(stats) >= 1
        assert 'username' in stats[0]
        assert 'profit' in stats[0]

    def test_get_betting_statistics(self, db):
        stats = db.users.get_betting_statistics()
        assert 'total_apostas' in stats
        assert 'saldo' in stats
        assert 'weekly_stats' in stats
