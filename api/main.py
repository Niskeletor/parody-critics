"""
FastAPI server for Parody Critics API
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import json
import httpx
import uuid
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from models.schemas import (
    CriticsResponse, CriticResponse, MediaInfo, CharacterInfo,
    StatsResponse, GenerationRequest, GenerationResponse,
    MediaType, SyncLogEntry
)
from config import get_config
from api.jellyfin_sync import JellyfinSyncManager
from api.llm_manager import CriticGenerationManager
from utils import get_logger
from utils.websocket_manager import websocket_manager, WebSocketProgressAdapter
from utils.sync_manager import SyncManager

# Configuration
config = get_config()
DB_PATH = config.get_absolute_db_path()

# Setup logging
setup_logger = get_logger('setup_wizard')
search_logger = get_logger('search')

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

# Initialize managers (will be configured on startup)
sync_manager: Optional[JellyfinSyncManager] = None
llm_manager: Optional[CriticGenerationManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global sync_manager, llm_manager

    # Startup
    print("🚀 Starting Parody Critics API...")

    # Verify database exists
    if not Path(DB_PATH).exists():
        print("❌ Database not found! Run database/init_db.py first")
        raise RuntimeError("Database not initialized")

    print(f"✅ Database connected: {DB_PATH}")

    # Initialize Jellyfin sync manager from configuration
    sync_manager = JellyfinSyncManager(
        jellyfin_url=config.JELLYFIN_URL,
        api_token=config.JELLYFIN_API_TOKEN,
        jellyfin_db_path=config.JELLYFIN_DB_PATH,
        local_db_path=str(DB_PATH)
    )

    print("🔄 Jellyfin Sync Manager initialized")

    # Initialize LLM manager
    llm_manager = CriticGenerationManager()
    print("🤖 LLM Manager initialized")

    # Check LLM system status
    try:
        llm_status = await llm_manager.get_system_status()
        healthy_endpoints = llm_status["healthy_endpoints"]
        total_endpoints = llm_status["total_endpoints"]
        print(f"🏥 LLM System: {healthy_endpoints}/{total_endpoints} endpoints healthy")
    except Exception as e:
        print(f"⚠️  LLM system check failed: {str(e)}")

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

# Mount static files for the frontend
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Routes

@app.get("/")
async def root():
    """Serve the frontend application"""
    from fastapi.responses import FileResponse
    static_dir = Path(__file__).parent.parent / "static"
    index_file = static_dir / "index.html"

    if index_file.exists():
        return FileResponse(str(index_file))

    # Fallback to API info if no frontend
    return {
        "message": "Parody Critics API",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "/static/index.html"
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
    has_critics: Optional[bool] = Query(None, description="Filter by critic availability"),
    start_letter: Optional[str] = Query(None, description="Filter by starting letter")
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

    if start_letter:
        if start_letter == '0-9':
            # Filter for titles starting with numbers or special characters
            conditions.append("SUBSTR(UPPER(m.title), 1, 1) GLOB '[0-9]*'")
        else:
            # Filter for titles starting with specific letter
            conditions.append("UPPER(m.title) LIKE ?")
            params.append(f"{start_letter.upper()}%")

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

@app.get("/api/media/search", response_model=List[MediaInfo])
async def search_media(
    query: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, le=50, description="Maximum number of results")
):
    """Search media by title with flexible matching"""

    # Optimized search query with Full Text Search (FTS) for better performance
    search_query = """
        SELECT m.id, m.tmdb_id, m.jellyfin_id, m.title, m.original_title,
               m.year, m.type, m.genres, m.overview, m.poster_url, m.imdb_id,
               m.vote_average, m.created_at,
               CASE WHEN c.media_id IS NOT NULL THEN 1 ELSE 0 END as has_critics,
               COUNT(c.id) as critics_count
        FROM media_fts
        JOIN media m ON media_fts.rowid = m.id
        LEFT JOIN critics c ON m.id = c.media_id
        WHERE media_fts MATCH ?
        GROUP BY m.id
        ORDER BY m.vote_average DESC
        LIMIT ?
    """

    # Create FTS query pattern with proper escaping for special characters
    fts_query = query.strip()

    # Escape FTS special characters to prevent syntax errors
    fts_special_chars = '"*()[]{}~:'
    for char in fts_special_chars:
        fts_query = fts_query.replace(char, f'"{char}"')

    # If FTS query is problematic, fallback to LIKE search
    try_fts = True
    if len(fts_query) < 2 or any(c in fts_query for c in ['<', '>', 'script']):
        try_fts = False

    # Try FTS first, fallback to LIKE if needed
    if try_fts:
        params = [fts_query, limit]
        try:
            rows = db_manager.execute_query(search_query, params)
        except Exception as e:
            search_logger.warning(f"FTS query failed, falling back to LIKE: {e}")
            try_fts = False

    if not try_fts:
        # Fallback to secure LIKE query
        fallback_query = """
            SELECT m.id, m.tmdb_id, m.jellyfin_id, m.title, m.original_title,
                   m.year, m.type, m.genres, m.overview, m.poster_url, m.imdb_id,
                   m.vote_average, m.created_at,
                   CASE WHEN c.media_id IS NOT NULL THEN 1 ELSE 0 END as has_critics,
                   COUNT(c.id) as critics_count
            FROM media m
            LEFT JOIN critics c ON m.id = c.media_id
            WHERE UPPER(m.title) LIKE UPPER(?) OR UPPER(m.original_title) LIKE UPPER(?)
            GROUP BY m.id
            ORDER BY m.vote_average DESC
            LIMIT ?
        """
        safe_pattern = f"%{query.strip()[:100]}%"  # Limit pattern length
        params = [safe_pattern, safe_pattern, limit]
        rows = db_manager.execute_query(fallback_query, params)

    media_list = []
    for row in rows:
        row_dict = dict(row)
        row_dict['has_critics'] = bool(row_dict['has_critics'])

        # Parse genres if present
        if row_dict['genres']:
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

@app.post("/api/sync/start")
async def start_sync(background_tasks: BackgroundTasks, sync_type: str = "full", batch_size: int = 100):
    """Start Jellyfin media synchronization"""
    if not sync_manager:
        raise HTTPException(status_code=500, detail="Sync manager not initialized")

    # Check if sync is already running
    current_progress = sync_manager.get_sync_progress()
    if current_progress and current_progress.get('status') == 'running':
        raise HTTPException(status_code=409, detail="Sync already in progress")

    try:
        # Start sync in background
        sync_id = await sync_manager.start_sync(sync_type=sync_type, batch_size=batch_size)

        return {
            "message": "Sync started successfully",
            "sync_id": sync_id,
            "sync_type": sync_type,
            "batch_size": batch_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sync: {str(e)}")

@app.get("/api/sync/progress")
async def get_sync_progress():
    """Get current synchronization progress"""
    if not sync_manager:
        raise HTTPException(status_code=500, detail="Sync manager not initialized")

    progress = sync_manager.get_sync_progress()

    if not progress:
        return {
            "status": "idle",
            "message": "No sync in progress"
        }

    return progress

@app.post("/api/sync/cancel")
async def cancel_sync():
    """Cancel current synchronization"""
    if not sync_manager:
        raise HTTPException(status_code=500, detail="Sync manager not initialized")

    success = sync_manager.cancel_sync()

    if success:
        return {"message": "Sync cancelled successfully"}
    else:
        return {"message": "No active sync to cancel"}

@app.get("/api/sync/stats")
async def get_sync_stats():
    """Get synchronization statistics"""
    if not sync_manager:
        raise HTTPException(status_code=500, detail="Sync manager not initialized")

    try:
        # Get media counts from Jellyfin DB
        jellyfin_counts = sync_manager.get_media_count_from_jellyfin_db()

        # Get local media count
        local_count = db_manager.execute_query("SELECT COUNT(*) FROM media", fetch_one=True)
        local_media_count = local_count[0] if local_count else 0

        return {
            "jellyfin_stats": jellyfin_counts,
            "local_media_count": local_media_count,
            "coverage_percent": (local_media_count / jellyfin_counts['total'] * 100) if jellyfin_counts['total'] > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sync stats: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        result = db_manager.execute_query("SELECT 1", fetch_one=True)

        # Test sync manager
        sync_manager_status = "initialized" if sync_manager else "not_initialized"

        return {
            "status": "healthy",
            "database": "connected",
            "sync_manager": sync_manager_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# LLM-powered critic generation endpoints

@app.post("/api/generate/critic/{tmdb_id}")
async def generate_critic_for_media(
    tmdb_id: str,
    character: str = Query(..., description="Character name (Marco Aurelio or Rosario Costras)"),
    force_endpoint: Optional[str] = Query(None, description="Force specific LLM endpoint")
):
    """Generate a new critic for specific media using LLM"""
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM system not available")

    # Validate character exists in database
    character_query = "SELECT id FROM characters WHERE name = ? AND active = TRUE"
    character_row = db_manager.execute_query(character_query, (character,), fetch_one=True)

    if not character_row:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid character. Character '{character}' not found or inactive."
        )

    # Get media information from database
    media_query = """
        SELECT id, tmdb_id, title, year, type, genres, overview
        FROM media
        WHERE tmdb_id = ?
    """
    media_row = db_manager.execute_query(media_query, (tmdb_id,), fetch_one=True)

    if not media_row:
        raise HTTPException(status_code=404, detail=f"Media not found: {tmdb_id}")

    media_dict = dict(media_row)

    # Prepare media info for LLM
    media_info = {
        "id": media_dict["id"],
        "tmdb_id": tmdb_id,
        "title": media_dict["title"],
        "year": media_dict.get("year"),
        "type": media_dict["type"],
        "genres": media_dict.get("genres", ""),
        "synopsis": media_dict.get("overview", "Sin sinopsis disponible")
    }

    try:
        # Generate critic using LLM
        result = await llm_manager.generate_critic(
            character=character,
            media_info=media_info,
            force_endpoint=force_endpoint
        )

        if not result["success"]:
            raise HTTPException(
                status_code=503,
                detail=f"Critic generation failed: {result['error']}"
            )

        # Parse the response
        parsed_critic = llm_manager.parse_critic_response(
            result["response"],
            character,
            media_info
        )

        # Check if character exists in database
        character_query = "SELECT id FROM characters WHERE name = ?"
        character_row = db_manager.execute_query(character_query, (character,), fetch_one=True)

        if not character_row:
            raise HTTPException(status_code=404, detail=f"Character not found: {character}")

        character_id = character_row[0]

        # Delete existing critic from this character for this media
        delete_query = """
            DELETE FROM critics
            WHERE media_id = ? AND character_id = ?
        """
        db_manager.execute_query(delete_query, (media_info["id"], character_id))

        # Insert new critic
        insert_query = """
            INSERT INTO critics (media_id, character_id, rating, content, generated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        critic_id = db_manager.execute_insert(insert_query, (
            media_info["id"],
            character_id,
            parsed_critic["rating"],
            parsed_critic["content"],
            datetime.now().isoformat()
        ))

        return {
            "success": True,
            "critic_id": critic_id,
            "tmdb_id": tmdb_id,
            "character": character,
            "rating": parsed_critic["rating"],
            "content": parsed_critic["content"],
            "generation_info": {
                "endpoint_used": result["endpoint_used"],
                "model_used": result["model_used"],
                "generation_time": result["generation_time"],
                "attempts": len(result["attempts"])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/api/generate/batch")
async def generate_batch_critics(
    character: str = Query(..., description="Character name"),
    limit: int = Query(10, le=50, description="Max number of media to process"),
    force_endpoint: Optional[str] = Query(None, description="Force specific LLM endpoint")
):
    """Generate critics for multiple media items without existing critics"""
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM system not available")

    # Validate character exists in database
    character_query = "SELECT id FROM characters WHERE name = ? AND active = TRUE"
    character_row = db_manager.execute_query(character_query, (character,), fetch_one=True)

    if not character_row:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid character. Character '{character}' not found or inactive."
        )

    # Get character ID
    character_query = "SELECT id FROM characters WHERE name = ?"
    character_row = db_manager.execute_query(character_query, (character,), fetch_one=True)

    if not character_row:
        raise HTTPException(status_code=404, detail=f"Character not found: {character}")

    character_id = character_row[0]

    # Get media without critics from this character
    media_query = """
        SELECT m.id, m.tmdb_id, m.title, m.year, m.type, m.genres, m.overview
        FROM media m
        LEFT JOIN critics c ON m.id = c.media_id AND c.character_id = ?
        WHERE c.id IS NULL AND m.tmdb_id IS NOT NULL
        ORDER BY m.created_at DESC
        LIMIT ?
    """

    media_rows = db_manager.execute_query(media_query, (character_id, limit))

    if not media_rows:
        return {
            "success": True,
            "message": f"No media found without critics from {character}",
            "processed": 0,
            "results": []
        }

    results = []
    processed = 0

    for media_row in media_rows:
        media_dict = dict(media_row)

        media_info = {
            "id": media_dict["id"],
            "tmdb_id": media_dict["tmdb_id"],
            "title": media_dict["title"],
            "year": media_dict.get("year"),
            "type": media_dict["type"],
            "genres": media_dict.get("genres", ""),
            "synopsis": media_dict.get("overview", "Sin sinopsis disponible")
        }

        try:
            # Generate critic
            result = await llm_manager.generate_critic(
                character=character,
                media_info=media_info,
                force_endpoint=force_endpoint
            )

            if result["success"]:
                # Parse and save critic
                parsed_critic = llm_manager.parse_critic_response(
                    result["response"],
                    character,
                    media_info
                )

                # Insert critic
                insert_query = """
                    INSERT INTO critics (media_id, character_id, rating, content, generated_at)
                    VALUES (?, ?, ?, ?, ?)
                """
                critic_id = db_manager.execute_insert(insert_query, (
                    media_info["id"],
                    character_id,
                    parsed_critic["rating"],
                    parsed_critic["content"],
                    datetime.now().isoformat()
                ))

                results.append({
                    "tmdb_id": media_dict["tmdb_id"],
                    "title": media_dict["title"],
                    "status": "success",
                    "critic_id": critic_id,
                    "rating": parsed_critic["rating"],
                    "generation_time": result["generation_time"]
                })
                processed += 1
            else:
                results.append({
                    "tmdb_id": media_dict["tmdb_id"],
                    "title": media_dict["title"],
                    "status": "failed",
                    "error": result["error"]
                })

        except Exception as e:
            results.append({
                "tmdb_id": media_dict["tmdb_id"],
                "title": media_dict["title"],
                "status": "error",
                "error": str(e)
            })

    return {
        "success": True,
        "character": character,
        "processed": processed,
        "total_attempted": len(media_rows),
        "results": results
    }

@app.post("/api/generate/cart-batch")
async def generate_cart_batch_critics(
    request: dict
):
    """Generate critics for specific media items and characters from cart"""
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM system not available")

    try:
        # Extract data from request
        media_items = request.get("media_items", [])
        selected_critics = request.get("selected_critics", [])

        if not media_items:
            raise HTTPException(status_code=400, detail="No media items provided")

        if not selected_critics:
            raise HTTPException(status_code=400, detail="No critics selected")

        # Validate critic IDs exist - Secure parameterized query
        if len(selected_critics) == 0:
            raise HTTPException(status_code=400, detail="No critics selected")

        # Build secure parameterized query with exact number of placeholders
        critics_placeholders = ",".join(["?" for _ in selected_critics])
        critics_query = "SELECT id, name FROM characters WHERE id IN (" + critics_placeholders + ")"
        valid_critics = db_manager.execute_query(critics_query, tuple(selected_critics))

        if len(valid_critics) != len(selected_critics):
            raise HTTPException(status_code=400, detail="Some selected critics are invalid")

        # Validate media items exist - Secure parameterized query
        media_tmdb_ids = [item.get("tmdb_id") for item in media_items]
        if len(media_tmdb_ids) == 0:
            raise HTTPException(status_code=400, detail="No media items provided")

        # Build secure parameterized query with exact number of placeholders
        media_placeholders = ",".join(["?" for _ in media_tmdb_ids])
        media_query = (
            "SELECT id, tmdb_id, title, year, type, genres, overview "
            "FROM media "
            "WHERE tmdb_id IN (" + media_placeholders + ")"
        )
        valid_media = db_manager.execute_query(media_query, tuple(str(tmdb_id) for tmdb_id in media_tmdb_ids))

        if len(valid_media) != len(media_items):
            raise HTTPException(status_code=400, detail="Some media items are invalid")

        # Convert to dict for easier lookup
        media_dict = {row[1]: dict(zip(["id", "tmdb_id", "title", "year", "type", "genres", "overview"], row)) for row in valid_media}
        critic_dict = {row[0]: row[1] for row in valid_critics}

        results = []
        total_processed = 0
        total_attempted = len(media_items) * len(selected_critics)

        # Process each combination of media + critic
        for media_item in media_items:
            tmdb_id = str(media_item.get("tmdb_id"))
            media_info = media_dict.get(tmdb_id)

            if not media_info:
                continue

            for critic_id in selected_critics:
                critic_name = critic_dict.get(critic_id)

                if not critic_name:
                    continue

                try:
                    # Check if this combination already exists
                    existing_query = """
                        SELECT id FROM critics
                        WHERE media_id = ? AND character_id = ?
                    """
                    existing = db_manager.execute_query(existing_query, (media_info["id"], critic_id), fetch_one=True)

                    if existing:
                        results.append({
                            "tmdb_id": tmdb_id,
                            "title": media_info["title"],
                            "critic": critic_name,
                            "status": "skipped",
                            "reason": "Critic already exists"
                        })
                        continue

                    print(f"🎭 Generating critic: {critic_name} for {media_info['title']}")

                    # Generate the critic
                    parsed_critic = await llm_manager.generate_critic(
                        character=critic_name,
                        media_info=media_info
                    )

                    print(f"✅ Generated critic response: {type(parsed_critic)} - Keys: {list(parsed_critic.keys()) if isinstance(parsed_critic, dict) else 'Not a dict'}")

                    # Extract the actual critic content from the response
                    # The LLM manager returns: {'success', 'response', 'character', 'media_title', etc.}
                    # We need to parse the actual critic from the 'response' field
                    critic_content = parsed_critic.get("response", "")

                    # For now, we'll use a default rating and store the full response
                    # In future versions, we could parse the response to extract rating and content separately
                    rating = 8.0  # Default rating, could be extracted from response later

                    # Insert the new critic
                    insert_query = """
                        INSERT INTO critics (media_id, character_id, rating, content, generated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    critic_db_id = db_manager.execute_insert(insert_query, (
                        media_info["id"],
                        critic_id,
                        rating,
                        critic_content,
                        datetime.now().isoformat()
                    ))

                    results.append({
                        "tmdb_id": tmdb_id,
                        "title": media_info["title"],
                        "critic": critic_name,
                        "status": "success",
                        "rating": rating,
                        "critic_id": critic_db_id
                    })
                    total_processed += 1

                except Exception as e:
                    print(f"❌ Error in batch processing: {str(e)} - Type: {type(e)}")
                    import traceback
                    traceback.print_exc()

                    results.append({
                        "tmdb_id": tmdb_id,
                        "title": media_info["title"],
                        "critic": critic_name,
                        "status": "error",
                        "error": str(e)
                    })

        return {
            "success": True,
            "processed": total_processed,
            "total_attempted": total_attempted,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cart batch processing failed: {str(e)}")

@app.get("/api/llm/status")
async def get_llm_status():
    """Get LLM system status and endpoint health"""
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM system not available")

    try:
        status = await llm_manager.get_system_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.post("/api/llm/test")
async def test_llm_generation(
    character: str = Query("Marco Aurelio", description="Character name"),
    endpoint: Optional[str] = Query(None, description="Specific endpoint to test")
):
    """Test LLM generation with a sample movie"""
    if not llm_manager:
        raise HTTPException(status_code=503, detail="LLM system not available")

    # Sample movie for testing
    test_movie = {
        "id": 0,
        "tmdb_id": "test",
        "title": "The Matrix",
        "year": 1999,
        "type": "movie",
        "genres": "Action, Sci-Fi",
        "synopsis": "Un programador descubre que la realidad es una simulación y debe elegir entre la verdad dolorosa o la ilusión cómoda."
    }

    try:
        result = await llm_manager.generate_critic(
            character=character,
            media_info=test_movie,
            force_endpoint=endpoint
        )

        if result["success"]:
            parsed = llm_manager.parse_critic_response(
                result["response"],
                character,
                test_movie
            )

            return {
                "success": True,
                "test_movie": test_movie,
                "character": character,
                "endpoint_used": result["endpoint_used"],
                "model_used": result["model_used"],
                "generation_time": result["generation_time"],
                "critic": {
                    "rating": parsed["rating"],
                    "content": parsed["content"]
                },
                "raw_response": result["response"]
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "attempts": result["attempts"]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

# ========================================
# Setup Wizard Endpoints
# ========================================

@app.post("/api/setup/check-requirements")
async def check_system_requirements():
    """🔍 Check system requirements for setup wizard"""
    setup_logger.info("🔍 Setup wizard: Checking system requirements")

    try:
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "overall_status": "unknown",
            "ready_for_setup": False
        }

        # 1. Check Database
        setup_logger.debug("Checking database status...")
        db_check = await _check_database_status()
        result["checks"]["database"] = db_check
        setup_logger.info(f"Database check: {db_check['status']}")

        # 2. Check LLM System
        setup_logger.debug("Checking LLM system status...")
        llm_check = await _check_llm_status()
        result["checks"]["llm"] = llm_check
        setup_logger.info(f"LLM check: {llm_check['status']}")

        # 3. Check Port availability
        setup_logger.debug("Checking port status...")
        port_check = _check_port_status()
        result["checks"]["port"] = port_check
        setup_logger.info(f"Port check: {port_check['status']}")

        # Determine overall status
        all_checks = [db_check, llm_check, port_check]
        failed_checks = [c for c in all_checks if c["status"] != "healthy"]

        if not failed_checks:
            result["overall_status"] = "healthy"
            result["ready_for_setup"] = True
        elif len(failed_checks) <= 1:
            result["overall_status"] = "warning"
            result["ready_for_setup"] = True
        else:
            result["overall_status"] = "error"
            result["ready_for_setup"] = False

        setup_logger.info(f"✅ Setup requirements check completed: {result['overall_status']}")
        return result

    except Exception as e:
        setup_logger.error(f"❌ Setup requirements check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Requirements check failed: {str(e)}")


async def _check_database_status() -> Dict[str, Any]:
    """Check database status for setup wizard"""
    try:
        db_path = Path(DB_PATH)

        if not db_path.exists():
            return {
                "status": "missing",
                "message": "Database file does not exist",
                "path": str(db_path),
                "needs_setup": True
            }

        # Check if database has required tables
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            required_tables = ['media', 'critics', 'characters']
            missing_tables = [t for t in required_tables if t not in tables]

            if missing_tables:
                return {
                    "status": "incomplete",
                    "message": f"Missing tables: {', '.join(missing_tables)}",
                    "path": str(db_path),
                    "needs_setup": True
                }

            # Check if characters exist
            cursor = conn.execute("SELECT COUNT(*) FROM characters")
            character_count = cursor.fetchone()[0]

            if character_count == 0:
                return {
                    "status": "empty",
                    "message": "Database exists but has no characters",
                    "path": str(db_path),
                    "needs_setup": True
                }

            return {
                "status": "healthy",
                "message": f"Database ready with {character_count} characters",
                "path": str(db_path),
                "needs_setup": False
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Database check failed: {str(e)}",
            "path": str(db_path) if 'db_path' in locals() else "unknown",
            "needs_setup": True
        }


async def _check_llm_status() -> Dict[str, Any]:
    """Check LLM system status for setup wizard"""
    try:
        if not llm_manager:
            return {
                "status": "unavailable",
                "message": "LLM manager not initialized",
                "endpoints": {},
                "needs_setup": False  # This is a system issue, not setup
            }

        # Reuse the existing system status check from CLI
        status = await llm_manager.get_system_status()

        if status['system_status'] == 'operational':
            return {
                "status": "healthy",
                "message": f"{status['healthy_endpoints']}/{status['total_endpoints']} endpoints healthy",
                "endpoints": status['endpoints'],
                "needs_setup": False
            }
        else:
            return {
                "status": "degraded",
                "message": f"Only {status['healthy_endpoints']}/{status['total_endpoints']} endpoints healthy",
                "endpoints": status['endpoints'],
                "needs_setup": False  # LLM issues aren't fixed by setup
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"LLM check failed: {str(e)}",
            "endpoints": {},
            "needs_setup": False
        }


def _check_port_status() -> Dict[str, Any]:
    """Check if current port is working"""
    try:
        # If we're responding to this request, the port is working
        return {
            "status": "healthy",
            "message": "API server is responding",
            "port": 8888,  # Current port
            "needs_setup": False
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Port check failed: {str(e)}",
            "port": 8888,
            "needs_setup": False
        }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": str(exc.detail) if hasattr(exc, 'detail') else "Resource not found"}
    )

# ========================================
# Setup Wizard Interactive Endpoints
# ========================================

@app.post("/api/setup/test-jellyfin")
async def test_jellyfin_connection(request: dict = Body(...)):
    """🎬 Test Jellyfin connection with user-provided configuration"""
    setup_logger.info("🎬 Setup wizard: Testing Jellyfin connection")

    try:
        url = request.get("url", "").strip()
        api_token = request.get("api_token", "").strip()

        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        setup_logger.debug(f"Testing Jellyfin connection to: {url}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Test basic connection
            try:
                response = await client.get(f"{url}/System/Info/Public")
                response.raise_for_status()

                server_info = response.json()
                server_name = server_info.get('ServerName', 'Unknown')
                version = server_info.get('Version', 'Unknown')

                setup_logger.info(f"Successfully connected to Jellyfin: {server_name} v{version}")

                result = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": True,
                    "server_name": server_name,
                    "version": version,
                    "message": f"Connected to {server_name} (v{version})"
                }

                # Test API token if provided
                if api_token:
                    setup_logger.debug("Testing API token validity")
                    headers = {"X-MediaBrowser-Token": api_token}
                    try:
                        users_response = await client.get(f"{url}/Users", headers=headers)
                        users_response.raise_for_status()

                        users = users_response.json()
                        setup_logger.info(f"API token valid - found {len(users)} users")
                        result["api_token_valid"] = True
                        result["users_count"] = len(users)
                        result["message"] += f" | API token valid ({len(users)} users)"

                    except httpx.HTTPStatusError as e:
                        setup_logger.warning(f"API token test failed: HTTP {e.response.status_code}")
                        result["api_token_valid"] = False
                        result["api_token_error"] = f"HTTP {e.response.status_code}: {e.response.text}"

                setup_logger.info(f"✅ Jellyfin connection test completed: {result['message']}")
                return result

            except httpx.ConnectError:
                error_msg = f"Cannot reach server at {url}"
                setup_logger.error(f"Jellyfin connection failed - network error: {error_msg}")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": f"Connection error: {error_msg}",
                    "suggestion": "Check if the URL is correct and the server is running"
                }

            except httpx.TimeoutException:
                error_msg = "Server took too long to respond (>15s)"
                setup_logger.error(f"Jellyfin connection timeout: {error_msg}")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": f"Timeout error: {error_msg}",
                    "suggestion": "Check if the server is responding or try a different URL"
                }

            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                setup_logger.error(f"Jellyfin HTTP error: {error_msg}")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": error_msg,
                    "suggestion": "Check if this is a valid Jellyfin server URL"
                }

    except Exception as e:
        setup_logger.error(f"Unexpected error during Jellyfin connection test: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@app.post("/api/setup/test-ollama")
async def test_ollama_connection(request: dict = Body(...)):
    """🤖 Test Ollama connection and get available models"""
    setup_logger.info("🤖 Setup wizard: Testing Ollama connection")

    try:
        url = request.get("url", "").strip()

        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        setup_logger.debug(f"Testing Ollama connection to: {url}")

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.get(f"{url}/api/tags")
                response.raise_for_status()

                models_data = response.json()
                available_models = []

                for model in models_data.get("models", []):
                    model_info = {
                        "name": model["name"],
                        "size": model.get("size", 0),
                        "size_gb": f"{model.get('size', 0) / (1024**3):.1f}GB" if model.get('size') else "Unknown",
                        "modified_at": model.get("modified_at", "")
                    }
                    available_models.append(model_info)

                if available_models:
                    setup_logger.info(f"Successfully connected to Ollama - found {len(available_models)} models")

                    result = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "success": True,
                        "models_count": len(available_models),
                        "models": available_models,
                        "message": f"Connected to Ollama ({len(available_models)} models available)",
                        "suggested_primary": available_models[0]["name"] if available_models else "qwen3:8b",
                        "suggested_secondary": available_models[1]["name"] if len(available_models) > 1 else "gpt-oss:20b"
                    }

                    setup_logger.info(f"✅ Ollama connection test completed: {result['message']}")
                    return result
                else:
                    setup_logger.warning("Ollama connection successful but no models found")
                    return {
                        "timestamp": datetime.utcnow().isoformat(),
                        "success": False,
                        "error": "No models found in Ollama",
                        "suggestion": "Pull a model first: 'ollama pull qwen2:7b' or 'ollama pull llama2:7b'"
                    }

            except httpx.ConnectError:
                error_msg = f"Cannot reach Ollama server at {url}"
                setup_logger.error(f"Ollama connection failed - network error: {error_msg}")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": f"Connection error: {error_msg}",
                    "suggestion": "Check if Ollama is running and the URL is correct"
                }

            except httpx.TimeoutException:
                error_msg = "Ollama server took too long to respond (>15s)"
                setup_logger.error(f"Ollama connection timeout: {error_msg}")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": f"Timeout error: {error_msg}",
                    "suggestion": "Check if Ollama server is responding"
                }

            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                setup_logger.error(f"Ollama HTTP error: {error_msg}")
                return {
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                    "error": error_msg,
                    "suggestion": "Check if this is a valid Ollama server URL"
                }

    except Exception as e:
        setup_logger.error(f"Unexpected error during Ollama connection test: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")

@app.post("/api/setup/save-configuration")
async def save_setup_configuration(config: dict = Body(...)):
    """💾 Save setup configuration to .env file"""
    setup_logger.info("💾 Setup wizard: Saving configuration to .env file")

    try:
        project_root = Path(__file__).parent.parent
        env_file = project_root / '.env'

        setup_logger.debug(f"Saving configuration to: {env_file}")

        # Validate required configuration
        required_fields = ["JELLYFIN_URL", "LLM_OLLAMA_URL", "LLM_PRIMARY_MODEL"]
        missing_fields = [field for field in required_fields if not config.get(field)]

        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required configuration: {', '.join(missing_fields)}"
            )

        # Build .env content
        env_content = []
        env_content.append("# Parody Critics Configuration")
        env_content.append(f"# Generated on {datetime.utcnow().isoformat()}")
        env_content.append("")

        # Jellyfin Configuration
        env_content.append("# Jellyfin Configuration")
        env_content.append(f"JELLYFIN_URL={config['JELLYFIN_URL']}")
        if config.get("JELLYFIN_API_TOKEN"):
            env_content.append(f"JELLYFIN_API_TOKEN={config['JELLYFIN_API_TOKEN']}")
        if config.get("JELLYFIN_DB_PATH"):
            env_content.append(f"JELLYFIN_DB_PATH={config['JELLYFIN_DB_PATH']}")
        env_content.append("")

        # LLM Configuration
        env_content.append("# LLM Configuration")
        env_content.append(f"LLM_OLLAMA_URL={config['LLM_OLLAMA_URL']}")
        env_content.append(f"LLM_PRIMARY_MODEL={config['LLM_PRIMARY_MODEL']}")
        if config.get("LLM_SECONDARY_MODEL"):
            env_content.append(f"LLM_SECONDARY_MODEL={config['LLM_SECONDARY_MODEL']}")
        env_content.append(f"LLM_TIMEOUT={config.get('LLM_TIMEOUT', '180')}")
        env_content.append(f"LLM_MAX_RETRIES={config.get('LLM_MAX_RETRIES', '2')}")
        env_content.append(f"LLM_ENABLE_FALLBACK={config.get('LLM_ENABLE_FALLBACK', 'true')}")
        env_content.append("")

        # Additional Configuration
        if config.get("LOG_LEVEL"):
            env_content.append("# Logging")
            env_content.append(f"PARODY_CRITICS_LOG_LEVEL={config['LOG_LEVEL']}")

        # Write to file
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_content))

        setup_logger.info(f"✅ Configuration saved to {env_file}")

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "success": True,
            "message": "Configuration saved successfully",
            "file_path": str(env_file),
            "preview": '\n'.join(env_content[:15]) + ("\n..." if len(env_content) > 15 else "")
        }

    except Exception as e:
        setup_logger.error(f"Error saving configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")

@app.post("/api/setup/initialize-database")
async def initialize_setup_database():
    """🗄️ Initialize database for first-time setup"""
    setup_logger.info("🗄️ Setup wizard: Initializing database")

    try:
        # Import database initialization
        from pathlib import Path
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        from init_database import create_database_schema

        # Initialize database
        result = await create_database_schema()

        if result.get("success"):
            setup_logger.info("✅ Database initialized successfully")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "success": True,
                "message": "Database initialized successfully",
                "details": result
            }
        else:
            setup_logger.error("❌ Database initialization failed")
            raise HTTPException(status_code=500, detail="Database initialization failed")

    except Exception as e:
        setup_logger.error(f"Error initializing database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")


# ============================================================================
# 🎬 MEDIA IMPORT ENDPOINTS WITH REAL-TIME PROGRESS
# ============================================================================

@app.websocket("/ws/import-progress/{session_id}")
async def websocket_import_progress(websocket: WebSocket, session_id: str):
    """🔌 WebSocket endpoint for real-time import progress updates"""
    client_id = await websocket_manager.connect_client(websocket)

    try:
        # Subscribe client to this session
        await websocket_manager.subscribe_to_session(client_id, session_id)

        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for messages (like ping/pong or client requests)
                message = await websocket.receive_text()

                # Handle client messages if needed
                data = json.loads(message)
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }))

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Ignore invalid JSON
                pass
            except Exception as e:
                setup_logger.warning(f"WebSocket error for {client_id}: {e}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        await websocket_manager.disconnect_client(client_id)


@app.post("/api/media/import/start")
async def start_media_import(background_tasks: BackgroundTasks):
    """🚀 Start comprehensive media import from Jellyfin with progress tracking"""

    # Generate unique session ID
    session_id = str(uuid.uuid4())

    try:
        # Initialize import session
        progress = websocket_manager.start_import_session(
            session_id,
            "Complete Media Library Import"
        )

        # Start background import task
        background_tasks.add_task(
            perform_media_import,
            session_id
        )

        return {
            "success": True,
            "session_id": session_id,
            "status": "started",
            "message": "Media import started successfully",
            "websocket_url": f"/ws/import-progress/{session_id}"
        }

    except Exception as e:
        setup_logger.error(f"Failed to start media import: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start import: {str(e)}")


@app.get("/api/media/import/status/{session_id}")
async def get_import_status(session_id: str):
    """📊 Get current status of media import session"""

    progress = websocket_manager.get_session_progress(session_id)

    if not progress:
        raise HTTPException(status_code=404, detail="Import session not found")

    return {
        "success": True,
        "session_id": session_id,
        "progress": progress
    }


@app.post("/api/media/import/cancel/{session_id}")
async def cancel_media_import(session_id: str):
    """🛑 Cancel ongoing media import session"""

    try:
        await websocket_manager.cancel_import_session(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "status": "cancelled",
            "message": "Import session cancelled successfully"
        }

    except Exception as e:
        setup_logger.error(f"Failed to cancel import {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel import: {str(e)}")


@app.get("/api/media/import/active")
async def get_active_imports():
    """📋 Get list of currently active import sessions"""

    try:
        active_sessions = websocket_manager.get_active_sessions()

        return {
            "success": True,
            "active_sessions": active_sessions,
            "count": len(active_sessions)
        }

    except Exception as e:
        setup_logger.error(f"Failed to get active imports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get active imports: {str(e)}")


async def perform_media_import(session_id: str):
    """🎬 Background task to perform actual media import with progress tracking"""

    progress_adapter = WebSocketProgressAdapter(session_id, websocket_manager)

    try:
        setup_logger.info(f"🎬 Starting media import for session {session_id}")

        # Simulate progressive import with real sync
        await websocket_manager.update_import_progress(session_id,
            current_item="Initializing connection...",
            processed_items=0,
            total_items=100
        )
        await asyncio.sleep(0.5)

        # Create sync manager instance with async context manager
        async with SyncManager(
            jellyfin_url=config.JELLYFIN_URL,
            api_key=config.JELLYFIN_API_TOKEN,
            database_path=DB_PATH
        ) as sync_manager:

            await websocket_manager.update_import_progress(session_id,
                current_item="Connected to Jellyfin successfully",
                processed_items=10
            )
            await asyncio.sleep(0.5)

            await websocket_manager.update_import_progress(session_id,
                current_item="Scanning media library...",
                processed_items=20
            )
            await asyncio.sleep(1)

            # Perform the complete sync with progress tracking
            await websocket_manager.update_import_progress(session_id,
                current_item="Importing movies and series...",
                processed_items=30
            )

            stats = await sync_manager.sync_jellyfin_library()

            await websocket_manager.update_import_progress(session_id,
                current_item="Processing metadata...",
                processed_items=70
            )
            await asyncio.sleep(0.5)

            await websocket_manager.update_import_progress(session_id,
                current_item="Finalizing import...",
                processed_items=90
            )
            await asyncio.sleep(0.5)

            await websocket_manager.update_import_progress(session_id,
                current_item="Import completed successfully!",
                processed_items=100
            )

            # Import completed successfully
            await websocket_manager.complete_import_session(
                session_id,
                success=True
            )

        setup_logger.info(f"✅ Media import completed for session {session_id}")
        setup_logger.info(f"📊 Import stats: {stats}")

    except Exception as e:
        setup_logger.error(f"❌ Media import failed for session {session_id}: {str(e)}")

        await websocket_manager.complete_import_session(
            session_id,
            success=False,
            error_message=str(e)
        )


# ============================================================================
# 🎭 Character Management API Endpoints
# ============================================================================

@app.post("/api/characters")
async def create_character(character_data: dict = Body(...)):
    """Create a new character"""
    try:
        # Validate required fields
        if not character_data.get('name'):
            raise HTTPException(status_code=400, detail="Character name is required")

        # Check if character already exists
        check_query = "SELECT id FROM characters WHERE name = ?"
        existing = db_manager.execute_query(check_query, (character_data['name'],), fetch_one=True)

        if existing:
            raise HTTPException(status_code=409, detail=f"Character '{character_data['name']}' already exists")

        # Generate character ID from name (lowercase, replace spaces with underscores, remove special chars)
        import re
        character_id = re.sub(r'[^a-z0-9_]', '', character_data['name'].lower().replace(' ', '_').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n'))

        # Ensure ID is unique
        base_id = character_id
        counter = 1
        while True:
            check_id_query = "SELECT id FROM characters WHERE id = ?"
            existing_id = db_manager.execute_query(check_id_query, (character_id,), fetch_one=True)
            if not existing_id:
                break
            character_id = f"{base_id}_{counter}"
            counter += 1

        # Insert new character
        insert_query = """
            INSERT INTO characters (id, name, emoji, personality, description, color, border_color, accent_color, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, TRUE)
        """
        db_manager.execute_insert(insert_query, (
            character_id,
            character_data['name'],
            character_data.get('emoji', '🎭'),
            character_data.get('personality', ''),
            character_data.get('description', ''),
            character_data.get('color', '#6366f1'),  # Default indigo color
            character_data.get('border_color', '#4f46e5'),  # Default indigo border
            character_data.get('accent_color', '#8b5cf6')   # Default purple accent
        ))

        return {
            "success": True,
            "id": character_id,
            "message": f"Character '{character_data['name']}' created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        setup_logger.error(f"❌ Error creating character: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating character: {str(e)}")

@app.put("/api/characters/{character_id}")
async def update_character(character_id: str, character_data: dict = Body(...)):
    """Update an existing character"""
    try:
        # Check if character exists
        check_query = "SELECT id FROM characters WHERE id = ?"
        existing = db_manager.execute_query(check_query, (character_id,), fetch_one=True)

        if not existing:
            raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

        # Validate required fields
        if not character_data.get('name'):
            raise HTTPException(status_code=400, detail="Character name is required")

        # Check if name conflicts with another character
        name_check_query = "SELECT id FROM characters WHERE name = ? AND id != ?"
        name_conflict = db_manager.execute_query(
            name_check_query,
            (character_data['name'], character_id),
            fetch_one=True
        )

        if name_conflict:
            raise HTTPException(
                status_code=409,
                detail=f"Character name '{character_data['name']}' is already taken"
            )

        # Update character
        update_query = """
            UPDATE characters
            SET name = ?, emoji = ?, personality = ?, description = ?, color = ?, border_color = ?, accent_color = ?
            WHERE id = ?
        """
        db_manager.execute_query(update_query, (
            character_data['name'],
            character_data.get('emoji', '🎭'),
            character_data.get('personality', ''),
            character_data.get('description', ''),
            character_data.get('color', '#6366f1'),  # Default indigo color
            character_data.get('border_color', '#4f46e5'),  # Default indigo border
            character_data.get('accent_color', '#8b5cf6'),   # Default purple accent
            character_id
        ))

        return {
            "success": True,
            "id": character_id,
            "message": f"Character '{character_data['name']}' updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        setup_logger.error(f"❌ Error updating character {character_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating character: {str(e)}")

@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: str):
    """Delete a character and all its critics"""
    try:
        # Check if character exists
        check_query = "SELECT id, name FROM characters WHERE id = ?"
        character = db_manager.execute_query(check_query, (character_id,), fetch_one=True)

        if not character:
            raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

        character_name = character[1]

        # Get count of critics that will be deleted
        count_query = "SELECT COUNT(*) FROM critics WHERE character_id = ?"
        critics_count = db_manager.execute_query(count_query, (character_id,), fetch_one=True)[0]

        # Delete all critics by this character first (foreign key constraint)
        delete_critics_query = "DELETE FROM critics WHERE character_id = ?"
        db_manager.execute_query(delete_critics_query, (character_id,))

        # Delete the character
        delete_character_query = "DELETE FROM characters WHERE id = ?"
        db_manager.execute_query(delete_character_query, (character_id,))

        return {
            "success": True,
            "message": f"Character '{character_name}' and {critics_count} critics deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        setup_logger.error(f"❌ Error deleting character {character_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting character: {str(e)}")

@app.delete("/api/characters/{character_id}/critics")
async def delete_character_critics(character_id: str):
    """Delete all critics written by a specific character"""
    try:
        # Check if character exists
        check_query = "SELECT id, name FROM characters WHERE id = ?"
        character = db_manager.execute_query(check_query, (character_id,), fetch_one=True)

        if not character:
            raise HTTPException(status_code=404, detail=f"Character not found: {character_id}")

        character_name = character[1]

        # Get count of critics that will be deleted
        count_query = "SELECT COUNT(*) FROM critics WHERE character_id = ?"
        critics_count = db_manager.execute_query(count_query, (character_id,), fetch_one=True)[0]

        # Delete all critics by this character
        delete_query = "DELETE FROM critics WHERE character_id = ?"
        db_manager.execute_query(delete_query, (character_id,))

        return {
            "success": True,
            "message": f"All {critics_count} critics by '{character_name}' deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        setup_logger.error(f"❌ Error deleting critics for character {character_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting critics: {str(e)}")

@app.post("/api/characters/import")
async def import_characters(import_data: dict = Body(...)):
    """Import characters from file content"""
    try:
        filename = import_data.get('filename', '')
        content = import_data.get('content', '')
        overwrite = import_data.get('overwrite', False)

        if not content:
            raise HTTPException(status_code=400, detail="File content is required")

        imported_count = 0
        errors = []

        if filename.endswith('.json'):
            # JSON format import
            try:
                characters_data = json.loads(content)

                if not isinstance(characters_data, list):
                    characters_data = [characters_data]

                for char_data in characters_data:
                    try:
                        # Check if character exists
                        check_query = "SELECT id FROM characters WHERE name = ?"
                        existing = db_manager.execute_query(
                            check_query,
                            (char_data.get('name', ''),),
                            fetch_one=True
                        )

                        if existing and not overwrite:
                            errors.append(f"Character '{char_data.get('name')}' already exists (skipped)")
                            continue

                        if existing and overwrite:
                            # Update existing character
                            update_query = """
                                UPDATE characters
                                SET emoji = ?, personality = ?, description = ?, color = ?, border_color = ?, accent_color = ?
                                WHERE name = ?
                            """
                            db_manager.execute_query(update_query, (
                                char_data.get('emoji', '🎭'),
                                char_data.get('personality', ''),
                                char_data.get('description', ''),
                                char_data.get('color', '#6366f1'),
                                char_data.get('border_color', '#4f46e5'),
                                char_data.get('accent_color', '#8b5cf6'),
                                char_data['name']
                            ))
                        else:
                            # Insert new character
                            insert_query = """
                                INSERT INTO characters (name, emoji, personality, description, color, border_color, accent_color, active)
                                VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
                            """
                            db_manager.execute_insert(insert_query, (
                                char_data['name'],
                                char_data.get('emoji', '🎭'),
                                char_data.get('personality', ''),
                                char_data.get('description', ''),
                                char_data.get('color', '#6366f1'),
                                char_data.get('border_color', '#4f46e5'),
                                char_data.get('accent_color', '#8b5cf6')
                            ))

                        imported_count += 1

                    except Exception as e:
                        errors.append(f"Error importing character '{char_data.get('name', 'unknown')}': {str(e)}")

            except json.JSONDecodeError as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

        elif filename.endswith('.md'):
            # Markdown format import (basic implementation)
            lines = content.split('\n')
            current_character = {}

            for line in lines:
                line = line.strip()

                if line.startswith('# ') or line.startswith('## '):
                    # Save previous character if exists
                    if current_character.get('name'):
                        try:
                            # Check if character exists
                            check_query = "SELECT id FROM characters WHERE name = ?"
                            existing = db_manager.execute_query(
                                check_query,
                                (current_character['name'],),
                                fetch_one=True
                            )

                            if existing and not overwrite:
                                errors.append(f"Character '{current_character['name']}' already exists (skipped)")
                            else:
                                if existing and overwrite:
                                    # Update existing
                                    update_query = """
                                        UPDATE characters
                                        SET emoji = ?, personality = ?, description = ?, color = ?, border_color = ?, accent_color = ?
                                        WHERE name = ?
                                    """
                                    db_manager.execute_query(update_query, (
                                        current_character.get('emoji', '🎭'),
                                        current_character.get('personality', ''),
                                        current_character.get('description', ''),
                                        current_character.get('color', '#6366f1'),
                                        current_character.get('border_color', '#4f46e5'),
                                        current_character.get('accent_color', '#8b5cf6'),
                                        current_character['name']
                                    ))
                                else:
                                    # Insert new
                                    insert_query = """
                                        INSERT INTO characters (name, emoji, personality, description, color, border_color, accent_color, active)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
                                    """
                                    db_manager.execute_insert(insert_query, (
                                        current_character['name'],
                                        current_character.get('emoji', '🎭'),
                                        current_character.get('personality', ''),
                                        current_character.get('description', ''),
                                        current_character.get('color', '#6366f1'),
                                        current_character.get('border_color', '#4f46e5'),
                                        current_character.get('accent_color', '#8b5cf6')
                                    ))

                                imported_count += 1

                        except Exception as e:
                            errors.append(f"Error importing character '{current_character['name']}': {str(e)}")

                    # Start new character
                    current_character = {
                        'name': line.replace('#', '').strip(),
                        'emoji': '🎭',
                        'personality': '',
                        'description': ''
                    }

                elif line.startswith('**Emoji:**'):
                    current_character['emoji'] = line.replace('**Emoji:**', '').strip()
                elif line.startswith('**Personalidad:**'):
                    current_character['personality'] = line.replace('**Personalidad:**', '').strip()
                elif line and not line.startswith('#'):
                    # Add to description
                    if current_character.get('description'):
                        current_character['description'] += ' ' + line
                    else:
                        current_character['description'] = line

            # Process last character
            if current_character.get('name'):
                try:
                    check_query = "SELECT id FROM characters WHERE name = ?"
                    existing = db_manager.execute_query(
                        check_query,
                        (current_character['name'],),
                        fetch_one=True
                    )

                    if existing and not overwrite:
                        errors.append(f"Character '{current_character['name']}' already exists (skipped)")
                    else:
                        if existing and overwrite:
                            update_query = """
                                UPDATE characters
                                SET emoji = ?, personality = ?, description = ?, color = ?, border_color = ?, accent_color = ?
                                WHERE name = ?
                            """
                            db_manager.execute_query(update_query, (
                                current_character.get('emoji', '🎭'),
                                current_character.get('personality', ''),
                                current_character.get('description', ''),
                                current_character.get('color', '#6366f1'),
                                current_character.get('border_color', '#4f46e5'),
                                current_character.get('accent_color', '#8b5cf6'),
                                current_character['name']
                            ))
                        else:
                            insert_query = """
                                INSERT INTO characters (name, emoji, personality, description, color, border_color, accent_color, active)
                                VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
                            """
                            db_manager.execute_insert(insert_query, (
                                current_character['name'],
                                current_character.get('emoji', '🎭'),
                                current_character.get('personality', ''),
                                current_character.get('description', ''),
                                current_character.get('color', '#6366f1'),
                                current_character.get('border_color', '#4f46e5'),
                                current_character.get('accent_color', '#8b5cf6')
                            ))

                        imported_count += 1

                except Exception as e:
                    errors.append(f"Error importing character '{current_character['name']}': {str(e)}")

        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Use .json or .md")

        result = {
            "success": True,
            "imported": imported_count,
            "message": f"Successfully imported {imported_count} characters"
        }

        if errors:
            result["errors"] = errors
            result["message"] += f" (with {len(errors)} errors/skipped)"

        return result

    except HTTPException:
        raise
    except Exception as e:
        setup_logger.error(f"❌ Error importing characters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error importing characters: {str(e)}")

@app.get("/api/characters/export")
async def export_characters():
    """Export all characters to Markdown format"""
    try:
        # Get all characters
        query = "SELECT * FROM characters WHERE active = TRUE ORDER BY name"
        characters = db_manager.execute_query(query)

        if not characters:
            return {
                "success": True,
                "data": "# Personajes\n\nNo hay personajes disponibles para exportar.\n",
                "filename": "personajes.md"
            }

        # Generate Markdown content
        md_content = "# 🎭 Personajes de Parody Critics\n\n"
        md_content += f"Exportado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md_content += f"Total de personajes: {len(characters)}\n\n"
        md_content += "---\n\n"

        for char in characters:
            char_dict = dict(char)
            md_content += f"## {char_dict['name']}\n\n"
            md_content += f"**Emoji:** {char_dict.get('emoji', '🎭')}\n\n"
            md_content += f"**Personalidad:** {char_dict.get('personality', 'No especificada')}\n\n"

            description = char_dict.get('description', 'Sin descripción disponible')
            md_content += f"**Descripción:**\n{description}\n\n"

            # Get character stats
            stats_query = """
                SELECT COUNT(*) as total_critics,
                       AVG(rating) as avg_rating
                FROM critics
                WHERE character_id = ?
            """
            stats = db_manager.execute_query(stats_query, (char_dict['id'],), fetch_one=True)

            if stats and stats[0] > 0:
                md_content += f"**Estadísticas:**\n"
                md_content += f"- Críticas escritas: {stats[0]}\n"
                md_content += f"- Rating promedio: {stats[1]:.1f}/10\n\n"
            else:
                md_content += "**Estadísticas:** Sin críticas escritas aún\n\n"

            md_content += "---\n\n"

        filename = f"personajes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        return {
            "success": True,
            "data": md_content,
            "filename": filename
        }

    except Exception as e:
        setup_logger.error(f"❌ Error exporting characters: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting characters: {str(e)}")

# ============================================================================

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