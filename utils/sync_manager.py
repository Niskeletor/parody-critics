#!/usr/bin/env python3
"""
🎭 Parody Critics - Synchronization Manager
Main sync orchestrator that coordinates Jellyfin API, database operations, and progress display
"""

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from .jellyfin_client import JellyfinClient, extract_media_info, JellyfinAPIError
from .sync_progress import SyncProgressDisplay, ProgressCallback, create_sync_progress
from .logger import get_logger, LogTimer, log_exception

logger = get_logger('sync_manager')


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class SyncManager:
    """
    Coordinates synchronization between Jellyfin and local database

    Features:
    - Async Jellyfin API integration
    - SQLite database operations
    - Real-time progress tracking
    - Error handling and recovery
    - Incremental sync support
    - Media metadata extraction
    """

    def __init__(
        self,
        jellyfin_url: str,
        api_key: str,
        database_path: str = "database/critics.db",
        user_id: Optional[str] = None,
        progress_display: Optional[SyncProgressDisplay] = None
    ):
        """
        Initialize sync manager

        Args:
            jellyfin_url: Jellyfin server URL
            api_key: Jellyfin API key
            database_path: Path to SQLite database
            user_id: Jellyfin user ID (optional)
            progress_display: Progress display instance (creates new if None)
        """
        self.jellyfin_url = jellyfin_url
        self.api_key = api_key
        self.database_path = Path(database_path)
        self.user_id = user_id
        self.progress_display = progress_display or create_sync_progress()

        # Initialize components
        self.jellyfin_client: Optional[JellyfinClient] = None
        self.db_connection: Optional[sqlite3.Connection] = None

        # Sync state
        self.existing_jellyfin_ids: Set[str] = set()
        self.sync_session_id: Optional[str] = None

        logger.info(f"Initialized sync manager - Jellyfin: {jellyfin_url}, DB: {database_path}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self):
        """Initialize connections to Jellyfin and database"""
        logger.info("Establishing connections")

        try:
            with LogTimer(logger, "Database connection"):
                await self._connect_database()

            with LogTimer(logger, "Jellyfin connection"):
                await self._connect_jellyfin()

            # Load existing Jellyfin IDs for incremental sync
            self.existing_jellyfin_ids = await self._load_existing_jellyfin_ids()
            logger.info(f"Loaded {len(self.existing_jellyfin_ids)} existing Jellyfin IDs")

        except Exception as e:
            logger.error(f"Failed to establish connections: {str(e)}")
            await self.disconnect()
            raise

    async def disconnect(self):
        """Close all connections"""
        logger.info("Closing connections")

        if self.jellyfin_client:
            await self.jellyfin_client.close()
            self.jellyfin_client = None

        if self.db_connection:
            self.db_connection.close()
            self.db_connection = None

    async def _connect_database(self):
        """Connect to SQLite database"""
        # Ensure database directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.db_connection = sqlite3.connect(
            str(self.database_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.db_connection.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        self.db_connection.execute("PRAGMA journal_mode=WAL")
        self.db_connection.commit()

        logger.debug(f"Connected to database: {self.database_path}")

    async def _connect_jellyfin(self):
        """Connect to Jellyfin server"""
        self.jellyfin_client = JellyfinClient(
            base_url=self.jellyfin_url,
            api_key=self.api_key,
            user_id=self.user_id,
            timeout=30,
            max_retries=3,
            enable_cache=True
        )

        await self.jellyfin_client.connect()
        logger.info(f"Connected to Jellyfin: {self.jellyfin_client.server_info}")

    async def _load_existing_jellyfin_ids(self) -> Set[str]:
        """Load existing Jellyfin IDs from database"""
        try:
            cursor = self.db_connection.execute(
                "SELECT jellyfin_id FROM media WHERE jellyfin_id IS NOT NULL"
            )
            return {row['jellyfin_id'] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"Failed to load existing Jellyfin IDs: {str(e)}")
            return set()

    def _create_sync_log_entry(self, operation: str, status: str = "started") -> str:
        """Create sync log entry and return session ID"""
        session_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            self.db_connection.execute(
                """
                INSERT INTO sync_log (session_id, operation, status, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, operation, status, datetime.now())
            )
            self.db_connection.commit()
            logger.debug(f"Created sync log entry: {session_id}")
            return session_id

        except sqlite3.Error as e:
            logger.error(f"Failed to create sync log entry: {str(e)}")
            return session_id  # Return ID anyway for consistency

    def _update_sync_log(self, session_id: str, status: str, items_processed: int = 0,
                        items_added: int = 0, items_updated: int = 0, error_message: Optional[str] = None):
        """Update sync log entry with results"""
        try:
            self.db_connection.execute(
                """
                UPDATE sync_log
                SET status = ?, completed_at = ?, items_processed = ?,
                    items_added = ?, items_updated = ?, error_message = ?
                WHERE session_id = ?
                """,
                (status, datetime.now(), items_processed, items_added, items_updated,
                 error_message, session_id)
            )
            self.db_connection.commit()
            logger.debug(f"Updated sync log: {session_id} -> {status}")

        except sqlite3.Error as e:
            logger.error(f"Failed to update sync log: {str(e)}")

    async def _upsert_media_item(self, media_info: Dict) -> Tuple[bool, bool]:
        """
        Insert or update media item in database

        Args:
            media_info: Extracted media information

        Returns:
            Tuple of (was_inserted, was_updated)
        """
        try:
            # Skip items with no TMDB ID (personal content, unidentified files)
            if not media_info.get('tmdb_id'):
                return False, False

            # Check if item exists by jellyfin_id
            cursor = self.db_connection.execute(
                "SELECT id FROM media WHERE jellyfin_id = ?",
                (media_info['jellyfin_id'],)
            )
            existing = cursor.fetchone()

            # Also check for duplicate tmdb_id with a different jellyfin_id
            # (same movie in multiple languages/editions in Jellyfin)
            if not existing:
                cursor = self.db_connection.execute(
                    "SELECT id FROM media WHERE tmdb_id = ?",
                    (media_info['tmdb_id'],)
                )
                if cursor.fetchone():
                    return False, False  # Already imported under a different jellyfin_id

            if existing:
                # Update existing item
                self.db_connection.execute(
                    """
                    UPDATE media SET
                        tmdb_id = ?, imdb_id = ?, title = ?, original_title = ?,
                        year = ?, type = ?, genres = ?, overview = ?,
                        runtime = ?, vote_average = ?, updated_at = ?
                    WHERE jellyfin_id = ?
                    """,
                    (
                        media_info['tmdb_id'], media_info['imdb_id'], media_info['title'],
                        media_info['original_title'], media_info['year'], media_info['type'],
                        media_info['genres'], media_info['overview'], media_info['runtime'],
                        media_info['vote_average'], datetime.now(), media_info['jellyfin_id']
                    )
                )
                self.db_connection.commit()
                return False, True  # Not inserted, but updated

            else:
                # Insert new item
                self.db_connection.execute(
                    """
                    INSERT INTO media (
                        jellyfin_id, tmdb_id, imdb_id, title, original_title,
                        year, type, genres, overview, runtime, vote_average,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        media_info['jellyfin_id'], media_info['tmdb_id'], media_info['imdb_id'],
                        media_info['title'], media_info['original_title'], media_info['year'],
                        media_info['type'], media_info['genres'], media_info['overview'],
                        media_info['runtime'], media_info['vote_average'],
                        datetime.now(), datetime.now()
                    )
                )
                self.db_connection.commit()
                return True, False  # Inserted, not updated

        except sqlite3.Error as e:
            logger.error(f"Database error upserting media item: {str(e)}")
            raise DatabaseError(f"Failed to save media item: {str(e)}")

    async def sync_jellyfin_library(
        self,
        library_id: Optional[str] = None,
        item_types: Optional[List[str]] = None,
        page_size: int = 100,
        ws_progress_callback=None,
        ws_error_callback=None
    ) -> Dict[str, Any]:
        """
        Synchronize Jellyfin library with local database

        Args:
            library_id: Specific library ID to sync (None for all)
            item_types: Filter by item types (['Movie', 'Series'])
            page_size: Items per page for pagination

        Returns:
            Sync results summary
        """
        operation = "Jellyfin Library Sync"
        if library_id:
            operation += f" (Library: {library_id})"

        logger.info(f"Starting {operation}")

        # Create sync log entry
        self.sync_session_id = self._create_sync_log_entry(operation)

        # Default to movies and series
        if item_types is None:
            item_types = ['Movie', 'Series']

        try:
            with self.progress_display.sync_session(operation) as progress:
                # Create progress callback
                progress_callback = ProgressCallback(progress)

                # Get items from Jellyfin with pagination
                items_processed = 0
                items_added = 0
                items_updated = 0
                items_unchanged = 0
                errors = 0

                logger.info(f"Fetching items from Jellyfin - Types: {item_types}")

                async for item_data, current_page, total_pages in self.jellyfin_client.get_movies_and_series(
                    fields=[
                        'Overview', 'Genres', 'ProductionYear', 'PremiereDate',
                        'CommunityRating', 'OfficialRating', 'RunTimeTicks',
                        'ProviderIds', 'MediaSources', 'Path'
                    ],
                    page_size=page_size,
                    progress_callback=progress_callback
                ):
                    try:
                        # Set total on first item
                        if items_processed == 0:
                            # We can't know exact total until we see the pagination info
                            # The progress callback will handle page-level updates
                            pass

                        # Extract media information
                        media_info = extract_media_info(item_data)
                        item_title = media_info['title'] or f"Item {media_info['jellyfin_id']}"

                        # Upsert to database
                        was_inserted, was_updated = await self._upsert_media_item(media_info)

                        # Update counters and progress
                        items_processed += 1
                        if was_inserted:
                            items_added += 1
                            progress.record_new_item(item_title)
                        elif was_updated:
                            items_updated += 1
                            progress.record_updated_item(item_title)
                        else:
                            items_unchanged += 1
                            progress.record_unchanged_item(item_title)

                        # Report real-time progress via WebSocket callback
                        if ws_progress_callback:
                            try:
                                estimated_total = max(total_pages * page_size, items_processed)
                                await ws_progress_callback(
                                    items_processed, estimated_total, item_title,
                                    items_added, items_updated, items_unchanged, errors
                                )
                            except Exception:
                                pass  # Don't let WebSocket errors break the sync

                        # Log progress periodically
                        if items_processed % 25 == 0:
                            logger.debug(f"Processed {items_processed} items")

                    except Exception as e:
                        errors += 1
                        failed_item = item_data.get('Name', 'Unknown')
                        error_msg = f"Failed to process item: {str(e)}"
                        logger.error(f"{error_msg} - Item: {failed_item}")
                        log_exception(logger, e, f"Processing item {item_data.get('Id', 'unknown')}")
                        progress.record_error(error_msg, failed_item)
                        if ws_error_callback:
                            try:
                                await ws_error_callback(failed_item, str(e))
                            except Exception:
                                pass

                # Update final totals in progress display
                if items_processed > 0:
                    progress.set_total_items(items_processed)

                # Create results summary
                results = {
                    'session_id': self.sync_session_id,
                    'operation': operation,
                    'status': 'completed' if errors == 0 else 'completed_with_errors',
                    'items_processed': items_processed,
                    'items_added': items_added,
                    'items_updated': items_updated,
                    'items_unchanged': items_unchanged,
                    'errors': errors,
                    'jellyfin_server': self.jellyfin_client.server_info.get('ServerName', 'Unknown'),
                    'start_time': progress.stats.start_time.isoformat() if progress.stats.start_time else None
                }

                # Update sync log with final results
                self._update_sync_log(
                    self.sync_session_id,
                    results['status'],
                    items_processed,
                    items_added,
                    items_updated
                )

                logger.info(f"Sync completed - Processed: {items_processed}, Added: {items_added}, "
                          f"Updated: {items_updated}, Errors: {errors}")

                return results

        except JellyfinAPIError as e:
            error_msg = f"Jellyfin API error: {str(e)}"
            logger.error(error_msg)
            self._update_sync_log(self.sync_session_id, "failed", error_message=error_msg)
            raise

        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg)
            log_exception(logger, e, "Jellyfin library sync")
            self._update_sync_log(self.sync_session_id, "failed", error_message=error_msg)
            raise

    async def get_sync_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent sync history from database

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of sync log entries
        """
        try:
            cursor = self.db_connection.execute(
                """
                SELECT session_id, operation, status, started_at, completed_at,
                       items_processed, items_added, items_updated, error_message
                FROM sync_log
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,)
            )

            return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Failed to get sync history: {str(e)}")
            return []

    async def cleanup_orphaned_media(self) -> int:
        """
        Remove media items from database that no longer exist in Jellyfin

        Returns:
            Number of items removed
        """
        logger.info("Starting cleanup of orphaned media items")

        try:
            # Get all current Jellyfin IDs
            current_ids = set()
            async for item_data, _, _ in self.jellyfin_client.get_movies_and_series(page_size=1000):
                current_ids.add(item_data['Id'])

            # Find items in database that don't exist in Jellyfin
            cursor = self.db_connection.execute(
                "SELECT jellyfin_id FROM media WHERE jellyfin_id IS NOT NULL"
            )
            db_ids = {row['jellyfin_id'] for row in cursor.fetchall()}

            orphaned_ids = db_ids - current_ids

            if orphaned_ids:
                # Remove orphaned items
                placeholders = ','.join('?' * len(orphaned_ids))
                cursor = self.db_connection.execute(
                    f"DELETE FROM media WHERE jellyfin_id IN ({placeholders})",
                    list(orphaned_ids)
                )
                deleted_count = cursor.rowcount
                self.db_connection.commit()

                logger.info(f"Cleaned up {deleted_count} orphaned media items")
                return deleted_count
            else:
                logger.info("No orphaned media items found")
                return 0

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned media: {str(e)}")
            log_exception(logger, e, "Media cleanup")
            return 0


# Convenience functions
async def sync_jellyfin(
    jellyfin_url: str,
    api_key: str,
    database_path: str = "database/critics.db",
    user_id: Optional[str] = None,
    page_size: int = 100
) -> Dict[str, Any]:
    """
    Convenience function for one-off Jellyfin sync

    Args:
        jellyfin_url: Jellyfin server URL
        api_key: Jellyfin API key
        database_path: Database file path
        user_id: Jellyfin user ID (optional)
        page_size: Items per page

    Returns:
        Sync results summary
    """
    async with SyncManager(jellyfin_url, api_key, database_path, user_id) as sync_manager:
        return await sync_manager.sync_jellyfin_library(page_size=page_size)


# Demo/test function
async def demo_sync():
    """Demonstrate sync manager with test data"""
    from config import Config

    config = Config()

    try:
        async with SyncManager(
            jellyfin_url=config.JELLYFIN_URL,
            api_key=config.JELLYFIN_API_TOKEN,
            database_path=config.DATABASE_PATH
        ) as sync_manager:

            results = await sync_manager.sync_jellyfin_library(page_size=50)

            print("\n🎭 Sync Results:")
            print(f"📊 Items Processed: {results['items_processed']}")
            print(f"🆕 Items Added: {results['items_added']}")
            print(f"🔄 Items Updated: {results['items_updated']}")
            print(f"❌ Errors: {results['errors']}")

    except Exception as e:
        logger.error(f"Demo sync failed: {str(e)}")
        log_exception(logger, e, "Demo sync")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_sync())