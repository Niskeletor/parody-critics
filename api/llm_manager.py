"""
🎭 Parody Critics - LLM Manager
Hybrid LLM system with local and cloud fallback for critic generation
"""
import httpx
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

# Import our logging system
from utils.logger import get_logger, LogTimer, log_exception
from config import Config

logger = get_logger('llm_manager')

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

        prompt = self._build_character_prompt(character, media_info)
        attempts = []

        logger.info(f"Starting critic generation - Character: {character}, Media: {media_info.get('title', 'Unknown')}")

        for endpoint_name, endpoint_config in endpoints_to_try:
            try:
                logger.info(f"Attempting generation with {endpoint_name} ({endpoint_config['model']})")

                start_time = time.time()

                with LogTimer(logger, f"LLM generation ({endpoint_name})"):
                    result = await self._generate_with_endpoint(
                        endpoint_config,
                        prompt
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

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"❌ Generation failed with {endpoint_name}: {error_msg}")
                log_exception(logger, e, f"Generation with {endpoint_name}")

                attempts.append({
                    "endpoint": endpoint_name,
                    "model": endpoint_config["model"],
                    "status": "failed",
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                })

                if not getattr(self.config, 'LLM_ENABLE_FALLBACK', True):
                    # If fallback is disabled, stop after first failure
                    logger.info("Fallback disabled - stopping after first failure")
                    break

                continue

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
        prompt: str
    ) -> Dict[str, Any]:
        """Generate using specific endpoint"""

        if endpoint_config["type"] == "ollama":
            return await self._generate_ollama(
                endpoint_config["url"],
                endpoint_config["model"],
                prompt
            )
        elif endpoint_config["type"] == "openai":
            return await self._generate_openai(
                endpoint_config["model"],
                prompt
            )
        else:
            raise ValueError(f"Unsupported endpoint type: {endpoint_config['type']}")

    async def _generate_ollama(self, url: str, model: str, prompt: str) -> Dict[str, Any]:
        """Generate using Ollama endpoint"""
        timeout = getattr(self.config, 'LLM_TIMEOUT', 180)

        logger.debug(f"Sending request to Ollama: {url} with model {model}")

        async with httpx.AsyncClient(timeout=timeout) as client:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "max_tokens": 500,
                    "top_p": 0.9
                }
            }

            try:
                response = await client.post(f"{url}/api/generate", json=payload)
                response.raise_for_status()

                result = response.json()
                logger.debug(f"Ollama response received - Response length: {len(result.get('response', ''))}")

                return result

            except httpx.TimeoutException:
                raise Exception(f"Ollama request timed out after {timeout}s")
            except httpx.HTTPStatusError as e:
                raise Exception(f"Ollama HTTP error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                raise Exception(f"Ollama request failed: {str(e)}")

    async def _generate_openai(self, model: str, prompt: str) -> Dict[str, Any]:
        """Generate using OpenAI endpoint (future implementation)"""
        # Future implementation for OpenAI API
        raise NotImplementedError("OpenAI integration not yet implemented")

    def _build_character_prompt(self, character: str, media_info: Dict[str, Any]) -> str:
        """Build character-specific prompt using structured personality fields + variation engine"""

        title = media_info.get("title", "Obra sin título")
        year = media_info.get("year", "Año desconocido")
        media_type = media_info.get("type", "movie")
        genres = media_info.get("genres", "Géneros desconocidos")
        synopsis = media_info.get("synopsis", "Sin sinopsis disponible")
        type_label = "película" if media_type == "movie" else "serie"

        character_data = self._get_character_from_db(character)
        if not character_data:
            logger.warning(f"Character '{character}' not found in DB, using fallback prompt")
            return f'Escribe una crítica de la {type_label} "{title}" ({year}) en máximo 150 palabras. Incluye una puntuación del 1 al 10 al inicio.'

        character_id = character_data.get('id', '')
        emoji = character_data.get('emoji', '🎭')
        description = character_data.get('description', '')
        personality = character_data.get('personality', '')

        # Parse structured personality fields
        motifs = json.loads(character_data.get('motifs') or '[]')
        catchphrases = json.loads(character_data.get('catchphrases') or '[]')
        avoid = json.loads(character_data.get('avoid') or '[]')
        red_flags = json.loads(character_data.get('red_flags') or '[]')

        # Identity block — who the character is and how they speak
        if description:
            identity = description
        else:
            identity = f"Eres {character} {emoji}. Arquetipo: {personality}."

        # Variation pack — makes each critique feel different
        variation = self._select_variation_pack(character_id, motifs, catchphrases)

        variation_lines = []
        if variation['motifs']:
            variation_lines.append(
                f"Para esta crítica, enfoca tu análisis usando estos conceptos: {', '.join(variation['motifs'])}."
            )
        if variation['catchphrase']:
            variation_lines.append(
                f"Puedes usar esta frase si encaja: \"{variation['catchphrase']}\""
            )
        variation_block = "\n".join(variation_lines)

        # Critic lens — what to avoid and what to call out
        lens_lines = []
        if avoid:
            lens_lines.append(f"Evita: {'; '.join(avoid)}.")
        if red_flags:
            lens_lines.append(f"Lo que detestas (menciónalo si aparece en la obra): {'; '.join(red_flags)}.")
        lens_block = "\n".join(lens_lines)

        # Enriched context block (TMDB + Brave, cached in DB)
        enriched_block = ""
        raw_enriched = media_info.get("enriched_context")
        if raw_enriched:
            try:
                ec = json.loads(raw_enriched) if isinstance(raw_enriched, str) else raw_enriched
                parts = []
                if ec.get("director"):
                    parts.append(f"Director: {ec['director']}")
                if ec.get("cast"):
                    parts.append(f"Reparto: {', '.join(ec['cast'])}")
                if ec.get("tagline"):
                    parts.append(f"Tagline: \"{ec['tagline']}\"")
                if ec.get("overview_full") and len(ec["overview_full"]) > len(synopsis):
                    parts.append(f"Sinopsis completa: {ec['overview_full'][:500]}")
                if ec.get("keywords"):
                    parts.append(f"Keywords temáticas: {', '.join(ec['keywords'][:12])}")
                if ec.get("social_snippets"):
                    snips = "\n".join(f"- {s}" for s in ec["social_snippets"][:4])
                    parts.append(f"Contexto crítico y social:\n{snips}")
                if parts:
                    enriched_block = "\n\nCONTEXTO ENRIQUECIDO:\n" + "\n".join(parts)
            except Exception as e:
                logger.warning(f"Could not parse enriched_context: {e}")

        # Soul: loves and hates
        loves = json.loads(character_data.get("loves") or "[]")
        hates = json.loads(character_data.get("hates") or "[]")
        soul_lines = []
        if loves:
            soul_lines.append(f"\nAMAS en el cine: {', '.join(loves[:8])}")
        if hates:
            soul_lines.append(f"DETESTAS en el cine: {', '.join(hates[:8])}")
            soul_lines.append("Cuando detectas lo que odias, reacciona con intensidad genuina.")
        soul_block = "\n".join(soul_lines)

        prompt = f"""{identity}

{variation_block}

{lens_block}

{soul_block}

OBRA A CRITICAR:
Título: "{title}" ({year})
Tipo: {type_label.capitalize()}
Géneros: {genres}
Sinopsis: {synopsis}{enriched_block}

INSTRUCCIONES:
Escribe una crítica de máximo 150 palabras como {character} {emoji}.
Empieza siempre con la puntuación: X/10
Basa tu análisis en los datos reales de la obra que te hemos dado arriba.
No inventes tramas, personajes ni elementos que no aparezcan en la sinopsis.
Después analiza desde tu perspectiva y con tu tono auténtico.
Sé directo y personal."""

        return prompt

    def parse_critic_response(self, raw_response: str, character: str, media_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response to extract structured critic data"""

        # Extract rating (look for patterns like "8/10", "Puntuación: 7", etc.)
        rating = None
        rating_patterns = [
            r"(\d+)/10",
            r"Puntuación[:\s]*(\d+)",
            r"Calificación[:\s]*(\d+)",
            r"Nota[:\s]*(\d+)"
        ]

        import re
        for pattern in rating_patterns:
            match = re.search(pattern, raw_response, re.IGNORECASE)
            if match:
                try:
                    rating = min(10, max(1, int(match.group(1))))  # Ensure 1-10 range
                    break
                except ValueError:
                    continue

        # If no rating found, default to 5
        if rating is None:
            rating = 5
            logger.warning(f"No rating found in response for {character}, defaulting to {rating}")

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