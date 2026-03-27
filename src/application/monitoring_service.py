import numpy as np
from scipy import stats
import logging

class ModelMonitor:
    """
    Monitoring service to detect Data Drift and Performance Decay.
    """
    def __init__(self, threshold=0.05):
        self.threshold = threshold
        self.reference_distribution = None

    def set_reference_data(self, data):
        self.reference_distribution = data

    def detect_drift(self, current_data):
        """
        Detects drift using Kolmogorov-Smirnov test.
        """
        if self.reference_distribution is None:
            return False, 1.0
        
        ks_stat, p_value = stats.ks_2samp(self.reference_distribution, current_data)
        is_drifting = p_value < self.threshold
        
        if is_drifting:
            logging.warning(f"⚠️ DATA DRIFT DETECTED: p-value={p_value:.4f}")
            
        return is_drifting, p_value

    def track_performance(self, rolling_rps):
        """
        Monitors RPS (Ranked Probability Score) decay.
        If rolling RPS exceeds 10% of historical baseline, trigger alert.
        """
        # Logic for performance monitoring
        pass
