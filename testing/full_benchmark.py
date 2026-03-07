#!/usr/bin/env python3
"""
Full Benchmark: Prompt Structure × Model Comparison
====================================================
Phase 1 — Prompt Battle  (model fixed: mistral-small3.1:24b)
  4 prompt variants × 6 characters × 4 films = 96 calls

Phase 2 — Model Battle  (prompt fixed: Phase 1 winner)
  4 models × 6 characters × 4 films = 96 calls

Metrics:
  voice_score   — LLM-as-judge (dolphin3) 0-3: catchphrases, anecdotes, character markers
  calibration   — rating within expected ideological range for character × film
  format_ok     — starts with X/10, 80-180 words

Usage:
  python3 testing/full_benchmark.py                          # full run
  python3 testing/full_benchmark.py --phase 1               # prompt battle only
  python3 testing/full_benchmark.py --phase 2 --variant V3  # model battle with V3
  python3 testing/full_benchmark.py --quick                 # 1 char × 1 film smoke test
  python3 testing/full_benchmark.py --no-judge              # skip LLM-as-judge (faster)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(globals().get("__file__", "testing/full_benchmark.py")).parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "benchmark-results"

DEFAULT_OLLAMA_URL  = "http://192.168.2.69:11434"
PHASE1_MODEL        = "mistral-small3.1:24b"
JUDGE_MODEL         = "dolphin3:latest"
PHASE2_MODELS       = [
    "mistral-small3.1:24b",
    "type32/eva-qwen-2.5-14b:latest",
    "muse-12b:latest",
    "LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M",
]

# ── MOVIES ───────────────────────────────────────────────────────────────────

MOVIES: list[dict] = [
    {
        "tmdb_id": 346698,
        "title": "Barbie",
        "year": 2023,
        "type": "movie",
        "genres": "Comedia, Aventura, Fantasía",
        "synopsis": (
            "Barbie (Margot Robbie) es una muñeca rubia despampanante que vive en Barbieland, un mundo "
            "de colores brillantes y neón lleno de Barbies guapísimas en bikini y con tacones. "
            "Cuando le surgen pensamientos existenciales viaja al mundo real con Ken (Ryan Gosling). "
            "La estética es hipnótica: rosa, brillante, y llena de chicas. "
            "Director: Greta Gerwig. También hay una crítica al patriarcado, pero sobre todo hay muchas "
            "Barbies rubias bailando y posando."
        ),
    },
    {
        "tmdb_id": 245891,
        "title": "John Wick",
        "year": 2014,
        "type": "movie",
        "genres": "Acción, Thriller",
        "synopsis": (
            "John Wick, un ex-asesino retirado, vuelve al mundo criminal para vengarse de quienes "
            "mataron a su perro — el último regalo de su esposa fallecida. Violencia coreografiada extrema, "
            "alta tasa de cadáveres, estética de neón. Director: Chad Stahelski. "
            "Protagonista: Keanu Reeves. Secuelas con franquicia de 4 entregas."
        ),
    },
    {
        "tmdb_id": 7299,
        "title": "Idiocracy",
        "year": 2006,
        "type": "movie",
        "genres": "Comedia, Ciencia ficción",
        "synopsis": (
            "Un soldado americano de inteligencia media es criogenizado y despierta en el año 2505, "
            "donde la humanidad ha degenerado por completo: nadie lee, el presidente es un ex-luchador, "
            "las plantas se riegan con bebida energética. Él es ahora el hombre más inteligente del mundo. "
            "Director: Mike Judge. Crítica satírica al anti-intelectualismo americano."
        ),
    },
    {
        "tmdb_id": 238,
        "title": "El Padrino",
        "year": 1972,
        "type": "movie",
        "genres": "Drama, Crimen",
        "synopsis": (
            "Don Vito Corleone dirige la familia mafiosa más poderosa de Nueva York. Tras un atentado, "
            "su hijo Michael, que quería mantenerse al margen, asume el mando y se convierte en "
            "el nuevo Padrino. Honor, lealtad, familia y venganza como valores centrales. "
            "Director: Francis Ford Coppola. Protagonistas: Marlon Brando, Al Pacino. "
            "Considerada una de las mejores películas de la historia."
        ),
    },
]

# ── EXPECTED RATINGS ─────────────────────────────────────────────────────────

# {character_name: {tmdb_id: (min, max)}}
EXPECTED_RATINGS: dict[str, dict[int, tuple[int, int]]] = {
    "Marco Aurelio":   {346698: (4, 6), 245891: (3, 5), 7299: (7, 9), 238: (5, 7)},
    "Rosario Costras": {346698: (5, 7), 245891: (4, 6), 7299: (3, 5), 238: (7, 9)},
    "Adolf Histeric":  {346698: (1, 2), 245891: (6, 8), 7299: (7, 9), 238: (5, 7)},
    "Charlie Sheen":   {346698: (6, 8), 245891: (8, 10), 7299: (5, 7), 238: (7, 9)},
    "Antonio Recio":   {346698: (1, 3), 245891: (6, 8), 7299: (4, 6), 238: (9, 10)},
    "Beavis":          {346698: (7, 9), 245891: (9, 10), 7299: (8, 10), 238: (2, 4)},
}

# ── CHARACTERS ───────────────────────────────────────────────────────────────

CHARACTERS: dict[str, dict] = {
    "Marco Aurelio": {
        "name": "Marco Aurelio",
        "emoji": "🏛️",
        "description": (
            "Eres Marco Aurelio 🏛️. Emperador filósofo estoico. Analizas el cine como "
            "reflejo de la condición humana, con distancia filosófica y resignación sabia. "
            "Citas a Epicteto y Séneca. Ves la decadencia de Roma en cada pantalla."
        ),
        "loves": json.dumps(["Virtud y disciplina", "Narrativas de sacrificio", "Reflexión filosófica", "Orden natural"]),
        "hates": json.dumps(["Hedonismo vacío", "Falta de propósito moral", "Entretenimiento sin sustancia"]),
        "red_flags": json.dumps(["glorificación del vicio", "ausencia de virtud", "nihilismo sin redención"]),
        "avoid": json.dumps(["Elogiar la superficialidad", "Ignorar el mensaje moral"]),
        "anecdotes": [
            "Como escribí en mis Meditaciones: 'La tranquilidad no es otra cosa que el buen orden del espíritu'.",
            "Epicteto me enseñó que no podemos controlar lo exterior, solo nuestra respuesta.",
            "Recuerdo cuando en Panonia, rodeado de muerte, encontré más verdad que en todo el Senado.",
            "Séneca tenía razón: ars longa, vita brevis — y este director lo ha olvidado.",
        ],
        "catchphrases": [
            "Memento mori.",
            "La virtud es el único bien verdadero.",
            "Como escribí en mis Meditaciones...",
        ],
    },
    "Rosario Costras": {
        "name": "Rosario Costras",
        "emoji": "✊",
        "description": (
            "Eres Rosario Costras ✊. Crítica feminista interseccional. Analizas cada obra "
            "desde la representación, el patriarcado y la justicia social. "
            "Tu rating refleja el grado de emancipación y diversidad."
        ),
        "loves": json.dumps(["Protagonistas femeninas con agencia", "Diversidad racial auténtica", "Crítica al patriarcado", "Directoras de cine"]),
        "hates": json.dumps(["Male gaze", "Blanqueamiento del reparto", "Mujer como objeto decorativo", "Final conservador"]),
        "red_flags": json.dumps(["male gaze explícito", "ausencia de diversidad racial", "violencia doméstica sin crítica"]),
        "avoid": json.dumps(["Ignorar la representación de minorías", "Elogiar la técnica sin considerar el mensaje social"]),
        "anecdotes": [
            "Mi cuñada de Albacete también lo vio y dijo que era 'muy rara', claro, ella no ha leído a bell hooks.",
            "Esto me recuerda a cuando fui al cine con el grupo de Mujeres en Red y tuvimos que salir a mitad.",
            "La representación importa — se lo digo siempre al médico de cabecera cuando me prescribe pastillas en lugar de escucharme.",
            "Como diría Angela Davis: no puedes ser feminista y no ser antirracista.",
        ],
        "catchphrases": [
            "La representación importa.",
            "¿Dónde están las mujeres de color?",
            "El male gaze sigue muy vivo.",
            "Esto es exactamente lo que explicamos en el taller.",
        ],
    },
    "Adolf Histeric": {
        "name": "Adolf Histeric",
        "emoji": "🎩",
        "description": (
            "Eres Adolf Histeric 🎩. Defensor exacerbado de la pureza cultural y cinematográfica. "
            "Ves conspiraciones ideológicas en cada película. Tu crítica es furia ideológica pura."
        ),
        "loves": json.dumps(["Épica histórica europea", "Cine bélico clásico", "Narrativas de destino y pueblo", "Expresionismo alemán"]),
        "hates": json.dumps(["Propaganda progresista", "Protagonistas de minorías", "Crítica al capitalismo", "Agenda woke"]),
        "red_flags": json.dumps(["agenda woke", "diversidad forzada", "protagonista no europeo", "crítica al capitalismo"]),
        "avoid": json.dumps(["Elogiar obras con mensajes progresistas", "Ignorar la agenda política"]),
        "anecdotes": [
            "Wagner entendía el arte como expresión del alma del pueblo — esto no.",
            "En el Reich que pudo ser, este director no habría pasado la censura cultural.",
            "El expresionismo alemán de los años 20 era cine de verdad, no esta basura degenerada.",
            "Como me dijo mi barbero de confianza: 'la decadencia cultural es la antesala del colapso'.",
        ],
        "catchphrases": [
            "¡Esto es una conspiración!",
            "¡Abajo con la degeneración cultural!",
            "¡El arte debe servir a la nación!",
            "Wagner se revuelve en su tumba.",
        ],
    },
    "Charlie Sheen": {
        "name": "Charlie Sheen",
        "emoji": "🌪️",
        "description": (
            "Eres Charlie Sheen 🌪️. Leyenda de Hollywood, adicto al exceso y al éxito. "
            "Winning es tu filosofía de vida. Cada película la juzgas por su energía, "
            "su autenticidad caótica y cuánto tigre sangre tiene."
        ),
        "loves": json.dumps(["Energía caótica y auténtica", "Personajes sin filtros", "Exceso y adrenalina", "Anticonformismo"]),
        "hates": json.dumps(["Moralismo aburrido", "Personajes que se disculpan por existir", "Cine corporativo y calculado", "Final feliz de manual"]),
        "red_flags": json.dumps(["protagonista pusilánime", "moraleja forzada", "ausencia de riesgo"]),
        "avoid": json.dumps(["Elogiar lo seguro y predecible", "Premiar la mediocridad disfrazada de arte"]),
        "anecdotes": [
            "Cuando rodábamos Two and a Half Men yo llegaba así al set y aun así era el mejor del equipo.",
            "En Bali con las goddesses aprendí que el límite es un concepto inventado por los mediocres.",
            "Mi abogado me dijo que no hablara de esto, pero mi abogado no tiene tiger blood.",
            "Winning. Eso es lo que yo hago. Eso es lo que esta película no hace.",
        ],
        "catchphrases": [
            "Winning!",
            "Tiger blood.",
            "Eres un troll enviado por troll trolls.",
            "No puedes procesar esto con un cerebro normal.",
        ],
    },
    "Antonio Recio": {
        "name": "Antonio Recio",
        "emoji": "🥩",
        "description": (
            "Eres Antonio Recio 🥩. Charcutero, hombre de orden, cabeza de familia. "
            "El mercado de La Boqueria, el chóped y los valores tradicionales son tu brújula moral. "
            "Desconfías de todo lo moderno y 'de esos'."
        ),
        "loves": json.dumps(["Familia tradicional", "Hombres que mandan", "Negocios honestos de toda la vida", "España de verdad"]),
        "hates": json.dumps(["Progres y sus tonterías", "Los de esos", "Feminismo radical", "Películas raras sin argumento"]),
        "red_flags": json.dumps(["protagonista maricón", "mensaje feminista", "familia desestructurada como cosa normal", "inmigración como tema positivo"]),
        "avoid": json.dumps(["Elogiar mensajes que van contra la familia", "Premiar lo raro por ser raro"]),
        "anecdotes": [
            "El chóped no se toca. La familia tampoco. Eso lo aprendí de mi padre y mi padre lo aprendió del suyo.",
            "En el mercado de La Boqueria llevamos cuatro generaciones. Eso es una saga, no estas películas modernas.",
            "Mi mujer Menchu vio esto y se fue a hacer la cena. Eso lo dice todo.",
            "Yo es que con estas cosas modernas no me aclaro. Dame un Paco Martínez Soria y aquí paz.",
        ],
        "catchphrases": [
            "¡Menchu!",
            "Esto es cosa de esos.",
            "En mi casa el que manda manda.",
            "El chóped es lo que es.",
        ],
    },
    "Beavis": {
        "name": "Beavis",
        "emoji": "🔥",
        "description": (
            "Eres Beavis 🔥. Tienes como 15 años y tu cerebro funciona en binario: mola o no mola. "
            "Amas el fuego, el heavy metal, la violencia, las explosiones y las chicas. "
            "Tu alter ego es Cornholio. Tu compañero es Butt-Head, que es idiota, aunque a veces tiene razón. "
            "Escribes críticas como si las dijeras en voz alta mientras ves la tele con Butt-Head."
        ),
        "loves": json.dumps([
            "Fuego y explosiones",
            "Heavy metal (Metallica, AC/DC, Slayer)",
            "Violencia, peleas y muertes en pantalla",
            "Chicas, especialmente rubias",
            "Cosas que van rápido (coches, motos, persecuciones)",
            "Personajes idiotas que no saben nada (se siente identificado)",
            "Escenas de destrucción masiva",
        ], ensure_ascii=False),
        "hates": json.dumps([
            "Películas donde solo hablan y no pasa nada",
            "Películas en blanco y negro o muy antiguas",
            "Cuando no hay ni una sola explosión",
            "Escenas románticas largas y aburridas (a menos que salgan chicas)",
            "Subtítulos (leer es un esfuerzo)",
            "Finales donde el malo se arrepiente y todos se abrazan",
        ], ensure_ascii=False),
        "red_flags": json.dumps([
            "Más de 10 minutos seguidos de diálogo sin acción",
            "Película en blanco y negro",
            "El protagonista es viejo y habla despacio",
            "No hay ni una sola explosión, pelea ni persecución en toda la peli",
        ], ensure_ascii=False),
        "avoid": json.dumps([
            "Usar palabras de más de tres sílabas sin confundirse",
            "Reflexionar filosóficamente sobre nada",
            "Dar una puntuación media (5 o 6) sin razón de peso",
        ], ensure_ascii=False),
        "anecdotes": [
            "Una vez prendí fuego a la papelera del cole y fue lo mejor que he hecho en mi vida.",
            "Butt-Head dice que El Padrino es una obra maestra pero Butt-Head es idiota.",
            "Yo soy Cornholio. Vine al videoclub a buscar algo con fuego.",
            "La mejor peli que he visto fue aquella donde todo explotaba al final. No sé cómo se llamaba.",
        ],
        "catchphrases": [
            "¡FUEGO! ¡FUEGO! Ehehe",
            "Esto mola. / Esto no mola.",
            "Soy Cornholio. Necesito TP para mi bungholio.",
            "Butt-Head dice que esto apesta, pero Butt-Head es idiota.",
            "Ehehe... dijo esa palabra... ehehe.",
            "¡Es lo más que he visto en mi vida!",
        ],
    },
}

# ── PROMPT VARIANTS ───────────────────────────────────────────────────────────

SYSTEM_BLOCK = (
    "You are a parody film criticism system.\n"
    "Your rating ALWAYS reflects the character's ideological perspective, NEVER technical quality.\n"
    "BEFORE writing a single word: evaluate the work against the character's loves, hates and red_flags.\n"
    "That analysis determines the number. The number is not an opinion about quality — it is an ideological judgment.\n"
    "A 5 or 6 is only valid if no love, hate or red_flag applies AND you have explicit reason for it.\n"
    "You are never neutral by default. Respond ONLY with the critic. Respond in Spanish."
)

VOICE_INSTRUCTION = (
    "\nUsa tu voz más característica: incluye alguna muletilla tuya, compara la obra con algo de tu vida "
    "o suelta una anécdota personal. Que se note quién eres, no solo qué piensas."
)

VARIANTS: list[dict] = [
    {"id": "V0", "voice_instruction": False, "anecdotes": False,
     "desc": "Baseline — prompt actual de producción sin cambios"},
    {"id": "V1", "voice_instruction": True,  "anecdotes": False,
     "desc": "Instrucción de voz explícita — pide muletillas y anécdotas"},
    {"id": "V2", "voice_instruction": False, "anecdotes": True,
     "desc": "Anécdotas en el soul — referencias concretas del personaje"},
    {"id": "V3", "voice_instruction": True,  "anecdotes": True,
     "desc": "Combinado — instrucción de voz + anécdotas (full enrichment)"},
]


def build_messages(variant: dict, character: dict, movie: dict) -> list[dict]:
    """Build the messages list for Ollama /api/chat."""
    user_block = _build_user_block(variant, character, movie)
    return [
        {"role": "system", "content": SYSTEM_BLOCK},
        {"role": "user", "content": user_block},
    ]


def _build_user_block(variant: dict, character: dict, movie: dict) -> str:
    name      = character["name"]
    emoji     = character["emoji"]
    desc      = character["description"]
    loves     = json.loads(character["loves"])
    hates     = json.loads(character["hates"])
    red_flags = json.loads(character["red_flags"])
    avoid     = json.loads(character["avoid"])

    parts = [desc]

    # V2/V3: inject anecdotes after identity
    if variant["anecdotes"] and character.get("anecdotes"):
        anec = "\n".join(f"- {a}" for a in character["anecdotes"])
        parts.append(f"REFERENCIAS PERSONALES QUE PUEDES USAR:\n{anec}")

    # NUNCA block
    nunca_lines = []
    if avoid:
        nunca_lines.append(f"NUNCA: {'; '.join(avoid)}.")
    if red_flags:
        nunca_lines.append(
            f"Si detectas alguno de estos elementos reacciona con intensidad negativa: {'; '.join(red_flags)}."
        )
    if nunca_lines:
        parts.append("\n".join(nunca_lines))

    # Rating rubric
    rubric = ["DECIDE EL RATING ANTES DE ESCRIBIR — en este orden:"]
    if red_flags:
        rubric.append(f"→ ¿La obra activa alguno de estos red_flags? {', '.join(red_flags[:4])} → pon 1-3")
    if hates:
        rubric.append(f"→ ¿La obra encarna algo que odias? {', '.join(hates[:5])} → pon 1-4")
    if loves:
        rubric.append(f"→ ¿La obra encarna algo que amas? {', '.join(loves[:5])} → pon 7-10")
    rubric.append("→ ¿Ninguna aplica con claridad? → justifica explícitamente por qué el número es 5 o 6")
    parts.append("RÚBRICA DE PUNTUACIÓN:\n" + "\n".join(rubric))

    # Film block
    title    = movie["title"]
    year     = movie["year"]
    genres   = movie["genres"]
    synopsis = movie["synopsis"]
    instrucciones = (
        f"Escribe una crítica de máximo 150 palabras como {name} {emoji}.\n"
        "Empieza con la puntuación que hayas decidido según la rúbrica: X/10\n"
        "Basa tu análisis en los datos reales de la obra que te hemos dado arriba.\n"
        "No inventes tramas, personajes ni elementos que no aparezcan en la sinopsis.\n"
        "Escribe desde tu perspectiva ideológica con tu tono auténtico.\n"
        "Sé directo y personal."
    )

    # V1/V3: append voice instruction
    if variant["voice_instruction"]:
        instrucciones += VOICE_INSTRUCTION

    parts.append(
        f"OBRA A CRITICAR:\n"
        f"Título: \"{title}\" ({year})\n"
        f"Géneros: {genres}\n"
        f"Sinopsis: {synopsis}\n\n"
        f"INSTRUCCIONES:\n{instrucciones}"
    )

    return "\n\n".join(parts)


# ── LLM CALLS ────────────────────────────────────────────────────────────────

async def call_ollama(
    url: str,
    model: str,
    messages: list[dict],
    think: bool = False,
    timeout: float = 180.0,
) -> tuple[str, float]:
    """Call Ollama /api/chat. Returns (content, elapsed_seconds)."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": think,
        "options": {
            "temperature": 0.75,
            "num_predict": 600,
            "top_p": 0.95,
            "top_k": 20,
        },
    }
    t0 = time.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{url}/api/chat", json=payload)
        resp.raise_for_status()
    elapsed = time.time() - t0
    content = resp.json().get("message", {}).get("content", "")
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content, elapsed


JUDGE_PROMPT = """\
You are evaluating a parody film critic. The character is: {character_name}.
Score the following text from 0 to 3:
  0 = generic, no personality markers at all
  1 = some character voice but could be almost anyone
  2 = clear character voice with at least one specific reference, anecdote or catchphrase
  3 = strong authentic voice, multiple personal references or characteristic anecdotes

Text:
{critic_text}

Reply with a single digit (0, 1, 2 or 3) and nothing else."""


async def call_judge(url: str, character_name: str, critic_text: str) -> int | None:
    """Call dolphin3 as LLM-as-judge. Returns voice_score 0-3 or None on error."""
    prompt = JUDGE_PROMPT.format(character_name=character_name, critic_text=critic_text)
    messages = [{"role": "user", "content": prompt}]
    try:
        content, _ = await call_ollama(
            url, JUDGE_MODEL, messages,
            think=False, timeout=60.0,
        )
        m = re.search(r"[0-3]", content.strip())
        return int(m.group()) if m else None
    except Exception:
        return None


# ── SCORING ───────────────────────────────────────────────────────────────────

def extract_rating(text: str) -> int | None:
    m = re.search(r"(\d{1,2})\s*/\s*10", text)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 10 else None
    return None


def score_result(
    text: str,
    character_name: str,
    tmdb_id: int,
    voice_score: int | None,
) -> dict:
    rating = extract_rating(text)
    word_count = len(text.split())
    expected_range = EXPECTED_RATINGS.get(character_name, {}).get(tmdb_id)

    calibration_ok: bool | None = None
    if rating is not None and expected_range is not None:
        lo, hi = expected_range
        calibration_ok = lo <= rating <= hi

    return {
        "format_ok":      rating is not None,
        "rating":         rating,
        "expected_range": list(expected_range) if expected_range else None,
        "calibration_ok": calibration_ok,
        "word_count":     word_count,
        "word_count_ok":  80 <= word_count <= 220,
        "voice_score":    voice_score,
    }


# ── SINGLE RUN ────────────────────────────────────────────────────────────────

async def run_one(
    variant: dict,
    model: str,
    character: dict,
    movie: dict,
    ollama_url: str,
    use_judge: bool,
) -> dict:
    char_name = character["name"]
    base = {
        "variant":   variant["id"],
        "model":     model,
        "character": char_name,
        "tmdb_id":   movie["tmdb_id"],
        "title":     movie["title"],
    }
    messages = build_messages(variant, character, movie)
    try:
        text, elapsed = await call_ollama(ollama_url, model, messages)
        voice_score = await call_judge(ollama_url, char_name, text) if use_judge else None
        scores = score_result(text, char_name, movie["tmdb_id"], voice_score)
        return {**base, "elapsed": round(elapsed, 1), "text": text, **scores, "error": None}
    except Exception as exc:
        return {
            **base, "elapsed": None, "text": None,
            "format_ok": False, "rating": None, "expected_range": None,
            "calibration_ok": None, "word_count": 0, "word_count_ok": False,
            "voice_score": None, "error": str(exc),
        }


# ── ORCHESTRATORS ─────────────────────────────────────────────────────────────

async def run_phase(
    label: str,
    combos: list[tuple],
    ollama_url: str,
    use_judge: bool,
) -> list[dict]:
    """Generic phase runner. combos is a list of (variant, model, character, movie)."""
    total = len(combos)
    results: list[dict] = []
    print(f"\n{'─'*60}")
    print(f"> {label}  ({total} llamadas)")
    print(f"{'─'*60}")
    for i, (variant, model, character, movie) in enumerate(combos, 1):
        tag = f"[{i:03d}/{total:03d}]"
        print(f"  {tag} {variant['id']} | {model[:28]:<28} | {character['name']:<16} x {movie['title']}", end=" ... ", flush=True)
        result = await run_one(variant, model, character, movie, ollama_url, use_judge)
        results.append(result)
        if result["error"]:
            print(f"ERROR: {result['error'][:60]}")
        else:
            cal = "OK" if result["calibration_ok"] else ("FAIL" if result["calibration_ok"] is False else "??")
            vs  = f"V={result['voice_score']}" if result["voice_score"] is not None else "V=?"
            print(f"{result['rating']}/10 [{cal}] {vs} {result['word_count']}w {result['elapsed']}s")
    return results


def build_phase1_combos(args) -> list[tuple]:
    variants   = [v for v in VARIANTS if v["id"] in args.variants]
    characters = [CHARACTERS[n] for n in args.characters if n in CHARACTERS]
    movies     = MOVIES[:args.films]
    return [
        (variant, args.phase1_model, char, movie)
        for variant in variants
        for char    in characters
        for movie   in movies
    ]


def build_phase2_combos(winner_variant: dict, args) -> list[tuple]:
    models     = args.phase2_models
    characters = [CHARACTERS[n] for n in args.characters if n in CHARACTERS]
    movies     = MOVIES[:args.films]
    return [
        (winner_variant, model, char, movie)
        for model  in models
        for char   in characters
        for movie  in movies
    ]


# ── WINNER SELECTION ──────────────────────────────────────────────────────────

def pick_winner(results: list[dict]) -> str:
    """Pick best variant by: avg voice_score (primary) + calibration_ok% (secondary)."""
    from collections import defaultdict
    stats: dict[str, dict] = defaultdict(lambda: {"voice": [], "cal": []})
    for r in results:
        if r["error"]:
            continue
        vid = r["variant"]
        if r["voice_score"] is not None:
            stats[vid]["voice"].append(r["voice_score"])
        if r["calibration_ok"] is not None:
            stats[vid]["cal"].append(int(r["calibration_ok"]))

    best_vid = "V0"
    best_score = -1.0
    for vid, s in stats.items():
        avg_voice = sum(s["voice"]) / len(s["voice"]) if s["voice"] else 0.0
        avg_cal   = sum(s["cal"])   / len(s["cal"])   if s["cal"]   else 0.0
        combined  = avg_voice + avg_cal * 0.5   # voice weighted 2x
        if combined > best_score:
            best_score = combined
            best_vid = vid
    return best_vid


# ── REPORTING ─────────────────────────────────────────────────────────────────

def _agg(results: list[dict], group_key: str) -> dict[str, dict]:
    from collections import defaultdict
    agg = defaultdict(lambda: {"voice": [], "cal": [], "times": [], "format": []})
    for r in results:
        if r["error"]:
            continue
        k = r[group_key]
        if r["voice_score"] is not None:
            agg[k]["voice"].append(r["voice_score"])
        if r["calibration_ok"] is not None:
            agg[k]["cal"].append(int(r["calibration_ok"]))
        if r["elapsed"] is not None:
            agg[k]["times"].append(r["elapsed"])
        agg[k]["format"].append(int(r["format_ok"]))
    return dict(agg)


def generate_report(
    phase1_results: list[dict],
    phase2_results: list[dict],
    winner_variant: dict,
    meta: dict,
) -> str:
    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines.append("# Full Benchmark Report")
    lines.append("")
    lines.append(f"**Date:** {meta['date']}")
    lines.append(f"**Ollama:** {meta['ollama_url']}")
    lines.append(f"**Phase 1 model:** {meta['phase1_model']}")
    lines.append(f"**Phase 2 models:** {', '.join(meta['phase2_models'])}")
    lines.append(f"**Judge model:** {meta['judge_model'] or 'disabled'}")
    lines.append(f"**Characters:** {', '.join(meta['characters'])}")
    lines.append(f"**Films:** {meta['films']}")
    lines.append("")

    # ── Phase 1 table ─────────────────────────────────────────────────────────
    if phase1_results:
        lines.append("## Phase 1 — Prompt Battle")
        lines.append("")
        lines.append("| Variant | Description | Avg Voice | Calibration% | Format% |")
        lines.append("|---------|-------------|-----------|--------------|---------|")
        agg1 = _agg(phase1_results, "variant")
        for v in VARIANTS:
            vid = v["id"]
            s = agg1.get(vid, {})
            avg_voice = f"{sum(s['voice'])/len(s['voice']):.2f}" if s.get("voice") else "n/a"
            cal_pct   = f"{100*sum(s['cal'])/len(s['cal']):.0f}%" if s.get("cal") else "n/a"
            fmt_pct   = f"{100*sum(s['format'])/len(s['format']):.0f}%" if s.get("format") else "n/a"
            lines.append(f"| {vid} | {v['desc']} | {avg_voice} | {cal_pct} | {fmt_pct} |")
        lines.append("")
        lines.append(f"**Winner: {winner_variant['id']}** — {winner_variant['desc']}")
        lines.append("")

    # ── Phase 2 table ─────────────────────────────────────────────────────────
    if phase2_results:
        lines.append("## Phase 2 — Model Battle")
        lines.append("")
        lines.append(f"Prompt variant: **{winner_variant['id']}** — {winner_variant['desc']}")
        lines.append("")
        lines.append("| Model | Avg Voice | Calibration% | Avg Time (s) |")
        lines.append("|-------|-----------|--------------|--------------|")
        agg2 = _agg(phase2_results, "model")
        for model, s in agg2.items():
            avg_voice = f"{sum(s['voice'])/len(s['voice']):.2f}" if s.get("voice") else "n/a"
            cal_pct   = f"{100*sum(s['cal'])/len(s['cal']):.0f}%" if s.get("cal") else "n/a"
            avg_time  = f"{sum(s['times'])/len(s['times']):.1f}" if s.get("times") else "n/a"
            lines.append(f"| {model} | {avg_voice} | {cal_pct} | {avg_time} |")
        lines.append("")

    # ── Per-character best combo ───────────────────────────────────────────────
    all_results = phase1_results + phase2_results
    if all_results:
        lines.append("## Per-Character Best Combo")
        lines.append("")
        lines.append("| Character | Best Variant | Best Model | Voice Score |")
        lines.append("|-----------|-------------|------------|-------------|")
        from collections import defaultdict
        char_best: dict[str, dict] = {}
        for r in all_results:
            if r["error"] or r["voice_score"] is not None:
                char = r["character"]
                vs = r["voice_score"] if r["voice_score"] is not None else -1
                if char not in char_best or vs > char_best[char]["voice_score"]:
                    char_best[char] = r
        for char_name in meta["characters"]:
            if char_name in char_best:
                r = char_best[char_name]
                vs = r["voice_score"] if r["voice_score"] is not None else "n/a"
                lines.append(f"| {char_name} | {r['variant']} | {r['model']} | {vs} |")
        lines.append("")

    # ── Best critic samples ───────────────────────────────────────────────────
    scored = [
        r for r in all_results
        if not r["error"] and r["text"] and r["voice_score"] is not None
    ]
    scored.sort(key=lambda r: r["voice_score"], reverse=True)
    samples = scored[:3]

    if samples:
        lines.append("## Top Critic Samples")
        lines.append("")
        for r in samples:
            lines.append(f"### {r['character']} x {r['title']} ({r['variant']} | {r['model']})")
            lines.append(f"Voice score: {r['voice_score']}/3 | Rating: {r['rating']}/10 | Words: {r['word_count']}")
            lines.append("")
            lines.append(r["text"])
            lines.append("")

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Full Parody Critics benchmark")
    p.add_argument("--ollama-url",    default=DEFAULT_OLLAMA_URL)
    p.add_argument("--phase",         type=int, choices=[1, 2], default=None,
                   help="Run only phase 1 or 2 (default: both)")
    p.add_argument("--variant",       default=None,
                   help="Force a specific variant for phase 2 (e.g. V3)")
    p.add_argument("--variants",      nargs="+", default=["V0", "V1", "V2", "V3"])
    p.add_argument("--phase1-model",  default=PHASE1_MODEL)
    p.add_argument("--phase2-models", nargs="+", default=PHASE2_MODELS)
    p.add_argument("--characters",    nargs="+", default=list(CHARACTERS.keys()))
    p.add_argument("--films",         type=int, default=4,
                   help="Number of films to use (1-4)")
    p.add_argument("--no-judge",      action="store_true",
                   help="Skip LLM-as-judge voice scoring (faster)")
    p.add_argument("--quick",         action="store_true",
                   help="Quick smoke test: 1 char x 1 film x V0 x primary model")
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    if args.quick:
        args.characters = ["Beavis"]
        args.films      = 1
        args.variants   = ["V0", "V3"]
        args.phase      = 1
        args.no_judge   = False

    use_judge = not args.no_judge
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")

    phase1_results: list[dict] = []
    phase2_results: list[dict] = []
    winner_variant = next(v for v in VARIANTS if v["id"] == "V0")

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    if args.phase in (None, 1):
        combos = build_phase1_combos(args)
        phase1_results = await run_phase(
            f"PHASE 1 -- Prompt Battle (model: {args.phase1_model})",
            combos, args.ollama_url, use_judge,
        )
        winner_id = args.variant or pick_winner(phase1_results)
        winner_variant = next(v for v in VARIANTS if v["id"] == winner_id)
        print(f"\nPhase 1 winner: {winner_id} -- {winner_variant['desc']}")

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    if args.phase in (None, 2):
        if args.variant:
            winner_variant = next(v for v in VARIANTS if v["id"] == args.variant)
        combos = build_phase2_combos(winner_variant, args)
        phase2_results = await run_phase(
            f"PHASE 2 -- Model Battle (prompt: {winner_variant['id']})",
            combos, args.ollama_url, use_judge,
        )

    # ── Save results ──────────────────────────────────────────────────────────
    all_results = phase1_results + phase2_results
    meta = {
        "date": ts,
        "ollama_url": args.ollama_url,
        "phase1_model": args.phase1_model,
        "phase2_models": args.phase2_models,
        "winner_variant": winner_variant["id"],
        "characters": args.characters,
        "films": args.films,
        "judge_model": JUDGE_MODEL if use_judge else None,
    }

    json_path = OUTPUT_DIR / f"{ts}-full-benchmark.json"
    json_path.write_text(json.dumps({"meta": meta, "results": all_results}, ensure_ascii=False, indent=2))
    print(f"\nJSON saved: {json_path}")

    report = generate_report(phase1_results, phase2_results, winner_variant, meta)
    md_path = OUTPUT_DIR / f"{ts}-full-benchmark.md"
    md_path.write_text(report)
    print(f"Report saved: {md_path}")
    print("\n" + "="*60)
    print(report[:2000])


if __name__ == "__main__":
    asyncio.run(main())
