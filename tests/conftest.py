"""
Test configuration — sets env vars and initializes DB schema at module load time,
before api.main is imported (db_manager is created at import time).
"""
import os
import sqlite3
import tempfile
from pathlib import Path

# ── Set env vars at module level (before any test imports api.main) ──────────
_tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmpdb.close()

os.environ["PARODY_CRITICS_DB_PATH"] = _tmpdb.name
os.environ["AVATAR_DIR"] = "/tmp/parody-test-avatars"
os.environ["PARODY_CRITICS_ENV"] = "development"
os.environ.setdefault("LLM_OLLAMA_URL", "http://localhost:11434")

# ── Initialize schema so tables exist when tests run ─────────────────────────
_schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
_schema_sql = _schema_path.read_text()

_conn = sqlite3.connect(_tmpdb.name)
for _stmt in [s.strip() for s in _schema_sql.split(";") if s.strip()]:
    try:
        _conn.execute(_stmt)
    except sqlite3.Error:
        pass  # Skip INSERT statements and errors — we only need table structure
_conn.commit()
_conn.close()
