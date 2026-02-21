#!/usr/bin/env python3
"""
Full sync script for Parody Critics - sync all media from Jellyfin
"""
import asyncio
from api.jellyfin_sync import JellyfinSyncManager
from config import get_config

async def main():
    """Execute full sync of all Jellyfin media"""
    print("🎭 Starting FULL sync of Parody Critics media...")

    # Get configuration
    config = get_config()

    # Initialize sync manager
    sync_manager = JellyfinSyncManager(
        jellyfin_url=config.JELLYFIN_URL,
        api_token=config.JELLYFIN_API_TOKEN,
        jellyfin_db_path=config.JELLYFIN_DB_PATH,
        local_db_path=config.get_absolute_db_path()
    )

    print(f"📊 Configuration loaded:")
    print(f"   Jellyfin URL: {config.JELLYFIN_URL}")
    print(f"   Jellyfin DB: {config.JELLYFIN_DB_PATH}")
    print(f"   Local DB: {config.get_absolute_db_path()}")
    print(f"   Batch size: {config.SYNC_BATCH_SIZE}")

    try:
        # Get current stats
        jellyfin_counts = sync_manager.get_media_count_from_jellyfin_db()
        print(f"\n📈 Jellyfin Media Stats:")
        print(f"   Movies: {jellyfin_counts['movies']:,}")
        print(f"   Series: {jellyfin_counts['series']:,}")
        print(f"   Total: {jellyfin_counts['total']:,}")

        # Check current local count
        import sqlite3
        with sqlite3.connect(config.get_absolute_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM media")
            local_count = cursor.fetchone()[0]

        print(f"   Local synced: {local_count:,}")
        print(f"   Remaining: {jellyfin_counts['total'] - local_count:,}")

        if local_count >= jellyfin_counts['total']:
            print("✅ All media already synced!")
            return

        # Start full sync
        print(f"\n🚀 Starting full sync with batch size {config.SYNC_BATCH_SIZE}...")
        sync_id = await sync_manager.start_sync(
            sync_type="full",
            batch_size=config.SYNC_BATCH_SIZE
        )

        print(f"📝 Sync started with ID: {sync_id}")

        # Monitor progress
        while True:
            await asyncio.sleep(2)  # Check every 2 seconds
            progress = sync_manager.get_sync_progress()

            if not progress:
                print("❌ Sync progress not available")
                break

            status = progress.get('status', 'unknown')
            processed = progress.get('processed', 0)
            total = progress.get('total', 0)

            if total > 0:
                percent = (processed / total) * 100
                print(f"⏳ Progress: {processed:,}/{total:,} ({percent:.1f}%) - Status: {status}")
            else:
                print(f"⏳ Status: {status} - Processed: {processed:,}")

            if status in ['completed', 'cancelled', 'failed']:
                break

        # Final stats
        with sqlite3.connect(config.get_absolute_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM media")
            final_count = cursor.fetchone()[0]

        print(f"\n🎉 Sync completed!")
        print(f"   Final local count: {final_count:,}")
        print(f"   Sync coverage: {(final_count/jellyfin_counts['total']*100):.1f}%")

        if final_count >= jellyfin_counts['total']:
            print("✅ ALL MEDIA SUCCESSFULLY SYNCED! 🎭")
        else:
            remaining = jellyfin_counts['total'] - final_count
            print(f"⚠️  Still missing {remaining:,} items")

    except Exception as e:
        print(f"❌ Sync failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())