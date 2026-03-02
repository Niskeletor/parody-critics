#!/usr/bin/env python3
"""
test_new_film.py — Test con película 2026 desconocida por los modelos.
Verifica que el contexto enriquecido (DuckDuckGo) se usa correctamente.

Uso: python test_new_film.py
"""
import sys
import re
import json
import sqlite3
import time
from pathlib import Path
from datetime import datetime

import httpx

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from model_profiles import get_profile  # noqa: E402
from prompt_builder import build_messages  # noqa: E402

OLLAMA_URL = "http://192.168.2.69:11434"
DB_PATH    = PROJECT_ROOT / "database" / "critics.db"
OUT_DIR    = PROJECT_ROOT / "docs" / "benchmark-results"

# Película de 2026 — fuera del training cutoff de todos los modelos
TEST_FILM_TMDB_ID = 1272837
TEST_FILM_TITLE   = "28 años después: El templo de los huesos"

MODELS_TO_TEST = [
    "phi4:latest",
    "type32/eva-qwen-2.5-14b:latest",
    "mistral-small3.1:24b",
]

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


def get_row(query, params):
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute(query, params).fetchone()
    con.close()
    return dict(row) if row else None


def call_stream(model, messages, profile):
    t0 = time.time()
    content = ""
    with httpx.Client(timeout=360) as c:
        with c.stream("POST", f"{OLLAMA_URL}/api/chat", json={
            "model": model, "messages": messages, "stream": True,
            "options": {
                "temperature": profile.temperature,
                "num_predict": profile.num_predict,
                "top_p": profile.top_p, "top_k": profile.top_k,
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
    print("  Cargando modelo...", end=" ", flush=True)
    t0 = time.time()
    with httpx.Client(timeout=360) as c:
        c.post(f"{OLLAMA_URL}/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": "OK"}],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 5},
        })
    print(f"listo ({time.time()-t0:.1f}s)")


def check_context_usage(text, enriched_context):
    """Check if the review mentions specific details from the enriched context."""
    ctx = json.loads(enriched_context) if isinstance(enriched_context, str) else enriched_context
    hits = []
    text_lower = text.lower()

    for actor in ctx.get("cast", []):
        first_name = actor.split()[0].lower()
        last_name = actor.split()[-1].lower()
        if first_name in text_lower or last_name in text_lower:
            hits.append(f"cast:{actor}")

    director = ctx.get("director", "")
    if director and director.split()[-1].lower() in text_lower:
        hits.append(f"director:{director}")

    for kw in ctx.get("keywords", []):
        if len(kw) > 6 and kw.lower() in text_lower:
            hits.append(f"kw:{kw}")

    return hits


def main():
    media = get_row("SELECT * FROM media WHERE tmdb_id=?", (TEST_FILM_TMDB_ID,))
    if not media:
        print(f"❌ Película no encontrada: tmdb_id={TEST_FILM_TMDB_ID}")
        sys.exit(1)

    print(f"\n{'='*65}")
    print(f"TEST PELÍCULA 2026 — {TEST_FILM_TITLE}")
    print(f"Director: {json.loads(media['enriched_context']).get('director','?')}")
    print(f"Reparto: {', '.join(json.loads(media['enriched_context']).get('cast',[]))}")
    print(f"Keywords: {', '.join(json.loads(media['enriched_context']).get('keywords',[])[:6])}...")
    print(f"Modelos: {', '.join(MODELS_TO_TEST)}")
    print(f"{'='*65}\n")

    all_results = {}
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    for model in MODELS_TO_TEST:
        print(f"\n{'─'*65}")
        print(f"MODELO: {model}")
        print(f"{'─'*65}")
        profile = get_profile(model)
        print(f"Perfil: think={profile.think} temp={profile.temperature} num_predict={profile.num_predict}")
        warmup(model)

        results = []
        for char_name in CANONICAL_CHARACTERS:
            char = get_row("SELECT * FROM characters WHERE name=? AND active=1", (char_name,))
            if not char:
                print(f"  ⚠️  Personaje no encontrado: {char_name}")
                continue

            print(f"\n── {char_name} ──")
            try:
                variation = {"motifs": [], "catchphrase": ""}
                messages  = build_messages(char, media, profile, variation)
                text, elapsed = call_stream(model, messages, profile)
                rating = parse_rating(text)
                words  = len(text.split())
                ok     = bool(text) and rating is not None and words >= 40
                ctx_hits = check_context_usage(text, media["enriched_context"])

                status = "✅" if ok else "⚠️ "
                ctx_str = f"  🔍 contexto: {', '.join(ctx_hits)}" if ctx_hits else "  ⚠️  sin refs al contexto enriquecido"
                print(f"  R:{rating if rating else '?':>2}/10  {elapsed:>6.1f}s  {words:>3}w  {status}")
                print(ctx_str)

                results.append({
                    "character": char_name, "rating": rating,
                    "elapsed": elapsed, "words": words, "ok": ok,
                    "text": text, "context_hits": ctx_hits,
                })
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                results.append({
                    "character": char_name, "rating": None, "elapsed": 0,
                    "words": 0, "ok": False, "text": f"ERROR: {e}", "context_hits": [],
                })

            time.sleep(2)

        all_results[model] = results

    # ── Write markdown ──
    slug = f"TEST_2026_templo_huesos_{date_str.replace(' ','_').replace(':','')}"
    md_path = OUT_DIR / f"{slug}.md"
    lines = [
        f"# Test película 2026 — {TEST_FILM_TITLE}",
        "",
        f"**Fecha**: {date_str}  ",
        "**Propósito**: Verificar uso de contexto enriquecido en película desconocida por los modelos (2026)  ",
        f"**Película**: {TEST_FILM_TITLE} (tmdb: {TEST_FILM_TMDB_ID}, dir. Nia DaCosta, 2026)  ",
        "",
        "## Resumen de ratings",
        "",
        f"| Personaje | {' | '.join(m.split('/')[0][:18] for m in MODELS_TO_TEST)} |",
        f"|-----------|{'|'.join(['---']*len(MODELS_TO_TEST))}|",
    ]

    chars = [r["character"] for r in all_results[MODELS_TO_TEST[0]]]
    for i, char in enumerate(chars):
        row_ratings = []
        for model in MODELS_TO_TEST:
            r = all_results[model][i] if i < len(all_results[model]) else None
            if r:
                ok = "✅" if r["ok"] else "⚠️"
                hits = "🔍" if r["context_hits"] else ""
                row_ratings.append(f"{r['rating']}/10 {ok}{hits}" if r["rating"] else f"— {ok}")
            else:
                row_ratings.append("—")
        lines.append(f"| {char} | {' | '.join(row_ratings)} |")

    lines += ["", "🔍 = la crítica menciona detalles del contexto enriquecido (reparto, director, keywords)", ""]

    for model in MODELS_TO_TEST:
        lines += ["---", "", f"## {model}", ""]
        for r in all_results[model]:
            rating_str = f"{r['rating']}/10" if r["rating"] else "SIN RATING"
            ok = "✅" if r["ok"] else "⚠️"
            ctx = f"  \n**Contexto detectado**: {', '.join(r['context_hits'])}" if r["context_hits"] else ""
            lines += [
                f"### {r['character']}",
                "",
                f"**{rating_str}** {ok} | {r['elapsed']}s | {r['words']} palabras{ctx}",
                "",
                r["text"] if r["text"] else "_Sin respuesta_",
                "",
            ]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*65}")
    print(f"COMPLETADO → {md_path}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
