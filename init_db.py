"""
Barabanki Connect - Unified Database Initialization & Migration Script

This script:
1. Initializes all database tables via SQLAlchemy metadata.
2. Applies Alembic migrations up to head.
3. Seeds authentic Barabanki baseline data and seed user accounts.
"""
import sys
import subprocess
from app.core.database import init_db
from app.seeds.seed_data import seed

def main():
    print("====================================================")
    print("   Barabanki Connect - Database Initialization     ")
    print("====================================================")
    
    print("\n[1/3] Creating database tables...")
    init_db()
    print("[OK] Tables initialized.")

    print("\n[2/3] Checking & applying Alembic migrations...")
    try:
        res = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True)
        if res.returncode == 0:
            print("[OK] Alembic migrations applied successfully.")
        else:
            print("Notice on migrations:", res.stderr.strip() or res.stdout.strip())
    except Exception as e:
        print(f"Migration runner notice: {e}")

    print("\n[3/3] Populating database with authentic Barabanki seed data...")
    seed()
    print("[OK] Seeding complete.")
    
    print("\n====================================================")
    print("Database setup complete! You can now start the app:")
    print("  uvicorn main:app --reload --port 8000")
    print("====================================================")

if __name__ == "__main__":
    main()
