"""
Media Enricher — fetches TMDB + FilmAffinity/Letterboxd context for a media item
and caches the result in media.enriched_context (JSON).
"""
import json
import sqlite3
from datetime import datetime
from typing import Optional

import httpx

from utils.logger import get_logger

logger = get_logger("media_enricher")


class MediaEnricher:

    def __init__(self, db_path: str, tmdb_token: str, brave_key: str = ""):
        self.db_path = db_path
        self.tmdb_token = tmdb_token
        self.brave_key = brave_key

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    async def enrich(self, media_id: int, tmdb_id: str, title: str,
                     year: Optional[int], media_type: str) -> dict:
        """Fetch TMDB + Brave context, cache in DB, return context dict."""
        logger.info(f"Enriching: {title} ({year}) — tmdb_id={tmdb_id}")

        tmdb_data   = await self._fetch_tmdb(tmdb_id, media_type)
        brave_snips = await self._fetch_social_snippets(
            tmdb_data.get("title") or tmdb_data.get("name") or title, year
        )

        context = self._build_context(tmdb_data, brave_snips)
        self._save(media_id, context)
        logger.info(f"✅ Enriched: {title} — {len(context['keywords'])} keywords, "
                    f"{len(context['social_snippets'])} snippets")
        return context

    async def enrich_all(
        self,
        limit: int = 500,
        session_id: str = None,
        progress_callback=None,
        cancelled_sessions: set = None,
    ) -> dict:
        """Enrich all media items that have no enriched_context yet."""
        rows = self._get_unenriched(limit)
        total   = len(rows)
        success = 0
        errors  = 0

        logger.info(f"Starting batch enrichment: {total} items pending")

        for i, row in enumerate(rows):
            if cancelled_sessions and session_id and session_id in cancelled_sessions:
                logger.info(f"Enrichment session {session_id} cancelled at {i}/{total}")
                break

            try:
                await self.enrich(
                    media_id   = row["id"],
                    tmdb_id    = row["tmdb_id"],
                    title      = row["title"],
                    year       = row.get("year"),
                    media_type = row["type"],
                )
                success += 1
            except Exception as e:
                logger.warning(f"Failed to enrich {row['title']}: {e}")
                errors += 1

            if progress_callback:
                await progress_callback(i + 1, total, row["title"])

        return {"total": total, "success": success, "errors": errors}

    def get_status(self) -> dict:
        """Return enrichment coverage stats."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM media")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM media WHERE enriched_context IS NOT NULL")
        enriched = cursor.fetchone()[0]
        conn.close()
        return {"total": total, "enriched": enriched, "pending": total - enriched}

    # ─────────────────────────────────────────────────────────────
    # TMDB fetch
    # ─────────────────────────────────────────────────────────────

    async def _fetch_tmdb(self, tmdb_id: str, media_type: str) -> dict:
        endpoint = "tv" if media_type == "series" else "movie"
        url = (
            f"https://api.themoviedb.org/3/{endpoint}/{tmdb_id}"
            "?language=es-ES&append_to_response=keywords,credits"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {self.tmdb_token}"}
            )
            resp.raise_for_status()
            return resp.json()

    # ─────────────────────────────────────────────────────────────
    # Social snippet fetch (FilmAffinity + Letterboxd)
    # ─────────────────────────────────────────────────────────────

    async def _fetch_social_snippets(self, title: str, year: Optional[int]) -> list:
        """Fetch from FilmAffinity (ES) + Letterboxd (EN). No API key needed."""
        import asyncio
        fa, lb = await asyncio.gather(
            self._fetch_filmaffinity(title, year),
            self._fetch_letterboxd(title, year),
            return_exceptions=True
        )
        snippets = []
        if isinstance(fa, list):
            snippets.extend(fa)
        if isinstance(lb, list):
            snippets.extend(lb)
        return snippets[:6]

    async def _fetch_filmaffinity(self, title: str, year: Optional[int]) -> list:
        import asyncio
        import re
        import html as _html
        def _search():
            from ddgs import DDGS
            query = f'"{title}" {year or ""} site:filmaffinity.com/es/reviews'.strip()
            with DDGS() as d:
                return d.text(query, max_results=4)
        try:
            results = await asyncio.to_thread(_search)
            film_id = None
            for r in (results or []):
                m = re.search(r'/(\d{5,7})\.html', r.get('href',''))
                if m:
                    film_id = m.group(1)
                    break
            if not film_id:
                return []
            resp = await asyncio.to_thread(
                lambda: __import__('httpx').get(
                    f'https://www.filmaffinity.com/es/reviews/1/{film_id}.html',
                    headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120'},
                    timeout=10, follow_redirects=True
                )
            )
            if resp.status_code != 200:
                return []
            texts = re.findall(r'>([^<>{}\n]{80,})<', resp.text)
            clean = []
            for t in texts:
                t = _html.unescape(t.strip())
                if len(t) > 80 and 'filmaffinity' not in t.lower() and 'cookie' not in t.lower():
                    clean.append('[FA] ' + t[:240])
            return clean[:3]
        except Exception as e:
            logger.warning(f"FilmAffinity fetch failed for {title}: {e}")
            return []

    async def _fetch_letterboxd(self, title: str, year: Optional[int]) -> list:
        import asyncio
        import re
        import html as _html
        def _search():
            from ddgs import DDGS
            query = f'"{title}" {year or ""} site:letterboxd.com/film'.strip()
            with DDGS() as d:
                return d.text(query, max_results=3)
        try:
            results = await asyncio.to_thread(_search)
            slug = None
            for r in (results or []):
                m = re.search(r'letterboxd\.com/film/([^/\s]+)/?', r.get('href',''))
                if m:
                    slug = m.group(1)
                    break
            if not slug:
                return []
            resp = await asyncio.to_thread(
                lambda: __import__('httpx').get(
                    f'https://letterboxd.com/film/{slug}/',
                    headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120'},
                    timeout=10, follow_redirects=True
                )
            )
            if resp.status_code != 200:
                return []
            texts = re.findall(r'>([^<>{}\n]{60,})<', resp.text)
            clean = []
            skip = {'letterboxd', 'sign in', 'create account', 'system.import', 'log in', 'films', 'lists', 'members'}
            for t in texts:
                t = _html.unescape(t.strip())
                tl = t.lower()
                if len(t) > 60 and not any(s in tl for s in skip) and '•' not in t:
                    clean.append('[LB] ' + t[:200])
            return clean[:3]
        except Exception as e:
            logger.warning(f"Letterboxd fetch failed for {title}: {e}")
            return []

    async def _fetch_brave(self, title: str, year: Optional[int]) -> list:
        """Kept for reference. No-op — replaced by _fetch_social_snippets."""
        return []

    # ─────────────────────────────────────────────────────────────
    # Context pack builder
    # ─────────────────────────────────────────────────────────────

    def _build_context(self, tmdb: dict, snippets: list) -> dict:
        # Director
        crew = tmdb.get("credits", {}).get("crew", [])
        director = next((c["name"] for c in crew if c.get("job") == "Director"), "")

        # Top 3 cast
        cast = [c["name"] for c in tmdb.get("credits", {}).get("cast", [])[:3]]

        # Keywords (movie uses 'keywords', tv uses 'results')
        kw_block = tmdb.get("keywords", {})
        kw_list  = kw_block.get("keywords") or kw_block.get("results") or []
        keywords = [k["name"] for k in kw_list[:15]]

        return {
            "title_canonical": tmdb.get("title") or tmdb.get("name", ""),
            "tagline":         tmdb.get("tagline", ""),
            "overview_full":   tmdb.get("overview", ""),
            "director":        director,
            "cast":            cast,
            "keywords":        keywords,
            "social_snippets": snippets[:4],
            "enriched_at":     datetime.now().isoformat(),
        }

    # ─────────────────────────────────────────────────────────────
    # DB helpers
    # ─────────────────────────────────────────────────────────────

    def _save(self, media_id: int, context: dict):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE media SET enriched_context = ?, enriched_at = ? WHERE id = ?",
            (json.dumps(context, ensure_ascii=False), context["enriched_at"], media_id),
        )
        conn.commit()
        conn.close()

    def _get_unenriched(self, limit: int) -> list:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, tmdb_id, title, year, type FROM media "
            "WHERE enriched_context IS NULL LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
