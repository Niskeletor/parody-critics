#!/usr/bin/env python3
"""
🎭 Parody Critics - Jellyfin API Connectivity Test
Test script to verify Jellyfin API connectivity and data retrieval

Author: SAL-9000
"""

import httpx
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

class JellyfinAPITester:
    """Test Jellyfin API connectivity and data retrieval"""

    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token

        # Set up authentication headers
        self.headers = {
            "Authorization": f'MediaBrowser Client="Parody Critics", Device="TestScript", DeviceId="parody-test-1", Version="1.0.0", Token="{api_token}"',
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def test_connection(self) -> Dict[str, Any]:
        """Test basic connectivity with system info endpoint"""
        print("🔌 Testing basic connectivity...")

        try:
            url = f"{self.base_url}/System/Info"
            start_time = time.time()
            with httpx.Client(headers=self.headers, timeout=10.0) as client:
                response = client.get(url)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connection successful! Response time: {response_time:.2f}s")
                print(f"   Server: Jellyfin {data.get('Version', 'Unknown')}")
                print(f"   Server Name: {data.get('ServerName', 'Unknown')}")
                return {
                    "success": True,
                    "response_time": response_time,
                    "server_info": data
                }
            else:
                print(f"❌ Connection failed! Status: {response.status_code}")
                return {"success": False, "status_code": response.status_code, "response": response.text}

        except httpx.RequestError as e:
            print(f"❌ Connection error: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_users(self) -> Dict[str, Any]:
        """Get list of Jellyfin users"""
        print("👥 Getting users list...")

        try:
            url = f"{self.base_url}/Users"
            with httpx.Client(headers=self.headers, timeout=10.0) as client:
                response = client.get(url)

            if response.status_code == 200:
                users = response.json()
                print(f"✅ Found {len(users)} users")
                for user in users:
                    print(f"   - {user['Name']} (ID: {user['Id']})")
                return {"success": True, "users": users}
            else:
                print(f"❌ Failed to get users! Status: {response.status_code}")
                return {"success": False, "status_code": response.status_code}

        except httpx.RequestError as e:
            print(f"❌ Error getting users: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_libraries(self, user_id: str) -> Dict[str, Any]:
        """Get media libraries for a user"""
        print(f"📚 Getting libraries for user {user_id}...")

        try:
            url = f"{self.base_url}/Users/{user_id}/Views"
            with httpx.Client(headers=self.headers, timeout=10.0) as client:
                response = client.get(url)

            if response.status_code == 200:
                data = response.json()
                libraries = data.get('Items', [])
                print(f"✅ Found {len(libraries)} libraries")
                for lib in libraries:
                    lib_type = lib.get('CollectionType', 'Mixed')
                    print(f"   - {lib['Name']} ({lib_type}) - ID: {lib['Id']}")
                return {"success": True, "libraries": libraries}
            else:
                print(f"❌ Failed to get libraries! Status: {response.status_code}")
                return {"success": False, "status_code": response.status_code}

        except httpx.RequestError as e:
            print(f"❌ Error getting libraries: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_movies_sample(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get a sample of movies from Jellyfin"""
        print(f"🎬 Getting {limit} movies sample...")

        try:
            url = f"{self.base_url}/Users/{user_id}/Items"
            params = {
                "IncludeItemTypes": "Movie",
                "Recursive": "true",
                "Fields": "ProviderIds,Overview,Genres,ProductionYear,Path",
                "Limit": limit,
                "SortBy": "DateCreated",
                "SortOrder": "Descending"
            }

            start_time = time.time()
            with httpx.Client(headers=self.headers, timeout=30.0) as client:
                response = client.get(url, params=params)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                movies = data.get('Items', [])
                total_count = data.get('TotalRecordCount', 0)

                print(f"✅ Retrieved {len(movies)} movies (Total: {total_count}) in {response_time:.2f}s")

                for movie in movies[:5]:  # Show first 5
                    title = movie.get('Name', 'Unknown')
                    year = movie.get('ProductionYear', 'Unknown')
                    tmdb_id = movie.get('ProviderIds', {}).get('Tmdb')
                    imdb_id = movie.get('ProviderIds', {}).get('Imdb')

                    print(f"   - {title} ({year})")
                    print(f"     TMDB: {tmdb_id}, IMDB: {imdb_id}")

                return {
                    "success": True,
                    "movies": movies,
                    "total_count": total_count,
                    "response_time": response_time
                }
            else:
                print(f"❌ Failed to get movies! Status: {response.status_code}")
                return {"success": False, "status_code": response.status_code, "response": response.text}

        except httpx.RequestError as e:
            print(f"❌ Error getting movies: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_series_sample(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get a sample of TV series from Jellyfin"""
        print(f"📺 Getting {limit} TV series sample...")

        try:
            url = f"{self.base_url}/Users/{user_id}/Items"
            params = {
                "IncludeItemTypes": "Series",
                "Recursive": "true",
                "Fields": "ProviderIds,Overview,Genres,ProductionYear,Path",
                "Limit": limit,
                "SortBy": "DateCreated",
                "SortOrder": "Descending"
            }

            start_time = time.time()
            with httpx.Client(headers=self.headers, timeout=30.0) as client:
                response = client.get(url, params=params)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                series = data.get('Items', [])
                total_count = data.get('TotalRecordCount', 0)

                print(f"✅ Retrieved {len(series)} series (Total: {total_count}) in {response_time:.2f}s")

                for show in series[:5]:  # Show first 5
                    title = show.get('Name', 'Unknown')
                    year = show.get('ProductionYear', 'Unknown')
                    tmdb_id = show.get('ProviderIds', {}).get('Tmdb')
                    tvdb_id = show.get('ProviderIds', {}).get('Tvdb')

                    print(f"   - {title} ({year})")
                    print(f"     TMDB: {tmdb_id}, TVDB: {tvdb_id}")

                return {
                    "success": True,
                    "series": series,
                    "total_count": total_count,
                    "response_time": response_time
                }
            else:
                print(f"❌ Failed to get series! Status: {response.status_code}")
                return {"success": False, "status_code": response.status_code, "response": response.text}

        except httpx.RequestError as e:
            print(f"❌ Error getting series: {str(e)}")
            return {"success": False, "error": str(e)}

    def run_full_test(self) -> Dict[str, Any]:
        """Run complete API connectivity test suite"""
        print("🎭 Starting Jellyfin API Connectivity Tests")
        print("=" * 50)

        results = {
            "timestamp": datetime.now().isoformat(),
            "jellyfin_url": self.base_url,
            "tests": {}
        }

        # Test 1: Basic connectivity
        connection_result = self.test_connection()
        results["tests"]["connection"] = connection_result

        if not connection_result.get("success"):
            print("\n❌ Connection failed, aborting remaining tests")
            return results

        print()

        # Test 2: Get users
        users_result = self.get_users()
        results["tests"]["users"] = users_result

        if not users_result.get("success") or not users_result.get("users"):
            print("\n❌ No users found, aborting remaining tests")
            return results

        # Use first user for media tests
        first_user = users_result["users"][0]
        user_id = first_user["Id"]
        print(f"\n🎯 Using user '{first_user['Name']}' for media tests")
        print()

        # Test 3: Get libraries
        libraries_result = self.get_libraries(user_id)
        results["tests"]["libraries"] = libraries_result
        print()

        # Test 4: Get movies sample
        movies_result = self.get_movies_sample(user_id, limit=10)
        results["tests"]["movies"] = movies_result
        print()

        # Test 5: Get series sample
        series_result = self.get_series_sample(user_id, limit=10)
        results["tests"]["series"] = series_result

        # Summary
        print("\n" + "=" * 50)
        print("🏁 Test Results Summary:")

        success_count = sum(1 for test in results["tests"].values() if test.get("success"))
        total_tests = len(results["tests"])

        print(f"✅ Successful tests: {success_count}/{total_tests}")

        if movies_result.get("success"):
            print(f"🎬 Total movies in library: {movies_result.get('total_count', 0)}")

        if series_result.get("success"):
            print(f"📺 Total series in library: {series_result.get('total_count', 0)}")

        return results


def main():
    """Main test execution"""
    # Jellyfin configuration
    JELLYFIN_URL = "http://192.168.45.181:8097"  # jellyfin-stg container
    API_TOKEN = "0187d70ea6204155a984d9e09f8e6840"

    # Create tester instance
    tester = JellyfinAPITester(JELLYFIN_URL, API_TOKEN)

    # Run tests
    results = tester.run_full_test()

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"jellyfin_api_test_results_{timestamp}.json"

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Results saved to: {results_file}")

    return results


if __name__ == "__main__":
    main()