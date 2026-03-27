"""
Testes de Import - Smoke Test.

Verifica que todos os módulos refatorados são importáveis sem erros.
Executar: python -m pytest tests/test_imports.py -v
"""

import sys
import os
import pytest

# Garante o root do projeto no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestCoreImports:
    """Verifica imports dos módulos core."""

    def test_domain_models(self):
        from src.domain.models import PredictionResult, BettingPick, Match, Team, MatchStats, Prediction
        assert PredictionResult is not None
        assert BettingPick is not None

    def test_db_manager(self):
        from src.database.db_manager import DBManager
        assert DBManager is not None

    def test_match_repository(self):
        from src.database.match_repository import MatchRepository
        assert MatchRepository is not None

    def test_prediction_repository(self):
        from src.database.prediction_repository import PredictionRepository
        assert PredictionRepository is not None

    def test_user_repository(self):
        from src.database.user_repository import UserRepository
        assert UserRepository is not None


class TestAnalysisImports:
    """Verifica imports dos módulos de análise."""

    def test_manager_ai(self):
        from src.analysis.manager_ai import ManagerAI
        assert ManagerAI is not None

    def test_unified_scanner(self):
        from src.analysis.unified_scanner import process_scanned_matches, scan_opportunities_core
        assert process_scanned_matches is not None

    def test_selection_strategy(self):
        from src.domain.strategies.selection_strategy import SelectionStrategy
        assert SelectionStrategy is not None


class TestMLImports:
    """Verifica imports dos módulos ML."""

    def test_model_v2(self):
        from src.models.model_v2 import ProfessionalPredictor, TimeAwareStacking
        assert ProfessionalPredictor is not None

    def test_features_v2(self):
        from src.ml.features_v2 import create_advanced_features, prepare_features_for_prediction
        assert create_advanced_features is not None

    def test_calibration(self):
        from src.ml.calibration import CalibratedConfidence, MultiThresholdCalibrator
        assert CalibratedConfidence is not None

    def test_focal_calibration(self):
        from src.ml.focal_calibration import TemperatureScaling, FocalLoss
        assert TemperatureScaling is not None


class TestInfraImports:
    """Verifica imports dos módulos de infraestrutura."""

    def test_feature_store(self):
        from src.features.feature_store import FeatureStore
        assert FeatureStore is not None


class TestFacadePattern:
    """Verifica que DBManager expõe repositórios como facade."""

    def test_dbmanager_has_repositories(self):
        from src.database.db_manager import DBManager
        from src.database.match_repository import MatchRepository
        from src.database.prediction_repository import PredictionRepository
        from src.database.user_repository import UserRepository

        db = DBManager(db_path=":memory:")
        assert isinstance(db.matches, MatchRepository)
        assert isinstance(db.predictions, PredictionRepository)
        assert isinstance(db.users, UserRepository)

    def test_repository_shares_connection(self):
        from src.database.db_manager import DBManager

        db = DBManager(db_path=":memory:")
        conn1 = db.connect()
        conn2 = db.matches._db.connect()
        # Devem usar a mesma instância de DBManager
        assert db.matches._db is db
        assert db.predictions._db is db
        assert db.users._db is db
