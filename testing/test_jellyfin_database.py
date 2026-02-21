#!/usr/bin/env python3
"""
🎭 Parody Critics - Jellyfin Database Access Test
Test script to verify direct SQLite database connectivity and data extraction

Author: SAL-9000
"""

import sqlite3
import json
import time
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

class JellyfinDatabaseTester:
    """Test Jellyfin SQLite database connectivity and data retrieval"""

    def __init__(self, db_path: str):
        self.db_path = db_path

        # Check if database exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")

    def test_connection(self) -> Dict[str, Any]:
        """Test basic database connectivity"""
        print("🔌 Testing database connectivity...")

        try:
            start_time = time.time()
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()[0]
            response_time = time.time() - start_time

            print(f"✅ Database connected! Response time: {response_time:.4f}s")
            print(f"   SQLite version: {version}")
            print(f"   Database path: {self.db_path}")

            return {
                "success": True,
                "response_time": response_time,
                "sqlite_version": version,
                "db_path": self.db_path
            }

        except sqlite3.Error as e:
            print(f"❌ Database error: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database table structure"""
        print("🏗️  Analyzing database schema...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = [row[0] for row in cursor.fetchall()]

                print(f"✅ Found {len(tables)} tables:")
                for table in tables[:20]:  # Show first 20
                    print(f"   - {table}")

                if len(tables) > 20:
                    print(f"   ... and {len(tables) - 20} more")

                # Get detailed info for key tables
                key_tables = ['TypedBaseItems', 'UserDatas', 'Ancestors']
                table_info = {}

                for table in key_tables:
                    if table in tables:
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = cursor.fetchall()
                        table_info[table] = [dict(col) for col in columns]

                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]

                        print(f"   📊 {table}: {count} records, {len(columns)} columns")

                return {
                    "success": True,
                    "tables": tables,
                    "table_count": len(tables),
                    "key_table_info": table_info
                }

        except sqlite3.Error as e:
            print(f"❌ Schema analysis error: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_movies_from_db(self, limit: int = 10) -> Dict[str, Any]:
        """Get movies directly from SQLite database"""
        print(f"🎬 Getting {limit} movies from database...")

        try:
            start_time = time.time()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Query for movies
                query = """
                SELECT
                    Id,
                    Name,
                    ProviderIds,
                    ProductionYear,
                    Overview,
                    Genres,
                    DateCreated,
                    DateModified,
                    Path,
                    Type
                FROM BaseItems
                WHERE Type = 'MediaBrowser.Controller.Entities.Movies.Movie'
                    AND Name IS NOT NULL
                ORDER BY DateCreated DESC
                LIMIT ?
                """

                cursor.execute(query, (limit,))
                movies = cursor.fetchall()

                # Get total count
                cursor.execute("SELECT COUNT(*) FROM BaseItems WHERE Type = 'MediaBrowser.Controller.Entities.Movies.Movie'")
                total_count = cursor.fetchone()[0]

            response_time = time.time() - start_time

            print(f"✅ Retrieved {len(movies)} movies (Total: {total_count}) in {response_time:.4f}s")

            for movie in movies[:5]:  # Show first 5
                movie_dict = dict(movie)
                title = movie_dict.get('Name', 'Unknown')
                year = movie_dict.get('ProductionYear', 'Unknown')

                # Parse ProviderIds JSON
                provider_ids = {}
                try:
                    if movie_dict.get('ProviderIds'):
                        provider_ids = json.loads(movie_dict['ProviderIds'])
                except json.JSONDecodeError:
                    pass

                tmdb_id = provider_ids.get('Tmdb')
                imdb_id = provider_ids.get('Imdb')

                print(f"   - {title} ({year})")
                print(f"     TMDB: {tmdb_id}, IMDB: {imdb_id}")
                print(f"     ID: {movie_dict['Id']}")

            return {
                "success": True,
                "movies": [dict(movie) for movie in movies],
                "total_count": total_count,
                "response_time": response_time
            }

        except sqlite3.Error as e:
            print(f"❌ Error getting movies: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_series_from_db(self, limit: int = 10) -> Dict[str, Any]:
        """Get TV series directly from SQLite database"""
        print(f"📺 Getting {limit} series from database...")

        try:
            start_time = time.time()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Query for series
                query = """
                SELECT
                    Id,
                    Name,
                    ProviderIds,
                    ProductionYear,
                    Overview,
                    Genres,
                    DateCreated,
                    DateModified,
                    Path,
                    Type
                FROM BaseItems
                WHERE Type = 'MediaBrowser.Controller.Entities.TV.Series'
                    AND Name IS NOT NULL
                ORDER BY DateCreated DESC
                LIMIT ?
                """

                cursor.execute(query, (limit,))
                series = cursor.fetchall()

                # Get total count
                cursor.execute("SELECT COUNT(*) FROM BaseItems WHERE Type = 'MediaBrowser.Controller.Entities.TV.Series'")
                total_count = cursor.fetchone()[0]

            response_time = time.time() - start_time

            print(f"✅ Retrieved {len(series)} series (Total: {total_count}) in {response_time:.4f}s")

            for show in series[:5]:  # Show first 5
                show_dict = dict(show)
                title = show_dict.get('Name', 'Unknown')
                year = show_dict.get('ProductionYear', 'Unknown')

                # Parse ProviderIds JSON
                provider_ids = {}
                try:
                    if show_dict.get('ProviderIds'):
                        provider_ids = json.loads(show_dict['ProviderIds'])
                except json.JSONDecodeError:
                    pass

                tmdb_id = provider_ids.get('Tmdb')
                tvdb_id = provider_ids.get('Tvdb')

                print(f"   - {title} ({year})")
                print(f"     TMDB: {tmdb_id}, TVDB: {tvdb_id}")
                print(f"     ID: {show_dict['Id']}")

            return {
                "success": True,
                "series": [dict(show) for show in series],
                "total_count": total_count,
                "response_time": response_time
            }

        except sqlite3.Error as e:
            print(f"❌ Error getting series: {str(e)}")
            return {"success": False, "error": str(e)}

    def analyze_performance_vs_api(self) -> Dict[str, Any]:
        """Analyze performance differences between direct DB and API"""
        print("⚡ Performance analysis: Database vs API...")

        try:
            # Time database queries
            db_times = []

            # Test 1: Get 100 movies
            start_time = time.time()
            movies_result = self.get_movies_from_db(100)
            if movies_result.get("success"):
                db_times.append(("movies_100", time.time() - start_time))

            # Test 2: Get 100 series
            start_time = time.time()
            series_result = self.get_series_from_db(100)
            if series_result.get("success"):
                db_times.append(("series_100", time.time() - start_time))

            # Test 3: Complex query with aggregation
            start_time = time.time()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT Type, COUNT(*) as count
                    FROM TypedBaseItems
                    WHERE Type IN ('Movie', 'Series', 'Season', 'Episode')
                    GROUP BY Type
                """)
                stats = cursor.fetchall()
            complex_query_time = time.time() - start_time
            db_times.append(("complex_stats", complex_query_time))

            print("📊 Database performance results:")
            for test_name, duration in db_times:
                print(f"   {test_name}: {duration:.4f}s")

            print(f"   Complex stats: {dict(stats)}")

            return {
                "success": True,
                "database_times": dict(db_times),
                "media_stats": dict(stats) if 'stats' in locals() else {}
            }

        except sqlite3.Error as e:
            print(f"❌ Performance analysis error: {str(e)}")
            return {"success": False, "error": str(e)}

    def test_data_extraction_for_sync(self) -> Dict[str, Any]:
        """Test data extraction patterns needed for synchronization"""
        print("🔄 Testing data extraction patterns for sync...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Test 1: Get movies with TMDB IDs (needed for our system)
                cursor.execute("""
                    SELECT Id, Name, ProviderIds, ProductionYear, DateModified
                    FROM TypedBaseItems
                    WHERE Type = 'Movie'
                        AND IsFolder = 0
                        AND ProviderIds LIKE '%Tmdb%'
                    ORDER BY DateModified DESC
                    LIMIT 50
                """)
                movies_with_tmdb = cursor.fetchall()

                # Test 2: Count items without TMDB IDs
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM TypedBaseItems
                    WHERE Type = 'Movie'
                        AND IsFolder = 0
                        AND (ProviderIds IS NULL OR ProviderIds NOT LIKE '%Tmdb%')
                """)
                movies_without_tmdb = cursor.fetchone()[0]

                # Test 3: Series with TMDB/TVDB IDs
                cursor.execute("""
                    SELECT Id, Name, ProviderIds, ProductionYear, DateModified
                    FROM TypedBaseItems
                    WHERE Type = 'Series'
                        AND (ProviderIds LIKE '%Tmdb%' OR ProviderIds LIKE '%Tvdb%')
                    ORDER BY DateModified DESC
                    LIMIT 50
                """)
                series_with_ids = cursor.fetchall()

                # Test 4: Recently modified items (for incremental sync)
                cursor.execute("""
                    SELECT Type, COUNT(*) as count
                    FROM TypedBaseItems
                    WHERE Type IN ('Movie', 'Series')
                        AND DateModified > datetime('now', '-30 days')
                    GROUP BY Type
                """)
                recent_changes = cursor.fetchall()

                print(f"✅ Sync analysis results:")
                print(f"   Movies with TMDB ID: {len(movies_with_tmdb)}")
                print(f"   Movies without TMDB ID: {movies_without_tmdb}")
                print(f"   Series with IDs: {len(series_with_ids)}")
                print(f"   Recent changes (30 days): {dict(recent_changes)}")

                # Show sample TMDB extraction
                print(f"\n📋 Sample TMDB extraction:")
                for movie in movies_with_tmdb[:3]:
                    movie_dict = dict(movie)
                    try:
                        provider_ids = json.loads(movie_dict['ProviderIds'])
                        tmdb_id = provider_ids.get('Tmdb')
                        print(f"   {movie_dict['Name']} → TMDB: {tmdb_id}")
                    except:
                        pass

                return {
                    "success": True,
                    "movies_with_tmdb": len(movies_with_tmdb),
                    "movies_without_tmdb": movies_without_tmdb,
                    "series_with_ids": len(series_with_ids),
                    "recent_changes": dict(recent_changes),
                    "sample_movies": [dict(m) for m in movies_with_tmdb[:10]]
                }

        except sqlite3.Error as e:
            print(f"❌ Sync analysis error: {str(e)}")
            return {"success": False, "error": str(e)}

    def run_full_test(self) -> Dict[str, Any]:
        """Run complete database connectivity test suite"""
        print("🎭 Starting Jellyfin Database Connectivity Tests")
        print("=" * 55)

        results = {
            "timestamp": datetime.now().isoformat(),
            "database_path": self.db_path,
            "tests": {}
        }

        # Test 1: Basic connectivity
        print()
        connection_result = self.test_connection()
        results["tests"]["connection"] = connection_result

        if not connection_result.get("success"):
            print("\n❌ Connection failed, aborting remaining tests")
            return results

        print()

        # Test 2: Database schema analysis
        schema_result = self.get_database_schema()
        results["tests"]["schema"] = schema_result
        print()

        # Test 3: Movies extraction
        movies_result = self.get_movies_from_db(10)
        results["tests"]["movies"] = movies_result
        print()

        # Test 4: Series extraction
        series_result = self.get_series_from_db(10)
        results["tests"]["series"] = series_result
        print()

        # Test 5: Performance analysis
        performance_result = self.analyze_performance_vs_api()
        results["tests"]["performance"] = performance_result
        print()

        # Test 6: Sync data extraction
        sync_result = self.test_data_extraction_for_sync()
        results["tests"]["sync_analysis"] = sync_result

        # Summary
        print("\n" + "=" * 55)
        print("🏁 Database Test Results Summary:")

        success_count = sum(1 for test in results["tests"].values() if test.get("success"))
        total_tests = len(results["tests"])

        print(f"✅ Successful tests: {success_count}/{total_tests}")

        if movies_result.get("success"):
            print(f"🎬 Total movies in database: {movies_result.get('total_count', 0)}")

        if series_result.get("success"):
            print(f"📺 Total series in database: {series_result.get('total_count', 0)}")

        if sync_result.get("success"):
            movies_with_tmdb = sync_result.get('movies_with_tmdb', 0)
            movies_without = sync_result.get('movies_without_tmdb', 0)
            total_movies = movies_with_tmdb + movies_without
            coverage = (movies_with_tmdb / total_movies * 100) if total_movies > 0 else 0
            print(f"🎯 TMDB coverage: {movies_with_tmdb}/{total_movies} ({coverage:.1f}%)")

        return results


def main():
    """Main test execution"""
    # Jellyfin database paths (common locations)
    possible_paths = [
        "/home/stilgar/docker/jellyfin-upgrade/config/data/jellyfin.db",  # Docker volume mount
        "/home/stilgar/.config/jellyfin-stg/data/jellyfin.db",  # User data
        "/var/lib/jellyfin/data/jellyfin.db",  # System install
        "/config/data/jellyfin.db",  # Docker volume
        # Try to detect from container
    ]

    # Try to find the database
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("❌ Jellyfin database not found in common locations:")
        for path in possible_paths:
            print(f"   - {path}")

        # Try to find via Docker container
        print("\n🔍 Trying to locate database via Docker...")
        try:
            import subprocess
            result = subprocess.run([
                "docker", "exec", "jellyfin-stg",
                "find", "/config", "-name", "jellyfin.db", "-type", "f"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                container_path = result.stdout.strip()
                print(f"✅ Found database in container: {container_path}")

                # We need to copy it out or access it differently
                print("💡 Database is inside Docker container - need different approach")
                return {"success": False, "reason": "database_in_container", "path": container_path}

        except Exception as e:
            print(f"🤔 Docker detection failed: {e}")

        return {"success": False, "reason": "database_not_found"}

    print(f"🎯 Using database: {db_path}")

    # Create tester instance
    try:
        tester = JellyfinDatabaseTester(db_path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return {"success": False, "error": str(e)}

    # Run tests
    results = tester.run_full_test()

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"jellyfin_db_test_results_{timestamp}.json"

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Results saved to: {results_file}")

    return results


if __name__ == "__main__":
    main()