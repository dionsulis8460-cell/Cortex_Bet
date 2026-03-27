"""
Prediction Validator
Validates system predictions against match results.
"""
import sys
import os
from datetime import datetime

# Add project root to path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.database.db_manager import DBManager
from src.analysis.bet_validator import validate_bet_logic

class PredictionValidator:
    def __init__(self):
        self.db = DBManager()
        
    def validate_pending_predictions(self):
        """
        Check all pending predictions for finished matches and validate them.
        """
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Get pending predictions for finished matches
        query = """
            SELECT 
                p.id,
                p.match_id,
                p.prediction_label,
                p.prediction_value,
                p.market_group,
                ms.corners_home_ft,
                ms.corners_away_ft,
                ms.corners_home_ht,
                ms.corners_away_ht,
                m.home_team_name,
                m.away_team_name
            FROM predictions p
            JOIN matches m ON p.match_id = m.match_id
            LEFT JOIN match_stats ms ON m.match_id = ms.match_id
            WHERE p.status = 'PENDING' 
              AND m.status = 'finished'
        """
        
        cursor.execute(query)
        pending = cursor.fetchall()
        
        if not pending:
            return 0
            
        updated_count = 0
        
        for row in pending:
            pred_id = row[0]
            label = row[2]
            # row[3] is value, row[4] is market_group
            
            # Stats
            c_h_ft = row[5]
            c_a_ft = row[6]
            c_h_ht = row[7]
            c_a_ht = row[8]
            
            if c_h_ft is None or c_a_ft is None:
                continue # No stats yet
                
            # Use the existing logic from bet_validator
            # Note: prediction_label usually looks like "Over 10.5" or "Home Over 4.5"
            # We need to extract the line from the label if logic needs it, 
            # OR pass the stored prediction_value as the line?
            # validate_bet_logic takes (label, line, stats...)
            # We should pass prediction_value as line, and label as label.
            
            
            # CRITICAL FIX: Extract line from AFTER "Over" or "Under" keyword
            # Wrong: r'(\d+\.?\d*)' captures "1" from "1T Under 5.5"
            # Correct: Look for number AFTER "Over" or "Under"
            import re
            
            # Try to find number after Over/Under first (most reliable)
            match = re.search(r'(?:over|under)\s*(\d+\.?\d*)', label, re.IGNORECASE)
            if match:
                line = float(match.group(1))
            else:
                # Fallback: any decimal number (but this can be wrong for "1T Under 5.5")
                match = re.search(r'(\d+\.\d+)', label)  # Require decimal point
                if match:
                    line = float(match.group(1))
                else:
                    # Last resort: use stored value
                    line = row[3]
                    if line is None:
                        continue  # Skip if we can't determine line

            is_correct = validate_bet_logic(
                label, line,
                c_h_ft, c_a_ft,
                c_h_ht, c_a_ht
            )
            
            if is_correct is not None:
                status = 'GREEN' if is_correct else 'RED'
                
                cursor.execute("""
                    UPDATE predictions
                    SET is_correct = ?, status = ?
                    WHERE id = ?
                """, (is_correct, status, pred_id))
                
                updated_count += 1
                
        conn.commit()
        return updated_count

if __name__ == "__main__":
    validator = PredictionValidator()
    count = validator.validate_pending_predictions()
    print(f"Validated {count} predictions.")
