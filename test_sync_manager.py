#!/usr/bin/env python3
"""
Quick test script for JellyfinSyncManager
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from api.jellyfin_sync import JellyfinSyncManager

async def test_sync_manager():
    """Test the sync manager functionality"""

    # Configuration
    jellyfin_url = "http://192.168.45.181:8097"
    api_token = "JELLYFIN_API_TOKEN_REDACTED"
    jellyfin_db_path = "/home/stilgar/docker/jellyfin-upgrade/config/data/jellyfin.db"
    local_db_path = "database/critics.db"

    print("🎭 Testing Jellyfin Sync Manager")
    print("=" * 50)

    # Create sync manager
    sync_manager = JellyfinSyncManager(
        jellyfin_url=jellyfin_url,
        api_token=api_token,
        jellyfin_db_path=jellyfin_db_path,
        local_db_path=local_db_path
    )

    print("✅ Sync manager created")

    # Test 1: Get media counts
    print("\n📊 Getting media counts from Jellyfin database...")
    try:
        counts = sync_manager.get_media_count_from_jellyfin_db()
        print(f"   Movies: {counts.get('movies', 0)}")
        print(f"   Series: {counts.get('series', 0)}")
        print(f"   Total: {counts.get('total', 0)}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Test 2: Extract sample media
    print("\n🎬 Extracting sample media (first 5)...")
    try:
        media_items = sync_manager.extract_media_from_jellyfin_db(limit=5)
        print(f"   Extracted {len(media_items)} items:")
        for item in media_items:
            print(f"   - {item.name} ({item.year}) - TMDB: {item.tmdb_id}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Test 3: Small sync test
    print("\n🔄 Testing small sync (first 3 items)...")
    try:
        sample_items = sync_manager.extract_media_from_jellyfin_db(limit=3)
        successful, failed = sync_manager.sync_media_to_local_db(sample_items)
        print(f"   Sync results: {successful} successful, {failed} failed")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    print("\n🏆 All tests completed successfully!")
    print("🚀 Ready to implement full synchronization!")

if __name__ == "__main__":
    asyncio.run(test_sync_manager())