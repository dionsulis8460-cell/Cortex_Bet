from abc import ABC, abstractmethod
from typing import Dict, Any

class IMLModel(ABC):
    """
    Interface for Machine Learning models used for match analysis.
    """
    
    @property
    @abstractmethod
    def version(self) -> str:
        pass
        
    @abstractmethod
    def predict(self, match_data: Any) -> Dict[str, Any]:
        """
        Takes match-specific feature data and returns predictions.
        """
        pass
