import sqlite3
import datetime

DB_PATH = 'data/football_data.db'

def upgrade_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("PRAGMA table_info(matches)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'last_updated' not in columns:
            print("Adding 'last_updated' column to matches table...")
            cursor.execute("ALTER TABLE matches ADD COLUMN last_updated TEXT")
            
            # Initialize with current time
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("UPDATE matches SET last_updated = ?", (now,))
            conn.commit()
            print("✅ Column added and initialized.")
        else:
            print("ℹ️ Column 'last_updated' already exists.")
            
        conn.close()
    except Exception as e:
        print(f"❌ Error updating DB: {e}")

if __name__ == "__main__":
    upgrade_db()
