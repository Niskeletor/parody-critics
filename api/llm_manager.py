"""
🎭 Parody Critics - LLM Manager
Hybrid LLM system with local and cloud fallback for critic generation
"""
import httpx
import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from config import get_config

logger = logging.getLogger(__name__)

class CriticGenerationManager:
    """Manage LLM endpoints with fallback for critic generation"""

    def __init__(self):
        self.config = get_config()
        self.setup_endpoints()

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
        if self.config.LLM_OPENAI_API_KEY:
            self.endpoints["openai_gpt4"] = {
                "url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4",
                "type": "openai",
                "priority": 3,
                "speed": "fast",
                "cost": "paid"
            }

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

        prompt = self._build_character_prompt(character, media_info)
        attempts = []

        for endpoint_name, endpoint_config in endpoints_to_try:
            try:
                logger.info(f"Attempting generation with {endpoint_name} ({endpoint_config['model']})")

                start_time = time.time()
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

                logger.info(f"Generation successful with {endpoint_name} in {generation_time:.1f}s")

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
                logger.warning(f"Generation failed with {endpoint_name}: {error_msg}")

                attempts.append({
                    "endpoint": endpoint_name,
                    "model": endpoint_config["model"],
                    "status": "failed",
                    "error": error_msg
                })

                if not self.config.LLM_ENABLE_FALLBACK:
                    # If fallback is disabled, stop after first failure
                    break

                continue

        # All endpoints failed
        logger.error(f"All endpoints failed for character {character}")
        return {
            "success": False,
            "error": "All LLM endpoints failed",
            "character": character,
            "media_title": media_info.get("title", "Unknown"),
            "attempts": attempts
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
        async with httpx.AsyncClient(timeout=self.config.LLM_TIMEOUT) as client:
            response = await client.post(
                f"{url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()

    async def _generate_openai(self, model: str, prompt: str) -> Dict[str, Any]:
        """Generate using OpenAI endpoint (future implementation)"""
        # Future implementation for OpenAI API
        raise NotImplementedError("OpenAI integration not yet implemented")

    def _build_character_prompt(self, character: str, media_info: Dict[str, Any]) -> str:
        """Build character-specific prompt for critic generation"""

        # Base media information
        title = media_info.get("title", "Película sin título")
        year = media_info.get("year", "Año desconocido")
        media_type = media_info.get("type", "movie")
        genres = media_info.get("genres", "Géneros desconocidos")
        synopsis = media_info.get("synopsis", "Sin sinopsis disponible")

        # Character-specific prompts
        character_prompts = {
            "Marco Aurelio": f"""Eres Marco Aurelio, el emperador filósofo romano (121-180 d.C.). Debes escribir una crítica de {'película' if media_type == 'movie' else 'serie'} desde tu perspectiva estoica y filosófica.

INFORMACIÓN DE LA OBRA:
Título: "{title}" ({year})
Tipo: {media_type.title()}
Géneros: {genres}
Sinopsis: {synopsis}

INSTRUCCIONES:
Escribe una crítica de máximo 150 palabras que incluya:

1. **Puntuación**: Califica del 1 al 10 la obra
2. **Reflexión estoica**: Analiza la obra desde los principios del estoicismo
3. **Enseñanzas**: Conecta con tus conceptos de virtud, sabiduría, aceptación del destino y control de las emociones
4. **Perspectiva imperial**: Reflexiona desde tu experiencia como emperador y filósofo

TONO: Sabio, reflexivo, sereno. Usa un lenguaje elevado pero accesible. Menciona conceptos estoicos como la ataraxia, el logos universal, la memento mori, etc.

Estructura tu respuesta claramente con la puntuación al inicio.""",

            "Rosario Costras": f"""Eres Rosario Costras, una activista progresista del siglo XXI muy crítica con los problemas sociales y estructuras de poder. Debes escribir una crítica de {'película' if media_type == 'movie' else 'serie'} desde tu perspectiva de justicia social.

INFORMACIÓN DE LA OBRA:
Título: "{title}" ({year})
Tipo: {media_type.title()}
Géneros: {genres}
Sinopsis: {synopsis}

INSTRUCCIONES:
Escribe una crítica de máximo 150 palabras que incluya:

1. **Puntuación**: Califica del 1 al 10 la obra (con perspectiva crítica social)
2. **Representación**: Analiza diversidad racial, de género, orientación sexual y clase social
3. **Estructuras de poder**: Critica las dinámicas de poder y privilegio mostradas
4. **Impacto social**: Evalúa si refuerza o desafía estereotipos y normas problemáticas

TONO: Combativo, directo, comprometido con la justicia social. Usa lenguaje actual y términos de activismo social. No tengas miedo de ser crítica cuando sea necesario.

Estructura tu respuesta claramente con la puntuación al inicio."""
        }

        default_prompt = f"""Escribe una crítica breve de la obra "{title}" ({year}) de máximo 150 palabras incluyendo una puntuación del 1 al 10."""

        return character_prompts.get(character, default_prompt)

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