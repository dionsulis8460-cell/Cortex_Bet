from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.domain.models import Match

class IScraper(ABC):
    """
    Interface for external data sources (SofaScore, etc.).
    """
    
    @abstractmethod
    async def get_live_matches(self) -> List[Match]:
        pass
        
    @abstractmethod
    async def get_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        pass
