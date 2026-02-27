#!/usr/bin/env python3
"""
Check database statistics after sync
"""
import sqlite3
from config import get_config

def main():
    config = get_config()
    db_path = config.get_absolute_db_path()

    print(f"📊 Checking database stats: {db_path}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Total media count
        cursor.execute("SELECT COUNT(*) FROM media")
        total_count = cursor.fetchone()[0]

        # Movies and series count
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN type = 'movie' THEN 1 END) as movies,
                COUNT(CASE WHEN type = 'series' THEN 1 END) as series
            FROM media
        """)
        movies, series = cursor.fetchone()

        # Media with TMDB IDs
        cursor.execute("SELECT COUNT(*) FROM media WHERE tmdb_id IS NOT NULL")
        with_tmdb = cursor.fetchone()[0]

        # Media without TMDB IDs
        cursor.execute("SELECT COUNT(*) FROM media WHERE tmdb_id IS NULL")
        without_tmdb = cursor.fetchone()[0]

        print("\n✅ Final Database Stats:")
        print(f"   📹 Total media: {total_count:,}")
        print(f"   🎬 Movies: {movies:,}")
        print(f"   📺 Series: {series:,}")
        print(f"   🎯 With TMDB ID: {with_tmdb:,} ({(with_tmdb/total_count*100):.1f}%)")
        print(f"   ❌ Without TMDB ID: {without_tmdb:,} ({(without_tmdb/total_count*100):.1f}%)")

        print("\n🎭 Sync Coverage:")
        print("   Jellyfin total: 3,827")
        print(f"   Local synced: {total_count:,}")
        print(f"   Coverage: {(total_count/3827*100):.1f}%")
        print(f"   Missing: {3827 - total_count:,} items")

        # Show some failed items without TMDB ID
        print("\n🔍 Sample of items without TMDB ID:")
        cursor.execute("SELECT title, year FROM media WHERE tmdb_id IS NULL LIMIT 10")
        for row in cursor.fetchall():
            print(f"   - {row[0]} ({row[1] if row[1] else 'No year'})")

if __name__ == "__main__":
    main()