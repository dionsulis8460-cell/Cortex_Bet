import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.manager_ai import ManagerAI, PredictionResult

class TestManagerAI(unittest.TestCase):
    
    @patch('src.analysis.manager_ai.ProfessionalPredictor')
    @patch('src.analysis.manager_ai.NeuralChallenger')
    @patch('src.analysis.manager_ai.FeatureStore')
    def setUp(self, MockFeatureStore, MockNeural, MockPredictor):
        self.mock_db = MagicMock()
        self.manager = ManagerAI(self.mock_db)
        self.manager.feature_store = MockFeatureStore()
        self.manager.ensemble = MockPredictor()
        self.manager.neural = MockNeural()
        
    def test_predict_match_flow(self):
        # Setup Mocks
        match_id = 123
        
        # Mock DB history
        mock_history = pd.DataFrame({
            'match_id': [123],
            'home_team_id': [1],
            'away_team_id': [2],
            'start_timestamp': [100000],
            'tournament_id': [5]
        })
        self.manager.db_manager.get_historical_data.return_value = mock_history
        
        # Mock Feature Store
        mock_features = pd.DataFrame([{'feat1': 1}])
        mock_display = pd.DataFrame([{'disp1': 1}])
        self.manager.feature_store.get_features.return_value = (mock_features, mock_display)
        
        # Mock Ensemble (Return array [10.2])
        self.manager.ensemble.predict.return_value = [10.2]
        
        # Mock Neural (Return tuple 5.0, 5.0 -> 10.0)
        self.manager.neural.predict_lambda.return_value = (5.0, 5.0)
        
        # Act
        result = self.manager.predict_match(match_id)
        
        # Assert
        self.assertIsInstance(result, PredictionResult)
        self.assertEqual(result.match_id, 123)
        self.assertEqual(result.final_prediction, 10.2)
        # line_val is determined dynamically by _find_best_line; we only assert it's a .5 line
        self.assertTrue(str(result.line_val).endswith('.5'), f"Expected a .5 line, got {result.line_val}")
        # Best bet should indicate Over or Under
        self.assertTrue("Over" in result.best_bet or "Under" in result.best_bet)
        
        # Consensus
        # Ensemble 10.2 (Under 10.5)
        # Neural 10.0 (Under 10.5)
        # Both agree -> High confidence
        self.assertGreater(result.consensus_confidence, 0.5)

if __name__ == '__main__':
    unittest.main()
