
import sqlite3
import os

def check_db():
    db_path = os.path.join(os.getcwd(), 'data', 'football_data.db')
    print(f"Checking DB at: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables found: {[t[0] for t in tables]}")
        
        if ('predictions',) in tables:
            print("\nALL Predictions for Match 14062165:")
            cursor.execute("SELECT id, model_version, category, prediction_label, confidence FROM predictions WHERE match_id = 14062165")
            rows = cursor.fetchall()
            for row in rows:
                print(row)

        else:
            print("❌ 'predictions' table not found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    check_db()
