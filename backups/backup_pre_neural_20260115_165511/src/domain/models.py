from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass(frozen=True)
class Team:
    id: int
    name: str
    league: str
    
@dataclass
class MatchStats:
    corners_home: int = 0
    corners_away: int = 0
    goals_home: int = 0
    goals_away: int = 0
    possession_home: float = 0.5
    possession_away: float = 0.5
    # Add other relevant metrics as needed (dangerous attacks, etc.)

@dataclass
class Prediction:
    model_version: str
    predicted_value: float
    confidence: float
    fair_odds: float
    raw_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Match:
    id: int
    home_team: Team
    away_team: Team
    timestamp: datetime
    status: str  # 'scheduled', 'inprogress', 'finished'
    current_score: Dict[str, int] = field(default_factory=lambda: {"home": 0, "away": 0})
    stats: Optional[MatchStats] = None
    predictions: List[Prediction] = field(default_factory=list)

    @property
    def total_corners(self) -> int:
        if self.stats:
            return self.stats.corners_home + self.stats.corners_away
        return 0
