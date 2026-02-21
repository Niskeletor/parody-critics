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
from datetime import datetime

from models.schemas import (
    CriticsResponse, CriticResponse, MediaInfo, CharacterInfo,
    StatsResponse, GenerationRequest, GenerationResponse,
    MediaType, SyncLogEntry
)
from config import get_config
from api.jellyfin_sync import JellyfinSyncManager
from api.llm_manager import CriticGenerationManager

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

    # Valid characters
    valid_characters = ["Marco Aurelio", "Rosario Costras"]
    if character not in valid_characters:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid character. Must be one of: {', '.join(valid_characters)}"
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

    # Valid characters
    valid_characters = ["Marco Aurelio", "Rosario Costras"]
    if character not in valid_characters:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid character. Must be one of: {', '.join(valid_characters)}"
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