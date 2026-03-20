#!/usr/bin/env python3
"""
Database initialization script
Creates the SQLite database and applies schema
"""

import sqlite3
from pathlib import Path

def init_database(db_path: str = "database/critics.db"):
    """Initialize the SQLite database with schema"""

    # Ensure database directory exists
    db_dir = Path(db_path).parent
    db_dir.mkdir(exist_ok=True)

    # Get schema file path
    script_dir = Path(__file__).parent
    schema_path = script_dir / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    # Read schema
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # Connect and execute schema
    print(f"🗃️ Initializing database: {db_path}")

    with sqlite3.connect(db_path) as conn:
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")

        # Execute schema
        conn.executescript(schema_sql)

        # Verify tables were created
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)

        tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ Created tables: {', '.join(tables)}")

        # Get initial stats
        cursor.execute("SELECT * FROM stats_summary")
        stats = cursor.fetchone()
        if stats:
            print(f"📊 Initial stats: {stats[0]} media, {stats[3]} critics")

        # Verify characters were inserted
        cursor.execute("SELECT COUNT(*) FROM characters WHERE active = TRUE")
        active_chars = cursor.fetchone()[0]
        print(f"🎭 Active characters: {active_chars}")

    print("🚀 Database initialized successfully!")
    return db_path

if __name__ == "__main__":
    import os
    import sys
    db_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("PARODY_CRITICS_DB_PATH", "database/critics.db")
    )
    init_database(db_path)