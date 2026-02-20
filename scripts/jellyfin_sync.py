#!/usr/bin/env python3
"""
Jellyfin Synchronization Script
Syncs media library from Jellyfin to local SQLite database
"""

import sqlite3
import json
import asyncio
import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import argparse

# Database schema imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from models.schemas import MediaDB, MediaType

class JellyfinSync:
    def __init__(self, jellyfin_url: str, api_key: str, db_path: str):
        self.jellyfin_url = jellyfin_url.rstrip('/')
        self.api_key = api_key
        self.db_path = db_path
        self.session = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def test_connection(self) -> bool:
        """Test connection to Jellyfin server"""
        try:
            response = await self.session.get(
                f"{self.jellyfin_url}/System/Info",
                headers={"X-Emby-Token": self.api_key}
            )
            response.raise_for_status()

            server_info = response.json()
            print(f"✅ Connected to Jellyfin: {server_info.get('ServerName', 'Unknown')}")
            print(f"   Version: {server_info.get('Version', 'Unknown')}")
            return True

        except Exception as e:
            print(f"❌ Failed to connect to Jellyfin: {e}")
            return False

    async def get_users(self) -> List[Dict[str, Any]]:
        """Get all users from Jellyfin"""
        try:
            response = await self.session.get(
                f"{self.jellyfin_url}/Users",
                headers={"X-Emby-Token": self.api_key}
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"❌ Failed to get users: {e}")
            return []

    async def get_libraries(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all media libraries for a user"""
        try:
            response = await self.session.get(
                f"{self.jellyfin_url}/Users/{user_id}/Views",
                headers={"X-Emby-Token": self.api_key}
            )
            response.raise_for_status()
            return response.json().get('Items', [])

        except Exception as e:
            print(f"❌ Failed to get libraries: {e}")
            return []

    async def get_library_items(self, user_id: str, library_id: str,
                               item_types: List[str] = None,
                               limit: int = 1000,
                               start_index: int = 0) -> Dict[str, Any]:
        """Get items from a specific library"""
        try:
            params = {
                'ParentId': library_id,
                'Recursive': 'true',
                'Fields': 'ProviderIds,Overview,Genres,ProductionYear,RunTimeTicks,CommunityRating,VoteCount,PremiereDate',
                'Limit': limit,
                'StartIndex': start_index
            }

            if item_types:
                params['IncludeItemTypes'] = ','.join(item_types)

            response = await self.session.get(
                f"{self.jellyfin_url}/Users/{user_id}/Items",
                headers={"X-Emby-Token": self.api_key},
                params=params
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"❌ Failed to get library items: {e}")
            return {'Items': [], 'TotalRecordCount': 0}

    def parse_media_item(self, item: Dict[str, Any]) -> Optional[MediaDB]:
        """Parse Jellyfin item to MediaDB model"""
        try:
            # Map Jellyfin types to our types
            jellyfin_type = item.get('Type', '')
            if jellyfin_type == 'Movie':
                media_type = MediaType.MOVIE
            elif jellyfin_type == 'Series':
                media_type = MediaType.SERIES
            else:
                return None  # Skip unsupported types

            # Get provider IDs
            provider_ids = item.get('ProviderIds', {})
            tmdb_id = provider_ids.get('Tmdb')

            if not tmdb_id:
                print(f"⚠️ Skipping {item.get('Name', 'Unknown')} - No TMDB ID")
                return None

            # Parse genres
            genres_list = item.get('Genres', [])
            genres_json = json.dumps(genres_list) if genres_list else None

            # Runtime in minutes
            runtime_ticks = item.get('RunTimeTicks')
            runtime_minutes = None
            if runtime_ticks:
                runtime_minutes = int(runtime_ticks / 600000000)  # Convert from ticks to minutes

            # Parse year
            year = item.get('ProductionYear') or item.get('PremiereDate', '')
            if isinstance(year, str) and year:
                try:
                    year = int(year[:4])
                except (ValueError, IndexError):
                    year = None

            return MediaDB(
                tmdb_id=str(tmdb_id),
                jellyfin_id=item['Id'],
                title=item.get('Name', ''),
                original_title=item.get('OriginalTitle'),
                year=year,
                type=media_type,
                genres=genres_json,
                overview=item.get('Overview'),
                poster_url=f"{self.jellyfin_url}/Items/{item['Id']}/Images/Primary" if item.get('ImageTags', {}).get('Primary') else None,
                backdrop_url=f"{self.jellyfin_url}/Items/{item['Id']}/Images/Backdrop" if item.get('BackdropImageTags') else None,
                imdb_id=provider_ids.get('Imdb'),
                runtime=runtime_minutes,
                vote_average=item.get('CommunityRating'),
                vote_count=item.get('VoteCount')
            )

        except Exception as e:
            print(f"❌ Error parsing item {item.get('Name', 'Unknown')}: {e}")
            return None

    def save_media_to_db(self, media_items: List[MediaDB]) -> Dict[str, int]:
        """Save media items to database"""
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0}

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for media in media_items:
                try:
                    # Check if exists
                    cursor.execute(
                        "SELECT id FROM media WHERE tmdb_id = ?",
                        (media.tmdb_id,)
                    )
                    existing = cursor.fetchone()

                    if existing:
                        # Update existing
                        cursor.execute("""
                            UPDATE media SET
                                jellyfin_id = ?, title = ?, original_title = ?, year = ?,
                                type = ?, genres = ?, overview = ?, poster_url = ?,
                                backdrop_url = ?, imdb_id = ?, runtime = ?,
                                vote_average = ?, vote_count = ?, updated_at = ?
                            WHERE tmdb_id = ?
                        """, (
                            media.jellyfin_id, media.title, media.original_title, media.year,
                            media.type.value, media.genres, media.overview, media.poster_url,
                            media.backdrop_url, media.imdb_id, media.runtime,
                            media.vote_average, media.vote_count, datetime.now().isoformat(),
                            media.tmdb_id
                        ))
                        stats['updated'] += 1
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO media (
                                tmdb_id, jellyfin_id, title, original_title, year, type,
                                genres, overview, poster_url, backdrop_url, imdb_id,
                                runtime, vote_average, vote_count
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            media.tmdb_id, media.jellyfin_id, media.title, media.original_title,
                            media.year, media.type.value, media.genres, media.overview,
                            media.poster_url, media.backdrop_url, media.imdb_id, media.runtime,
                            media.vote_average, media.vote_count
                        ))
                        stats['inserted'] += 1

                except Exception as e:
                    print(f"❌ Error saving {media.title}: {e}")
                    stats['skipped'] += 1

            conn.commit()

        return stats

    def log_sync_operation(self, stats: Dict[str, int], error_message: str = None):
        """Log sync operation to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            total_processed = stats.get('inserted', 0) + stats.get('updated', 0) + stats.get('skipped', 0)
            total_success = stats.get('inserted', 0) + stats.get('updated', 0)
            total_errors = stats.get('skipped', 0)

            cursor.execute("""
                INSERT INTO sync_log (
                    sync_type, total_processed, total_success, total_errors,
                    completed_at, status, error_message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'jellyfin_sync',
                total_processed,
                total_success,
                total_errors,
                datetime.now().isoformat(),
                'error' if error_message else 'completed',
                error_message,
                json.dumps(stats)
            ))

            conn.commit()

    async def sync_library(self, library_types: List[str] = None) -> Dict[str, int]:
        """Main sync function"""
        print("🔄 Starting Jellyfin sync...")

        # Default to movies and series
        if library_types is None:
            library_types = ['Movie', 'Series']

        # Test connection
        if not await self.test_connection():
            raise Exception("Cannot connect to Jellyfin")

        # Get first admin user
        users = await self.get_users()
        admin_user = next((u for u in users if u.get('Policy', {}).get('IsAdministrator')), None)

        if not admin_user:
            raise Exception("No admin user found")

        user_id = admin_user['Id']
        print(f"📊 Using user: {admin_user.get('Name', 'Unknown')}")

        # Get libraries
        libraries = await self.get_libraries(user_id)
        print(f"📚 Found {len(libraries)} libraries")

        all_media = []
        total_stats = {'movies': 0, 'series': 0, 'processed': 0}

        # Process each library
        for library in libraries:
            lib_name = library.get('Name', 'Unknown')
            lib_id = library['Id']

            print(f"🔍 Processing library: {lib_name}")

            # Get all items in batches
            start_index = 0
            batch_size = 500

            while True:
                result = await self.get_library_items(
                    user_id, lib_id, library_types, batch_size, start_index
                )

                items = result.get('Items', [])
                if not items:
                    break

                print(f"   📝 Processing batch {start_index // batch_size + 1}: {len(items)} items")

                # Parse items
                for item in items:
                    media = self.parse_media_item(item)
                    if media:
                        all_media.append(media)
                        if media.type == MediaType.MOVIE:
                            total_stats['movies'] += 1
                        else:
                            total_stats['series'] += 1

                total_stats['processed'] += len(items)

                # Check if we got all items
                if len(items) < batch_size:
                    break

                start_index += batch_size

        print(f"📊 Parsed {len(all_media)} media items ({total_stats['movies']} movies, {total_stats['series']} series)")

        # Save to database
        if all_media:
            print("💾 Saving to database...")
            save_stats = self.save_media_to_db(all_media)
            print(f"   ✅ Inserted: {save_stats['inserted']}")
            print(f"   🔄 Updated: {save_stats['updated']}")
            print(f"   ⚠️ Skipped: {save_stats['skipped']}")

            # Log the operation
            self.log_sync_operation(save_stats)

            return save_stats
        else:
            print("⚠️ No media items to save")
            return {'inserted': 0, 'updated': 0, 'skipped': 0}

async def main():
    parser = argparse.ArgumentParser(description='Sync Jellyfin media to local database')
    parser.add_argument('--jellyfin-url', required=True, help='Jellyfin server URL')
    parser.add_argument('--api-key', required=True, help='Jellyfin API key')
    parser.add_argument('--db-path', default='database/critics.db', help='SQLite database path')
    parser.add_argument('--types', nargs='+', choices=['Movie', 'Series'],
                       default=['Movie', 'Series'], help='Media types to sync')

    args = parser.parse_args()

    # Validate database exists
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Run 'python database/init_db.py' first")
        return

    try:
        async with JellyfinSync(args.jellyfin_url, args.api_key, args.db_path) as sync:
            stats = await sync.sync_library(args.types)

            print("🎉 Sync completed successfully!")
            print(f"📈 Final stats: {json.dumps(stats, indent=2)}")

    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()) or 0)