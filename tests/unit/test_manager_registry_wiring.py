"""Runtime behavior tests for ManagerAI champion/challenger wiring."""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from src.analysis.manager_ai import ManagerAI


def _minimal_history(match_id: int = 1) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "match_id": match_id,
                "home_team_id": 10,
                "away_team_id": 20,
                "start_timestamp": 1700000000,
                "tournament_id": 99,
            }
        ]
    )


def _wire_common_mocks(manager: ManagerAI, match_id: int = 1) -> None:
    manager.db_manager.get_historical_data.return_value = _minimal_history(match_id)

    manager.feature_store = MagicMock()
    manager.feature_store.get_inference_features.return_value = pd.DataFrame([{"f1": 1.0}])

    manager.ensemble = MagicMock()
    manager.ensemble.predict.return_value = np.array([9.0])

    manager.neural = MagicMock()
    manager.neural.predict_lambda.return_value = (6.0, 5.0)  # total = 11.0
    manager.neural.get_neural_distributions.return_value = {}

    manager.statistical = MagicMock()
    manager.statistical.calculate_covariance.return_value = 0.0
    manager.statistical.analyze_match.return_value = ([], {}, {})

    manager._get_confidence = MagicMock(return_value=0.70)
    manager._find_best_line = MagicMock(return_value=(10.5, "Over", True, 0.72))


def test_registry_champion_neural_drives_line_selection():
    db = MagicMock()
    manager = ManagerAI(db)
    _wire_common_mocks(manager)

    manager.runtime_champion_id = "neural_challenger_v1"
    manager.runtime_challenger_id = "ensemble_v1"

    manager.predict_match(1)

    manager._find_best_line.assert_called_once_with(
        projected_mu=11.0,
        neural_mu=9.0,
    )


def test_registry_champion_ensemble_drives_line_selection():
    db = MagicMock()
    manager = ManagerAI(db)
    _wire_common_mocks(manager)

    manager.runtime_champion_id = "ensemble_v1"
    manager.runtime_challenger_id = "neural_challenger_v1"

    manager.predict_match(1)

    manager._find_best_line.assert_called_once_with(
        projected_mu=9.0,
        neural_mu=11.0,
    )
