#!/usr/bin/env python3
"""
Test LLM connectivity and character prompt generation
"""
import httpx
import json
import time
from typing import Dict, Any

class LLMTester:
    """Test different LLM endpoints for critic generation"""

    def __init__(self, ollama_url: str = "http://192.168.45.104:11434"):
        self.ollama_url = ollama_url

    async def test_ollama_connectivity(self) -> Dict[str, Any]:
        """Test basic Ollama connectivity"""
        print("🔗 Testing Ollama connectivity...")

        async with httpx.AsyncClient() as client:
            try:
                # Get available models
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                models = response.json()

                print(f"✅ Connected to Ollama server")
                print(f"📋 Available models:")
                for model in models.get('models', []):
                    print(f"   - {model['name']} ({model['details']['parameter_size']})")

                return {"status": "success", "models": models}

            except Exception as e:
                print(f"❌ Failed to connect to Ollama: {str(e)}")
                return {"status": "error", "error": str(e)}

    async def test_character_generation(self, model: str = "qwen3:8b") -> Dict[str, Any]:
        """Test character-based critic generation"""
        print(f"\n🎭 Testing character generation with {model}...")

        # Test prompts for both characters
        test_cases = [
            {
                "character": "Marco Aurelio",
                "prompt": """Eres Marco Aurelio, el emperador filósofo romano. Debes escribir una crítica de película desde tu perspectiva estoica.

Película: "The Matrix" (1999)
Género: Ciencia ficción, Acción
Sinopsis: Un programador descubre que la realidad es una simulación y debe elegir entre la verdad dolorosa o la ilusión cómoda.

Escribe una crítica de máximo 150 palabras, incluyendo:
1. Una puntuación del 1-10
2. Reflexión desde la filosofía estoica
3. Tu perspectiva sobre la búsqueda de la verdad vs. la comodidad de la ignorancia

Mantén tu tono sabio, reflexivo y sereno."""
            },
            {
                "character": "Rosario Costras",
                "prompt": """Eres Rosario Costras, una activista progresista muy crítica con los problemas sociales. Debes escribir una crítica de película desde tu perspectiva de justicia social.

Película: "The Matrix" (1999)
Género: Ciencia ficción, Acción
Sinopsis: Un programador descubre que la realidad es una simulación y debe elegir entre la verdad dolorosa o la ilusión cómoda.

Escribe una crítica de máximo 150 palabras, incluyendo:
1. Una puntuación del 1-10
2. Análisis de representación y diversidad
3. Crítica a las estructuras de poder mostradas en la película

Mantén tu tono combativo, directo y comprometido con la justicia social."""
            }
        ]

        results = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for test_case in test_cases:
                try:
                    print(f"🎬 Testing {test_case['character']}...")

                    start_time = time.time()
                    response = await client.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": test_case["prompt"],
                            "stream": False
                        }
                    )
                    response.raise_for_status()

                    result = response.json()
                    generation_time = time.time() - start_time

                    print(f"✅ {test_case['character']} response generated ({generation_time:.1f}s)")
                    print(f"📝 Response preview: {result['response'][:100]}...")

                    results.append({
                        "character": test_case["character"],
                        "status": "success",
                        "response": result["response"],
                        "generation_time": generation_time,
                        "prompt_eval_count": result.get("prompt_eval_count", 0),
                        "eval_count": result.get("eval_count", 0)
                    })

                except Exception as e:
                    print(f"❌ Failed to generate for {test_case['character']}: {str(e)}")
                    results.append({
                        "character": test_case["character"],
                        "status": "error",
                        "error": str(e)
                    })

        return results

    async def test_performance_metrics(self, model: str = "qwen3:8b") -> Dict[str, Any]:
        """Test performance metrics"""
        print(f"\n📊 Testing performance metrics for {model}...")

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                test_prompt = "Escribe una crítica corta de 50 palabras sobre la película Titanic desde la perspectiva de Marco Aurelio."

                start_time = time.time()
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": test_prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()

                result = response.json()
                total_time = time.time() - start_time

                metrics = {
                    "total_duration_ms": result.get("total_duration", 0) / 1000000,
                    "load_duration_ms": result.get("load_duration", 0) / 1000000,
                    "prompt_eval_duration_ms": result.get("prompt_eval_duration", 0) / 1000000,
                    "eval_duration_ms": result.get("eval_duration", 0) / 1000000,
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "response_tokens": result.get("eval_count", 0),
                    "tokens_per_second": result.get("eval_count", 0) / (result.get("eval_duration", 1) / 1000000000),
                    "real_time_seconds": total_time
                }

                print(f"⚡ Performance metrics:")
                print(f"   Total time: {metrics['total_duration_ms']:.0f}ms")
                print(f"   Tokens/sec: {metrics['tokens_per_second']:.1f}")
                print(f"   Response tokens: {metrics['response_tokens']}")

                return {"status": "success", "metrics": metrics}

            except Exception as e:
                print(f"❌ Performance test failed: {str(e)}")
                return {"status": "error", "error": str(e)}

async def main():
    """Run all LLM tests"""
    print("🎭 Starting Parody Critics LLM Testing Suite...")

    tester = LLMTester()

    # Test 1: Basic connectivity
    connectivity_result = await tester.test_ollama_connectivity()

    if connectivity_result["status"] == "success":
        # Test 2: Character generation
        character_results = await tester.test_character_generation()

        # Test 3: Performance metrics
        performance_result = await tester.test_performance_metrics()

        # Summary
        print(f"\n📋 TEST SUMMARY:")
        print(f"✅ Connectivity: OK")

        successful_chars = [r for r in character_results if r["status"] == "success"]
        print(f"🎭 Characters tested: {len(successful_chars)}/{len(character_results)}")

        for result in successful_chars:
            print(f"   - {result['character']}: {result['generation_time']:.1f}s")

        if performance_result["status"] == "success":
            metrics = performance_result["metrics"]
            print(f"⚡ Performance: {metrics['tokens_per_second']:.1f} tokens/sec")

        print(f"\n🚀 LLM system ready for integration!")

        # Show sample responses
        print(f"\n📝 Sample responses:")
        for result in successful_chars[:2]:  # Show first 2
            print(f"\n--- {result['character']} ---")
            print(result['response'][:300] + "..." if len(result['response']) > 300 else result['response'])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())