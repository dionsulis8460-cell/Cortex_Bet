
import sys
import os
sys.path.append(os.getcwd())
from src.scrapers.sofascore import SofaScoreScraper

def check_leagues():
    ids = [325, 390, 17, 8, 31, 35, 34, 23, 83]
    scraper = SofaScoreScraper(headless=True, verbose=False)
    scraper.start()
    
    print(f"{'ID':<10} {'Tournament Name'}")
    print("-" * 40)
    
    for t_id in ids:
        # We can't easily look up by ID directly via search, but we can try to fetch a season or unique tournament details
        # URL: https://www.sofascore.com/api/v1/unique-tournament/{id}
        url = f"https://www.sofascore.com/api/v1/unique-tournament/{t_id}"
        data = scraper._fetch_api(url)
        if data and 'uniqueTournament' in data:
            name = data['uniqueTournament']['name']
            country = data['uniqueTournament'].get('category', {}).get('name', 'Unknown')
            print(f"{t_id:<10} {name} ({country})")
        else:
            print(f"{t_id:<10} Not Found")
            
    scraper.stop()

if __name__ == "__main__":
    check_leagues()
