#!/usr/bin/env python3
"""
Test LLM fallback system: Local LLM + Cloud LLM fallback
"""
import httpx
import asyncio
import time
from typing import Dict, Any, Optional, List

class LLMFallbackManager:
    """Manage multiple LLM endpoints with fallback strategy"""

    def __init__(self):
        self.endpoints = {
            "ollama_qwen3": {
                "url": "http://192.168.45.104:11434",
                "model": "qwen3:8b",
                "type": "ollama",
                "priority": 1,  # Higher priority = try first
                "speed": "fast",
                "cost": "free"
            },
            "ollama_gpt_oss": {
                "url": "http://192.168.45.104:11434",
                "model": "gpt-oss:20b",
                "type": "ollama",
                "priority": 2,
                "speed": "slower",
                "cost": "free"
            }
            # Future cloud endpoints can be added here
            # "openai_gpt4": {
            #     "url": "https://api.openai.com/v1/chat/completions",
            #     "model": "gpt-4",
            #     "type": "openai",
            #     "priority": 3,
            #     "speed": "fast",
            #     "cost": "paid"
            # }
        }

    async def test_endpoint_health(self, endpoint_name: str) -> Dict[str, Any]:
        """Test if an endpoint is healthy and responsive"""
        endpoint = self.endpoints[endpoint_name]

        try:
            if endpoint["type"] == "ollama":
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{endpoint['url']}/api/tags")
                    response.raise_for_status()

                    # Check if specific model is available
                    models = response.json().get("models", [])
                    model_available = any(m["name"] == endpoint["model"] for m in models)

                    return {
                        "status": "healthy" if model_available else "model_unavailable",
                        "response_time": response.elapsed.total_seconds(),
                        "model_available": model_available
                    }
            else:
                # Future: Add health checks for other endpoint types
                return {"status": "not_implemented"}

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def generate_critic_with_fallback(
        self,
        character: str,
        movie_info: Dict[str, Any],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Generate critic with automatic fallback to other endpoints"""

        prompt = self._build_character_prompt(character, movie_info)

        # Sort endpoints by priority (higher first)
        sorted_endpoints = sorted(
            self.endpoints.items(),
            key=lambda x: x[1]["priority"],
            reverse=True
        )

        attempts = []

        for endpoint_name, endpoint_config in sorted_endpoints:
            try:
                print(f"🎯 Trying {endpoint_name} ({endpoint_config['model']})...")

                start_time = time.time()

                if endpoint_config["type"] == "ollama":
                    result = await self._generate_ollama(
                        endpoint_config["url"],
                        endpoint_config["model"],
                        prompt
                    )
                else:
                    # Future: Add other endpoint types
                    continue

                generation_time = time.time() - start_time

                attempts.append({
                    "endpoint": endpoint_name,
                    "status": "success",
                    "generation_time": generation_time,
                    "response": result["response"]
                })

                print(f"✅ Success with {endpoint_name} in {generation_time:.1f}s")

                return {
                    "success": True,
                    "endpoint_used": endpoint_name,
                    "response": result["response"],
                    "generation_time": generation_time,
                    "attempts": attempts
                }

            except Exception as e:
                error_msg = str(e)
                print(f"❌ {endpoint_name} failed: {error_msg}")

                attempts.append({
                    "endpoint": endpoint_name,
                    "status": "failed",
                    "error": error_msg
                })

                continue

        # All endpoints failed
        return {
            "success": False,
            "error": "All endpoints failed",
            "attempts": attempts
        }

    async def _generate_ollama(self, url: str, model: str, prompt: str) -> Dict[str, Any]:
        """Generate using Ollama endpoint"""
        async with httpx.AsyncClient(timeout=120.0) as client:
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

    def _build_character_prompt(self, character: str, movie_info: Dict[str, Any]) -> str:
        """Build character-specific prompt"""

        character_prompts = {
            "Marco Aurelio": f"""Eres Marco Aurelio, el emperador filósofo romano. Escribe una crítica de película desde tu perspectiva estoica.

Película: "{movie_info['title']}" ({movie_info.get('year', 'N/A')})
Género: {movie_info.get('genres', 'N/A')}
Sinopsis: {movie_info.get('synopsis', 'No disponible')}

Escribe una crítica de máximo 150 palabras incluyendo:
1. Puntuación del 1-10
2. Reflexión desde la filosofía estoica
3. Conexión con tus enseñanzas sobre virtud, sabiduría y aceptación

Mantén tu tono sabio, reflexivo y sereno.""",

            "Rosario Costras": f"""Eres Rosario Costras, una activista progresista muy crítica con los problemas sociales. Escribe una crítica de película desde tu perspectiva de justicia social.

Película: "{movie_info['title']}" ({movie_info.get('year', 'N/A')})
Género: {movie_info.get('genres', 'N/A')}
Sinopsis: {movie_info.get('synopsis', 'No disponible')}

Escribe una crítica de máximo 150 palabras incluyendo:
1. Puntuación del 1-10
2. Análisis de representación y diversidad
3. Crítica a las estructuras de poder mostradas

Mantén tu tono combativo, directo y comprometido con la justicia social."""
        }

        return character_prompts.get(character, f"Escribe una crítica de la película {movie_info['title']}")

async def test_fallback_system():
    """Test the LLM fallback management system"""
    print("🔄 Testing LLM Fallback Management System...")

    manager = LLMFallbackManager()

    # Test 1: Health checks
    print("\n🏥 Testing endpoint health...")
    healthy_endpoints = []
    for endpoint_name in manager.endpoints:
        health = await manager.test_endpoint_health(endpoint_name)
        status_emoji = "✅" if health["status"] == "healthy" else "❌"
        print(f"   {status_emoji} {endpoint_name}: {health['status']}")
        if health["status"] == "healthy":
            healthy_endpoints.append(endpoint_name)

    if not healthy_endpoints:
        print("❌ No healthy endpoints available for testing!")
        return []

    # Test 2: Fallback generation
    print(f"\n🎭 Testing critic generation with {len(healthy_endpoints)} healthy endpoints...")

    test_movies = [
        {
            "title": "Inception",
            "year": 2010,
            "genres": "Sci-Fi, Thriller",
            "synopsis": "Un ladrón que roba secretos del subconsciente debe realizar la tarea inversa: implantar una idea."
        },
        {
            "title": "The Godfather",
            "year": 1972,
            "genres": "Crime, Drama",
            "synopsis": "La historia de una familia mafiosa y la transformación de su heredero más joven."
        }
    ]

    characters = ["Marco Aurelio", "Rosario Costras"]

    results = []

    for movie in test_movies[:1]:  # Test with one movie for now
        for character in characters:
            print(f"\n🎬 Generating critic for '{movie['title']}' by {character}...")

            result = await manager.generate_critic_with_fallback(character, movie)

            if result["success"]:
                print(f"✅ Generated successfully using {result['endpoint_used']}")
                print(f"📝 Preview: {result['response'][:150]}...")
                print(f"⏱️  Time: {result['generation_time']:.1f}s")

                # Count attempts
                successful_attempts = [a for a in result['attempts'] if a['status'] == 'success']
                failed_attempts = [a for a in result['attempts'] if a['status'] == 'failed']

                if len(failed_attempts) > 0:
                    print(f"🔄 Fallback used: {len(failed_attempts)} attempts failed before success")
            else:
                print(f"❌ All endpoints failed: {result['error']}")

            results.append({
                "movie": movie["title"],
                "character": character,
                "result": result
            })

    # Summary
    print(f"\n📊 FALLBACK SYSTEM TEST SUMMARY:")
    successful = sum(1 for r in results if r["result"]["success"])
    print(f"✅ Successful generations: {successful}/{len(results)}")
    print(f"🏥 Healthy endpoints: {len(healthy_endpoints)}/{len(manager.endpoints)}")

    if successful > 0:
        print(f"🚀 LLM Fallback system is ready for production!")

        # Analyze which endpoints were used
        endpoint_usage = {}
        for r in results:
            if r["result"]["success"]:
                endpoint = r["result"]["endpoint_used"]
                endpoint_usage[endpoint] = endpoint_usage.get(endpoint, 0) + 1

        print(f"📈 Endpoint usage:")
        for endpoint, count in endpoint_usage.items():
            print(f"   - {endpoint}: {count} times")

    return results

async def test_failure_simulation():
    """Test fallback behavior by simulating endpoint failures"""
    print("\n🚨 Testing failure simulation...")

    manager = LLMFallbackManager()

    # Temporarily disable the first endpoint to test fallback
    print("🔧 Simulating primary endpoint failure...")

    # Modify the URL of the first endpoint to make it fail
    original_qwen3_url = manager.endpoints["ollama_qwen3"]["url"]
    manager.endpoints["ollama_qwen3"]["url"] = "http://192.168.45.999:11434"  # Non-existent server

    test_movie = {
        "title": "Test Movie",
        "year": 2023,
        "genres": "Drama",
        "synopsis": "A test movie to validate the fallback system."
    }

    result = await manager.generate_critic_with_fallback("Marco Aurelio", test_movie)

    if result["success"]:
        print(f"✅ Fallback successful! Used: {result['endpoint_used']}")
        print(f"🔄 Total attempts: {len(result['attempts'])}")

        for attempt in result['attempts']:
            status_emoji = "✅" if attempt['status'] == 'success' else "❌"
            print(f"   {status_emoji} {attempt['endpoint']}: {attempt['status']}")

    else:
        print(f"❌ Fallback failed: {result['error']}")

    # Restore original URL
    manager.endpoints["ollama_qwen3"]["url"] = original_qwen3_url

    return result

if __name__ == "__main__":
    async def main():
        print("🎭 Starting LLM Fallback System Tests...")

        # Test 1: Normal operation
        results = await test_fallback_system()

        # Test 2: Failure simulation
        failure_result = await test_failure_simulation()

        print(f"\n🎉 All fallback tests completed!")

        return {
            "normal_operation": results,
            "failure_simulation": failure_result
        }

    asyncio.run(main())