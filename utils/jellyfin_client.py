#!/usr/bin/env python3
"""
🎭 Parody Critics - Jellyfin API Client
Enhanced client for Jellyfin API with pagination, caching and error handling
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator, Tuple
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient

from .logger import get_logger, LogTimer, log_exception

logger = get_logger('jellyfin')


class JellyfinAPIError(Exception):
    """Custom exception for Jellyfin API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class JellyfinClient:
    """
    Async Jellyfin API client with pagination and progress tracking

    Features:
    - Async/await support for high performance
    - Automatic pagination for large libraries
    - Connection pooling and retries
    - Progress tracking with callbacks
    - Comprehensive error handling
    - Response caching for metadata
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        enable_cache: bool = True
    ):
        """
        Initialize Jellyfin client

        Args:
            base_url: Jellyfin server URL (e.g., "http://192.168.1.100:8096")
            api_key: Jellyfin API key for authentication
            user_id: User ID for user-specific content
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts
            enable_cache: Enable response caching
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user_id = user_id
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_cache = enable_cache

        # Session management
        self._client: Optional[AsyncClient] = None
        self._server_info: Optional[Dict] = None

        # Cache for metadata
        self._cache: Dict[str, Dict] = {} if enable_cache else {}

        logger.info(f"Initialized Jellyfin client for: {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Establish connection to Jellyfin server"""
        logger.info("Connecting to Jellyfin server")

        # Create HTTP client with connection pooling
        self._client = AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            follow_redirects=True
        )

        try:
            with LogTimer(logger, "Server info retrieval"):
                # Test connection and get server info
                self._server_info = await self._get_server_info()

            logger.info(
                f"Connected to Jellyfin: {self._server_info.get('ServerName', 'Unknown')} "
                f"v{self._server_info.get('Version', 'Unknown')}"
            )

            # Get user info if user_id provided
            if self.user_id:
                user_info = await self._get_user_info()
                logger.info(f"Authenticated as user: {user_info.get('Name', 'Unknown')}")

        except Exception as e:
            logger.error(f"Failed to connect to Jellyfin: {str(e)}")
            await self.close()
            raise JellyfinAPIError(f"Connection failed: {str(e)}")

    async def close(self):
        """Close connection to Jellyfin server"""
        if self._client:
            logger.debug("Closing Jellyfin connection")
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Make HTTP request to Jellyfin API

        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint (without base URL)
            params: URL parameters
            data: Request body data
            use_cache: Whether to use cached response

        Returns:
            JSON response as dictionary

        Raises:
            JellyfinAPIError: If request fails
        """
        if not self._client:
            raise JellyfinAPIError("Client not connected. Call connect() first.")

        # Build URL
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))

        # Add authentication
        if params is None:
            params = {}
        if self.api_key:
            params['api_key'] = self.api_key
        if self.user_id and 'UserId' not in params:
            params['UserId'] = self.user_id

        # Check cache for GET requests
        cache_key = f"{method}:{url}:{json.dumps(params, sort_keys=True)}"
        if method == 'GET' and use_cache and self.enable_cache and cache_key in self._cache:
            logger.debug(f"Cache hit for: {endpoint}")
            return self._cache[cache_key]

        # Make request with retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Request {method} {endpoint} (attempt {attempt + 1})")

                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data
                )

                # Handle HTTP errors
                if response.status_code >= 400:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(f"API error for {endpoint}: {error_msg}")

                    # Don't retry client errors (4xx)
                    if 400 <= response.status_code < 500:
                        raise JellyfinAPIError(error_msg, response.status_code, response.json() if response.content else None)

                    # Retry server errors (5xx)
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    raise JellyfinAPIError(error_msg, response.status_code, response.json() if response.content else None)

                # Parse JSON response
                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from {endpoint}: {str(e)}")
                    raise JellyfinAPIError(f"Invalid JSON response: {str(e)}")

                # Cache successful GET responses
                if method == 'GET' and use_cache and self.enable_cache:
                    self._cache[cache_key] = result

                return result

            except httpx.TimeoutException as e:
                last_error = JellyfinAPIError(f"Request timeout after {self.timeout}s")
                logger.warning(f"Timeout for {endpoint} (attempt {attempt + 1})")

            except httpx.ConnectError as e:
                last_error = JellyfinAPIError(f"Connection error: {str(e)}")
                logger.warning(f"Connection error for {endpoint} (attempt {attempt + 1})")

            except JellyfinAPIError:
                raise  # Re-raise our custom errors

            except Exception as e:
                last_error = JellyfinAPIError(f"Unexpected error: {str(e)}")
                logger.error(f"Unexpected error for {endpoint}: {str(e)}")
                log_exception(logger, e, f"Request to {endpoint}")

            # Wait before retry
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

        # All retries failed
        logger.error(f"All {self.max_retries + 1} attempts failed for {endpoint}")
        raise last_error or JellyfinAPIError(f"Request to {endpoint} failed after {self.max_retries + 1} attempts")

    async def _get_server_info(self) -> Dict:
        """Get Jellyfin server information"""
        return await self._make_request('GET', '/System/Info/Public')

    async def _get_user_info(self) -> Dict:
        """Get current user information"""
        if not self.user_id:
            raise JellyfinAPIError("User ID required for user info")
        return await self._make_request('GET', f'/Users/{self.user_id}')

    async def get_library_items_paginated(
        self,
        parent_id: Optional[str] = None,
        item_types: Optional[List[str]] = None,
        include_types: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        page_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Tuple[Dict, int, int], None]:
        """
        Get library items with pagination and progress tracking

        Args:
            parent_id: Parent folder ID (None for all libraries)
            item_types: Filter by item types (['Movie', 'Series', etc.])
            include_types: Include specific types only
            fields: Additional metadata fields to include
            page_size: Number of items per page
            progress_callback: Callback function for progress updates

        Yields:
            Tuple of (item_data, current_page, total_pages)
        """
        logger.info(f"Starting paginated library scan - page_size: {page_size}")

        # Build base parameters
        params = {
            'Recursive': True,
            'StartIndex': 0,
            'Limit': page_size,
            'SortBy': 'SortName',
            'SortOrder': 'Ascending'
        }

        if parent_id:
            params['ParentId'] = parent_id
        if item_types:
            params['IncludeItemTypes'] = ','.join(item_types)
        if include_types:
            params['IncludeItemTypes'] = ','.join(include_types)
        if fields:
            params['Fields'] = ','.join(fields)

        # Get first page to determine total count
        first_page = await self._make_request('GET', '/Items', params)
        total_items = first_page.get('TotalRecordCount', 0)
        total_pages = (total_items + page_size - 1) // page_size  # Ceiling division

        logger.info(f"Found {total_items} items across {total_pages} pages")

        if total_items == 0:
            logger.warning("No items found in library")
            return

        # Process first page
        current_page = 1
        if progress_callback:
            progress_callback(current_page, total_pages, len(first_page.get('Items', [])))

        for item in first_page.get('Items', []):
            yield item, current_page, total_pages

        # Process remaining pages
        for page in range(1, total_pages):
            current_page = page + 1
            params['StartIndex'] = page * page_size

            logger.debug(f"Fetching page {current_page}/{total_pages}")

            with LogTimer(logger, f"Page {current_page} fetch"):
                page_data = await self._make_request('GET', '/Items', params)

            items = page_data.get('Items', [])
            logger.debug(f"Page {current_page} contains {len(items)} items")

            if progress_callback:
                progress_callback(current_page, total_pages, len(items))

            for item in items:
                yield item, current_page, total_pages

    async def get_movies_and_series(
        self,
        fields: Optional[List[str]] = None,
        page_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Tuple[Dict, int, int], None]:
        """
        Get all movies and TV series from Jellyfin

        Args:
            fields: Additional metadata fields
            page_size: Items per page
            progress_callback: Progress update callback

        Yields:
            Tuple of (item_data, current_page, total_pages)
        """
        # Default fields for media information
        if fields is None:
            fields = [
                'Overview', 'Genres', 'ProductionYear', 'PremiereDate',
                'CommunityRating', 'OfficialRating', 'RunTimeTicks',
                'ProviderIds', 'MediaSources', 'Path'
            ]

        item_types = ['Movie', 'Series']

        async for item, page, total_pages in self.get_library_items_paginated(
            item_types=item_types,
            fields=fields,
            page_size=page_size,
            progress_callback=progress_callback
        ):
            yield item, page, total_pages

    async def get_item_by_id(self, item_id: str, fields: Optional[List[str]] = None) -> Dict:
        """
        Get single item by ID

        Args:
            item_id: Jellyfin item ID
            fields: Additional fields to include

        Returns:
            Item data dictionary
        """
        params = {}
        if fields:
            params['Fields'] = ','.join(fields)

        return await self._make_request('GET', f'/Items/{item_id}', params)

    async def search_items(
        self,
        query: str,
        item_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for items by name

        Args:
            query: Search query
            item_types: Filter by item types
            limit: Maximum results

        Returns:
            List of matching items
        """
        params = {
            'searchTerm': query,
            'Limit': limit,
            'Recursive': True
        }

        if item_types:
            params['IncludeItemTypes'] = ','.join(item_types)

        response = await self._make_request('GET', '/Items', params)
        return response.get('Items', [])

    def clear_cache(self):
        """Clear the response cache"""
        if self.enable_cache:
            self._cache.clear()
            logger.info("Jellyfin response cache cleared")

    @property
    def server_info(self) -> Optional[Dict]:
        """Get cached server information"""
        return self._server_info

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._client is not None and self._server_info is not None


# Utility functions for data extraction

def extract_media_info(jellyfin_item: Dict) -> Dict:
    """
    Extract relevant media information from Jellyfin item

    Args:
        jellyfin_item: Raw item data from Jellyfin API

    Returns:
        Cleaned media information dictionary
    """
    # Extract provider IDs
    provider_ids = jellyfin_item.get('ProviderIds', {})
    tmdb_id = provider_ids.get('Tmdb')
    imdb_id = provider_ids.get('Imdb')

    # Extract genres
    genres = []
    if 'Genres' in jellyfin_item and jellyfin_item['Genres']:
        genres = jellyfin_item['Genres']

    # Convert runtime from ticks to minutes
    runtime_minutes = None
    if 'RunTimeTicks' in jellyfin_item and jellyfin_item['RunTimeTicks']:
        # Jellyfin stores runtime in ticks (100-nanosecond units)
        runtime_minutes = int(jellyfin_item['RunTimeTicks'] / (10**7 * 60))

    # Extract year from ProductionYear or PremiereDate
    year = jellyfin_item.get('ProductionYear')
    if not year and 'PremiereDate' in jellyfin_item:
        try:
            premiere_date = jellyfin_item['PremiereDate']
            if premiere_date:
                year = int(premiere_date.split('-')[0])
        except (ValueError, IndexError):
            pass

    return {
        'jellyfin_id': jellyfin_item['Id'],
        'tmdb_id': tmdb_id,
        'imdb_id': imdb_id,
        'title': jellyfin_item.get('Name', ''),
        'original_title': jellyfin_item.get('OriginalTitle'),
        'year': year,
        'type': 'movie' if jellyfin_item.get('Type') == 'Movie' else 'series',
        'genres': json.dumps(genres) if genres else None,
        'overview': jellyfin_item.get('Overview'),
        'runtime': runtime_minutes,
        'vote_average': jellyfin_item.get('CommunityRating'),
        'vote_count': None,  # Jellyfin doesn't provide vote count
        'poster_url': None,  # We'll construct this from server info if needed
        'backdrop_url': None,  # We'll construct this from server info if needed
    }


def format_item_summary(item: Dict) -> str:
    """
    Format item for logging/display

    Args:
        item: Jellyfin item dictionary

    Returns:
        Formatted summary string
    """
    item_type = item.get('Type', 'Unknown')
    name = item.get('Name', 'Unnamed')
    year = item.get('ProductionYear', '????')

    return f"{item_type}: {name} ({year})"