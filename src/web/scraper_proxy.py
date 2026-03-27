import sys
import os
import json
from datetime import datetime

# Add root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.scrapers.sofascore import SofaScoreScraper

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No date provided"}))
        return

    date_str = sys.argv[1]
    
    # Optional: league filter
    leagues = [325, 390, 17, 8, 31, 35, 34, 23, 83]
    
    scraper = SofaScoreScraper(headless=True, verbose=False)
    try:
        scraper.start()
        matches = scraper.get_scheduled_matches(date_str, leagues)
        # Ensure ONLY the JSON is printed to stdout
        sys.stdout.write(json.dumps(matches))
    except Exception as e:
        sys.stderr.write(str(e))
        sys.stdout.write(json.dumps({"error": str(e)}))
    finally:
        scraper.stop()

if __name__ == "__main__":
    main()
