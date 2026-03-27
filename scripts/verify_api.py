
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from web_app.lib.dashboard_data import get_dashboard_data

def verify_api():
    print("Fetching dashboard data...")
    # Fetch data for today
    data = get_dashboard_data(type='predictions', date='today')
    
    found_neural = False
    found_stats = False
    
    for match in data:
        print(f"\nMatch: {match['homeTeam']} vs {match['awayTeam']}")
        for pred in match['predictions']:
            model = pred.get('model', 'Unknown')
            print(f"  - {pred['type']}: {pred['confidence']}% ({model})")
            
            if model == 'Neural_Challenger': found_neural = True
            if model == 'Statistical': found_stats = True
            
    if found_neural and found_stats:
        print("\n✅ SUCCESS: Both models found in API response!")
    elif found_neural:
        print("\n⚠️ WARNING: Only Neural found (Statistical missing?)")
    elif found_stats:
        print("\n⚠️ WARNING: Only Statistical found (Neural missing?)")
    else:
        print("\n❌ ERROR: No predictions found.")

if __name__ == "__main__":
    verify_api()
