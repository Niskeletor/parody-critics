"""
🎭 Parody Critics - LLM Manager
Hybrid LLM system with local and cloud fallback for critic generation
"""
import asyncio
import httpx
import json
import random
import re
import sqlite3
import time
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

_OPENAI_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "groq":   "https://api.groq.com/openai/v1",
}


def _strip_think_blocks(text: str) -> str:
    """Remove <think>...</think> sections produced by reasoning models."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

class CriticGenerationManager:
    """Manage LLM endpoints with fallback for critic generation"""

    def __init__(self):
        self.config = Config()
        self.db_path = self.config.get_absolute_db_path()
        self.setup_endpoints()
        logger.info("CriticGenerationManager initialized successfully")

    def setup_endpoints(self):
        """Setup available LLM endpoints with priority order.

        When LLM_PROVIDER=ollama (default): primary + secondary both Ollama.
        When LLM_PROVIDER=groq|openai|anthropic: cloud primary, optional Ollama secondary.
        Fallback between endpoints respects LLM_ENABLE_FALLBACK.
        """
        self.endpoints = {}

        if self.config.LLM_PROVIDER == "ollama":
            self.endpoints["ollama_primary"] = {
                "url": self.config.LLM_OLLAMA_URL,
                "model": self.config.LLM_PRIMARY_MODEL,
                "type": "ollama",
                "priority": 1,
            }
            self.endpoints["ollama_secondary"] = {
                "url": self.config.LLM_OLLAMA_URL,
                "model": self.config.LLM_SECONDARY_MODEL,
                "type": "ollama",
                "priority": 2,
            }
        else:
            # Cloud primary
            if not self.config.LLM_API_KEY:
                logger.warning(
                    f"LLM_PROVIDER={self.config.LLM_PROVIDER} but LLM_API_KEY is empty — "
                    "generation will fail until a key is configured"
                )
            self.endpoints["cloud_primary"] = {
                "type": self.config.LLM_PROVIDER,   # "openai" | "groq" | "anthropic"
                "model": self.config.LLM_PRIMARY_MODEL,
                "api_key": self.config.LLM_API_KEY,
                "priority": 1,
            }
            # Ollama secondary as fallback (if a secondary model is configured)
            if self.config.LLM_SECONDARY_MODEL:
                self.endpoints["ollama_secondary"] = {
                    "url": self.config.LLM_OLLAMA_URL,
                    "model": self.config.LLM_SECONDARY_MODEL,
                    "type": "ollama",
                    "priority": 2,
                }

        logger.info(f"Configured {len(self.endpoints)} LLM endpoints: {list(self.endpoints.keys())}")

    def _get_character_from_db(self, character_name: str) -> Optional[Dict[str, Any]]:
        """Get character data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("""
                    SELECT id, name, emoji, personality, description,
                           motifs, catchphrases, avoid, red_flags, loves, hates
                    FROM characters
                    WHERE name = ? AND active = TRUE
                """, (character_name,)).fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting character from database: {e}")
            return None

    def _get_recent_motifs(self, character_id: str, limit: int = 15) -> List[str]:
        """Get recently used motifs for a character (for anti-repetition)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("""
                    SELECT motif FROM character_motif_history
                    WHERE character_id = ?
                    ORDER BY used_at DESC
                    LIMIT ?
                """, (character_id, limit)).fetchall()
            return [row[0] for row in rows]
        except Exception as e:
            logger.warning(f"Could not get recent motifs for {character_id}: {e}")
            return []

    def _record_motif_usage(self, character_id: str, motifs: List[str]):
        """Record used motifs and prune history to last 100 per character"""
        if not motifs:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(
                    "INSERT INTO character_motif_history (character_id, motif) VALUES (?, ?)",
                    [(character_id, m) for m in motifs],
                )
                # Keep history lean — last 100 per character
                conn.execute("""
                    DELETE FROM character_motif_history
                    WHERE character_id = ? AND id NOT IN (
                        SELECT id FROM character_motif_history
                        WHERE character_id = ?
                        ORDER BY used_at DESC
                        LIMIT 100
                    )
                """, (character_id, character_id))
        except Exception as e:
            logger.warning(f"Could not record motif usage for {character_id}: {e}")

    def _select_variation_pack(
        self, character_id: str, motifs: List[str], catchphrases: List[str]
    ) -> Dict[str, Any]:
        """Pick 2-3 motifs (avoiding recent) and optionally 1 catchphrase"""
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
        ep_type = endpoint["type"]

        try:
            if ep_type == "ollama":
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{endpoint['url']}/api/tags")
                    response.raise_for_status()
                    models = response.json().get("models", [])
                    model_available = any(m["name"] == endpoint["model"] for m in models)
                    return {
                        "status": "healthy" if model_available else "model_unavailable",
                        "model_available": model_available,
                        "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    }

            elif ep_type in ("openai", "groq"):
                # GET /models is a free call — validates the API key works
                base_url = _OPENAI_BASE_URLS[ep_type]
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(
                        f"{base_url}/models",
                        headers={"Authorization": f"Bearer {endpoint['api_key']}"},
                    )
                return {
                    "status": "healthy" if r.status_code == 200 else "auth_error",
                    "provider": ep_type,
                }

            elif ep_type == "anthropic":
                # Anthropic has no free health endpoint — check key presence only
                return {
                    "status": "healthy" if endpoint.get("api_key") else "no_api_key",
                    "provider": "anthropic",
                }

            return {"status": "unknown_type"}

        except Exception as e:
            logger.warning(f"Health check failed for {endpoint_name}: {str(e)}")
            log_exception(logger, e, f"Health check for {endpoint_name}")
            return {"status": "unhealthy", "error": str(e)}

    async def generate_critic(
        self,
        character: str,
        media_info: Dict[str, Any],
        force_endpoint: Optional[str] = None,
        language: str = "es",
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

        attempts = []

        logger.info(f"Starting critic generation - Character: {character}, Media: {media_info.get('title', 'Unknown')}")

        for endpoint_name, endpoint_config in endpoints_to_try:
            try:
                logger.info(f"Attempting generation with {endpoint_name} ({endpoint_config['model']})")

                profile = get_profile(endpoint_config["model"])
                messages = self._build_messages(character, media_info, profile, language=language)

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
        """Dispatch generation to the appropriate provider caller."""
        ep_type = endpoint_config["type"]

        if ep_type == "ollama":
            return await self._call_ollama_chat(
                endpoint_config["url"],
                endpoint_config["model"],
                messages,
                profile,
            )
        if ep_type in ("openai", "groq"):
            return await self._call_openai_chat(
                ep_type,
                endpoint_config["model"],
                endpoint_config["api_key"],
                messages,
                profile,
            )
        if ep_type == "anthropic":
            return await self._call_anthropic_chat(
                endpoint_config["model"],
                endpoint_config["api_key"],
                messages,
                profile,
            )
        raise ValueError(f"Unsupported endpoint type: {ep_type}")

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
                "repeat_penalty": 1.15,
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

    async def _call_openai_chat(
        self, provider: str, model: str, api_key: str,
        messages: List[Dict[str, str]], profile
    ) -> Dict[str, Any]:
        """Generate via OpenAI-compatible API (OpenAI and Groq share the same format).

        No connection retries — cloud endpoints don't have transient ConnectErrors.
        Errors map directly to existing LLM exception types.
        """
        base_url = _OPENAI_BASE_URLS[provider]
        timeout = getattr(self.config, "LLM_TIMEOUT", 60)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": profile.temperature,
            "max_tokens": 600,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(f"{provider} /chat/completions → model={model}")
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"{provider} timed out after {timeout}s (model={model})",
                timeout_seconds=timeout,
            ) from e
        except httpx.HTTPStatusError as e:
            raise LLMHTTPError(
                f"{provider} HTTP {e.response.status_code}: {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e

        content = response.json()["choices"][0]["message"]["content"]
        logger.debug(f"{provider} response — content_len={len(content)}")
        return {"response": content}

    async def _call_anthropic_chat(
        self, model: str, api_key: str,
        messages: List[Dict[str, str]], profile
    ) -> Dict[str, Any]:
        """Generate via Anthropic Messages API.

        Anthropic does not accept role:'system' inside messages — it must be
        passed as a top-level 'system' field. We extract it here.
        """
        timeout = getattr(self.config, "LLM_TIMEOUT", 60)

        # Extract system prompt (Anthropic requires it as a separate field)
        system = ""
        user_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                user_messages.append(m)

        payload = {
            "model": model,
            "max_tokens": 600,
            "temperature": profile.temperature,
            "messages": user_messages,
        }
        if system:
            payload["system"] = system

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.debug(f"anthropic /v1/messages → model={model}")
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Anthropic timed out after {timeout}s (model={model})",
                timeout_seconds=timeout,
            ) from e
        except httpx.HTTPStatusError as e:
            raise LLMHTTPError(
                f"Anthropic HTTP {e.response.status_code}: {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e

        content = response.json()["content"][0]["text"]
        logger.debug(f"anthropic response — content_len={len(content)}")
        return {"response": content}

    def _build_messages(
        self, character: str, media_info: Dict[str, Any], profile, language: str = "es"
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
        messages = build_messages(character_data, media_info, profile, variation, language=language)

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