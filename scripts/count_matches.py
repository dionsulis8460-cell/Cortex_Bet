
import sqlite3
import os

def check_db_count():
    db_path = os.path.join(os.getcwd(), 'data', 'football_data.db')
    print(f"Checking DB at: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM matches")
        count = cursor.fetchone()[0]
        print(f"Total Matches in DB: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    check_db_count()
