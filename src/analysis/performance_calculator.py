"""
Performance Calculator for AI Predictions

Calculates various performance metrics for the AI model:
- Win Rate (overall and by date)
- RPS (Ranked Probability Score) - Calibration quality
- MAE (Mean Absolute Error) - Prediction accuracy
- ECE (Expected Calibration Error) - Confidence alignment
- Performance by market type
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import sqlite3
import numpy as np


class PerformanceCalculator:
    def __init__(self, db_path: str = 'data/football_data.db'):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def calculate_win_rate_by_date(
        self, 
        from_date: Optional[str] = None, 
        to_date: Optional[str] = None,
        model_version: str = 'CORTEX_V2.1_CALIBRATED'
    ) -> List[Dict[str, Any]]:
        """
        Calculate win rate grouped by date
        
        Returns:
            List of {date, total_bets, wins, losses, pending, win_rate}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build date filter
        date_filter = " AND p.prediction_label != 'Tactical Analysis Data'"
        params = []
        
        if from_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) >= ?"
            params.append(from_date)
        if to_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) <= ?"
            params.append(to_date)
        
        query = f"""
            WITH MatchRanked AS (
                SELECT 
                    p.is_correct,
                    DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) as match_date,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.match_id
                        ORDER BY p.confidence DESC
                    ) as rank
                FROM predictions p
                JOIN matches m ON p.match_id = m.match_id
                WHERE 1=1 {date_filter}
            )
            SELECT 
                match_date,
                COUNT(*) as total_bets,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) as pending
            FROM MatchRanked
            WHERE rank <= 7
            GROUP BY match_date
            ORDER BY match_date ASC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            match_date, total, wins, losses, pending = row
            finished = total - pending
            
            # Skip dates with no finished bets (all pending or no data)
            if finished == 0:
                continue
                
            win_rate = (wins / finished * 100) if finished > 0 else 0
            
            results.append({
                'date': match_date,
                'total_bets': total,
                'wins': wins,
                'losses': losses,
                'pending': pending,
                'win_rate': round(win_rate, 1)
            })
        
        conn.close()
        return results
    
    def calculate_overall_metrics(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        model_version: str = 'CORTEX_V2.1_CALIBRATED'
    ) -> Dict[str, Any]:
        """
        Calculate overall performance metrics
        
        Returns:
            {total_bets, wins, losses, pending, win_rate, rps, mae, ece}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build date filter
        date_filter = " AND p.prediction_label != 'Tactical Analysis Data'"
        params = []
        
        if from_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) >= ?"
            params.append(from_date)
        if to_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) <= ?"
            params.append(to_date)
        
        # Get basic counts
        # CTE to identify Top 7 Predictions Per Match
        top7_cte = f"""
            WITH MatchRanked AS (
                SELECT 
                    p.id,
                    p.is_correct,
                    p.confidence,
                    p.match_id,
                    DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) as match_date,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.match_id 
                        ORDER BY p.confidence DESC
                    ) as rank
                FROM predictions p
                JOIN matches m ON p.match_id = m.match_id
                WHERE 1=1 {date_filter}
            )
        """

        # Get basic counts for Top 7 Per Match
        query = f"""
            {top7_cte}
            SELECT 
                COUNT(*) as total_bets,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN is_correct IS NULL THEN 1 ELSE 0 END) as pending
            FROM MatchRanked
            WHERE rank <= 7
        """
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        total, wins, losses, pending = row
        total = total or 0
        wins = wins or 0
        losses = losses or 0
        pending = pending or 0
        
        finished = total - pending
        win_rate = (wins / finished * 100) if finished > 0 else 0
        
        # Calculate advanced metrics (only for finished predictions)
        rps, mae, ece = self._calculate_advanced_metrics(cursor, date_filter, params)
        
        conn.close()
        
        return {
            'total_bets': total,
            'wins': wins,
            'losses': losses,
            'pending': pending,
            'win_rate': round(win_rate, 1),
            'rps': round(rps, 4) if rps is not None else None,
            'mae': round(mae, 2) if mae is not None else None,
            'ece': round(ece, 4) if ece is not None else None
        }
    
    def _calculate_advanced_metrics(
        self, 
        cursor, 
        date_filter: str, 
        params: List
    ) -> tuple:
        """Calculate RPS, MAE, and ECE"""
        
        # Get finished predictions with confidence and results
        query = f"""
            SELECT 
                p.confidence,
                p.is_correct,
                p.prediction_value as predicted,
                COALESCE(s.corners_home_ft + s.corners_away_ft, 0) as actual
            FROM predictions p
            JOIN matches m ON p.match_id = m.match_id
            LEFT JOIN match_stats s ON m.match_id = s.match_id
            WHERE p.is_correct IS NOT NULL {date_filter}
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        if not rows:
            return None, None, None
        
        confidences = []
        is_corrects = []
        predicted_values = []
        actual_values = []
        
        for row in rows:
            conf, is_correct, pred, actual = row
            confidences.append(conf)
            is_corrects.append(1 if is_correct else 0)
            predicted_values.append(pred)
            actual_values.append(actual)
        
        # RPS (Ranked Probability Score) - Lower is better
        # Simplified: Average squared error between predicted probability and outcome
        rps_scores = [(conf - outcome)**2 for conf, outcome in zip(confidences, is_corrects)]
        rps = np.mean(rps_scores) if rps_scores else None
        
        # MAE (Mean Absolute Error)
        mae_errors = [abs(pred - actual) for pred, actual in zip(predicted_values, actual_values) if pred and actual]
        mae = np.mean(mae_errors) if mae_errors else None
        
        # ECE (Expected Calibration Error)
        # Bin predictions by confidence and compare to actual accuracy
        ece = self._calculate_ece(confidences, is_corrects)
        
        return rps, mae, ece
    
    def _calculate_ece(self, confidences: List[float], outcomes: List[int], num_bins: int = 10) -> float:
        """Calculate Expected Calibration Error"""
        if not confidences:
            return None
        
        bin_edges = np.linspace(0, 1, num_bins + 1)
        bin_indices = np.digitize(confidences, bin_edges) - 1
        
        ece = 0.0
        for i in range(num_bins):
            mask = bin_indices == i
            if np.sum(mask) > 0:
                avg_confidence = np.mean(np.array(confidences)[mask])
                avg_accuracy = np.mean(np.array(outcomes)[mask])
                ece += np.sum(mask) / len(confidences) * abs(avg_confidence - avg_accuracy)
        
        return ece
    
    def get_performance_by_market(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        model_version: str = 'CORTEX_V2.1_CALIBRATED'
    ) -> List[Dict[str, Any]]:
        """
        Get performance breakdown by market type
        
        Returns:
            List of {market, total_bets, win_rate, avg_confidence, roi_potential}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build date filter
        date_filter = " AND p.prediction_label != 'Tactical Analysis Data'"
        params = []
        
        if from_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) >= ?"
            params.append(from_date)
        if to_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) <= ?"
            params.append(to_date)
        
        query = f"""
            SELECT 
                p.prediction_label as market,
                COUNT(*) as total_bets,
                SUM(CASE WHEN p.is_correct = 1 THEN 1 ELSE 0 END) as wins,
                AVG(p.confidence) as avg_confidence,
                AVG(p.fair_odds) as avg_fair_odds
            FROM predictions p
            JOIN matches m ON p.match_id = m.match_id
            WHERE p.is_correct IS NOT NULL {date_filter}
            GROUP BY p.prediction_label
            ORDER BY total_bets DESC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            market, total, wins, avg_conf, avg_odds = row
            win_rate = (wins / total * 100) if total > 0 else 0
            # ROI potential: (avg_odds - 1) * win_rate - (1 - win_rate)
            roi_potential = ((avg_odds - 1) * (wins / total) - (1 - wins / total)) * 100 if total > 0 else 0
            
            results.append({
                'market': market,
                'total_bets': total,
                'win_rate': round(win_rate, 1),
                'avg_confidence': round(avg_conf * 100, 1),
                'roi_potential': round(roi_potential, 1)
            })
        
        conn.close()
        return results
    
    def get_top7_predictions_by_date(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        model_version: str = 'CORTEX_V2.1_CALIBRATED'
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get Top 7 predictions grouped by date
        
        Returns:
            {date: [{match_id, home_team, away_team, prediction, confidence, status, ...}]}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build date filter
        date_filter = " AND p.prediction_label != 'Tactical Analysis Data'"
        params = []
        
        if from_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) >= ?"
            params.append(from_date)
        if to_date:
            date_filter += " AND DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) <= ?"
            params.append(to_date)
        
        query = f"""
            WITH MatchRanked AS (
                SELECT 
                    DATE(datetime(m.start_timestamp, 'unixepoch', '-3 hours')) as match_date,
                    m.match_id,
                    m.home_team_name,
                    m.away_team_name,
                    p.prediction_label,
                    p.prediction_value,
                    p.confidence,
                    p.fair_odds,
                    p.is_correct,
                    p.status,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.match_id
                        ORDER BY p.confidence DESC
                    ) as rank
                FROM predictions p
                JOIN matches m ON p.match_id = m.match_id
                WHERE 1=1 {date_filter}
            )
            SELECT 
                match_date,
                match_id,
                home_team_name,
                away_team_name,
                prediction_label,
                prediction_value,
                confidence,
                fair_odds,
                is_correct,
                status
            FROM MatchRanked
            WHERE rank <= 7
            ORDER BY match_date DESC, confidence DESC
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Group by date
        results_by_date = {}
        for row in rows:
            match_date = row[0]
            if match_date not in results_by_date:
                results_by_date[match_date] = []
            
            # Fix boolean for frontend
            is_correct_val = row[8]
            if is_correct_val is not None:
                is_correct_val = bool(is_correct_val)

            results_by_date[match_date].append({
                'match_id': row[1],
                'home_team': row[2],
                'away_team': row[3],
                'prediction': row[4],
                'predicted_value': row[5],
                'confidence': round(row[6] * 100, 1),
                'fair_odd': round(row[7], 2),
                'is_correct': is_correct_val,
                'status': row[9] or 'PENDING'
            })
        
        conn.close()
        return results_by_date


def get_performance_data(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main entry point - returns all performance data
    """
    calc = PerformanceCalculator()
    
    return {
        'overall_metrics': calc.calculate_overall_metrics(from_date, to_date),
        'global_metrics': calc.calculate_overall_metrics(None, None), # No filter = Global
        'win_rate_by_date': calc.calculate_win_rate_by_date(from_date, to_date),
        'performance_by_market': calc.get_performance_by_market(from_date, to_date),
        'top7_by_date': calc.get_top7_predictions_by_date(from_date, to_date)
    }
