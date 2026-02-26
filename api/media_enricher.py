"""
Media Enricher — fetches TMDB + Brave Search context for a media item
and caches the result in media.enriched_context (JSON).
"""
import json
import sqlite3
import urllib.parse
from datetime import datetime
from typing import Optional

import httpx

from utils.logger import get_logger

logger = get_logger("media_enricher")


class MediaEnricher:

    def __init__(self, db_path: str, tmdb_token: str, brave_key: str):
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
        brave_snips = await self._fetch_brave(
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
    # Brave Search fetch
    # ─────────────────────────────────────────────────────────────

    async def _fetch_brave(self, title: str, year: Optional[int]) -> list:
        if not self.brave_key:
            return []
        year_str = str(year) if year else ""
        query = f'"{title}" {year_str} critica opinion controversia reseña'.strip()
        url = (
            "https://api.search.brave.com/res/v1/web/search?"
            + urllib.parse.urlencode({"q": query, "count": 5})
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                url,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.brave_key,
                },
            )
            if resp.status_code == 429:
                logger.warning("Brave API quota exceeded — skipping snippets for this item")
                return []
            resp.raise_for_status()
            data = resp.json()

        snippets = []
        for r in data.get("web", {}).get("results", []):
            desc = r.get("description", "")
            desc = desc.replace("<strong>", "").replace("</strong>", "").strip()
            if desc:
                snippets.append(desc[:250])
        return snippets

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
