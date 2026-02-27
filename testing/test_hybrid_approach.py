#!/usr/bin/env python3
"""
🎭 Parody Critics - Hybrid Approach Validation
Compare Jellyfin API vs Direct Database performance and data consistency

Author: SAL-9000
"""

import httpx
import sqlite3
import json
import time
from typing import Dict, List, Any
from datetime import datetime

class HybridApproachValidator:
    """Compare API vs Database approaches for Jellyfin data access"""

    def __init__(self, api_url: str, api_token: str, db_path: str):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.db_path = db_path

        # API headers
        self.headers = {
            "Authorization": f'MediaBrowser Client="Parody Critics Hybrid", Device="Validator", DeviceId="hybrid-test-1", Version="1.0.0", Token="{api_token}"',
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_api_movies(self, limit: int = 50) -> Dict[str, Any]:
        """Get movies via Jellyfin API"""
        print(f"🌐 Getting {limit} movies via API...")

        try:
            start_time = time.time()

            # First get users to get first user ID
            with httpx.Client(headers=self.headers, timeout=30.0) as client:
                users_response = client.get(f"{self.api_url}/Users")
                if users_response.status_code != 200:
                    raise Exception(f"Users API failed: {users_response.status_code}")

                users = users_response.json()
                if not users:
                    raise Exception("No users found")

                user_id = users[0]['Id']

                # Get movies
                url = f"{self.api_url}/Users/{user_id}/Items"
                params = {
                    "IncludeItemTypes": "Movie",
                    "Recursive": "true",
                    "Fields": "ProviderIds,Overview,Genres,ProductionYear,Path",
                    "Limit": limit,
                    "SortBy": "DateCreated",
                    "SortOrder": "Descending"
                }

                response = client.get(url, params=params)

            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                movies = data.get('Items', [])
                total_count = data.get('TotalRecordCount', 0)

                print(f"✅ API: Retrieved {len(movies)} movies (Total: {total_count}) in {response_time:.4f}s")

                return {
                    "success": True,
                    "movies": movies,
                    "total_count": total_count,
                    "response_time": response_time
                }
            else:
                raise Exception(f"API request failed: {response.status_code}")

        except Exception as e:
            print(f"❌ API Error: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_db_movies(self, limit: int = 50) -> Dict[str, Any]:
        """Get movies via direct database access"""
        print(f"💾 Getting {limit} movies via Database...")

        try:
            start_time = time.time()

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Complex query with JOIN to get provider IDs
                query = """
                SELECT
                    b.Id,
                    b.Name,
                    b.ProductionYear,
                    b.Overview,
                    b.Genres,
                    b.DateCreated,
                    b.Path,
                    GROUP_CONCAT(
                        CASE
                            WHEN p.ProviderId = 'Tmdb' THEN 'Tmdb:' || p.ProviderValue
                            WHEN p.ProviderId = 'Imdb' THEN 'Imdb:' || p.ProviderValue
                            WHEN p.ProviderId = 'Tvdb' THEN 'Tvdb:' || p.ProviderValue
                            ELSE p.ProviderId || ':' || p.ProviderValue
                        END, '|'
                    ) as ProviderIds
                FROM BaseItems b
                LEFT JOIN BaseItemProviders p ON b.Id = p.ItemId
                WHERE b.Type = 'MediaBrowser.Controller.Entities.Movies.Movie'
                    AND b.Name IS NOT NULL
                GROUP BY b.Id, b.Name, b.ProductionYear, b.Overview, b.Genres, b.DateCreated, b.Path
                ORDER BY b.DateCreated DESC
                LIMIT ?
                """

                cursor.execute(query, (limit,))
                movies = cursor.fetchall()

                # Get total count
                cursor.execute("SELECT COUNT(*) FROM BaseItems WHERE Type = 'MediaBrowser.Controller.Entities.Movies.Movie'")
                total_count = cursor.fetchone()[0]

            response_time = time.time() - start_time

            print(f"✅ DB: Retrieved {len(movies)} movies (Total: {total_count}) in {response_time:.4f}s")

            return {
                "success": True,
                "movies": [dict(movie) for movie in movies],
                "total_count": total_count,
                "response_time": response_time
            }

        except Exception as e:
            print(f"❌ Database Error: {str(e)}")
            return {"success": False, "error": str(e)}

    def compare_movie_data(self, api_movies: List[Dict], db_movies: List[Dict]) -> Dict[str, Any]:
        """Compare data consistency between API and Database"""
        print("🔍 Comparing data consistency...")

        # Create lookup dictionaries
        api_lookup = {movie.get('Name', '').lower(): movie for movie in api_movies}
        db_lookup = {movie.get('Name', '').lower(): movie for movie in db_movies}

        # Find common movies
        common_titles = set(api_lookup.keys()) & set(db_lookup.keys())
        api_only_titles = set(api_lookup.keys()) - set(db_lookup.keys())
        db_only_titles = set(db_lookup.keys()) - set(api_lookup.keys())

        print("📊 Data consistency results:")
        print(f"   Common movies: {len(common_titles)}")
        print(f"   API-only movies: {len(api_only_titles)}")
        print(f"   DB-only movies: {len(db_only_titles)}")

        # Analyze provider ID consistency
        provider_consistency = []
        for title in list(common_titles)[:10]:  # Test first 10 common movies
            api_movie = api_lookup[title]
            db_movie = db_lookup[title]

            api_providers = api_movie.get('ProviderIds', {})
            db_providers_raw = db_movie.get('ProviderIds', '')

            # Parse DB providers
            db_providers = {}
            if db_providers_raw:
                for provider_pair in db_providers_raw.split('|'):
                    if ':' in provider_pair:
                        provider, value = provider_pair.split(':', 1)
                        db_providers[provider] = value

            # Compare TMDB IDs
            api_tmdb = api_providers.get('Tmdb')
            db_tmdb = db_providers.get('Tmdb')

            consistency_check = {
                "title": title,
                "api_tmdb": api_tmdb,
                "db_tmdb": db_tmdb,
                "tmdb_matches": api_tmdb == db_tmdb,
                "api_providers": api_providers,
                "db_providers": db_providers
            }

            provider_consistency.append(consistency_check)

        # Calculate consistency rate
        tmdb_matches = sum(1 for check in provider_consistency if check['tmdb_matches'])
        consistency_rate = (tmdb_matches / len(provider_consistency) * 100) if provider_consistency else 0

        print(f"   TMDB ID consistency: {tmdb_matches}/{len(provider_consistency)} ({consistency_rate:.1f}%)")

        return {
            "common_movies": len(common_titles),
            "api_only_movies": len(api_only_titles),
            "db_only_movies": len(db_only_titles),
            "provider_consistency": provider_consistency,
            "tmdb_consistency_rate": consistency_rate,
            "sample_api_only": list(api_only_titles)[:5],
            "sample_db_only": list(db_only_titles)[:5]
        }

    def performance_benchmark(self) -> Dict[str, Any]:
        """Benchmark performance of both approaches"""
        print("⚡ Performance Benchmark...")

        results = {}

        # Test different data volumes
        test_sizes = [10, 50, 100]

        for size in test_sizes:
            print(f"\n📏 Testing with {size} movies:")

            # API performance
            api_result = self.get_api_movies(size)
            api_time = api_result.get('response_time', float('inf'))

            # Database performance
            db_result = self.get_db_movies(size)
            db_time = db_result.get('response_time', float('inf'))

            # Calculate speedup
            if api_time > 0 and db_time > 0:
                speedup = api_time / db_time
                print(f"   ⚡ Database is {speedup:.2f}x faster than API")
            else:
                speedup = None

            results[f"test_{size}"] = {
                "api_time": api_time,
                "db_time": db_time,
                "speedup": speedup,
                "api_success": api_result.get('success', False),
                "db_success": db_result.get('success', False)
            }

        return results

    def analyze_tmdb_coverage(self) -> Dict[str, Any]:
        """Analyze TMDB ID coverage in database"""
        print("🎯 Analyzing TMDB Coverage...")

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Movies with TMDB IDs
                cursor.execute("""
                    SELECT COUNT(DISTINCT b.Id) as count
                    FROM BaseItems b
                    JOIN BaseItemProviders p ON b.Id = p.ItemId
                    WHERE b.Type = 'MediaBrowser.Controller.Entities.Movies.Movie'
                        AND p.ProviderId = 'Tmdb'
                """)
                movies_with_tmdb = cursor.fetchone()[0]

                # Total movies
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM BaseItems
                    WHERE Type = 'MediaBrowser.Controller.Entities.Movies.Movie'
                """)
                total_movies = cursor.fetchone()[0]

                # Series with TMDB/TVDB IDs
                cursor.execute("""
                    SELECT COUNT(DISTINCT b.Id) as count
                    FROM BaseItems b
                    JOIN BaseItemProviders p ON b.Id = p.ItemId
                    WHERE b.Type = 'MediaBrowser.Controller.Entities.TV.Series'
                        AND p.ProviderId IN ('Tmdb', 'Tvdb')
                """)
                series_with_ids = cursor.fetchone()[0]

                # Total series
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM BaseItems
                    WHERE Type = 'MediaBrowser.Controller.Entities.TV.Series'
                """)
                total_series = cursor.fetchone()[0]

                # Calculate coverage percentages
                movie_coverage = (movies_with_tmdb / total_movies * 100) if total_movies > 0 else 0
                series_coverage = (series_with_ids / total_series * 100) if total_series > 0 else 0

                print("📊 TMDB/TVDB Coverage:")
                print(f"   Movies with TMDB: {movies_with_tmdb}/{total_movies} ({movie_coverage:.1f}%)")
                print(f"   Series with IDs: {series_with_ids}/{total_series} ({series_coverage:.1f}%)")

                return {
                    "movies_with_tmdb": movies_with_tmdb,
                    "total_movies": total_movies,
                    "movie_coverage_percent": movie_coverage,
                    "series_with_ids": series_with_ids,
                    "total_series": total_series,
                    "series_coverage_percent": series_coverage
                }

        except Exception as e:
            print(f"❌ Coverage analysis error: {str(e)}")
            return {"success": False, "error": str(e)}

    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete hybrid approach validation"""
        print("🎭 Starting Hybrid Approach Validation")
        print("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "api_url": self.api_url,
            "database_path": self.db_path,
            "tests": {}
        }

        print()

        # Test 1: Performance Benchmark
        performance_results = self.performance_benchmark()
        results["tests"]["performance"] = performance_results

        print("\n" + "=" * 40)

        # Test 2: Data Consistency
        print("🔄 Data Consistency Analysis...")

        # Get sample data from both sources
        api_result = self.get_api_movies(30)
        db_result = self.get_db_movies(30)

        if api_result.get('success') and db_result.get('success'):
            consistency_analysis = self.compare_movie_data(
                api_result['movies'],
                db_result['movies']
            )
            results["tests"]["data_consistency"] = consistency_analysis
        else:
            print("❌ Could not perform consistency analysis")
            results["tests"]["data_consistency"] = {"success": False}

        print("\n" + "=" * 40)

        # Test 3: TMDB Coverage Analysis
        coverage_analysis = self.analyze_tmdb_coverage()
        results["tests"]["tmdb_coverage"] = coverage_analysis

        # Final Recommendations
        print("\n" + "=" * 60)
        print("🏆 RECOMMENDATIONS & CONCLUSIONS:")

        avg_db_speedup = []
        for test_name, test_result in performance_results.items():
            if test_result.get('speedup') and test_result['speedup'] > 0:
                avg_db_speedup.append(test_result['speedup'])

        if avg_db_speedup:
            avg_speedup = sum(avg_db_speedup) / len(avg_db_speedup)
            print(f"   📈 Database is {avg_speedup:.2f}x faster on average")

        if coverage_analysis.get('movie_coverage_percent', 0) > 80:
            print(f"   🎯 TMDB coverage is excellent ({coverage_analysis['movie_coverage_percent']:.1f}%)")
            print("   ✅ RECOMMENDED: Hybrid approach with database-first strategy")
        elif coverage_analysis.get('movie_coverage_percent', 0) > 50:
            print(f"   🎯 TMDB coverage is good ({coverage_analysis['movie_coverage_percent']:.1f}%)")
            print("   ⚠️  RECOMMENDED: API-first with database fallback")
        else:
            print(f"   🎯 TMDB coverage is low ({coverage_analysis['movie_coverage_percent']:.1f}%)")
            print("   🚨 RECOMMENDED: API-only approach")

        print("   💡 For bulk sync: Use database for speed")
        print("   💡 For real-time: Use API for accuracy")

        return results


def main():
    """Main validation execution"""
    # Configuration
    API_URL = "http://192.168.45.181:8097"  # jellyfin-stg
    API_TOKEN = "0187d70ea6204155a984d9e09f8e6840"
    DB_PATH = "/home/stilgar/docker/jellyfin-upgrade/config/data/jellyfin.db"

    # Create validator
    validator = HybridApproachValidator(API_URL, API_TOKEN, DB_PATH)

    # Run validation
    results = validator.run_full_validation()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"hybrid_validation_results_{timestamp}.json"

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Complete results saved to: {results_file}")

    return results


if __name__ == "__main__":
    main()