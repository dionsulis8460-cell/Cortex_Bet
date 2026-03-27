
import argparse
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db_manager import DBManager
from src.scrapers.sofascore import SofaScoreScraper

def update_results(target_date=None, force_all_pending=False):
    db = DBManager()
    scraper = SofaScoreScraper(headless=True, verbose=True)
    
    print(f"\nStarting Results Updater")
    print(f"Target Date: {target_date if target_date else 'ALL PENDING or RECENT'}")
    
    # 1. Identify Matches to Update
    conn = db.connect()
    cursor = conn.cursor()
    
    matches_to_update = []
    
    if target_date:
        # User specified a date (YYYY-MM-DD)
        # Convert to unix timestamp range for query
        # Since DB stores start_timestamp, we need to be careful with timezones.
        # DB usually stores UTC timestamp.
        # Simple approach: Get all matches, filter by YYYY-MM-DD string conversion in SQL
        query = """
            SELECT match_id, home_team_name, away_team_name, status, start_timestamp 
            FROM matches 
            WHERE DATE(datetime(start_timestamp, 'unixepoch', '-3 hours')) = ?
        """
        cursor.execute(query, (target_date,))
        rows = cursor.fetchall()
        matches_to_update = rows
    elif force_all_pending:
        # Update ALL matches that are not 'finished' but started in the past
        now_ts = int(datetime.now().timestamp())
        query = """
            SELECT match_id, home_team_name, away_team_name, status, start_timestamp 
            FROM matches 
            WHERE status != 'finished' AND start_timestamp < ?
        """
        cursor.execute(query, (now_ts,))
        matches_to_update = cursor.fetchall()
    else:
        # Default: Update Pending matches from Yesterday and Today
        # Good for routine cron jobs
        now_ts = int(datetime.now().timestamp())
        yesterday_ts = int((datetime.now() - timedelta(days=1)).timestamp())
        query = """
            SELECT match_id, home_team_name, away_team_name, status, start_timestamp 
            FROM matches 
            WHERE status != 'finished' 
              AND start_timestamp BETWEEN ? AND ?
        """
        cursor.execute(query, (yesterday_ts, now_ts))
        matches_to_update = cursor.fetchall()

    if not matches_to_update:
        print("No matches found to update.")
        return

    print(f"Found {len(matches_to_update)} matches to check/update...")
    
    scraper.start()
    
    updated_count = 0
    stats_updated_count = 0
    
    try:
        for match in matches_to_update:
            match_id, home, away, current_status, start_ts = match
            print(f"\nChecking: {home} vs {away} (ID: {match_id}) [{current_status}]")
            
            # A. Get Latest Details (Status, Score)
            details = scraper.get_match_details(match_id)
            if not details:
                print(f"   Could not fetch details for {match_id}")
                continue
                
            new_status = details['status']
            print(f"   Status: {current_status} -> {new_status}")
            
            # Save basic updates (Score, Status)
            db.save_match(details)
            updated_count += 1
            
            # B. If Finished (or Live), Get Stats
            # We fetch stats even for live games to see live pressure, but definitely for finished
            if new_status == 'finished' or new_status == 'inprogress':
                print(f"   Fetching detailed statistics...")
                stats = scraper.get_match_stats(match_id)
                
                # Basic check if we got data
                if stats['total_shots_home'] == 0 and stats['total_shots_away'] == 0:
                     print("   Stats empty/zeros (maybe source delay). Saved anyway.")
                else:
                     print(f"   Stats fetched: {stats['corners_home_ft']}-{stats['corners_away_ft']} corners, {stats['expected_goals_home']}-{stats['expected_goals_away']} xG")
                
                db.save_stats(match_id, stats)
                stats_updated_count += 1
                
    except KeyboardInterrupt:
        print("\nUpdate user interrupted.")
    except Exception as e:
        print(f"\nError during update loop: {e}")
    finally:
        scraper.stop()
        
    print(f"\nSummary:")
    print(f"   - Matches Checked: {updated_count}")
    print(f"   - Stats Updated: {stats_updated_count}")
    
    # Run Prediction Checker (Green/Red)
    print("\nVerifying Predictions (Green/Red)...")
    db.check_predictions()
    print("Verification Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update match results and stats.")
    parser.add_argument("--date", type=str, help="Specific date to update (YYYY-MM-DD)")
    parser.add_argument("--all-pending", action="store_true", help="Force update of ALL pending matches in history (that started already)")
    
    args = parser.parse_args()
    
    update_results(target_date=args.date, force_all_pending=args.all_pending)
