#!/usr/bin/env python3
"""
benchmark_model.py — Benchmark completo de un modelo, guarda resultados en Markdown.

Uso:
    python benchmark_model.py "hf.co/LatitudeGames/Muse-12B-GGUF:Q4_K_M"

Genera:
    docs/benchmark-results/<slug>.md   — resultados legibles con todas las críticas
    docs/benchmark-results/<slug>.json — datos crudos para comparativas
"""
import sys
import re
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from model_profiles import get_profile  # noqa: E402
from prompt_builder import build_messages  # noqa: E402

# ─── Config ───────────────────────────────────────────────
OLLAMA_URL = "http://192.168.2.69:11434"
DB_PATH    = PROJECT_ROOT / "database" / "critics.db"
OUT_DIR    = PROJECT_ROOT / "docs" / "benchmark-results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CANONICAL_CHARACTERS = [
    "Mark Hamill",
    "Po (Teletubbie Rojo)",
    "Adolf Histeric",
    "Rosario Costras",
    "Elon Musaka",
    "Alan Turbing",
    "El Gran Lebowski",
    "Lloyd Kaufman",
]

CANONICAL_MOVIES = [
    (181808, "Star Wars: Los últimos Jedi"),
    (496243, "Parásitos"),
    (694,    "El resplandor"),
    (508442, "Soul"),
]

SLEEP_BETWEEN = 2


# ─── Helpers ──────────────────────────────────────────────
def get_row(query, params):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute(query, params).fetchone()
    con.close()
    return dict(row) if row else None


def call_stream(model, messages, profile):
    """Call Ollama streaming. Returns (content, elapsed_seconds)."""
    t0 = time.time()
    content = ""
    with httpx.Client(timeout=360) as c:
        with c.stream("POST", f"{OLLAMA_URL}/api/chat", json={
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": profile.temperature,
                "num_predict": profile.num_predict,
                "top_p": profile.top_p,
                "top_k": profile.top_k,
            },
        }) as resp:
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line)
                    content += chunk.get("message", {}).get("content", "")
                    if chunk.get("done"):
                        break
    elapsed = time.time() - t0
    if profile.strip_think:
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content.strip(), round(elapsed, 1)


def parse_rating(text):
    m = re.search(r"\b(\d{1,2})/10\b", text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 10:
            return n
    return None


def warmup(model):
    print("  Cargando modelo en VRAM...", end=" ", flush=True)
    t0 = time.time()
    with httpx.Client(timeout=360) as c:
        c.post(f"{OLLAMA_URL}/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": "OK"}],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 5},
        })
    elapsed = time.time() - t0
    print(f"listo ({elapsed:.1f}s)")


# ─── Markdown builder ─────────────────────────────────────
def build_markdown(model, profile, results, date_str):
    lines = []

    lines += [
        f"# Benchmark: {model}",
        "",
        "## Configuración",
        "",
        "| Campo | Valor |",
        "|-------|-------|",
        f"| **Modelo** | `{model}` |",
        f"| **Fecha** | {date_str} |",
        f"| **think** | {profile.think} |",
        f"| **temperature** | {profile.temperature} |",
        f"| **num_predict** | {profile.num_predict} |",
        f"| **system_in_user** | {profile.system_in_user} |",
        "| **Servidor** | Omnius — 192.168.2.69:11434 (RTX 5060 Ti 16GB) |",
        "",
        "## Tabla resumen",
        "",
        "| Personaje | Película | Rating | Tiempo | Palabras | OK |",
        "|-----------|----------|--------|--------|----------|----|",
    ]

    for r in results:
        ok = "✅" if r["ok"] else "❌"
        rating_str = f"{r['rating']}/10" if r["rating"] else "—"
        lines.append(
            f"| {r['character']} | {r['title']} | {rating_str} | {r['elapsed']}s | {r['words']} | {ok} |"
        )

    ok_count = sum(1 for r in results if r["ok"])
    total = len(results)
    lines += [
        "",
        f"**{ok_count}/{total} críticas OK**",
        "",
    ]

    # Individual critiques grouped by character
    lines += ["---", "", "## Críticas completas", ""]
    current_char = None
    for r in results:
        if r["character"] != current_char:
            current_char = r["character"]
            lines += [f"### {current_char}", ""]
        rating_str = f"{r['rating']}/10" if r["rating"] else "SIN RATING"
        ok = "✅" if r["ok"] else "❌"
        lines += [
            f"#### → {r['title']}",
            "",
            f"**{rating_str}** {ok} | {r['elapsed']}s | {r['words']} palabras",
            "",
            r["text"] if r["text"] else "_Sin respuesta_",
            "",
        ]

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Uso: python benchmark_model.py 'nombre-modelo:tag'")
        sys.exit(1)

    model = sys.argv[1]
    profile = get_profile(model)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    slug = re.sub(r"[^\w\-]", "_", model)

    print(f"\n{'='*60}")
    print(f"BENCHMARK: {model}")
    print(f"Perfil: think={profile.think} temp={profile.temperature} num_predict={profile.num_predict}")
    print(f"Total: {len(CANONICAL_CHARACTERS)} personajes × {len(CANONICAL_MOVIES)} películas = "
          f"{len(CANONICAL_CHARACTERS)*len(CANONICAL_MOVIES)} críticas")
    print(f"{'='*60}\n")

    warmup(model)

    results = []
    total = len(CANONICAL_CHARACTERS) * len(CANONICAL_MOVIES)
    n = 0

    for char_name in CANONICAL_CHARACTERS:
        char = get_row("SELECT * FROM characters WHERE name=? AND active=1", (char_name,))
        if not char:
            print(f"  ⚠️  Personaje no encontrado: {char_name}")
            continue

        print(f"\n── {char_name} ──")

        for tmdb_id, title in CANONICAL_MOVIES:
            n += 1
            media = get_row("SELECT * FROM media WHERE tmdb_id=?", (tmdb_id,))
            if not media:
                print(f"  ⚠️  Película no encontrada: {title}")
                continue

            print(f"  [{n:2d}/{total}] → {title:<30}", end=" ", flush=True)

            try:
                variation = {"motifs": [], "catchphrase": ""}
                messages  = build_messages(char, media, profile, variation)
                text, elapsed = call_stream(model, messages, profile)
                rating = parse_rating(text)
                words  = len(text.split())
                ok     = bool(text) and rating is not None and words >= 40

                status = "✅" if ok else "⚠️ "
                print(f"R:{rating if rating else '?':>2}/10  {elapsed:>6.1f}s  {words:>3}w  {status}")

                results.append({
                    "character": char_name,
                    "tmdb_id":   tmdb_id,
                    "title":     title,
                    "rating":    rating,
                    "elapsed":   elapsed,
                    "words":     words,
                    "ok":        ok,
                    "text":      text,
                })

            except Exception as e:
                print(f"❌ ERROR: {e}")
                results.append({
                    "character": char_name, "tmdb_id": tmdb_id, "title": title,
                    "rating": None, "elapsed": 0, "words": 0, "ok": False,
                    "text": f"ERROR: {e}",
                })

            time.sleep(SLEEP_BETWEEN)

    # ── Write outputs ──
    md_path   = OUT_DIR / f"{slug}.md"
    json_path = OUT_DIR / f"{slug}.json"

    md_content = build_markdown(model, profile, results, date_str)
    md_path.write_text(md_content, encoding="utf-8")

    json_data = {
        "model": model, "date": date_str,
        "profile": vars(profile), "results": results,
        "ok_count": sum(1 for r in results if r["ok"]),
        "total": len(results),
    }
    json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")

    ok_count = json_data["ok_count"]
    print(f"\n{'='*60}")
    print(f"COMPLETADO: {ok_count}/{len(results)} OK")
    print(f"  Markdown → {md_path}")
    print(f"  JSON     → {json_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
