"""Characterization tests for canonical feature pipeline behavior."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from src.features.feature_store import FeatureStore


REPO_ROOT = Path(__file__).resolve().parents[2]


def _minimal_history_df() -> pd.DataFrame:
    """Return the minimum historical dataframe shape expected by the feature pipeline."""
    return pd.DataFrame(
        [
            {
                "match_id": 1,
                "start_timestamp": 1700000000,
                "home_team_id": 10,
                "away_team_id": 20,
                "corners_home_ft": 5,
                "corners_away_ft": 4,
                "shots_ot_home_ft": 3,
                "shots_ot_away_ft": 2,
                "home_score": 1,
                "away_score": 0,
                "corners_home_ht": 2,
                "corners_away_ht": 1,
                "dangerous_attacks_home": 40,
                "dangerous_attacks_away": 35,
                "blocked_shots_home": 4,
                "blocked_shots_away": 3,
                "crosses_home": 10,
                "crosses_away": 9,
                "tackles_home": 14,
                "tackles_away": 15,
                "interceptions_home": 7,
                "interceptions_away": 8,
                "clearances_home": 20,
                "clearances_away": 19,
                "recoveries_home": 34,
                "recoveries_away": 33,
                "tournament_id": 17,
                "tournament_name": "Premier League",
            }
        ]
    )


def test_get_training_features_delegates_to_create_advanced_features():
    """Training features must be generated via the canonical create_advanced_features path."""
    db = MagicMock()
    store = FeatureStore(db)

    fake_x = pd.DataFrame([{"f1": 1.0}])
    fake_y = pd.Series([9.0])
    fake_timestamps = pd.Series([1700000000])

    with patch("src.features.feature_store.create_advanced_features") as mocked:
        mocked.return_value = (fake_x, fake_y, fake_timestamps, pd.DataFrame())

        x, y, timestamps = store.get_training_features(_minimal_history_df())

    assert x.equals(fake_x)
    assert y.equals(fake_y)
    assert timestamps.equals(fake_timestamps)
    mocked.assert_called_once()


def test_get_inference_features_delegates_to_build_match_features():
    """Inference features must be created by FeatureStore.build_match_features."""
    db = MagicMock()
    db.get_historical_data.return_value = _minimal_history_df()

    store = FeatureStore(db)

    with patch.object(FeatureStore, "build_match_features") as mocked_builder:
        mocked_builder.return_value = pd.DataFrame([{"f1": 1.0}])

        features = store.get_inference_features(match_id=99, home_id=10, away_id=20)

    assert list(features.columns) == ["f1"]
    db.get_historical_data.assert_called_once()
    mocked_builder.assert_called_once_with(10, 20, db.get_historical_data.return_value)


def test_training_entrypoints_use_feature_store_as_canonical_source():
    """Operational training scripts must route feature generation via FeatureStore."""
    trainer_content = (REPO_ROOT / "src" / "training" / "trainer.py").read_text(encoding="utf-8")
    train_script_content = (REPO_ROOT / "scripts" / "train_model.py").read_text(encoding="utf-8")
    neural_train_content = (REPO_ROOT / "src" / "ml" / "train_neural.py").read_text(encoding="utf-8")

    assert "from src.features.feature_store import FeatureStore" in trainer_content
    assert "from src.features.feature_store import FeatureStore" in train_script_content
    assert "from src.features.feature_store import FeatureStore" in neural_train_content
    assert "get_training_features" in trainer_content
    assert "get_training_features" in train_script_content
    assert "get_training_features" in neural_train_content


def test_calibration_entrypoints_use_feature_store_training_path():
    """Calibrator training helpers must reuse the canonical FeatureStore training API."""
    save_calibrator_content = (
        REPO_ROOT / "src" / "scripts" / "save_production_calibrator.py"
    ).read_text(encoding="utf-8")
    calibration_content = (REPO_ROOT / "src" / "ml" / "calibration.py").read_text(encoding="utf-8")

    assert "from src.features.feature_store import FeatureStore" in save_calibrator_content
    assert "FeatureStore(db)" in save_calibrator_content
    assert "get_training_features" in save_calibrator_content

    assert "from src.features.feature_store import FeatureStore" in calibration_content
    assert "feature_store = FeatureStore(db_manager)" in calibration_content
    assert "get_training_features" in calibration_content


def test_model_v2_compatibility_wrapper_delegates_to_feature_store():
    """Legacy model_v2 helper must delegate to canonical FeatureStore API."""
    model_v2_content = (REPO_ROOT / "src" / "models" / "model_v2.py").read_text(encoding="utf-8")

    assert "from src.features.feature_store import FeatureStore" in model_v2_content
    assert "feature_store = FeatureStore(None)" in model_v2_content
    assert "return feature_store.get_training_features(df)" in model_v2_content
