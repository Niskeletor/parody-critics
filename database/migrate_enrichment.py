#!/usr/bin/env python3
"""
Migration: Add enriched_context column to media table.
Safe to run multiple times (idempotent).
"""
import sqlite3, sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "critics.db"

def run_migration(db_path: str = None):
    path = db_path or str(DB_PATH)
    if not Path(path).exists():
        print(f"❌ Database not found: {path}")
        sys.exit(1)

    print(f"🗃️  Migrating database: {path}")

    with sqlite3.connect(path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(media)")
        existing = {row[1] for row in cursor.fetchall()}

        for col, definition in [
            ("enriched_context", "TEXT"),
            ("enriched_at",      "DATETIME"),
        ]:
            if col not in existing:
                cursor.execute(f"ALTER TABLE media ADD COLUMN {col} {definition}")
                print(f"  ✅ Added column: {col}")
            else:
                print(f"  ⏭️  Already exists: {col}")

        conn.commit()

    print("🚀 Migration complete!")

if __name__ == "__main__":
    run_migration()
