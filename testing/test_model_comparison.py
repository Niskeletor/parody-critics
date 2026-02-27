#!/usr/bin/env python3
"""
Compare different models for critic generation quality
"""
import httpx
import time
import asyncio

async def test_model_comparison():
    """Compare qwen3:8b vs gpt-oss:20b for critic generation"""
    print("🏁 Comparing models for critic generation quality...")

    models_to_test = ["qwen3:8b", "gpt-oss:20b"]
    ollama_url = "http://192.168.45.104:11434"

    test_prompt = """Eres Marco Aurelio, el emperador filósofo romano. Escribe una crítica breve (máximo 100 palabras) de la película "Blade Runner" (1982) desde tu perspectiva estoica.

Película: "Blade Runner" (1982)
Género: Ciencia ficción, thriller
Sinopsis: En un futuro distópico, un cazador de androides debe perseguir y "retirar" replicantes fugitivos que buscan extender su vida programada.

Incluye:
1. Puntuación del 1-10
2. Reflexión sobre la mortalidad y el propósito de la existencia
3. Tu perspectiva estoica sobre el valor de la vida artificial vs. natural"""

    results = []

    async with httpx.AsyncClient(timeout=180.0) as client:
        for model in models_to_test:
            try:
                print(f"\n🤖 Testing {model}...")

                start_time = time.time()
                response = await client.post(
                    f"{ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": test_prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()

                result = response.json()
                generation_time = time.time() - start_time

                tokens_per_sec = result.get("eval_count", 0) / (result.get("eval_duration", 1) / 1000000000)

                print(f"✅ {model} completed in {generation_time:.1f}s ({tokens_per_sec:.1f} tok/s)")

                results.append({
                    "model": model,
                    "response": result["response"],
                    "generation_time": generation_time,
                    "tokens_per_second": tokens_per_sec,
                    "response_length": len(result["response"]),
                    "token_count": result.get("eval_count", 0)
                })

            except Exception as e:
                print(f"❌ {model} failed: {str(e)}")
                results.append({
                    "model": model,
                    "error": str(e)
                })

    # Display results
    print("\n📊 MODEL COMPARISON RESULTS:")
    print("=" * 60)

    for result in results:
        if "error" not in result:
            print(f"\n🤖 {result['model']}:")
            print(f"   ⏱️  Time: {result['generation_time']:.1f}s")
            print(f"   ⚡ Speed: {result['tokens_per_second']:.1f} tok/s")
            print(f"   📝 Length: {result['response_length']} chars ({result['token_count']} tokens)")
            print("   📖 Response:")
            print(f"   {'-' * 50}")
            # Show first 200 chars
            preview = result['response'][:200] + "..." if len(result['response']) > 200 else result['response']
            print(f"   {preview}")
            print()

    return results

if __name__ == "__main__":
    asyncio.run(test_model_comparison())