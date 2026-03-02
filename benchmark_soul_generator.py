#!/usr/bin/env python3
"""
benchmark_soul_generator.py — Evalúa la calidad del generador de almas.

Modos:
  --tier easy|medium|hard|all   Un solo modelo (phi4 por defecto)
  --compare                      3 modelos × 9 sujetos, tabla comparativa

Uso:
  venv/bin/python benchmark_soul_generator.py --tier easy
  venv/bin/python benchmark_soul_generator.py --compare
  venv/bin/python benchmark_soul_generator.py --compare --models phi4:latest mistral-small3.1:24b
"""
import sys
import asyncio
import time
import argparse
import httpx
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from soul_generator import SoulGenerator  # noqa: E402

OLLAMA_URL = "http://192.168.2.69:11434"

COMPARE_MODELS = [
    "phi4:latest",
    "type32/eva-qwen-2.5-14b:latest",
    "mistral-small3.1:24b",
]

# ── Test subjects ──────────────────────────────────────────────────────────────

TEST_SUBJECTS = {
    "easy": [
        {"name": "Steven Spielberg",    "notes": "Cineasta global, cobertura masiva"},
        {"name": "Quentin Tarantino",   "notes": "Director icónico, muy citado en medios"},
        {"name": "Roger Ebert",         "notes": "Crítico de cine histórico, muy relevante"},
    ],
    "medium": [
        {"name": "Antonio Recio",       "notes": "Personaje ficción español (LQSA)"},
        {"name": "Jesús Gil",           "notes": "Personaje español polémico, fallecido 2004"},
        {"name": "Pedro Almodóvar",     "notes": "Cineasta español, cobertura limitada en inglés"},
    ],
    "hard": [
        {"name": "Calígula",            "notes": "Figura histórica antigua, fuentes académicas"},
        {"name": "Esperanza Gracia",    "notes": "Figura española oscura para IA global"},
        {"name": "Herschell G. Lewis",  "notes": "Cineasta gore de nicho, mínima cobertura web"},
    ],
}

ALL_SOUL_FIELDS = [
    "caricature_name", "emoji", "color", "personality", "description",
    "loves", "hates", "motifs", "catchphrases", "avoid", "red_flags",
]
SOUL_LIST_FIELDS = ["loves", "hates", "motifs", "catchphrases", "avoid", "red_flags"]
GENERIC_CINEMA_TERMS = {
    "cine", "película", "películas", "actor", "actores", "historia",
    "drama", "acción", "comedia", "arte", "cultura", "ficción", "narrativa",
    "dirección", "guión", "efectos", "escenas", "escena", "visual",
}


# ── Scoring ────────────────────────────────────────────────────────────────────

def score_ddg(snippets: list[str]) -> dict:
    count = len(snippets)
    total_chars = sum(len(s) for s in snippets)
    if count >= 6:
        quality = "🟢 Excelente"
    elif count >= 4:
        quality = "🟢 Bueno"
    elif count >= 2:
        quality = "🟡 Parcial"
    else:
        quality = "🔴 Pobre"
    return {"count": count, "total_chars": total_chars, "quality": quality}


def score_soul(soul: dict | None, real_name: str, snippets: list[str]) -> dict:
    """Puntuación 0-12 en 4 componentes."""
    if soul is None:
        return {
            "total": 0, "fields_complete": 0, "list_avg": 0.0,
            "specificity": 0, "context_used": 0, "notes": ["❌ JSON inválido"],
        }

    notes = []

    # 1) Completitud (0-4)
    filled = sum(1 for f in ALL_SOUL_FIELDS if soul.get(f))
    fields_score = round(filled / len(ALL_SOUL_FIELDS) * 4)
    if filled < len(ALL_SOUL_FIELDS):
        missing = [f for f in ALL_SOUL_FIELDS if not soul.get(f)]
        notes.append(f"⚠️  Campos vacíos: {', '.join(missing)}")

    # 2) Profundidad de listas (0-3)
    list_counts = [len(soul.get(f, [])) for f in SOUL_LIST_FIELDS]
    list_avg = sum(list_counts) / len(list_counts) if list_counts else 0.0
    list_score = min(3, round(list_avg / 2))
    if list_avg < 3:
        notes.append(f"⚠️  Listas cortas (avg {list_avg:.1f} items)")

    # 3) Especificidad (0-3): loves/hates no son solo términos genéricos
    all_items = [
        item.lower()
        for f in ["loves", "hates", "red_flags"]
        for item in soul.get(f, [])
    ]
    if all_items:
        specific = sum(1 for item in all_items if not any(g in item for g in GENERIC_CINEMA_TERMS))
        spec_ratio = specific / len(all_items)
        specificity_score = round(spec_ratio * 3)
        if specificity_score <= 1:
            notes.append("⚠️  Especificidad baja — loves/hates poco distintivos")
    else:
        spec_ratio = 0.0
        specificity_score = 0

    # 4) Contexto usado (0-2): rasgos específicos del personaje en loves/hates
    specific_items = [
        item for f in ["loves", "hates", "red_flags"]
        for item in soul.get(f, [])
        if not any(g in item.lower() for g in GENERIC_CINEMA_TERMS)
    ]
    if len(specific_items) >= 4:
        context_score = 2
    elif len(specific_items) >= 2 or snippets:
        context_score = 1
    else:
        context_score = 0

    total = fields_score + list_score + specificity_score + context_score

    return {
        "total": total,
        "fields_complete": filled,
        "list_avg": round(list_avg, 1),
        "specificity": specificity_score,
        "context_used": context_score,
        "notes": notes,
    }


# ── Warmup ─────────────────────────────────────────────────────────────────────

async def warmup_model(model: str):
    print(f"  Cargando {model}...", end=" ", flush=True)
    t0 = time.time()
    async with httpx.AsyncClient(timeout=360) as client:
        await client.post(f"{OLLAMA_URL}/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": "OK"}],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 5},
        })
    print(f"listo ({time.time() - t0:.1f}s)")


# ── Single-model tier run ──────────────────────────────────────────────────────

async def run_subject(sg: SoulGenerator, subject: dict) -> dict:
    real_name = subject["name"]
    print(f"\n  👤 {real_name}  ({subject['notes']})")

    t0 = time.time()
    try:
        snippets = await sg.fetch_context(real_name)
    except Exception as e:
        print(f"     DDG: ❌ ERROR: {e}")
        snippets = []
    ddg_elapsed = round(time.time() - t0, 1)

    ddg = score_ddg(snippets)
    print(f"     DDG  {ddg_elapsed}s  →  {ddg['count']} snippets / {ddg['total_chars']} chars  {ddg['quality']}")
    for i, s in enumerate(snippets[:3], 1):
        print(f"       [{i}] {s[:110].replace(chr(10),' ')}{'…' if len(s) > 110 else ''}")
    if len(snippets) > 3:
        print(f"       … y {len(snippets) - 3} más")

    t1 = time.time()
    soul = None
    try:
        prompt = sg._soul_prompt(real_name, snippets, archetype=None)
        raw = await sg._call_llm(prompt)
        soul = sg._extract_json(raw)
    except Exception as e:
        print(f"     LLM: ❌ ERROR: {e}")
    llm_elapsed = round(time.time() - t1, 1)

    sc = score_soul(soul, real_name, snippets)
    if soul:
        print(f"     LLM  {llm_elapsed}s  →  ✅  {soul.get('caricature_name','?')} {soul.get('emoji','?')}  [{soul.get('personality','?')}]")
        print(f"     Score {sc['total']}/12  (campos {sc['fields_complete']}/11 · listas {sc['list_avg']} · especif {sc['specificity']}/3 · ctx {sc['context_used']}/2)")
    else:
        print(f"     LLM  {llm_elapsed}s  →  ⚠️  JSON inválido  Score 0/12")
    for note in sc["notes"]:
        print(f"     {note}")

    return {
        "subject": subject, "ddg": ddg, "ddg_elapsed": ddg_elapsed,
        "snippets": snippets, "soul": soul, "llm_elapsed": llm_elapsed, "scoring": sc,
    }


# ── Compare mode ───────────────────────────────────────────────────────────────

async def run_compare(models: list[str]):
    sg = SoulGenerator()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    all_subjects = [
        (tier, subject)
        for tier, subjects in TEST_SUBJECTS.items()
        for subject in subjects
    ]

    # Phase 1: DDG for all subjects — once, shared across models
    print(f"\n{'='*65}")
    print(f"FASE 1 — DDG fetch ({len(all_subjects)} personajes)")
    print(f"{'='*65}")
    ddg_cache: dict[str, dict] = {}
    snippets_cache: dict[str, list] = {}
    for tier, subject in all_subjects:
        real_name = subject["name"]
        print(f"  {real_name}...", end=" ", flush=True)
        try:
            snippets = await sg.fetch_context(real_name)
        except Exception:
            snippets = []
        ddg_cache[real_name] = score_ddg(snippets)
        snippets_cache[real_name] = snippets
        print(f"{ddg_cache[real_name]['count']} snippets  {ddg_cache[real_name]['quality']}")
        await asyncio.sleep(2)

    # Phase 2: LLM for each model
    all_results: dict[str, list] = {}

    for model in models:
        print(f"\n{'='*65}")
        print(f"MODELO: {model}")
        print(f"{'='*65}")

        # Override endpoint cache to force this specific model
        sg._endpoint_cache = {"url": OLLAMA_URL, "model": model, "label": model}

        await warmup_model(model)

        model_results = []
        for tier, subject in all_subjects:
            real_name = subject["name"]
            snippets = snippets_cache[real_name]
            print(f"\n  👤 {real_name} [{tier}]")

            t0 = time.time()
            soul = None
            try:
                prompt = sg._soul_prompt(real_name, snippets, archetype=None)
                raw = await sg._call_llm(prompt)
                soul = sg._extract_json(raw)
            except Exception as e:
                print(f"     ❌ ERROR: {e}")
            llm_elapsed = round(time.time() - t0, 1)

            sc = score_soul(soul, real_name, snippets)
            if soul:
                print(f"     {llm_elapsed}s  →  ✅  {soul.get('caricature_name','?')} {soul.get('emoji','?')}  [{soul.get('personality','?')}]")
                print(f"     Score {sc['total']}/12  (especif {sc['specificity']}/3)")
            else:
                print(f"     {llm_elapsed}s  →  ⚠️  JSON inválido")

            model_results.append({
                "tier": tier, "subject": subject, "soul": soul,
                "llm_elapsed": llm_elapsed, "scoring": sc,
                "snippets": snippets, "ddg": ddg_cache[real_name],
            })
            await asyncio.sleep(1)

        all_results[model] = model_results

    # ── Markdown report ─────────────────────────────────────────────────────────
    _write_compare_report(models, all_subjects, all_results, ddg_cache, date_str)


def _write_compare_report(models, all_subjects, all_results, ddg_cache, date_str):
    slug = f"benchmark_soul_compare_{datetime.now().strftime('%Y-%m-%d_%H%M')}"
    out_dir = PROJECT_ROOT / "docs" / "benchmark-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{slug}.md"

    short_names = [m.split("/")[-1].split(":")[0][:16] for m in models]

    lines = [
        "# Benchmark Soul Generator — Comparativa de Modelos",
        "",
        f"**Fecha**: {date_str}  ",
        f"**Modelos**: {', '.join(models)}  ",
        "**Score máximo**: 12 (campos 4 + listas 3 + especificidad 3 + contexto 2)  ",
        "",
        "## Tabla comparativa",
        "",
        f"| Personaje | Tier | DDG | {' | '.join(short_names)} |",
        f"|-----------|------|-----|{'|'.join(['---'] * len(models))}|",
    ]

    for tier, subject in all_subjects:
        real_name = subject["name"]
        ddg = ddg_cache[real_name]
        ddg_cell = f"{ddg['count']}s {'✅' if ddg['count'] >= 4 else '⚠️'}"
        model_cells = []
        for model in models:
            results = all_results[model]
            r = next((x for x in results if x["subject"]["name"] == real_name), None)
            if r and r["soul"]:
                sc = r["scoring"]
                ok = "✅" if sc["total"] >= 9 else ("🟡" if sc["total"] >= 7 else "⚠️")
                model_cells.append(f"**{sc['total']}/12** {ok} `{r['soul'].get('emoji','?')}`")
            elif r:
                model_cells.append("0/12 ❌")
            else:
                model_cells.append("—")
        lines.append(f"| {real_name} | {tier} | {ddg_cell} | {' | '.join(model_cells)} |")

    # Summary per model
    lines += ["", "## Resumen por modelo", "",
              "| Modelo | JSON válidos | Score avg | Especif avg | Tiempo avg |",
              "|--------|-------------|-----------|-------------|------------|"]
    for model in models:
        results = all_results[model]
        valid = sum(1 for r in results if r["soul"] is not None)
        scores = [r["scoring"]["total"] for r in results]
        specs = [r["scoring"]["specificity"] for r in results]
        times = [r["llm_elapsed"] for r in results]
        avg_s = sum(scores) / len(scores)
        avg_sp = sum(specs) / len(specs)
        avg_t = sum(times) / len(times)
        lines.append(f"| {model} | {valid}/{len(results)} | {avg_s:.1f}/12 | {avg_sp:.1f}/3 | {avg_t:.1f}s |")

    # Detailed souls per model
    lines += ["", "---", "", "## Almas generadas por modelo", ""]
    for model in models:
        lines += [f"### {model}", ""]
        for r in all_results[model]:
            soul = r["soul"]
            sc = r["scoring"]
            real_name = r["subject"]["name"]
            lines.append(f"#### {real_name} [{r['tier']}] — {sc['total']}/12")
            lines.append("")
            if soul:
                lines += [
                    f"**{soul.get('caricature_name')} {soul.get('emoji')}** [{soul.get('personality')}] `{soul.get('color')}`  ",
                    f"{soul.get('description', '')}  ",
                    "",
                    f"❤️ **Loves**: {', '.join(soul.get('loves', []))}  ",
                    f"💀 **Hates**: {', '.join(soul.get('hates', []))}  ",
                    f"🚩 **Red flags**: {', '.join(soul.get('red_flags', []))}  ",
                    f"🎭 **Catchphrases**: {' | '.join(soul.get('catchphrases', []))}  ",
                ]
                if sc["notes"]:
                    for note in sc["notes"]:
                        lines.append(f"- {note}")
            else:
                lines.append("_❌ JSON inválido_")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*65}")
    print(f"COMPLETADO → {md_path}")
    print(f"{'='*65}\n")


# ── Single-tier mode ───────────────────────────────────────────────────────────

async def run_tiers(tiers: list[str]):
    sg = SoulGenerator()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_results: dict[str, list] = {}

    for tier in tiers:
        subjects = TEST_SUBJECTS.get(tier, [])
        if not subjects:
            continue
        print(f"\n{'='*65}")
        print(f"TIER: {tier.upper()}  —  {len(subjects)} personajes")
        print(f"{'='*65}")
        tier_results = []
        for subject in subjects:
            result = await run_subject(sg, subject)
            tier_results.append(result)
            if subject is not subjects[-1]:
                await asyncio.sleep(3)
        all_results[tier] = tier_results

    # Markdown report (single-model format)
    slug = f"benchmark_soul_generator_{datetime.now().strftime('%Y-%m-%d_%H%M')}"
    out_dir = PROJECT_ROOT / "docs" / "benchmark-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{slug}.md"

    lines = [
        "# Benchmark Soul Generator",
        "",
        f"**Fecha**: {date_str}  ",
        f"**Tiers**: {', '.join(tiers)}  ",
        "",
        "| Tier | Válidos | DDG avg snippets | Score avg |",
        "|------|---------|------------------|-----------|",
    ]
    for tier, results in all_results.items():
        ok = sum(1 for r in results if r["soul"] is not None)
        avg_ddg = sum(r["ddg"]["count"] for r in results) / len(results)
        avg_score = sum(r["scoring"]["total"] for r in results) / len(results)
        lines.append(f"| {tier.upper()} | {ok}/{len(results)} | {avg_ddg:.1f} | {avg_score:.1f}/12 |")

    lines += ["", "---", ""]
    for tier, results in all_results.items():
        lines += [f"## Tier {tier.upper()}", ""]
        for r in results:
            soul = r["soul"]
            sc = r["scoring"]
            ddg = r["ddg"]
            lines += [
                f"### {r['subject']['name']}",
                f"*{r['subject']['notes']}*  ",
                f"**DDG**: {ddg['count']} snippets / {ddg['total_chars']} chars / {r['ddg_elapsed']}s / {ddg['quality']}  ",
                f"**LLM**: {r['llm_elapsed']}s | **Score**: {sc['total']}/12  ",
                "",
            ]
            if r["snippets"]:
                lines.append("**Snippets DDG:**")
                for i, s in enumerate(r["snippets"], 1):
                    lines.append(f"{i}. {s[:200].replace(chr(10), ' ')}")
                lines.append("")
            if soul:
                lines += [
                    f"**{soul.get('caricature_name')} {soul.get('emoji')}** [{soul.get('personality')}] `{soul.get('color')}`  ",
                    f"{soul.get('description', '')}  ",
                    "",
                    f"❤️ Loves: {', '.join(soul.get('loves', []))}  ",
                    f"💀 Hates: {', '.join(soul.get('hates', []))}  ",
                    f"🚩 Red flags: {', '.join(soul.get('red_flags', []))}  ",
                    f"🎭 Catchphrases: {' | '.join(soul.get('catchphrases', []))}  ",
                ]
            else:
                lines.append("_❌ JSON inválido_")
            if sc["notes"]:
                for note in sc["notes"]:
                    lines.append(f"- {note}")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n{'='*65}")
    print(f"COMPLETADO → {md_path}")
    print(f"{'='*65}\n")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark soul generator")
    parser.add_argument("--tier", choices=["easy", "medium", "hard", "all"], default="all")
    parser.add_argument("--compare", action="store_true", help="Comparar múltiples modelos")
    parser.add_argument("--models", nargs="+", default=COMPARE_MODELS,
                        help="Modelos para --compare (default: phi4, eva-qwen, mistral-small)")
    args = parser.parse_args()

    if args.compare:
        asyncio.run(run_compare(args.models))
    else:
        tiers = ["easy", "medium", "hard"] if args.tier == "all" else [args.tier]
        asyncio.run(run_tiers(tiers))
