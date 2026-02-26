"""
Pydantic models for the Parody Critics API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

class MediaType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"

class SyncStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

# Request/Response Models

class CriticResponse(BaseModel):
    """Single critic review response"""
    critic_id: Optional[int] = None
    character_id: str
    author: str
    emoji: str
    rating: int = Field(ge=1, le=10)
    content: str
    personality: str
    generated_at: datetime
    color: str
    border_color: str
    accent_color: str

class CriticsResponse(BaseModel):
    """Multiple critics for a media item"""
    tmdb_id: str
    title: str
    year: Optional[int]
    type: MediaType
    critics: Dict[str, CriticResponse]
    total_critics: int

class MediaInfo(BaseModel):
    """Media information response"""
    id: int
    tmdb_id: str
    jellyfin_id: str
    title: str
    original_title: Optional[str]
    year: Optional[int]
    type: MediaType
    genres: Optional[List[str]]
    overview: Optional[str]
    poster_url: Optional[str]
    imdb_id: Optional[str]
    vote_average: Optional[float]
    has_critics: bool
    critics_count: int
    created_at: datetime

class CharacterInfo(BaseModel):
    """Character information"""
    id: str
    name: str
    emoji: str
    color: str
    personality: str
    description: str
    active: bool
    total_reviews: Optional[int] = 0
    avg_rating: Optional[float] = None

class StatsResponse(BaseModel):
    """API statistics response"""
    total_media: int
    total_movies: int
    total_series: int
    total_critics: int
    active_characters: int
    media_without_critics: int
    last_media_sync: Optional[datetime]
    last_critic_generation: Optional[datetime]

class SyncLogEntry(BaseModel):
    """Sync operation log entry"""
    id: int
    sync_type: str
    total_processed: int
    total_success: int
    total_errors: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: SyncStatus
    error_message: Optional[str]

class GenerationRequest(BaseModel):
    """Request to generate critics for specific media"""
    tmdb_id: Optional[str] = None
    jellyfin_id: Optional[str] = None
    character_ids: Optional[List[str]] = None
    force_regenerate: bool = False

class GenerationResponse(BaseModel):
    """Response from critic generation"""
    success: bool
    message: str
    generated_count: int
    skipped_count: int
    error_count: int
    details: Optional[Dict] = None

# Database Models (for internal use)

class MediaDB(BaseModel):
    """Internal media model matching database schema"""
    id: Optional[int] = None
    tmdb_id: str
    jellyfin_id: str
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    type: MediaType
    genres: Optional[str] = None  # JSON string
    overview: Optional[str] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    imdb_id: Optional[str] = None
    runtime: Optional[int] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class CriticDB(BaseModel):
    """Internal critic model matching database schema"""
    id: Optional[int] = None
    media_id: int
    character_id: str
    rating: int = Field(ge=1, le=10)
    content: str
    preview_length: int = 300
    generated_at: Optional[datetime] = None
    generation_model: Optional[str] = None
    generation_prompt: Optional[str] = None
    tokens_used: Optional[int] = None

class CharacterDB(BaseModel):
    """Internal character model matching database schema"""
    id: str
    name: str
    emoji: str
    color: str
    border_color: str
    accent_color: str
    personality: str
    description: str
    prompt_template: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None