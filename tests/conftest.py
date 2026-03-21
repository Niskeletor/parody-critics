"""
Test configuration — creates a temp SQLite DB with schema for each test session.
"""
import os
import tempfile
import pytest
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create a temporary SQLite DB with the full schema for the test session."""
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    schema_sql = schema_path.read_text()

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    import sqlite3
    conn = sqlite3.connect(db_path)
    # Run schema — skip INSERT statements (we just need tables)
    statements = [s.strip() for s in schema_sql.split(";") if s.strip()]
    for stmt in statements:
        try:
            conn.execute(stmt)
        except sqlite3.Error:
            pass  # Skip inserts/errors — we only need the table structure
    conn.commit()
    conn.close()

    os.environ["PARODY_CRITICS_DB_PATH"] = db_path
    os.environ["AVATAR_DIR"] = "/tmp/parody-test-avatars"
    os.environ["PARODY_CRITICS_ENV"] = "development"

    yield db_path

    os.unlink(db_path)
