
from src.database.db_manager import DBManager
import sys
import os

def seed_users():
    db = DBManager()
    
    users = [
        {"username": "Mathee", "password": "Valm0001!", "role": "admin", "bankroll": 5000.0},
        {"username": "gigante", "password": "gigante", "role": "user", "bankroll": 1000.0},
        {"username": "thiago", "password": "thiago", "role": "user", "bankroll": 1000.0}
    ]
    
    print("Seeding users...")
    for u in users:
        # Check if exists
        existing = db.get_user_by_username(u['username'])
        if existing:
            print(f"User {u['username']} exists. Updating password...")
            db.update_user_password(u['username'], u['password'])
        else:
            print(f"Creating user {u['username']}...")
            db.create_user(u['username'], u['password'], u['role'], u['bankroll'])
            
    print("✅ Users seeded successfully.")

if __name__ == "__main__":
    # Ensure strict path for imports if run as script
    sys.path.append(os.getcwd())
    seed_users()
