from typing import List, Optional, Dict, Any
import asyncio
from src.domain.models import Match, Team
from src.infrastructure.scrapers.scraper_interface import IScraper
from src.scrapers.sofascore import SofaScoreScraper
from datetime import datetime

class SofaScoreScraperAdapter(IScraper):
    """
    Adapter for the existing SofaScoreScraper to comply with the IScraper interface.
    """
    
    def __init__(self, headless: bool = True):
        self.scraper = SofaScoreScraper(headless=headless)
        
    async def get_live_matches(self) -> List[Match]:
        """
        Fetches live matches and maps them to Domain Match objects.
        Uses asyncio.to_thread to run the synchronous Playwright scraper without blocking the event loop.
        """
        return await asyncio.to_thread(self._get_live_matches_sync)

    def _get_live_matches_sync(self) -> List[Match]:
        """Synchronous implementation of get_live_matches."""
        self.scraper.start()
        try:
            # Date for today (mocking for now, should use real datetime)
            today = datetime.now().strftime('%Y-%m-%d')
            raw_matches = self.scraper.get_scheduled_matches(today)
            
            domain_matches = []
            for m in raw_matches:
                home_team = Team(id=m['home_id'], name=m['home_team'], league=m['tournament'])
                away_team = Team(id=m['away_id'], name=m['away_team'], league=m['tournament'])
                
                match = Match(
                    id=m['match_id'],
                    home_team=home_team,
                    away_team=away_team,
                    timestamp=datetime.fromtimestamp(m['timestamp']),
                    status=m['status'],
                    current_score={"home": m['home_score'], "away": m['away_score']}
                )
                domain_matches.append(match)
            return domain_matches
        finally:
            self.scraper.stop()

    async def get_match_details(self, match_id: int) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_match_details_sync, match_id)

    def _get_match_details_sync(self, match_id: int) -> Optional[Dict[str, Any]]:
        self.scraper.start()
        try:
            details = self.scraper.get_match_details(match_id)
            stats = self.scraper.get_match_stats(match_id)
            if details:
                details['stats'] = stats
            return details
        finally:
            self.scraper.stop()
