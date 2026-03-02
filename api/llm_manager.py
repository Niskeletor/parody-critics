"""
🎭 Parody Critics - LLM Manager
Hybrid LLM system with local and cloud fallback for critic generation
"""
import asyncio
import httpx
import re
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import our logging system
from utils.logger import get_logger, LogTimer, log_exception
from config import Config
try:
    from model_profiles import get_profile  # noqa: E402
    from prompt_builder import build_messages  # noqa: E402
    from llm_errors import LLMConnectionError, LLMTimeoutError, LLMHTTPError  # noqa: E402
except ImportError:
    from api.model_profiles import get_profile  # noqa: E402
    from api.prompt_builder import build_messages  # noqa: E402
    from api.llm_errors import LLMConnectionError, LLMTimeoutError, LLMHTTPError  # noqa: E402

# Retry config: only on connection errors (transient). Never on timeouts —
# if Ollama already spent 180s once, retrying wastes another 180s.
_CONNECT_RETRY_ATTEMPTS = 3
_CONNECT_RETRY_BACKOFF = 2.0  # seconds; doubles each attempt (2s, 4s)

logger = get_logger('llm_manager')


def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> sections produced by reasoning models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

class CriticGenerationManager:
    """Manage LLM endpoints with fallback for critic generation"""

    def __init__(self):
        self.config = Config()
        self.db_path = self.config.get_absolute_db_path()
        self.setup_endpoints()

        # Statistics tracking
        self.generation_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'character_stats': {}
        }

        logger.info("CriticGenerationManager initialized successfully")

    def setup_endpoints(self):
        """Setup available LLM endpoints with priority order"""
        self.endpoints = {
            "ollama_primary": {
                "url": self.config.LLM_OLLAMA_URL,
                "model": self.config.LLM_PRIMARY_MODEL,
                "type": "ollama",
                "priority": 1,  # Try first
                "speed": "fast",
                "cost": "free"
            },
            "ollama_secondary": {
                "url": self.config.LLM_OLLAMA_URL,
                "model": self.config.LLM_SECONDARY_MODEL,
                "type": "ollama",
                "priority": 2,  # Try second
                "speed": "slower",
                "cost": "free"
            }
        }

        # Future cloud endpoints
        if hasattr(self.config, 'LLM_OPENAI_API_KEY') and self.config.LLM_OPENAI_API_KEY:
            self.endpoints["openai_gpt4"] = {
                "url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4",
                "type": "openai",
                "priority": 3,
                "speed": "fast",
                "cost": "paid"
            }
            logger.info("OpenAI endpoint configured")

        logger.info(f"Configured {len(self.endpoints)} LLM endpoints: {list(self.endpoints.keys())}")

    def _get_character_from_db(self, character_name: str) -> Optional[Dict[str, Any]]:
        """Get character data from database"""
        import sqlite3

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, emoji, personality, description,
                       motifs, catchphrases, avoid, red_flags, loves, hates
                FROM characters
                WHERE name = ? AND active = TRUE
            """, (character_name,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting character from database: {e}")
            return None

    def _get_recent_motifs(self, character_id: str, limit: int = 15) -> List[str]:
        """Get recently used motifs for a character (for anti-repetition)"""
        import sqlite3
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT motif FROM character_motif_history
                WHERE character_id = ?
                ORDER BY used_at DESC
                LIMIT ?
            """, (character_id, limit))
            result = [row[0] for row in cursor.fetchall()]
            conn.close()
            return result
        except Exception as e:
            logger.warning(f"Could not get recent motifs for {character_id}: {e}")
            return []

    def _record_motif_usage(self, character_id: str, motifs: List[str]):
        """Record used motifs and prune history to last 100 per character"""
        import sqlite3
        if not motifs:
            return
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for motif in motifs:
                cursor.execute(
                    "INSERT INTO character_motif_history (character_id, motif) VALUES (?, ?)",
                    (character_id, motif)
                )
            # Keep history lean — last 100 per character
            cursor.execute("""
                DELETE FROM character_motif_history
                WHERE character_id = ? AND id NOT IN (
                    SELECT id FROM character_motif_history
                    WHERE character_id = ?
                    ORDER BY used_at DESC
                    LIMIT 100
                )
            """, (character_id, character_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not record motif usage for {character_id}: {e}")

    def _select_variation_pack(
        self, character_id: str, motifs: List[str], catchphrases: List[str]
    ) -> Dict[str, Any]:
        """Pick 2-3 motifs (avoiding recent) and optionally 1 catchphrase"""
        import random
        if not motifs:
            return {"motifs": [], "catchphrase": None}

        recent = set(self._get_recent_motifs(character_id, limit=15))
        available = [m for m in motifs if m not in recent]

        # If all motifs have been used recently, reset and use all
        if len(available) < 2:
            available = motifs

        count = min(3, len(available))
        selected = random.sample(available, count)
        catchphrase = random.choice(catchphrases) if catchphrases and random.random() > 0.4 else None

        self._record_motif_usage(character_id, selected)
        logger.debug(f"Variation pack for {character_id}: motifs={selected}, catchphrase={'yes' if catchphrase else 'no'}")
        return {"motifs": selected, "catchphrase": catchphrase}

    async def health_check_endpoint(self, endpoint_name: str) -> Dict[str, Any]:
        """Check if an endpoint is healthy and responsive"""
        endpoint = self.endpoints[endpoint_name]

        try:
            if endpoint["type"] == "ollama":
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{endpoint['url']}/api/tags")
                    response.raise_for_status()

                    models = response.json().get("models", [])
                    model_available = any(m["name"] == endpoint["model"] for m in models)

                    return {
                        "status": "healthy" if model_available else "model_unavailable",
                        "model_available": model_available,
                        "response_time": response.elapsed.total_seconds() if response.elapsed else 0
                    }
            else:
                # Future: Add health checks for other endpoint types
                return {"status": "not_implemented"}

        except Exception as e:
            logger.warning(f"Health check failed for {endpoint_name}: {str(e)}")
            log_exception(logger, e, f"Health check for {endpoint_name}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def generate_critic(
        self,
        character: str,
        media_info: Dict[str, Any],
        force_endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate critic with automatic fallback"""

        if force_endpoint and force_endpoint in self.endpoints:
            # Use specific endpoint if requested
            endpoints_to_try = [(force_endpoint, self.endpoints[force_endpoint])]
        else:
            # Use priority order with fallback
            endpoints_to_try = sorted(
                self.endpoints.items(),
                key=lambda x: x[1]["priority"]
            )

        # Update stats
        self.generation_stats['total_requests'] += 1

        # Track character usage
        if character not in self.generation_stats['character_stats']:
            self.generation_stats['character_stats'][character] = {
                'requests': 0,
                'successful': 0,
                'avg_time': 0.0
            }

        self.generation_stats['character_stats'][character]['requests'] += 1

        attempts = []

        logger.info(f"Starting critic generation - Character: {character}, Media: {media_info.get('title', 'Unknown')}")

        for endpoint_name, endpoint_config in endpoints_to_try:
            try:
                logger.info(f"Attempting generation with {endpoint_name} ({endpoint_config['model']})")

                profile = get_profile(endpoint_config["model"])
                messages = self._build_messages(character, media_info, profile)

                logger.info(
                    f"[profile: {endpoint_config['model']} "
                    f"think={profile.think} temp={profile.temperature}]"
                )

                start_time = time.time()

                with LogTimer(logger, f"LLM generation ({endpoint_name})"):
                    result = await self._generate_with_endpoint(
                        endpoint_config,
                        messages,
                        profile,
                    )

                generation_time = time.time() - start_time

                attempts.append({
                    "endpoint": endpoint_name,
                    "model": endpoint_config["model"],
                    "status": "success",
                    "generation_time": generation_time,
                    "response": result["response"]
                })

                # Update success stats
                self.generation_stats['successful_requests'] += 1
                self.generation_stats['total_time'] += generation_time
                self.generation_stats['character_stats'][character]['successful'] += 1

                # Update character average time
                char_stats = self.generation_stats['character_stats'][character]
                if char_stats['successful'] > 0:
                    char_stats['avg_time'] = ((char_stats['avg_time'] * (char_stats['successful'] - 1)) + generation_time) / char_stats['successful']

                logger.info(f"✅ Generation successful with {endpoint_name} in {generation_time:.1f}s - Character: {character}")

                return {
                    "success": True,
                    "endpoint_used": endpoint_name,
                    "model_used": endpoint_config["model"],
                    "character": character,
                    "media_title": media_info.get("title", "Unknown"),
                    "response": result["response"],
                    "generation_time": generation_time,
                    "attempts": attempts
                }

            except LLMTimeoutError as e:
                logger.warning(
                    f"⏱️ {endpoint_name} timed out after {e.timeout_seconds}s "
                    f"— trying next endpoint"
                )
                attempts.append({
                    "endpoint": endpoint_name,
                    "model": endpoint_config["model"],
                    "status": "timeout",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

            except LLMConnectionError as e:
                logger.warning(
                    f"🔌 {endpoint_name} unreachable after retries — trying next endpoint"
                )
                attempts.append({
                    "endpoint": endpoint_name,
                    "model": endpoint_config["model"],
                    "status": "connection_error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

            except LLMHTTPError as e:
                logger.warning(
                    f"🌐 {endpoint_name} HTTP {e.status_code} — trying next endpoint"
                )
                attempts.append({
                    "endpoint": endpoint_name,
                    "model": endpoint_config["model"],
                    "status": f"http_{e.status_code}",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

            except Exception as e:
                logger.warning(
                    f"❌ {endpoint_name} unexpected error — trying next endpoint"
                )
                log_exception(logger, e, f"Generation with {endpoint_name}")
                attempts.append({
                    "endpoint": endpoint_name,
                    "model": endpoint_config["model"],
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

            if not self.config.LLM_ENABLE_FALLBACK:
                logger.info("Fallback disabled — stopping after first failure")
                break

        # All endpoints failed
        self.generation_stats['failed_requests'] += 1

        error_summary = f"All {len(endpoints_to_try)} endpoints failed for character {character}"
        logger.error(f"🚨 {error_summary}")

        return {
            "success": False,
            "error": "All LLM endpoints failed",
            "character": character,
            "media_title": media_info.get("title", "Unknown"),
            "attempts": attempts,
            "timestamp": datetime.now().isoformat()
        }

    async def _generate_with_endpoint(
        self,
        endpoint_config: Dict[str, Any],
        messages: List[Dict[str, str]],
        profile,
    ) -> Dict[str, Any]:
        """Generate using specific endpoint"""

        if endpoint_config["type"] == "ollama":
            return await self._call_ollama_chat(
                endpoint_config["url"],
                endpoint_config["model"],
                messages,
                profile,
            )
        elif endpoint_config["type"] == "openai":
            return await self._generate_openai(
                endpoint_config["model"],
                messages,
            )
        else:
            raise ValueError(f"Unsupported endpoint type: {endpoint_config['type']}")

    async def _call_ollama_chat(
        self, url: str, model: str, messages: List[Dict[str, str]], profile
    ) -> Dict[str, Any]:
        """Generate using Ollama /api/chat with profile-driven parameters.

        Retry policy:
        - ConnectError (server unreachable): up to _CONNECT_RETRY_ATTEMPTS with
          exponential backoff. Transient — worth retrying.
        - TimeoutException: no retry. If 180s wasn't enough once, retrying wastes
          another 180s. Caller should try the secondary model instead.
        - HTTPStatusError: no retry. HTTP errors are deterministic.
        """
        timeout = getattr(self.config, 'LLM_TIMEOUT', 180)

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": profile.think,
            "options": {
                "temperature": profile.temperature,
                "num_predict": profile.num_predict,
                "top_p": profile.top_p,
                "top_k": profile.top_k,
            },
        }

        last_connect_error: Optional[Exception] = None

        for attempt in range(_CONNECT_RETRY_ATTEMPTS):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    logger.debug(
                        f"Ollama /api/chat → {url} model={model} "
                        f"(attempt {attempt + 1}/{_CONNECT_RETRY_ATTEMPTS})"
                    )
                    response = await client.post(f"{url}/api/chat", json=payload)
                    response.raise_for_status()

                result = response.json()
                msg = result.get("message", {})
                raw_content = msg.get("content", "")

                # deepseek-r1 with think=True can return empty content —
                # all reasoning goes to message.thinking.
                if not raw_content.strip() and msg.get("thinking"):
                    logger.warning(
                        f"Empty content from {model} — falling back to message.thinking"
                    )
                    raw_content = msg["thinking"]

                if profile.strip_think:
                    raw_content = _strip_think_blocks(raw_content)

                thinking_len = len(msg.get("thinking", ""))
                logger.debug(
                    f"Ollama response — content_len={len(raw_content)} "
                    f"thinking_len={thinking_len}"
                )
                return {"response": raw_content}

            except httpx.TimeoutException as e:
                # Don't retry — propagate immediately so caller tries secondary
                raise LLMTimeoutError(
                    f"Ollama timed out after {timeout}s (model={model})",
                    timeout_seconds=timeout,
                ) from e

            except httpx.HTTPStatusError as e:
                raise LLMHTTPError(
                    f"Ollama HTTP {e.response.status_code}: {e.response.text[:200]}",
                    status_code=e.response.status_code,
                ) from e

            except httpx.ConnectError as e:
                last_connect_error = e
                if attempt < _CONNECT_RETRY_ATTEMPTS - 1:
                    wait = _CONNECT_RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Ollama connection failed (attempt {attempt + 1}), "
                        f"retrying in {wait:.0f}s — {e}"
                    )
                    await asyncio.sleep(wait)
                    continue

        raise LLMConnectionError(
            f"Could not connect to Ollama at {url} after {_CONNECT_RETRY_ATTEMPTS} attempts",
        ) from last_connect_error

    async def _generate_openai(self, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate using OpenAI endpoint (future implementation)"""
        raise NotImplementedError("OpenAI integration not yet implemented")

    def _build_messages(
        self, character: str, media_info: Dict[str, Any], profile
    ) -> List[Dict[str, str]]:
        """Build chat messages for critic generation, delegating to prompt_builder."""
        media_type = media_info.get("type", "movie")
        type_label = "película" if media_type == "movie" else "serie"
        title = media_info.get("title", "Obra sin título")
        year = media_info.get("year", "Año desconocido")

        character_data = self._get_character_from_db(character)
        logger.debug(f"Character '{character}' {'found' if character_data else 'NOT found'} in DB")

        if not character_data:
            logger.warning(f"Character '{character}' not found in DB, using fallback messages")
            fallback = f'Escribe una crítica de la {type_label} "{title}" ({year}) en máximo 150 palabras. Incluye una puntuación del 1 al 10 al inicio.'
            return [{"role": "user", "content": fallback}]

        character_id = character_data.get("id", "")
        motifs = json.loads(character_data.get("motifs") or "[]")
        catchphrases = json.loads(character_data.get("catchphrases") or "[]")

        variation = self._select_variation_pack(character_id, motifs, catchphrases)
        messages = build_messages(character_data, media_info, profile, variation)

        logger.debug(
            f"Messages built for '{character}' — "
            f"think={profile.think}, system_in_user={profile.system_in_user}"
        )
        return messages

    def parse_critic_response(self, raw_response: str, character: str, media_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response to extract structured critic data"""

        # Extract rating (look for patterns like "8/10", "Puntuación: 7", etc.)
        rating = None
        rating_patterns = [
            r"\b(\d{1,2})/10",           # 8/10 — most common
            r"Puntuación[:\s]*(\d{1,2})",
            r"Calificación[:\s]*(\d{1,2})",
            r"Nota[:\s]*(\d{1,2})",
            r"^(\d{1,2})\s*[/\-]",       # line starting with number
        ]

        import re
        for pattern in rating_patterns:
            match = re.search(pattern, raw_response, re.IGNORECASE | re.MULTILINE)
            if match:
                try:
                    candidate = int(match.group(1))
                    if 1 <= candidate <= 10:
                        rating = candidate
                        break
                except ValueError:
                    continue

        # If no rating found, default to 5
        if rating is None:
            rating = 5
            logger.warning(f"No rating found in response for {character}, defaulting to {rating}")
        else:
            logger.debug(f"Rating parsed: {rating}/10 for {character}")

        return {
            "rating": rating,
            "content": raw_response.strip(),
            "character": character,
            "media_id": media_info.get("id"),
            "tmdb_id": media_info.get("tmdb_id"),
            "generated_at": time.time()
        }

    async def get_system_status(self) -> Dict[str, Any]:
        """Get status of all LLM endpoints"""
        status = {
            "timestamp": time.time(),
            "total_endpoints": len(self.endpoints),
            "endpoints": {}
        }

        for endpoint_name in self.endpoints:
            health = await self.health_check_endpoint(endpoint_name)
            status["endpoints"][endpoint_name] = {
                "model": self.endpoints[endpoint_name]["model"],
                "status": health["status"],
                "priority": self.endpoints[endpoint_name]["priority"]
            }

        healthy_count = sum(1 for ep in status["endpoints"].values() if ep["status"] == "healthy")
        status["healthy_endpoints"] = healthy_count
        status["system_status"] = "operational" if healthy_count > 0 else "degraded"

        return status