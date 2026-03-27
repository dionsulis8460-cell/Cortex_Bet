from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models import Match

class IMatchRepository(ABC):
    """
    Interface for match data persistence following the Repository Pattern.
    """
    
    @abstractmethod
    async def get_match_by_id(self, match_id: int) -> Optional[Match]:
        pass
        
    @abstractmethod
    async def save_match(self, match: Match) -> bool:
        pass
        
    @abstractmethod
    async def get_live_matches(self) -> List[Match]:
        pass
