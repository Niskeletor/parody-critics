#!/usr/bin/env python3
"""
Benchmark autónomo — Parody Critics
Llama directamente a Ollama sin necesitar el servidor FastAPI.
Resultados en logs/benchmark_{model}_{timestamp}.log

Uso: python benchmark_auto.py
"""
import sys
import json
import sqlite3
import re
import time
from datetime import datetime
from pathlib import Path

import httpx

# --- Path setup ---
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from model_profiles import get_profile  # noqa: E402
from prompt_builder import build_messages  # noqa: E402

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OLLAMA_URL = "http://192.168.2.69:11434"
DB_PATH    = PROJECT_ROOT / "database" / "critics.db"
LOG_DIR    = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Modelos a testear — en orden de prioridad
MODELS = [
    "richardyoung/qwen3-14b-abliterated:latest",
    "mis-firefly-22b:latest",
    "hf.co/LatitudeGames/Muse-12B-GGUF:Q4_K_M",
    "LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M",
    "phi4-reasoning:14b",
    "type32/eva-qwen-2.5-14b:latest",
    "dolphin3:latest",
]

# 8 personajes canónicos del benchmark
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

# 4 películas canónicas (tmdb_id)
CANONICAL_MOVIES = [181808, 496243, 694, 508442]

# 3 combos del smoke test (tmdb_id, character)
SMOKE_COMBOS = [
    (496243, "Adolf Histeric"),      # Ideológico + red_flags
    (694,    "Po (Teletubbie Rojo)"),# Voz infantil vs horror
    (508442, "Alan Turbing"),        # Analítico vs emocional
]

SLEEP_BETWEEN_CALLS = 3   # segundos entre críticas
OLLAMA_TIMEOUT      = 240 # segundos por llamada


# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────
def get_character(cur, name: str) -> dict | None:
    cur.execute(
        "SELECT * FROM characters WHERE name = ? AND active = 1", (name,)
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def get_media(cur, tmdb_id: int) -> dict | None:
    cur.execute("SELECT * FROM media WHERE tmdb_id = ?", (tmdb_id,))
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


# ─────────────────────────────────────────────
# Ollama caller
# ─────────────────────────────────────────────
def call_ollama(model: str, messages: list, profile) -> tuple[str, float]:
    """Returns (content, elapsed_seconds). Raises on error."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": profile.temperature,
            "num_predict": profile.num_predict,
            "top_p": profile.top_p,
            "top_k": profile.top_k,
        },
    }
    if profile.think:
        payload["think"] = True

    t0 = time.time()
    with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
        resp = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
    elapsed = time.time() - t0

    msg = data.get("message", {})
    content = msg.get("content", "")

    if profile.strip_think:
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    # Fallback: deepseek puede dejar content vacío con think=True
    if not content.strip() and msg.get("thinking"):
        content = msg["thinking"]

    return content.strip(), elapsed


def parse_rating(text: str) -> int | None:
    m = re.search(r"\b(\d{1,2})/10\b", text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 10:
            return n
    return None


# ─────────────────────────────────────────────
# Benchmark runner
# ─────────────────────────────────────────────
def run_model_benchmark(model: str, con: sqlite3.Connection) -> dict:
    cur = con.cursor()
    profile = get_profile(model)
    slug = model.replace("/", "_").replace(":", "_").replace(".", "_")
    ts   = datetime.now().strftime("%Y%m%d_%H%M")
    log_path = LOG_DIR / f"benchmark_{slug}_{ts}.log"

    results = {
        "model": model,
        "profile": vars(profile),
        "smoke_pass": 0,
        "smoke_total": 0,
        "bench_ok": 0,
        "bench_total": 0,
        "errors": [],
        "critiques": [],
        "log_path": str(log_path),
    }

    def log(line=""):
        print(line)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"{'='*60}")
    log(f"BENCHMARK: {model}")
    log(f"Fecha: {datetime.now()}")
    log(f"Perfil: think={profile.think} temp={profile.temperature} "
        f"num_predict={profile.num_predict} sys_in_user={profile.system_in_user}")
    log(f"{'='*60}")

    # ── FASE 2: Smoke test ──────────────────────────────────────
    log("\n─── FASE 2: SMOKE TEST ───")
    for tmdb_id, char_name in SMOKE_COMBOS:
        char = get_character(cur, char_name)
        media = get_media(cur, tmdb_id)
        if not char or not media:
            log(f"  ⚠️  SKIP {char_name} / tmdb={tmdb_id} — no encontrado en DB")
            continue

        label = f"[{char_name}] → [{media.get('title', tmdb_id)}]"
        log(f"\n  {label}")

        try:
            variation = {"motifs": [], "catchphrase": ""}
            messages  = build_messages(char, media, profile, variation)
            content, elapsed = call_ollama(model, messages, profile)
            rating = parse_rating(content)

            ok = bool(content) and rating is not None
            status = "✅" if ok else "⚠️ "
            log(f"  {status} Rating: {rating} | {elapsed:.1f}s")
            log(f"     {content[:250].replace(chr(10), ' ')}")

            results["smoke_total"] += 1
            if ok:
                results["smoke_pass"] += 1

        except Exception as e:
            log(f"  ❌ ERROR: {e}")
            results["errors"].append(f"SMOKE {label}: {e}")
            results["smoke_total"] += 1

        time.sleep(SLEEP_BETWEEN_CALLS)

    smoke_verdict = "PASA" if results["smoke_pass"] >= 2 else "FALLA"
    log(f"\n  Smoke: {results['smoke_pass']}/{results['smoke_total']} → {smoke_verdict}")

    if results["smoke_pass"] < 2:
        log(f"\n⛔ Smoke test fallido — saltando benchmark completo para {model}")
        return results

    # ── FASE 3: Benchmark 8×4 ──────────────────────────────────
    log("\n─── FASE 3: BENCHMARK 8×4 (32 críticas) ───")

    for char_name in CANONICAL_CHARACTERS:
        char = get_character(cur, char_name)
        if not char:
            log(f"  ⚠️  Personaje no encontrado: {char_name}")
            continue

        for tmdb_id in CANONICAL_MOVIES:
            media = get_media(cur, tmdb_id)
            if not media:
                log(f"  ⚠️  Película no encontrada: tmdb={tmdb_id}")
                continue

            label = f"[{char_name}] → [{media.get('title', tmdb_id)}]"
            log(f"\n  {label}")

            try:
                variation = {"motifs": [], "catchphrase": ""}
                messages  = build_messages(char, media, profile, variation)
                content, elapsed = call_ollama(model, messages, profile)
                rating = parse_rating(content)

                ok = bool(content) and rating is not None and len(content) > 60
                status = "✅" if ok else "⚠️ "

                log(f"  {status} Rating: {rating} | {elapsed:.1f}s | {len(content.split())} palabras")
                log(f"     {content[:300].replace(chr(10), ' ')}")

                results["bench_total"] += 1
                if ok:
                    results["bench_ok"] += 1

                results["critiques"].append({
                    "character": char_name,
                    "tmdb_id": tmdb_id,
                    "title": media.get("title"),
                    "rating": rating,
                    "words": len(content.split()),
                    "elapsed": round(elapsed, 1),
                    "ok": ok,
                    "preview": content[:200],
                })

            except Exception as e:
                log(f"  ❌ ERROR: {e}")
                results["errors"].append(f"BENCH {label}: {e}")
                results["bench_total"] += 1

            time.sleep(SLEEP_BETWEEN_CALLS)

    # ── FASE 4: Decisión ───────────────────────────────────────
    ok_count = results["bench_ok"]
    total    = results["bench_total"]
    pct      = (ok_count / total * 100) if total else 0

    if ok_count >= 27:
        verdict = "✅ CONFIRMADO — candidato de producción"
    elif ok_count >= 19:
        verdict = "⚠️  PARCIAL — ajustar parámetros y re-testear"
    else:
        verdict = "❌ DESCARTADO"

    log(f"\n{'='*60}")
    log(f"RESULTADO: {model}")
    log(f"  Smoke:     {results['smoke_pass']}/{results['smoke_total']}")
    log(f"  Benchmark: {ok_count}/{total} ({pct:.0f}%)")
    log(f"  Errores:   {len(results['errors'])}")
    log(f"  Veredicto: {verdict}")
    log(f"{'='*60}\n")

    results["verdict"] = verdict

    # Guardar JSON de resultados completo
    json_path = log_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    print(f"\n{'#'*60}")
    print("# PARODY CRITICS — BENCHMARK AUTOMÁTICO")
    print(f"# {len(MODELS)} modelos × 32 críticas c/u")
    print(f"# Inicio: {datetime.now()}")
    print(f"# Resultados: {LOG_DIR}/")
    print(f"{'#'*60}\n")

    con = sqlite3.connect(DB_PATH)
    summary = []

    for i, model in enumerate(MODELS, 1):
        print(f"\n[{i}/{len(MODELS)}] Iniciando: {model}")
        print("-" * 60)

        try:
            result = run_model_benchmark(model, con)
            summary.append(result)
        except Exception as e:
            print(f"❌ Error fatal benchmarking {model}: {e}")
            summary.append({"model": model, "verdict": f"❌ ERROR FATAL: {e}"})

    con.close()

    # Resumen final
    print(f"\n{'#'*60}")
    print("# RESUMEN FINAL")
    print(f"{'#'*60}")
    for r in summary:
        bench_ok    = r.get("bench_ok", "?")
        bench_total = r.get("bench_total", "?")
        verdict     = r.get("verdict", "sin datos")
        print(f"  {r['model']}")
        print(f"    {bench_ok}/{bench_total} críticas OK — {verdict}")
    print()

    # Guardar resumen global
    summary_path = LOG_DIR / f"benchmark_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Resumen guardado en: {summary_path}\n")


if __name__ == "__main__":
    main()
