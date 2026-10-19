#!/usr/bin/env python3
"""
Barabanki Connect — Database Backup & Restoration Utility
Supports:
  - SQLite (Hot backup via Python sqlite3 backup API)
  - PostgreSQL (via pg_dump / pg_restore or psql)
"""

import sys
import shutil
import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.core.config import settings
from app.core.database import get_masked_db_url

BACKUP_DIR = BASE_DIR / "backups"


def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def backup_sqlite(source_path: Path) -> Path:
    """Create a consistent hot backup of SQLite database using sqlite3 online backup API."""
    ensure_backup_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"barabanki_backup_{timestamp}.db"

    print(f"[*] Starting SQLite hot backup from: {source_path}")
    source_conn = sqlite3.connect(str(source_path))
    dest_conn = sqlite3.connect(str(backup_path))

    try:
        with dest_conn:
            source_conn.backup(dest_conn, pages=100)
        print(f"[+] Backup successfully completed: {backup_path}")
        print(f"[+] Backup size: {backup_path.stat().st_size:,} bytes")
    finally:
        source_conn.close()
        dest_conn.close()

    return backup_path


def restore_sqlite(backup_path: Path, target_path: Path) -> bool:
    """Safely restore SQLite database from backup after validating integrity."""
    if not backup_path.exists():
        print(f"[-] Error: Backup file not found: {backup_path}")
        return False

    print(f"[*] Validating backup integrity: {backup_path}")
    test_conn = sqlite3.connect(str(backup_path))
    try:
        cursor = test_conn.cursor()
        res = cursor.execute("PRAGMA integrity_check").fetchone()
        if not res or res[0] != "ok":
            print(f"[-] Integrity check failed: {res}")
            return False
        print("[+] Integrity check passed: 'ok'")
    finally:
        test_conn.close()

    # Create safety backup of existing target before overwriting
    if target_path.exists():
        safety_path = target_path.with_suffix(".pre_restore.bak")
        shutil.copy2(target_path, safety_path)
        print(f"[+] Safety snapshot of current database saved to: {safety_path}")

    shutil.copy2(backup_path, target_path)
    print(f"[+] Database successfully restored to: {target_path}")
    return True


def list_backups():
    ensure_backup_dir()
    backups = sorted(BACKUP_DIR.glob("barabanki_backup_*.db"), reverse=True)
    if not backups:
        print("[*] No database backups found in: " + str(BACKUP_DIR))
        return

    print(f"[*] Found {len(backups)} backup(s) in {BACKUP_DIR}:")
    for b in backups:
        size_kb = b.stat().st_size / 1024
        modified = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"  - {b.name} ({size_kb:.1f} KB) [Created: {modified}]")


def main():
    parser = argparse.ArgumentParser(description="Barabanki Connect Database Backup & Restore Tool")
    parser.add_argument("--backup", action="store_true", help="Create an immediate database backup")
    parser.add_argument("--restore", type=str, help="Path to backup file to restore from")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument("--verify", type=str, help="Verify integrity of a backup file")

    args = parser.parse_args()

    db_url = settings.DATABASE_URL

    if args.list:
        list_backups()
        return

    if args.verify:
        v_path = Path(args.verify)
        if not v_path.exists():
            print(f"[-] File not found: {v_path}")
            sys.exit(1)
        conn = sqlite3.connect(str(v_path))
        res = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        print(f"[*] Integrity check for {v_path.name}: {res[0]}")
        return

    if args.backup:
        if db_url.startswith("sqlite"):
            raw_path = db_url.replace("sqlite:///", "").replace("./", "")
            source_file = (BASE_DIR / raw_path).resolve()
            if not source_file.exists():
                print(f"[-] Source SQLite database not found at: {source_file}")
                sys.exit(1)
            backup_sqlite(source_file)
        else:
            masked = get_masked_db_url(db_url)
            print("[*] PostgreSQL detected. Command for PostgreSQL backup (credentials masked):")
            print(f'  pg_dump "{masked}" -F c -b -v -f backups/barabanki_pg_backup_$(date +%Y%m%d_%H%M%S).dump')
            print("  (Tip: Set PGPASSWORD environment variable or use ~/.pgpass to avoid exposing passwords)")
        return

    if args.restore:
        backup_file = Path(args.restore).resolve()
        if db_url.startswith("sqlite"):
            raw_path = db_url.replace("sqlite:///", "").replace("./", "")
            target_file = (BASE_DIR / raw_path).resolve()
            success = restore_sqlite(backup_file, target_file)
            if not success:
                sys.exit(1)
        else:
            masked = get_masked_db_url(db_url)
            print("[*] PostgreSQL detected. Command for PostgreSQL restore (credentials masked):")
            print(f'  pg_restore -d "{masked}" -v {backup_file}')
        return

    parser.print_help()


if __name__ == "__main__":
    main()
