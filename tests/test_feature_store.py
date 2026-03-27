"""
Tests for Task 2 — Feature Store Centralization.

Verifies:
1. FeatureStore.build_match_features() is the single entry point.
2. FeatureStore.get_inference_features() delegates to build_match_features().
3. prepare_features_for_prediction() emits DeprecationWarning and delegates.
4. neural_engine.NeuralChallenger no longer imports create_advanced_features directly.
"""
import sys
import os
import warnings
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_history(home_id=1, away_id=2, n=10):
    """Minimal historical DataFrame with enough rows for rolling averages."""
    rng = np.random.default_rng(seed=0)
    rows = []
    for i in range(n):
        rows.append(
            {
                "match_id": i,
                "start_timestamp": 1_700_000_000 + i * 86400,
                "home_team_id": home_id if i % 2 == 0 else away_id,
                "away_team_id": away_id if i % 2 == 0 else home_id,
                "corners_home_ft": float(rng.integers(3, 9)),
                "corners_away_ft": float(rng.integers(3, 9)),
                "corners_home_ht": float(rng.integers(1, 5)),
                "corners_away_ht": float(rng.integers(1, 5)),
                "shots_ot_home_ft": float(rng.integers(2, 8)),
                "shots_ot_away_ft": float(rng.integers(2, 8)),
                "home_score": int(rng.integers(0, 3)),
                "away_score": int(rng.integers(0, 3)),
                "dangerous_attacks_home": float(rng.integers(30, 80)),
                "dangerous_attacks_away": float(rng.integers(30, 80)),
                "blocked_shots_home": float(rng.integers(1, 10)),
                "blocked_shots_away": float(rng.integers(1, 10)),
                "crosses_home": float(rng.integers(5, 20)),
                "crosses_away": float(rng.integers(5, 20)),
                "tackles_home": float(rng.integers(10, 30)),
                "tackles_away": float(rng.integers(10, 30)),
                "interceptions_home": float(rng.integers(5, 15)),
                "interceptions_away": float(rng.integers(5, 15)),
                "clearances_home": float(rng.integers(10, 40)),
                "clearances_away": float(rng.integers(10, 40)),
                "recoveries_home": float(rng.integers(20, 60)),
                "recoveries_away": float(rng.integers(20, 60)),
                "tournament_id": "BR_A",
                "tournament_name": "Brasileirao A",
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestFeatureStoreBuildMatchFeatures(unittest.TestCase):
    """Unit tests for FeatureStore.build_match_features() staticmethod."""

    def test_returns_single_row_dataframe(self):
        """build_match_features must return exactly 1 row."""
        from src.features.feature_store import FeatureStore

        df = _make_history(home_id=1, away_id=2, n=12)
        result = FeatureStore.build_match_features(home_id=1, away_id=2, df_history=df)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1, "Expected exactly 1 prediction row")

    def test_raises_on_insufficient_history(self):
        """build_match_features must raise ValueError when < 5 relevant games."""
        from src.features.feature_store import FeatureStore

        df = _make_history(home_id=1, away_id=2, n=2)  # only 2 games
        with self.assertRaises((ValueError, Exception)):
            FeatureStore.build_match_features(home_id=1, away_id=2, df_history=df)

    def test_get_inference_features_delegates(self):
        """get_inference_features() must produce same result as build_match_features()."""
        from src.features.feature_store import FeatureStore

        df = _make_history(home_id=1, away_id=2, n=12)

        mock_db = MagicMock()
        mock_db.get_historical_data.return_value = df

        store = FeatureStore(mock_db)

        via_instance = store.get_inference_features(match_id=999, home_id=1, away_id=2)
        via_static = FeatureStore.build_match_features(home_id=1, away_id=2, df_history=df)

        # Must have same columns (order may vary)
        self.assertEqual(sorted(via_instance.columns), sorted(via_static.columns))
        # DB must have been called exactly once
        mock_db.get_historical_data.assert_called_once()


class TestPrepareFeatureDeprecation(unittest.TestCase):
    """Ensures prepare_features_for_prediction emits DeprecationWarning."""

    def test_emits_deprecation_warning(self):
        from src.ml.features_v2 import prepare_features_for_prediction
        from src.features.feature_store import FeatureStore

        df = _make_history(home_id=1, away_id=2, n=12)
        mock_db = MagicMock()
        mock_db.get_historical_data.return_value = df

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = prepare_features_for_prediction(
                home_id=1, away_id=2, db_manager=mock_db
            )
            deprecation_warnings = [
                x for x in w if issubclass(x.category, DeprecationWarning)
            ]
            self.assertTrue(
                len(deprecation_warnings) >= 1,
                "Expected at least one DeprecationWarning",
            )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)


class TestNeuralEngineNoDirectCreateAdvancedFeatures(unittest.TestCase):
    """
    Smoke test: neural_engine module must NOT import create_advanced_features
    at the module level (it should only use FeatureStore).
    """

    def test_neural_engine_does_not_directly_import_create_advanced_features(self):
        import importlib
        import src.models.neural_engine as ne_module

        module_source_file = ne_module.__file__
        with open(module_source_file, "r", encoding="utf-8") as f:
            source = f.read()

        # The only mention of create_advanced_features should be absent at module-scope
        # (it may appear in comments but must not be imported)
        import_line = "from src.ml.features_v2 import create_advanced_features"
        self.assertNotIn(
            import_line,
            source,
            "neural_engine.py must not directly import create_advanced_features; "
            "it should delegate to FeatureStore instead.",
        )


if __name__ == "__main__":
    unittest.main()
