from typing import List, Optional
import sqlite3
import json
from datetime import datetime
from src.domain.models import Match, Team, MatchStats, Prediction
from src.infrastructure.persistence.repository_interface import IMatchRepository
from src.database.db_manager import DBManager

class SQLiteMatchRepository(IMatchRepository):
    """
    SQLite implementation of the IMatchRepository interface.
    Uses the existing DBManager to interact with the database.
    """
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    async def get_match_by_id(self, match_id: int) -> Optional[Match]:
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # 1. Fetch match data
        cursor.execute("SELECT * FROM matches WHERE match_id = ?", (match_id,))
        row = cursor.fetchone()
        if not row:
            return None
            
        # Helper to map row to dict (assuming standard schema)
        columns = [col[0] for col in cursor.description]
        match_dict = dict(zip(columns, row))
        
        # 2. Fetch stats
        cursor.execute("SELECT * FROM match_stats WHERE match_id = ?", (match_id,))
        stats_row = cursor.fetchone()
        stats = None
        if stats_row:
            s_columns = [col[0] for col in cursor.description]
            s_dict = dict(zip(s_columns, stats_row))
            stats = MatchStats(
                corners_home=s_dict.get('corners_home_ft', 0),
                corners_away=s_dict.get('corners_away_ft', 0),
                goals_home=match_dict.get('home_score', 0),
                goals_away=match_dict.get('away_score', 0)
            )

        # 3. Create Domain Object
        home_team = Team(id=match_dict['home_team_id'], name=match_dict['home_team_name'], league=match_dict['tournament_name'])
        away_team = Team(id=match_dict['away_team_id'], name=match_dict['away_team_name'], league=match_dict['tournament_name'])
        
        match = Match(
            id=match_id,
            home_team=home_team,
            away_team=away_team,
            timestamp=datetime.fromtimestamp(match_dict['start_timestamp']),
            status=match_dict['status'],
            current_score={"home": match_dict['home_score'], "away": match_dict['away_score']},
            stats=stats
        )
        
        # 4. Fetch Predictions
        cursor.execute("SELECT * FROM predictions WHERE match_id = ?", (match_id,))
        for pred_row in cursor.fetchall():
            p_cols = [col[0] for col in cursor.description]
            p_dict = dict(zip(p_cols, pred_row))
            match.predictions.append(Prediction(
                model_version=p_dict['model_version'],
                predicted_value=p_dict['prediction_value'],
                confidence=p_dict['confidence'],
                fair_odds=p_dict.get('fair_odds', 0.0),
                raw_score=p_dict.get('raw_model_score')
            ))
            
        return match

    async def save_match(self, match: Match) -> bool:
        """
        Adapts the Domain Match object back to the legacy dict expected by DBManager.
        """
        match_data = {
            'id': match.id,
            'tournament': match.home_team.league,
            'tournament_id': None, # Need refinement
            'season_id': 0, # Need refinement
            'status': match.status,
            'timestamp': int(match.timestamp.timestamp()),
            'home_id': match.home_team.id,
            'home_name': match.home_team.name,
            'away_id': match.away_team.id,
            'away_name': match.away_team.name,
            'home_score': match.current_score["home"],
            'away_score': match.current_score["away"],
            'match_minute': None
        }
        self.db.save_match(match_data)
        
        if match.stats:
            stats_data = {
                'corners_home_ft': match.stats.corners_home,
                'corners_away_ft': match.stats.corners_away
            }
            self.db.save_stats(match.id, stats_data)
            
        for pred in match.predictions:
            self.db.save_prediction(
                match_id=match.id,
                model_version=pred.model_version,
                value=pred.predicted_value,
                label=pred.metadata.get('label', 'N/A'),
                confidence=pred.confidence,
                fair_odds=pred.fair_odds,
                raw_model_score=pred.raw_score
            )
            
        return True

    async def get_live_matches(self) -> List[Match]:
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Fetch matches that are not finished
        cursor.execute("SELECT * FROM matches WHERE status != 'finished' LIMIT 50")
        rows = cursor.fetchall()
        
        matches = []
        columns = [col[0] for col in cursor.description]
        
        for row in rows:
            match_dict = dict(zip(columns, row))
            match_id = match_dict['match_id']
            
            # Create Team objects
            home_team = Team(id=match_dict['home_team_id'], name=match_dict['home_team_name'], league=match_dict['tournament_name'])
            away_team = Team(id=match_dict['away_team_id'], name=match_dict['away_team_name'], league=match_dict['tournament_name'])
            
            # Create Match object
            match = Match(
                id=match_id,
                home_team=home_team,
                away_team=away_team,
                timestamp=datetime.fromtimestamp(match_dict['start_timestamp']),
                status=match_dict['status'],
                current_score={"home": match_dict['home_score'], "away": match_dict['away_score']}
            )
            
            # Fetch stats if available
            cursor.execute("SELECT * FROM match_stats WHERE match_id = ?", (match_id,))
            stats_row = cursor.fetchone()
            if stats_row:
                s_columns = [col[0] for col in cursor.description]
                s_dict = dict(zip(s_columns, stats_row))
                match.stats = MatchStats(
                    corners_home=s_dict.get('corners_home_ft', 0),
                    corners_away=s_dict.get('corners_away_ft', 0),
                    goals_home=match_dict.get('home_score', 0),
                    goals_away=match_dict.get('away_score', 0)
                )
                
            matches.append(match)
            
        return matches
