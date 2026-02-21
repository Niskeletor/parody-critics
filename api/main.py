"""
FastAPI server for Parody Critics API
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import sqlite3
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager

from models.schemas import (
    CriticsResponse, CriticResponse, MediaInfo, CharacterInfo,
    StatsResponse, GenerationRequest, GenerationResponse,
    MediaType, SyncLogEntry
)
from config import get_config

# Configuration
config = get_config()
DB_PATH = config.get_absolute_db_path()

class DatabaseManager:
    """Database connection manager"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False):
        """Execute query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            return cursor.fetchall()

    def execute_insert(self, query: str, params: tuple = ()):
        """Execute insert and return lastrowid"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

# Initialize database manager
db_manager = DatabaseManager(str(DB_PATH))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("🚀 Starting Parody Critics API...")

    # Verify database exists
    if not Path(DB_PATH).exists():
        print("❌ Database not found! Run database/init_db.py first")
        raise RuntimeError("Database not initialized")

    print(f"✅ Database connected: {DB_PATH}")
    yield

    # Shutdown
    print("🛑 Shutting down Parody Critics API...")

# Create FastAPI app
app = FastAPI(
    title="Parody Critics API",
    description="API para gestionar críticas parodia de Jellyfin",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware with environment-specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Routes

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Parody Critics API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/critics/{tmdb_id}", response_model=CriticsResponse)
async def get_critics_by_tmdb(tmdb_id: str):
    """Get critics for a specific TMDB ID"""

    # Get media info
    media_query = """
        SELECT id, tmdb_id, title, year, type
        FROM media
        WHERE tmdb_id = ?
    """

    media_row = db_manager.execute_query(media_query, (tmdb_id,), fetch_one=True)

    if not media_row:
        raise HTTPException(status_code=404, detail=f"Media not found: {tmdb_id}")

    media_dict = dict(media_row)

    # Get critics
    critics_query = """
        SELECT c.character_id, c.rating, c.content, c.generated_at,
               ch.name, ch.emoji, ch.personality, ch.color,
               ch.border_color, ch.accent_color
        FROM critics c
        JOIN characters ch ON c.character_id = ch.id
        WHERE c.media_id = ? AND ch.active = TRUE
        ORDER BY c.generated_at DESC
    """

    critics_rows = db_manager.execute_query(critics_query, (media_dict['id'],))

    if not critics_rows:
        raise HTTPException(status_code=404, detail=f"No critics found for TMDB ID: {tmdb_id}")

    # Build response
    critics_dict = {}
    for row in critics_rows:
        row_dict = dict(row)
        critics_dict[row_dict['character_id']] = CriticResponse(
            character_id=row_dict['character_id'],
            author=row_dict['name'],
            emoji=row_dict['emoji'],
            rating=row_dict['rating'],
            content=row_dict['content'],
            personality=row_dict['personality'],
            generated_at=row_dict['generated_at'],
            color=row_dict['color'],
            border_color=row_dict['border_color'],
            accent_color=row_dict['accent_color']
        )

    return CriticsResponse(
        tmdb_id=tmdb_id,
        title=media_dict['title'],
        year=media_dict.get('year'),
        type=MediaType(media_dict['type']),
        critics=critics_dict,
        total_critics=len(critics_dict)
    )

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get API statistics"""

    query = "SELECT * FROM stats_summary"
    stats_row = db_manager.execute_query(query, fetch_one=True)

    if not stats_row:
        # Fallback if view doesn't work
        return StatsResponse(
            total_media=0,
            total_movies=0,
            total_series=0,
            total_critics=0,
            active_characters=0,
            media_without_critics=0,
            last_media_sync=None,
            last_critic_generation=None
        )

    stats_dict = dict(stats_row)
    return StatsResponse(**stats_dict)

@app.get("/api/characters", response_model=List[CharacterInfo])
async def get_characters(active_only: bool = Query(True, description="Only return active characters")):
    """Get all characters"""

    query = """
        SELECT ch.*,
               COUNT(c.id) as total_reviews
        FROM characters ch
        LEFT JOIN critics c ON ch.id = c.character_id
    """

    if active_only:
        query += " WHERE ch.active = TRUE"

    query += " GROUP BY ch.id ORDER BY ch.name"

    rows = db_manager.execute_query(query)

    characters = []
    for row in rows:
        row_dict = dict(row)
        characters.append(CharacterInfo(**row_dict))

    return characters

@app.get("/api/media", response_model=List[MediaInfo])
async def get_media(
    type: Optional[MediaType] = Query(None, description="Filter by media type"),
    limit: int = Query(50, le=200, description="Limit results"),
    offset: int = Query(0, description="Offset for pagination"),
    has_critics: Optional[bool] = Query(None, description="Filter by critic availability")
):
    """Get media list"""

    base_query = """
        SELECT m.*,
               COUNT(c.id) as critics_count,
               CASE WHEN COUNT(c.id) > 0 THEN 1 ELSE 0 END as has_critics
        FROM media m
        LEFT JOIN critics c ON m.id = c.media_id
    """

    conditions = []
    params = []

    if type:
        conditions.append("m.type = ?")
        params.append(type.value)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " GROUP BY m.id"

    if has_critics is not None:
        base_query += f" HAVING has_critics = {1 if has_critics else 0}"

    base_query += " ORDER BY m.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = db_manager.execute_query(base_query, tuple(params))

    media_list = []
    for row in rows:
        row_dict = dict(row)
        # Parse genres JSON
        if row_dict.get('genres'):
            try:
                row_dict['genres'] = json.loads(row_dict['genres'])
            except json.JSONDecodeError:
                row_dict['genres'] = []

        media_list.append(MediaInfo(**row_dict))

    return media_list

@app.get("/api/sync-logs", response_model=List[SyncLogEntry])
async def get_sync_logs(limit: int = Query(10, le=100, description="Limit results")):
    """Get recent sync operation logs"""

    query = """
        SELECT * FROM sync_log
        ORDER BY started_at DESC
        LIMIT ?
    """

    rows = db_manager.execute_query(query, (limit,))

    logs = []
    for row in rows:
        row_dict = dict(row)
        logs.append(SyncLogEntry(**row_dict))

    return logs

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = db_manager.execute_query("SELECT 1", fetch_one=True)

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-01-01T00:00:00Z"  # Would be actual timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": str(exc.detail) if hasattr(exc, 'detail') else "Resource not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn

    print("🎭 Starting Parody Critics API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )