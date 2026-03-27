"""
Scanner Trigger Wrapper for Web Dashboard

This script acts as a CLI entry point for the web dashboard to trigger
the unified scanner with a specific date.

Usage:
    python scanner_trigger.py --date YYYY-MM-DD
    python scanner_trigger.py --date today
    python scanner_trigger.py --date tomorrow
"""

import sys
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.unified_scanner import process_scanned_matches
from src.scrapers.sofascore import SofaScoreScraper
from src.database.db_manager import DBManager
from src.models.model_v2 import ProfessionalPredictor


def parse_date(date_str: str) -> str:
    """Parse date string and return YYYY-MM-DD format"""
    if date_str == 'today':
        return datetime.now().strftime('%Y-%m-%d')
    elif date_str == 'tomorrow':
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        # Validate format
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return date_str
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD, 'today', or 'tomorrow'")


def main():
    parser = argparse.ArgumentParser(description='Run scanner for specific date')
    parser.add_argument('--date', required=True, help='Date to scan (YYYY-MM-DD, today, or tomorrow)')
    args = parser.parse_args()

    try:
        # Parse date
        target_date = parse_date(args.date)
        print(f"🔍 Scanning matches for {target_date}...")

        # Initialize components
        db = DBManager()
        scraper = SofaScoreScraper()
        predictor = ProfessionalPredictor()

        # Scrape matches for target date
        print(f"📡 Fetching matches from SofaScore...")
        matches = scraper.get_matches_by_date(target_date)
        
        if not matches:
            print(f"⚠️ No matches found for {target_date}")
            # Return JSON for API consumption
            print(json.dumps({
                'success': True,
                'matches_processed': 0,
                'date': target_date,
                'message': 'No matches found'
            }))
            return

        print(f"✅ Found {len(matches)} matches")

        # Process matches (saves to DB and generates predictions)
        print(f"🤖 Processing predictions...")
        results = process_scanned_matches(
            matches=matches,
            db=db,
            predictor=predictor,
            progress_callback=None,
            verbose=False  # Suppress detailed logs for web
        )

        matches_processed = len(results)
        print(f"✅ Scanner complete! Processed {matches_processed} matches")

        # Output JSON for API consumption
        print(json.dumps({
            'success': True,
            'matches_processed': matches_processed,
            'date': target_date,
            'message': f'Successfully processed {matches_processed} matches'
        }))

    except Exception as e:
        print(f"❌ Scanner error: {str(e)}", file=sys.stderr)
        print(json.dumps({
            'success': False,
            'error': str(e)
        }))
        sys.exit(1)


if __name__ == '__main__':
    main()
