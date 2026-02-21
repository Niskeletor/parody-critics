"""
🎭 Parody Critics - Jellyfin Hybrid Synchronization Manager
Combines database-first bulk operations with API validation for optimal performance

Author: SAL-9000
"""

import httpx
import sqlite3
import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class MediaType(Enum):
    MOVIE = "movie"
    SERIES = "series"
    EPISODE = "episode"

@dataclass
class MediaItem:
    """Represents a media item from Jellyfin"""
    id: str
    name: str
    type: MediaType
    tmdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    year: Optional[int] = None
    overview: Optional[str] = None
    genres: Optional[str] = None
    path: Optional[str] = None
    date_created: Optional[str] = None
    date_modified: Optional[str] = None

@dataclass
class SyncProgress:
    """Tracks synchronization progress"""
    sync_id: str
    status: SyncStatus
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    current_item: Optional[str] = None

class JellyfinSyncManager:
    """Hybrid synchronization manager for Jellyfin data"""

    def __init__(self, jellyfin_url: str, api_token: str, jellyfin_db_path: str, local_db_path: str):
        self.jellyfin_url = jellyfin_url.rstrip('/')
        self.api_token = api_token
        self.jellyfin_db_path = jellyfin_db_path
        self.local_db_path = local_db_path

        # API headers
        self.headers = {
            "Authorization": f'MediaBrowser Client="Parody Critics Sync", Device="SyncManager", DeviceId="sync-1", Version="1.0.0", Token="{api_token}"',
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Sync state
        self.current_sync: Optional[SyncProgress] = None

    def get_local_db_connection(self) -> sqlite3.Connection:
        """Get connection to local Parody Critics database"""
        conn = sqlite3.connect(self.local_db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def get_jellyfin_db_connection(self) -> sqlite3.Connection:
        """Get connection to Jellyfin database (read-only)"""
        conn = sqlite3.connect(f"file:{self.jellyfin_db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    async def get_jellyfin_users(self) -> List[Dict[str, Any]]:
        """Get Jellyfin users via API"""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                response = await client.get(f"{self.jellyfin_url}/Users")
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get users: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"API error getting users: {e}")
            return []

    def extract_media_from_jellyfin_db(self, limit: Optional[int] = None, offset: int = 0) -> List[MediaItem]:
        """Extract media items directly from Jellyfin database"""
        logger.info(f"Extracting media from Jellyfin DB (limit: {limit}, offset: {offset})")

        try:
            with self.get_jellyfin_db_connection() as conn:
                cursor = conn.cursor()

                # Complex query to get movies and series with provider IDs
                query = """
                SELECT
                    b.Id,
                    b.Name,
                    b.Type,
                    b.ProductionYear,
                    b.Overview,
                    b.Genres,
                    b.Path,
                    b.DateCreated,
                    b.DateModified,
                    GROUP_CONCAT(
                        CASE
                            WHEN p.ProviderId = 'Tmdb' THEN 'tmdb:' || p.ProviderValue
                            WHEN p.ProviderId = 'Imdb' THEN 'imdb:' || p.ProviderValue
                            WHEN p.ProviderId = 'Tvdb' THEN 'tvdb:' || p.ProviderValue
                        END, '|'
                    ) as provider_ids
                FROM BaseItems b
                LEFT JOIN BaseItemProviders p ON b.Id = p.ItemId
                    AND p.ProviderId IN ('Tmdb', 'Imdb', 'Tvdb')
                WHERE b.Type IN (
                    'MediaBrowser.Controller.Entities.Movies.Movie',
                    'MediaBrowser.Controller.Entities.TV.Series'
                )
                    AND b.Name IS NOT NULL
                    AND LENGTH(TRIM(b.Name)) > 0
                GROUP BY b.Id, b.Name, b.Type, b.ProductionYear, b.Overview, b.Genres, b.Path, b.DateCreated, b.DateModified
                ORDER BY b.DateCreated DESC
                """

                params = []
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                    if offset:
                        query += " OFFSET ?"
                        params.append(offset)

                cursor.execute(query, params)
                rows = cursor.fetchall()

                media_items = []
                for row in rows:
                    row_dict = dict(row)

                    # Parse provider IDs
                    tmdb_id = None
                    imdb_id = None
                    tvdb_id = None

                    if row_dict['provider_ids']:
                        providers = row_dict['provider_ids'].split('|')
                        for provider in providers:
                            if provider and ':' in provider:
                                provider_type, provider_value = provider.split(':', 1)
                                if provider_type == 'tmdb':
                                    tmdb_id = provider_value
                                elif provider_type == 'imdb':
                                    imdb_id = provider_value
                                elif provider_type == 'tvdb':
                                    tvdb_id = provider_value

                    # Determine media type
                    media_type = MediaType.MOVIE if 'Movie' in row_dict['Type'] else MediaType.SERIES

                    media_item = MediaItem(
                        id=row_dict['Id'],
                        name=row_dict['Name'],
                        type=media_type,
                        tmdb_id=tmdb_id,
                        imdb_id=imdb_id,
                        tvdb_id=tvdb_id,
                        year=row_dict['ProductionYear'],
                        overview=row_dict['Overview'],
                        genres=row_dict['Genres'],
                        path=row_dict['Path'],
                        date_created=row_dict['DateCreated'],
                        date_modified=row_dict['DateModified']
                    )

                    media_items.append(media_item)

                logger.info(f"Extracted {len(media_items)} media items from Jellyfin DB")
                return media_items

        except Exception as e:
            logger.error(f"Error extracting from Jellyfin DB: {e}")
            return []

    def get_media_count_from_jellyfin_db(self) -> Dict[str, int]:
        """Get total media counts from Jellyfin database"""
        try:
            with self.get_jellyfin_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT
                        CASE
                            WHEN Type = 'MediaBrowser.Controller.Entities.Movies.Movie' THEN 'movies'
                            WHEN Type = 'MediaBrowser.Controller.Entities.TV.Series' THEN 'series'
                        END as media_type,
                        COUNT(*) as count
                    FROM BaseItems
                    WHERE Type IN (
                        'MediaBrowser.Controller.Entities.Movies.Movie',
                        'MediaBrowser.Controller.Entities.TV.Series'
                    )
                        AND Name IS NOT NULL
                        AND LENGTH(TRIM(Name)) > 0
                    GROUP BY Type
                """)

                results = cursor.fetchall()
                counts = {row[0]: row[1] for row in results}

                # Add total count
                counts['total'] = sum(counts.values())

                return counts

        except Exception as e:
            logger.error(f"Error getting media counts: {e}")
            return {'movies': 0, 'series': 0, 'total': 0}

    def sync_media_to_local_db(self, media_items: List[MediaItem]) -> Tuple[int, int]:
        """Sync media items to local database"""
        successful = 0
        failed = 0

        try:
            with self.get_local_db_connection() as conn:
                cursor = conn.cursor()

                for item in media_items:
                    try:
                        # Insert or update media in local database
                        cursor.execute("""
                            INSERT OR REPLACE INTO media (
                                jellyfin_id, tmdb_id, title, year, type,
                                overview, genres, path, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            item.id,
                            item.tmdb_id,
                            item.name,
                            item.year,
                            item.type.value,
                            item.overview,
                            item.genres,
                            item.path,
                            datetime.now().isoformat()
                        ))

                        successful += 1

                    except Exception as e:
                        logger.error(f"Failed to sync item {item.name}: {e}")
                        failed += 1

                conn.commit()

        except Exception as e:
            logger.error(f"Database sync error: {e}")
            return 0, len(media_items)

        return successful, failed

    async def start_sync(self, sync_type: str = "full", batch_size: int = 100) -> str:
        """Start synchronization process"""
        sync_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize progress tracking
        self.current_sync = SyncProgress(
            sync_id=sync_id,
            status=SyncStatus.RUNNING,
            start_time=datetime.now(timezone.utc)
        )

        try:
            # Log sync start
            logger.info(f"Starting sync {sync_id} (type: {sync_type})")
            self._log_sync_start(sync_id, sync_type)

            # Get total counts
            counts = self.get_media_count_from_jellyfin_db()
            self.current_sync.total_items = counts['total']

            logger.info(f"Found {counts['total']} total items ({counts.get('movies', 0)} movies, {counts.get('series', 0)} series)")

            # Process in batches
            offset = 0
            total_successful = 0
            total_failed = 0

            while offset < self.current_sync.total_items:
                # Update current progress
                self.current_sync.current_item = f"Processing batch {offset//batch_size + 1}"

                # Extract batch from Jellyfin DB
                media_batch = self.extract_media_from_jellyfin_db(
                    limit=batch_size,
                    offset=offset
                )

                if not media_batch:
                    break

                # Sync batch to local DB
                successful, failed = self.sync_media_to_local_db(media_batch)

                total_successful += successful
                total_failed += failed

                self.current_sync.processed_items = offset + len(media_batch)
                self.current_sync.successful_items = total_successful
                self.current_sync.failed_items = total_failed

                logger.info(f"Batch complete: {successful}/{len(media_batch)} successful, {failed} failed")

                offset += batch_size

                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.1)

            # Complete sync
            self.current_sync.status = SyncStatus.COMPLETED
            self.current_sync.end_time = datetime.now(timezone.utc)

            duration = (self.current_sync.end_time - self.current_sync.start_time).total_seconds()

            logger.info(f"Sync {sync_id} completed in {duration:.2f}s: {total_successful} successful, {total_failed} failed")

            # Log sync completion
            self._log_sync_completion(sync_id, total_successful, total_failed, duration)

            return sync_id

        except Exception as e:
            logger.error(f"Sync {sync_id} failed: {e}")
            if self.current_sync:
                self.current_sync.status = SyncStatus.FAILED
                self.current_sync.error_message = str(e)
                self.current_sync.end_time = datetime.now(timezone.utc)

            self._log_sync_error(sync_id, str(e))
            raise

    def _log_sync_start(self, sync_id: str, sync_type: str):
        """Log sync start to database"""
        try:
            with self.get_local_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sync_log (sync_id, operation, status, started_at)
                    VALUES (?, ?, ?, ?)
                """, (sync_id, sync_type, 'running', datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log sync start: {e}")

    def _log_sync_completion(self, sync_id: str, successful: int, failed: int, duration: float):
        """Log sync completion to database"""
        try:
            with self.get_local_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_log
                    SET status = ?, completed_at = ?, items_processed = ?,
                        items_successful = ?, items_failed = ?, duration = ?
                    WHERE sync_id = ?
                """, (
                    'completed',
                    datetime.now().isoformat(),
                    successful + failed,
                    successful,
                    failed,
                    duration,
                    sync_id
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log sync completion: {e}")

    def _log_sync_error(self, sync_id: str, error: str):
        """Log sync error to database"""
        try:
            with self.get_local_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sync_log
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE sync_id = ?
                """, ('failed', datetime.now().isoformat(), error, sync_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log sync error: {e}")

    def get_sync_progress(self) -> Optional[Dict[str, Any]]:
        """Get current sync progress"""
        if not self.current_sync:
            return None

        progress_dict = asdict(self.current_sync)

        # Calculate completion percentage
        if self.current_sync.total_items > 0:
            progress_dict['completion_percent'] = (
                self.current_sync.processed_items / self.current_sync.total_items * 100
            )
        else:
            progress_dict['completion_percent'] = 0

        # Format timestamps
        if self.current_sync.start_time:
            progress_dict['start_time'] = self.current_sync.start_time.isoformat()
        if self.current_sync.end_time:
            progress_dict['end_time'] = self.current_sync.end_time.isoformat()

        # Convert enum to string
        progress_dict['status'] = self.current_sync.status.value

        return progress_dict

    def cancel_sync(self) -> bool:
        """Cancel current synchronization"""
        if self.current_sync and self.current_sync.status == SyncStatus.RUNNING:
            self.current_sync.status = SyncStatus.CANCELLED
            self.current_sync.end_time = datetime.now(timezone.utc)
            logger.info(f"Sync {self.current_sync.sync_id} cancelled")
            return True
        return False