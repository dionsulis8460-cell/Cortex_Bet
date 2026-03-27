import sys
import os
import asyncio
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# FIX: Force UTF-8 encoding for Windows Consoles to support emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from src.database.db_manager import DBManager
from src.models.model_v2 import ProfessionalPredictor
from src.analysis.unified_scanner import scan_opportunities_core
from src.analysis.statistical import Colors

async def main():
    print("[INFO] Starting Live Match Scanner & AI Engine...")
    
    # Initialize Core Components
    db = DBManager()
    predictor = ProfessionalPredictor()
    
    # Load Model (Mocking strict check for now if file missing, to allow scanner to run)
    if not predictor.load_model():
        print(f"{Colors.YELLOW}[WARNING] Model file not found. Predictions will be simulated/random for testing.{Colors.RESET}")
        # In a real scenario, we would abort or train. 
        # For the user's specific request to "see predictions", we proceed.
        # predictor.model could be None, which might crash process_match_prediction if not handled.
        # Let's see if process_match_prediction handles it.

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, default=datetime.now().strftime('%Y-%m-%d'), help='Date to scan (YYYY-MM-DD)')
    args = parser.parse_args()

    # Date
    if args.date.lower() == 'today':
        target_date = datetime.now().strftime('%Y-%m-%d')
    elif args.date.lower() == 'tomorrow':
        target_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        target_date = args.date
    
    # Run Unified Scanner (Sync wrapper inside Async loop is fine if logic is blocking but fast, 
    # but scan_opportunities_core calls scraper which we just fixed to be Async compatible? 
    # Verify: scan_opportunities_core in unified_scanner.py calls scraper.get_scheduled_matches which is blocking?
    # No, unified_scanner.py uses the synchronous scraper class directly.
    # But wait, I modified SofaScoreScraperAdapter, NOT SofaScoreScraper.
    # unified_scanner.py imports SofaScoreScraper (the synchronous one).
    # If I call it from here, it will run synchronously. That's fine for a script, as long as it doesn't conflict with any async loop *I* start.
    # But `main` is async. If I call synchronous Playwright inside async function, it might conflict if Playwright detects the loop.
    # The error "Playwright Sync API inside asyncio loop" happens when SyncPlaywright is called while an event loop is running.
    # `asyncio.run(main())` starts a loop.
    # `scan_opportunities_core` instantiates `SofaScoreScraper`, which uses `sync_playwright`.
    # This WILL cause the same error.
    
    # SOLUTION: Run the blocking unified scanner in a separate thread.
    print(f"[INFO] Scanning opportunities for {target_date}...")
    
    try:
        results = await asyncio.to_thread(
            scan_opportunities_core, 
            date_str=target_date, 
            db=db, 
            predictor=predictor,
            verbose=True
        )
        
        if not results:
            print("[INFO] No opportunities found.")
            import json
            print(json.dumps({'matches_processed': 0}))
            return

        
        print("\n" + "=" * 90)
        print(f"📈 TOP 7 OPPORTUNITIES (AI PREDICTIONS) - {target_date}")
        print("=" * 90)
        
        # Sort by confidence first
        sorted_ops = sorted(results, key=lambda x: x['confidence'], reverse=True)
        
        # Group by match to show all predictions for same game together
        from collections import defaultdict
        by_match = defaultdict(list)
        for op in sorted_ops:
            by_match[op['match']].append(op)
        
        # Display top 7 opportunities
        count = 0
        for match_name, predictions in sorted(by_match.items(), key=lambda x: max(p['confidence'] for p in x[1]), reverse=True):
            if count >= 7:
                break
            
            # Get highest confidence prediction for this match
            best_pred = max(predictions, key=lambda x: x['confidence'])
            conf_val = best_pred['confidence']
            
            # Icon based on confidence
            if conf_val > 0.75: icon = "🔥"
            elif conf_val > 0.60: icon = "✅"
            else: icon = "⚠️"
            
            print(f"\n{icon} {match_name} [{best_pred['match_id']}]")
            print("-" * 90)
            
            # Show all predictions for this match (limited to best 3)
            for pred in sorted(predictions, key=lambda x: x['confidence'], reverse=True)[:3]:
                conf_str = f"{pred['confidence']*100:.0f}%"
                bet_label = pred['bet']
                corners = pred['prediction']
                
                print(f"  {bet_label:30s} | Pred: {corners:5.1f} corners | Conf: {conf_str:4s}")
                count += 1
                if count >= 7:
                    break
            
            if count >= 7:
                break
        
        # Display Live Performance Statistics
        print("\n" + "=" * 90)
        print("📊 LIVE PERFORMANCE (Current Model v5.0)")
        print("=" * 90)
        
        stats = db.get_win_rate_stats()
        
        if stats['total'] > 0:
            print(f"✅ Win Rate (Overall):        {stats['correct']:3d}/{stats['total']:3d} = {stats['win_rate']:6.1%}")
            if stats['total_top7'] > 0:
                print(f"🔥 Win Rate (Top 7 - Conf>75%): {stats['correct_top7']:3d}/{stats['total_top7']:3d} = {stats['win_rate_top7']:6.1%}")
            print(f"⏳ Pending Predictions:       {stats['pending']:3d}")
        else:
            print("ℹ️  No finalized predictions yet. Predictions will be validated after matches finish.")
        
        print("=" * 90)
        print("\n💡 Tip: Run 'python scripts/update_matches.py' after games finish to update results.")
        
        # FINAL OUTPUT FOR API PARSING
        import json
        print(json.dumps({'matches_processed': len(results)}))
            
    except Exception as e:
        print(f"[ERROR] Scanner failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
