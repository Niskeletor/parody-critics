#!/usr/bin/env python3
"""
Soul Generator — Simulated pipeline test
Tests the full DDG + LLM pipeline BEFORE integrating into the UI:

  1. DDG search for a real person → context snippets
  2. LLM prompt → JSON with all soul fields
  3. Per-field regeneration with existing soul as context
  4. Emoji + color coherence check

Run with:
  python test_soul_generator.py
  python test_soul_generator.py --person "Donald Trump" --archetype troll
  python test_soul_generator.py --person "Marilyn Monroe" --regen description
"""

import argparse
import asyncio
import json
import re
import sys
import time

import httpx

# ── Servers to try in order (phi4 is on secondary) ──────────────────────────
OLLAMA_ENDPOINTS = [
    {"url": "http://192.168.2.69:11434",   "model": "phi4:latest",  "label": "secondary/phi4"},
    {"url": "http://192.168.45.104:11434", "model": "qwen3:8b",     "label": "primary/qwen3"},
]
TIMEOUT = 120

# ── Archetypes ───────────────────────────────────────────────────────────────
ARCHETYPES = [
    "fanatico_ideologico",
    "intelectual",
    "nostalgico",
    "nihilista",
    "troll",
    "ingenuo_entusiasta",
    "woke",
    "estoico",
]

SOUL_FIELDS = [
    "caricature_name",
    "emoji",
    "color",
    "personality",
    "description",
    "loves",
    "hates",
    "motifs",
    "catchphrases",
    "avoid",
    "red_flags",
]

SEP  = "=" * 72
THIN = "-" * 72


# ── DDG search ────────────────────────────────────────────────────────────────

def ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """Run a DuckDuckGo text search synchronously."""
    from ddgs import DDGS
    with DDGS() as d:
        return list(d.text(query, max_results=max_results)) or []


async def fetch_person_context(real_name: str) -> list[str]:
    """
    Two DDG queries for the person:
      1. Wikipedia / biography
      2. Controversies / opinions
    Returns combined snippets (deduplicated, max 8).
    """
    print(f"\n[DDG] Searching for: {real_name!r} ...")
    t0 = time.time()

    queries = [
        f"{real_name} wikipedia personalidad caracteristicas",
        f"{real_name} controversias frases opiniones polémicas",
    ]

    snippets = []
    for q in queries:
        results = await asyncio.to_thread(ddg_search, q, max_results=4)
        for r in results:
            body = r.get("body", "").strip()
            if body and len(body) > 40:
                snippets.append(body[:300])

    # Deduplicate preserving order
    seen = set()
    unique = []
    for s in snippets:
        key = s[:80]
        if key not in seen:
            seen.add(key)
            unique.append(s)

    elapsed = time.time() - t0
    print(f"[DDG] Got {len(unique)} snippets in {elapsed:.1f}s")
    return unique[:8]


# ── LLM helper ───────────────────────────────────────────────────────────────

async def find_available_endpoint() -> dict | None:
    """Return the first reachable Ollama endpoint that has its model loaded."""
    for ep in OLLAMA_ENDPOINTS:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.get(f"{ep['url']}/api/tags")
                r.raise_for_status()
                models = [m["name"] for m in r.json().get("models", [])]
                if ep["model"] in models:
                    print(f"[LLM] Using {ep['label']} @ {ep['url']}")
                    return ep
                else:
                    print(f"[LLM] {ep['label']}: model {ep['model']!r} not loaded (available: {models})")
        except Exception as e:
            print(f"[LLM] {ep['label']} unreachable: {e}")
    return None


async def call_llm(endpoint: dict, prompt: str) -> tuple[str, float]:
    """Call Ollama and return (raw_response, elapsed_seconds)."""
    payload = {
        "model": endpoint["model"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.85,
            "top_p": 0.9,
        },
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(f"{endpoint['url']}/api/generate", json=payload)
        resp.raise_for_status()
    elapsed = time.time() - t0
    return resp.json().get("response", ""), elapsed


# ── Prompt builders ───────────────────────────────────────────────────────────

def build_soul_prompt(real_name: str, snippets: list[str], archetype: str | None) -> str:
    snippets_block = "\n".join(f"- {s}" for s in snippets)
    archetype_line = (
        f'El arquetipo ha sido preseleccionado por el usuario: "{archetype}". '
        f'Usa EXACTAMENTE ese valor en el campo "personality".'
        if archetype
        else f"Elige el arquetipo más apropiado de esta lista: {', '.join(ARCHETYPES)}."
    )

    return f"""Eres un sistema de generación de personajes paródicos de crítica cinematográfica.

PERSONA REAL A PARODIAR:
Nombre real: {real_name}

CONTEXTO (fragmentos de búsqueda web):
{snippets_block}

INSTRUCCIONES:
Crea un personaje paródico basado en "{real_name}". El personaje es una caricatura exagerada
de sus características más conocidas, enfocadas específicamente en cómo vería el CINE.
{archetype_line}

Genera un JSON válido con EXACTAMENTE estos campos y tipos:
{{
  "caricature_name": "Apodo caricaturesco divertido (no el nombre real, algo inventado)",
  "emoji": "Un único emoji que represente al personaje",
  "color": "#RRGGBB — color hex que evoque la esencia del personaje",
  "personality": "uno de: {', '.join(ARCHETYPES)}",
  "description": "2-3 frases en 2ª persona. Empieza con 'Eres...' Describe quién es como crítico de cine, qué le mueve y cómo habla.",
  "loves": ["4 a 6 cosas que el personaje AMA en el cine"],
  "hates": ["4 a 6 cosas que el personaje ODIA en el cine"],
  "motifs": ["6 a 8 temas recurrentes en sus críticas (palabras clave cortas)"],
  "catchphrases": ["2 o 3 frases que usa habitualmente al criticar"],
  "avoid": ["2 o 3 comportamientos a evitar en sus críticas (para dar instrucciones al modelo)"],
  "red_flags": ["3 a 5 cosas específicas que le provocan una reacción intensa"]
}}

IMPORTANTE:
- Todos los campos deben ser COHERENTES entre sí (mismo tono, misma lógica interna)
- El foco es cómo esta persona vería el CINE, no su vida en general
- El personaje es una CARICATURA, no una biografía exacta
- Responde SOLO con el JSON válido, sin texto adicional, sin bloques de código markdown""".strip()


def build_regen_prompt(field: str, current_soul: dict, real_name: str) -> str:
    # Show all OTHER fields as context
    context_fields = {k: v for k, v in current_soul.items() if k != field}
    context_json = json.dumps(context_fields, ensure_ascii=False, indent=2)

    field_hints = {
        "caricature_name": "Apodo caricaturesco divertido (string)",
        "emoji": "Un único emoji (string)",
        "color": "Color hex #RRGGBB (string)",
        "personality": f"Uno de: {', '.join(ARCHETYPES)} (string)",
        "description": "2-3 frases en 2ª persona empezando con 'Eres...' (string)",
        "loves": "Lista de 4-6 cosas que AMA en el cine (array de strings)",
        "hates": "Lista de 4-6 cosas que ODIA en el cine (array de strings)",
        "motifs": "Lista de 6-8 temas/motivos recurrentes (array de strings cortos)",
        "catchphrases": "Lista de 2-3 frases habituales (array de strings)",
        "avoid": "Lista de 2-3 comportamientos a evitar (array de strings)",
        "red_flags": "Lista de 3-5 desencadenantes de reacción intensa (array de strings)",
    }

    return f"""Eres un sistema de generación de personajes paródicos.

PERSONAJE: basado en "{real_name}"

ALMA ACTUAL DEL PERSONAJE (NO modifiques estos campos):
{context_json}

TAREA: Regenera ÚNICAMENTE el campo "{field}".
Tipo esperado: {field_hints.get(field, 'ver esquema')}

El nuevo valor debe ser COHERENTE con todos los campos existentes mostrados arriba.
Responde SOLO con el JSON: {{"{field}": <nuevo_valor>}}
Sin texto adicional.""".strip()


# ── JSON parser ───────────────────────────────────────────────────────────────

def extract_json(raw: str) -> dict | None:
    """Extract first valid JSON object from LLM output (strips think-tags and markdown fences)."""
    # Remove <think>...</think> blocks (DeepSeek / qwen3)
    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Extract first {...} block
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


def validate_soul(soul: dict) -> list[str]:
    """Return list of missing / wrong-type field errors."""
    errors = []
    list_fields = {"loves", "hates", "motifs", "catchphrases", "avoid", "red_flags"}
    str_fields  = {"caricature_name", "emoji", "color", "personality", "description"}

    for f in str_fields:
        if f not in soul:
            errors.append(f"Missing: {f}")
        elif not isinstance(soul[f], str):
            errors.append(f"Wrong type (expected str): {f}")

    for f in list_fields:
        if f not in soul:
            errors.append(f"Missing: {f}")
        elif not isinstance(soul[f], list):
            errors.append(f"Wrong type (expected list): {f}")
        elif len(soul[f]) == 0:
            errors.append(f"Empty list: {f}")

    if "personality" in soul and soul["personality"] not in ARCHETYPES:
        errors.append(f"Invalid archetype: {soul['personality']!r}. Must be one of {ARCHETYPES}")

    if "color" in soul and not re.match(r"^#[0-9A-Fa-f]{6}$", soul.get("color", "")):
        errors.append(f"Invalid hex color: {soul.get('color')!r}")

    return errors


# ── Display ───────────────────────────────────────────────────────────────────

def print_soul(soul: dict, label: str = "SOUL"):
    print(f"\n{THIN}")
    print(f"  {label}")
    print(THIN)
    for field in SOUL_FIELDS:
        val = soul.get(field, "—")
        if isinstance(val, list):
            print(f"  {field}:")
            for item in val:
                print(f"    • {item}")
        else:
            print(f"  {field}: {val}")


# ── Main test flow ────────────────────────────────────────────────────────────

async def run_test(real_name: str, archetype: str | None, regen_field: str | None):
    print(SEP)
    print("  SOUL GENERATOR — Pipeline Simulation")
    print(f"  Person    : {real_name}")
    print(f"  Archetype : {archetype or '(auto-detect)'}")
    print(f"  Regen     : {regen_field or '(full generation only)'}")
    print(SEP)

    # ── Step 0: find LLM endpoint ────────────────────────────────────────────
    endpoint = await find_available_endpoint()
    if not endpoint:
        print("\n[ERROR] No LLM endpoint available. Check Ollama servers.")
        sys.exit(1)

    # ── Step 1: DDG search ────────────────────────────────────────────────────
    snippets = await fetch_person_context(real_name)
    if not snippets:
        print("[WARN] No DDG snippets found — proceeding with LLM knowledge only")

    print("\n[DDG] Snippets preview:")
    for i, s in enumerate(snippets[:4], 1):
        print(f"  {i}. {s[:120]}...")

    # ── Step 2: Full soul generation ─────────────────────────────────────────
    print(f"\n[LLM] Generating full soul ({endpoint['label']}) ...")
    prompt = build_soul_prompt(real_name, snippets, archetype)

    print(f"[LLM] Prompt length: {len(prompt)} chars")

    raw, elapsed = await call_llm(endpoint, prompt)
    print(f"[LLM] Response in {elapsed:.1f}s — {len(raw)} chars")

    soul = extract_json(raw)
    if soul is None:
        print("[ERROR] Could not parse JSON from LLM response.")
        print("--- Raw response ---")
        print(raw[:500])
        sys.exit(1)

    errors = validate_soul(soul)
    if errors:
        print(f"\n[VALIDATION] {len(errors)} issue(s):")
        for e in errors:
            print(f"  ✗ {e}")
    else:
        print(f"\n[VALIDATION] ✅ All {len(SOUL_FIELDS)} fields present and valid")

    print_soul(soul, f"GENERATED SOUL — {real_name} ({elapsed:.1f}s)")

    # ── Step 3: Per-field regeneration (optional) ─────────────────────────────
    if regen_field:
        if regen_field not in SOUL_FIELDS:
            print(f"\n[ERROR] Unknown field: {regen_field!r}. Valid: {SOUL_FIELDS}")
            sys.exit(1)

        print(f"\n[REGEN] Regenerating field: {regen_field!r} ...")
        regen_prompt = build_regen_prompt(regen_field, soul, real_name)
        raw2, elapsed2 = await call_llm(endpoint, regen_prompt)
        print(f"[REGEN] Done in {elapsed2:.1f}s")

        regen_result = extract_json(raw2)
        if regen_result and regen_field in regen_result:
            print(f"\n[REGEN] Before: {json.dumps(soul.get(regen_field), ensure_ascii=False)}")
            print(f"[REGEN] After:  {json.dumps(regen_result[regen_field], ensure_ascii=False)}")
            soul[regen_field] = regen_result[regen_field]
            print(f"\n[REGEN] ✅ Field '{regen_field}' updated successfully")
        else:
            print(f"[REGEN] ✗ Could not parse regen result. Raw: {raw2[:200]}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  FINAL RESULT (ready to save to DB)")
    print(SEP)
    print(json.dumps(soul, ensure_ascii=False, indent=2))

    print(f"\n{SEP}")
    print("  PIPELINE SUMMARY")
    print(SEP)
    print(f"  DDG snippets   : {len(snippets)}")
    print(f"  Generation     : {elapsed:.1f}s  [{endpoint['label']}]")
    if regen_field:
        print(f"  Regen ({regen_field}) : {elapsed2:.1f}s")
    print(f"  Validation     : {'✅ OK' if not errors else f'✗ {len(errors)} issues'}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Soul Generator pipeline test")
    parser.add_argument("--person",   default="Elon Musk",   help="Real name to parodize")
    parser.add_argument("--archetype", default=None,          help=f"Optional archetype: {', '.join(ARCHETYPES)}")
    parser.add_argument("--regen",    default=None,           help=f"Also test regen of this field: {', '.join(SOUL_FIELDS)}")
    args = parser.parse_args()

    if args.archetype and args.archetype not in ARCHETYPES:
        print(f"Invalid archetype {args.archetype!r}. Must be one of: {', '.join(ARCHETYPES)}")
        sys.exit(1)

    asyncio.run(run_test(args.person, args.archetype, args.regen))


if __name__ == "__main__":
    main()
