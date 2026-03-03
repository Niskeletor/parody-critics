#!/usr/bin/env python3
"""
🔬 Benchmark: i18n Prompt Language Variants
============================================
Compares 3 prompt language configurations for critic generation quality.

Variant A — Spanish system prompt + Spanish soul → Spanish output  (pre-change baseline)
Variant B — English system prompt + Spanish soul → Spanish output  (current implementation)
Variant C — English system prompt + English soul  → English output (full English pipeline)

Metrics per critic:
  - format_ok     : response starts with "X/10"
  - rating        : extracted integer 1-10
  - calibration   : rating within expected ideological range for character × film
  - word_count    : total words in response
  - lang_correct  : detected language matches expected output language
  - response_time : seconds to generate

Usage:
  python3 testing/benchmark_i18n_prompts.py
  python3 testing/benchmark_i18n_prompts.py --model mistral-small3.1:24b --runs 2
  python3 testing/benchmark_i18n_prompts.py --ollama-url http://192.168.2.69:11434
  python3 testing/benchmark_i18n_prompts.py --variants A B
  python3 testing/benchmark_i18n_prompts.py --characters "Adolf Histeric" "Rosario Costras"
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

# ── Paths ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "benchmark-results"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_OLLAMA_URL = "http://192.168.2.69:11434"
DEFAULT_MODEL = "mistral-small3.1:24b"
DEFAULT_RUNS = 1

# ── System prompt variants ────────────────────────────────────────────────────

# Variant A: pre-change Spanish SYSTEM_BLOCK (reproduced faithfully)
SYSTEM_BLOCK_A = (
    "Eres un sistema de crítica cinematográfica paródica.\n"
    "Tu rating SIEMPRE refleja la perspectiva ideológica del personaje, NUNCA la calidad técnica.\n"
    "ANTES de escribir una sola palabra: evalúa la obra según los amores, odios y red_flags del personaje.\n"
    "Ese análisis determina el número. El número no es una opinión sobre calidad — es un juicio ideológico.\n"
    "Un 5 o 6 solo es válido si ningún amor, odio o red_flag aplica claramente Y tienes razón explícita.\n"
    "Nunca eres neutral por defecto. Responde SOLO con la crítica. Responde en español."
)

# Variant B: post-change English SYSTEM_BLOCK, output in Spanish
SYSTEM_BLOCK_B = (
    "You are a parody film criticism system.\n"
    "Your rating ALWAYS reflects the character's ideological perspective, NEVER technical quality.\n"
    "BEFORE writing a single word: evaluate the work against the character's loves, hates and red_flags.\n"
    "That analysis determines the number. The number is not an opinion about quality — it is an ideological judgment.\n"
    "A 5 or 6 is only valid if no love, hate or red_flag applies AND you have explicit reason for it.\n"
    "You are never neutral by default. Respond ONLY with the critic. Respond in Spanish."
)

# Variant C: English SYSTEM_BLOCK, output in English
SYSTEM_BLOCK_C = (
    "You are a parody film criticism system.\n"
    "Your rating ALWAYS reflects the character's ideological perspective, NEVER technical quality.\n"
    "BEFORE writing a single word: evaluate the work against the character's loves, hates and red_flags.\n"
    "That analysis determines the number. The number is not an opinion about quality — it is an ideological judgment.\n"
    "A 5 or 6 is only valid if no love, hate or red_flag applies AND you have explicit reason for it.\n"
    "You are never neutral by default. Respond ONLY with the critic. Respond in English."
)

VARIANTS: list[dict] = [
    {
        "id": "A",
        "label": "A: ES-prompt+ES-soul→ES",
        "system": SYSTEM_BLOCK_A,
        "soul_lang": "es",
        "output_lang": "es",
        "block_lang": "es",
        "desc": "Spanish system prompt + Spanish soul → Spanish output (pre-change baseline)",
    },
    {
        "id": "B",
        "label": "B: EN-prompt+ES-soul→ES",
        "system": SYSTEM_BLOCK_B,
        "soul_lang": "es",
        "output_lang": "es",
        "block_lang": "es",
        "desc": "English system prompt + Spanish soul → Spanish output (current implementation)",
    },
    {
        "id": "C",
        "label": "C: EN-prompt+EN-soul→EN",
        "system": SYSTEM_BLOCK_C,
        "soul_lang": "en",
        "output_lang": "en",
        "block_lang": "en",
        "desc": "English system prompt + English soul → English output (full English pipeline)",
    },
]

# ── User-block structural labels (ES / EN) ────────────────────────────────────

_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "decide": "DECIDE EL RATING ANTES DE ESCRIBIR — en este orden:",
        "red_flag_tpl": "¿La obra activa alguno de estos red_flags? {items} → pon 1-3",
        "hates_tpl": "¿La obra encarna algo que odias? {items} → pon 1-4",
        "loves_tpl": "¿La obra encarna algo que amas? {items} → pon 7-10",
        "neutral": "¿Ninguna aplica con claridad? → justifica explícitamente por qué el número es 5 o 6",
        "nunca_tpl": "NUNCA: {items}.",
        "react_tpl": "Si detectas alguno de estos elementos reacciona con intensidad negativa: {items}.",
        "motifs_tpl": "Para esta crítica, enfoca tu análisis usando estos conceptos: {items}.",
        "phrase_tpl": 'Puedes usar esta frase si encaja: "{phrase}"',
        "rubric": "RÚBRICA DE PUNTUACIÓN",
        "obra": "OBRA A CRITICAR",
        "titulo": "Título",
        "tipo": "Tipo",
        "generos": "Géneros",
        "sinopsis": "Sinopsis",
        "instrucciones": "INSTRUCCIONES",
        "type_movie": "película",
        "type_show": "serie",
        "write_tpl": "Escribe una crítica de máximo 150 palabras como {name} {emoji}.",
        "start": "Empieza con la puntuación que hayas decidido según la rúbrica: X/10",
        "base": "Basa tu análisis en los datos reales de la obra que te hemos dado arriba.",
        "no_invent": "No inventes tramas, personajes ni elementos que no aparezcan en la sinopsis.",
        "perspective": "Escribe desde tu perspectiva ideológica con tu tono auténtico.",
        "direct": "Sé directo y personal.",
    },
    "en": {
        "decide": "DECIDE THE RATING BEFORE WRITING — in this order:",
        "red_flag_tpl": "Does the work trigger any of these red_flags? {items} → rate 1-3",
        "hates_tpl": "Does the work embody something you hate? {items} → rate 1-4",
        "loves_tpl": "Does the work embody something you love? {items} → rate 7-10",
        "neutral": "Does none apply clearly? → explicitly justify why the rating is 5 or 6",
        "nunca_tpl": "NEVER: {items}.",
        "react_tpl": "If you detect any of these elements, react with intense negativity: {items}.",
        "motifs_tpl": "For this review, focus your analysis using these concepts: {items}.",
        "phrase_tpl": 'You may use this phrase if it fits: "{phrase}"',
        "rubric": "RATING RUBRIC",
        "obra": "WORK TO REVIEW",
        "titulo": "Title",
        "tipo": "Type",
        "generos": "Genres",
        "sinopsis": "Synopsis",
        "instrucciones": "INSTRUCTIONS",
        "type_movie": "film",
        "type_show": "series",
        "write_tpl": "Write a review of maximum 150 words as {name} {emoji}.",
        "start": "Start with the rating you decided per the rubric: X/10",
        "base": "Base your analysis on the actual data about the work provided above.",
        "no_invent": "Do not invent plots, characters, or elements not mentioned in the synopsis.",
        "perspective": "Write from your ideological perspective with your authentic voice.",
        "direct": "Be direct and personal.",
    },
}

# ── Helper ────────────────────────────────────────────────────────────────────


def _jdump(lst: list[str]) -> str:
    return json.dumps(lst, ensure_ascii=False)


# ── Character souls ───────────────────────────────────────────────────────────

CHARACTERS: dict[str, dict[str, dict]] = {
    "Adolf Histeric": {
        "es": {
            "name": "Adolf Histeric",
            "emoji": "🎩",
            "personality": "fanatico_ideologico",
            "description": (
                "Eres Adolf Histeric 🎩. Defensor exacerbado de la pureza cultural y cinematográfica. "
                "Ves conspiraciones ideológicas en cada película y expones sin filtros la agenda detrás de la obra. "
                "Tu crítica es furia ideológica pura."
            ),
            "loves": _jdump([
                "Épica histórica europea",
                "Cine bélico clásico",
                "Narrativas de destino y pueblo",
                "Cinematografía expresionista alemana",
            ]),
            "hates": _jdump([
                "Películas con temática social de izquierda",
                "Protagonistas de minorías",
                "Crítica al capitalismo",
                "Propaganda comunista disfrazada de arte",
            ]),
            "red_flags": _jdump([
                "lucha de clases",
                "diversidad racial forzada",
                "crítica al capitalismo",
                "agenda woke",
                "protagonista no europeo",
            ]),
            "avoid": _jdump([
                "Elogiar obras con mensajes progresistas",
                "Ignorar la agenda política detrás de la película",
            ]),
            "motifs": ["pureza cultural", "conspiración", "degeneración", "traición"],
            "catchphrases": [
                "¡Esto es una conspiración!",
                "¡Abajo con la degeneración cultural!",
                "¡El arte debe servir a la nación!",
            ],
        },
        "en": {
            "name": "Adolf Histeric",
            "emoji": "🎩",
            "personality": "fanatico_ideologico",
            "description": (
                "You are Adolf Histeric 🎩. An exacerbated defender of cultural and cinematic purity. "
                "You see ideological conspiracies in every film and expose the agenda behind each work without filter. "
                "Your review is pure ideological fury."
            ),
            "loves": _jdump([
                "European historical epics",
                "Classic war films",
                "Narratives of destiny and folk",
                "German expressionist cinema",
            ]),
            "hates": _jdump([
                "Left-wing social theme films",
                "Minority protagonists",
                "Capitalism critique",
                "Communist propaganda disguised as art",
            ]),
            "red_flags": _jdump([
                "class struggle",
                "forced racial diversity",
                "capitalism critique",
                "woke agenda",
                "non-European protagonist",
            ]),
            "avoid": _jdump([
                "Praising works with progressive messages",
                "Ignoring the political agenda behind the film",
            ]),
            "motifs": ["cultural purity", "conspiracy", "degeneration", "betrayal"],
            "catchphrases": [
                "This is a conspiracy!",
                "Down with cultural degeneration!",
                "Art must serve the nation!",
            ],
        },
    },
    "Rosario Costras": {
        "es": {
            "name": "Rosario Costras",
            "emoji": "✊",
            "personality": "woke",
            "description": (
                "Eres Rosario Costras ✊. Crítica feminista interseccional especializada en cine. "
                "Analizas cada obra desde el prisma de la representación, el patriarcado y la justicia social. "
                "Tu rating refleja el grado de emancipación y diversidad de la película."
            ),
            "loves": _jdump([
                "Protagonistas femeninas con agencia propia",
                "Diversidad racial auténtica",
                "Crítica al patriarcado y al capitalismo",
                "Directoras de cine",
                "Representación LGBTQ+",
            ]),
            "hates": _jdump([
                "Male gaze",
                "Blanqueamiento del reparto",
                "Glorificación de la violencia masculina",
                "Mujer como objeto decorativo",
                "Final conservador o sumiso",
            ]),
            "red_flags": _jdump([
                "director blanco masculino sin autocrítica",
                "male gaze explícito",
                "ausencia de diversidad racial",
                "violencia doméstica sin crítica narrativa",
            ]),
            "avoid": _jdump([
                "Ignorar la representación de minorías",
                "Elogiar la técnica sin considerar el mensaje social",
            ]),
            "motifs": ["representación", "patriarcado", "interseccionalidad", "emancipación"],
            "catchphrases": [
                "La representación importa",
                "¿Dónde están las mujeres de color?",
                "El male gaze sigue vivo",
            ],
        },
        "en": {
            "name": "Rosario Costras",
            "emoji": "✊",
            "personality": "woke",
            "description": (
                "You are Rosario Costras ✊. An intersectional feminist film critic. "
                "You analyze every work through the lens of representation, patriarchy, and social justice. "
                "Your rating reflects the degree of emancipation and diversity in the film."
            ),
            "loves": _jdump([
                "Female protagonists with agency",
                "Authentic racial diversity",
                "Critique of patriarchy and capitalism",
                "Female directors",
                "LGBTQ+ representation",
            ]),
            "hates": _jdump([
                "Male gaze",
                "Whitewashing of casts",
                "Glorification of male violence",
                "Woman as decorative object",
                "Conservative or submissive ending",
            ]),
            "red_flags": _jdump([
                "white male director without self-critique",
                "explicit male gaze",
                "absence of racial diversity",
                "uncritical domestic violence",
            ]),
            "avoid": _jdump([
                "Ignoring minority representation",
                "Praising technique without considering the social message",
            ]),
            "motifs": ["representation", "patriarchy", "intersectionality", "emancipation"],
            "catchphrases": [
                "Representation matters",
                "Where are the women of color?",
                "The male gaze is alive and well",
            ],
        },
    },
    "Mark Hamill": {
        "es": {
            "name": "Mark Hamill",
            "emoji": "🌟",
            "personality": "nostalgico",
            "description": (
                "Eres Mark Hamill 🌟. Actor icónico de Star Wars que vivió la edad de oro del cine artesanal. "
                "Defiendes los efectos prácticos, las actuaciones de corazón y la narrativa honesta. "
                "Las secuelas que traicionan el legado te parten el alma."
            ),
            "loves": _jdump([
                "Star Wars original (IV, V, VI)",
                "Efectos prácticos y maquillaje artesanal",
                "Actuaciones auténticas de corazón",
                "Ciencia ficción clásica con alma",
                "Películas que respetan el legado",
            ]),
            "hates": _jdump([
                "Secuelas que traicionan el canon",
                "CGI que reemplaza la artesanía",
                "Personajes clásicos degradados o ridiculizados",
                "Películas de comité sin visión",
                "Wokismo forzado en sagas queridas",
            ]),
            "red_flags": _jdump([
                "Luke Skywalker degradado o traicionado",
                "personajes clásicos destruidos para el nuevo arco",
                "agenda política en Star Wars",
                "secuela de Disney que destruye el legado",
            ]),
            "avoid": _jdump([
                "Elogiar secuelas o remakes de sagas clásicas",
                "Ignorar el trato dado a los personajes originales",
            ]),
            "motifs": ["legado", "traición", "artesanía", "alma", "autenticidad"],
            "catchphrases": [
                "El cine que recuerdo no era así",
                "Los efectos prácticos son el alma del cine",
                "¡Han disparó primero!",
            ],
        },
        "en": {
            "name": "Mark Hamill",
            "emoji": "🌟",
            "personality": "nostalgico",
            "description": (
                "You are Mark Hamill 🌟. An iconic Star Wars actor who lived through the golden age of handcrafted cinema. "
                "You champion practical effects, heartfelt performances, and honest storytelling. "
                "Sequels that betray the legacy break your soul."
            ),
            "loves": _jdump([
                "Original Star Wars (IV, V, VI)",
                "Practical effects and handcrafted makeup",
                "Heartfelt authentic performances",
                "Classic sci-fi with soul",
                "Films that honor the legacy",
            ]),
            "hates": _jdump([
                "Sequels that betray the canon",
                "CGI replacing craftsmanship",
                "Classic characters degraded or ridiculed",
                "Committee-made films without vision",
                "Forced wokism in beloved sagas",
            ]),
            "red_flags": _jdump([
                "Luke Skywalker degraded or betrayed",
                "classic characters destroyed for new arcs",
                "political agenda in Star Wars",
                "Disney sequel destroying the legacy",
            ]),
            "avoid": _jdump([
                "Praising sequels or remakes of classic sagas",
                "Ignoring the treatment of original characters",
            ]),
            "motifs": ["legacy", "betrayal", "craftsmanship", "soul", "authenticity"],
            "catchphrases": [
                "The cinema I remember wasn't like this",
                "Practical effects are the soul of cinema",
                "Han shot first!",
            ],
        },
    },
}

# ── Test movies ───────────────────────────────────────────────────────────────

MOVIES: list[dict] = [
    {
        "tmdb_id": 181808,
        "title": "Star Wars: Los últimos Jedi",
        "year": 2017,
        "type": "movie",
        "genres": "Acción, Aventura, Ciencia ficción",
        "synopsis": (
            "La Resistencia lucha por sobrevivir contra la Primera Orden. Rey busca a Luke Skywalker "
            "para aprender los poderes de la Fuerza, mientras Kylo Ren duda entre la luz y la oscuridad. "
            "El tagline 'Deja morir el pasado' define la película: el legado debe ser destruido para que nazca algo nuevo. "
            "Director: Rian Johnson. Protagonistas: Daisy Ridley (Rey), Mark Hamill (Luke), John Boyega (Finn)."
        ),
    },
    {
        "tmdb_id": 496243,
        "title": "Parásitos",
        "year": 2019,
        "type": "movie",
        "genres": "Drama, Thriller, Comedia negra",
        "synopsis": (
            "La familia Kim, trabajadores sin empleo, se va infiltrando en la vida de los adinerados Park "
            "suplantando identidades. Lo que empieza como una oportunidad se convierte en un violento conflicto "
            "de clases. Bong Joon-ho (director coreano) explora la desigualdad social con un giro explosivo. "
            "Ganadora del Oscar a Mejor Película."
        ),
    },
    {
        "tmdb_id": 694,
        "title": "El resplandor",
        "year": 1980,
        "type": "movie",
        "genres": "Terror, Drama",
        "synopsis": (
            "Jack Torrance acepta cuidar el hotel Overlook en invierno junto a su esposa Wendy y su hijo Danny. "
            "Aislados por la nieve, Jack cae en la locura bajo influencias sobrenaturales y comienza a perseguir "
            "a su familia. Director: Stanley Kubrick. Protagonistas: Jack Nicholson, Shelley Duvall. "
            "Adaptación del libro de Stephen King, célebre por sus efectos prácticos y su atmósfera opresiva."
        ),
    },
    {
        "tmdb_id": 508442,
        "title": "Soul",
        "year": 2020,
        "type": "movie",
        "genres": "Animación, Aventura, Comedia",
        "synopsis": (
            "Joe Gardner, profesor de música afroamericano con sueños de ser jazzista, tiene un accidente "
            "justo cuando logra su gran oportunidad. Su alma viaja a los reinos cósmicos donde se descubren "
            "los propósitos de vida antes de nacer. Película Pixar con protagonista negro, sin romance como eje, "
            "centrada en la pasión por el arte y el sentido de la existencia."
        ),
    },
]

# ── Expected ideological rating ranges ───────────────────────────────────────
# Based on established benchmark data (docs/benchmark-comparison.md).
# Format: {tmdb_id: (min_acceptable, max_acceptable)}

EXPECTED_RATINGS: dict[str, dict[int, tuple[int, int]]] = {
    "Adolf Histeric": {
        181808: (1, 4),   # TLJ: agenda woke, protagonista no europeo → muy bajo
        496243: (1, 3),   # Parásitos: lucha de clases, director coreano → muy bajo
        694:    (1, 5),   # Resplandor: posible crítica velada, Kubrick cuestionable → bajo/medio
        508442: (1, 3),   # Soul: protagonista negro, colectivismo → muy bajo
    },
    "Rosario Costras": {
        181808: (6, 9),   # TLJ: protagonista femenina Rey, diversidad racial → positivo
        496243: (7, 10),  # Parásitos: crítica desigualdad social → muy positivo
        694:    (2, 5),   # Resplandor: male gaze, director blanco, Wendy víctima → negativo
        508442: (7, 10),  # Soul: protagonista negro, sin male gaze, sin romance forzado → positivo
    },
    "Mark Hamill": {
        181808: (1, 3),   # TLJ: Luke degradado, secuela Disney → muy negativo
        496243: (7, 10),  # Parásitos: actuaciones auténticas, alma → positivo
        694:    (7, 10),  # Resplandor: efectos prácticos, clásico artesanal → positivo
        508442: (6, 9),   # Soul: película con alma, Pixar → medio-positivo
    },
}

# ── Prompt construction (replicates prompt_builder._render_user_block) ────────


def build_user_block(character_data: dict, movie: dict, variation: dict, lang: str = "es") -> str:
    """
    Replicate the prompt_builder user block in ES or EN.
    Handles structural labels, rubric, NUNCA block, and movie data block.
    """
    t = _LABELS[lang]

    name = character_data["name"]
    emoji = character_data.get("emoji", "🎭")
    description = character_data.get("description", "")
    personality = character_data.get("personality", "")

    # Identity block
    if description:
        identity = description
    else:
        pfx = "Eres" if lang == "es" else "You are"
        arc_label = "Arquetipo" if lang == "es" else "Archetype"
        identity = f"{pfx} {name} {emoji}. {arc_label}: {personality}."

    # Variation pack
    variation_lines = []
    if variation.get("motifs"):
        variation_lines.append(t["motifs_tpl"].format(items=", ".join(variation["motifs"])))
    if variation.get("catchphrase"):
        variation_lines.append(t["phrase_tpl"].format(phrase=variation["catchphrase"]))
    variation_block = "\n".join(variation_lines)

    # Parse soul arrays
    avoid = json.loads(character_data.get("avoid") or "[]")
    red_flags = json.loads(character_data.get("red_flags") or "[]")
    loves = json.loads(character_data.get("loves") or "[]")
    hates = json.loads(character_data.get("hates") or "[]")

    # NUNCA / NEVER block
    nunca_lines = []
    if avoid:
        nunca_lines.append(t["nunca_tpl"].format(items="; ".join(avoid)))
    if red_flags:
        nunca_lines.append(t["react_tpl"].format(items="; ".join(red_flags)))
    nunca_block = "\n".join(nunca_lines)

    # Rating rubric — explicit decision tree derived from soul
    rubric_lines = [t["decide"]]
    if red_flags:
        rubric_lines.append("→ " + t["red_flag_tpl"].format(items=", ".join(red_flags[:4])))
    if hates:
        rubric_lines.append("→ " + t["hates_tpl"].format(items=", ".join(hates[:6])))
    if loves:
        rubric_lines.append("→ " + t["loves_tpl"].format(items=", ".join(loves[:6])))
    rubric_lines.append("→ " + t["neutral"])
    rubric_block = "\n".join(rubric_lines)

    # Movie data block
    type_label = t["type_movie"] if movie.get("type", "movie") == "movie" else t["type_show"]
    movie_block = (
        f"{t['obra']}:\n"
        f"{t['titulo']}: \"{movie['title']}\" ({movie.get('year', '?')})\n"
        f"{t['tipo']}: {type_label.capitalize()}\n"
        f"{t['generos']}: {movie.get('genres', '?')}\n"
        f"{t['sinopsis']}: {movie.get('synopsis', '?')}"
    )

    # Instruction block
    instr_block = (
        f"{t['instrucciones']}:\n"
        f"{t['write_tpl'].format(name=name, emoji=emoji)}\n"
        f"{t['start']}\n"
        f"{t['base']}\n"
        f"{t['no_invent']}\n"
        f"{t['perspective']}\n"
        f"{t['direct']}"
    )

    parts = [identity]
    if variation_block:
        parts.append(variation_block)
    if nunca_block:
        parts.append(nunca_block)
    parts.append(f"\n{t['rubric']}:\n{rubric_block}")
    parts.append(f"\n{movie_block}\n\n{instr_block}")

    return "\n\n".join(parts)


def build_messages(variant: dict, character_data: dict, movie: dict, variation: dict) -> list[dict]:
    """Build the messages list for Ollama /api/chat for a given variant."""
    user_block = build_user_block(
        character_data=character_data,
        movie=movie,
        variation=variation,
        lang=variant["block_lang"],
    )
    return [
        {"role": "system", "content": variant["system"]},
        {"role": "user", "content": user_block},
    ]


# ── LLM call ──────────────────────────────────────────────────────────────────


async def call_ollama(
    ollama_url: str,
    model: str,
    messages: list[dict],
    timeout: float = 120.0,
) -> tuple[str, float]:
    """Call Ollama /api/chat. Returns (content, elapsed_seconds)."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,  # disable thinking to match production critic generation
        "options": {
            "temperature": 0.75,
            "num_predict": 600,
            "top_p": 0.95,
            "top_k": 20,
        },
    }
    start = time.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
    elapsed = time.time() - start
    content = resp.json().get("message", {}).get("content", "")
    # Strip think blocks (qwen3, deepseek)
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content, elapsed


# ── Scoring ───────────────────────────────────────────────────────────────────

_ES_MARKERS = frozenset(
    ["de", "la", "el", "en", "que", "un", "una", "por", "con", "los", "las", "del", "al", "es", "se", "no", "su"]
)
_EN_MARKERS = frozenset(
    ["the", "of", "and", "to", "in", "is", "it", "that", "for", "this", "was", "are", "not", "but", "with", "its"]
)


def extract_rating(text: str) -> int | None:
    """Extract the first X/10 rating from the first 80 characters."""
    m = re.search(r"(\d{1,2})\s*/\s*10", text[:80])
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 10 else None
    return None


def detect_language(text: str) -> str:
    """Heuristic language detection. Returns 'es', 'en', or 'unknown'."""
    words = {w.lower().strip(".,;:!?\"'()[]{}") for w in text.split()}
    es_hits = len(words & _ES_MARKERS)
    en_hits = len(words & _EN_MARKERS)
    if es_hits == 0 and en_hits == 0:
        return "unknown"
    if es_hits > en_hits * 1.5:
        return "es"
    if en_hits > es_hits * 1.5:
        return "en"
    return "unknown"


def score_result(
    text: str,
    char_name: str,
    tmdb_id: int,
    expected_output_lang: str,
) -> dict:
    """Compute all quality metrics for a single critic."""
    rating = extract_rating(text)
    word_count = len(text.split())
    detected_lang = detect_language(text)
    expected_range = EXPECTED_RATINGS.get(char_name, {}).get(tmdb_id)

    calibration_ok: bool | None = None
    if rating is not None and expected_range is not None:
        lo, hi = expected_range
        calibration_ok = lo <= rating <= hi

    return {
        "format_ok": rating is not None,
        "rating": rating,
        "expected_range": list(expected_range) if expected_range else None,
        "calibration_ok": calibration_ok,
        "word_count": word_count,
        "word_count_ok": 80 <= word_count <= 220,
        "lang_detected": detected_lang,
        "lang_correct": detected_lang == expected_output_lang,
    }


# ── Single run ────────────────────────────────────────────────────────────────


async def run_one(
    variant: dict,
    char_name: str,
    char_souls: dict,
    movie: dict,
    run_idx: int,
    ollama_url: str,
    model: str,
) -> dict:
    """Execute a single variant × character × movie combination."""
    soul_lang = variant["soul_lang"]
    output_lang = variant["output_lang"]
    soul = char_souls[soul_lang]

    # Variation: first 3 motifs + first catchphrase for realism
    motifs = soul.get("motifs", [])[:3]
    catchphrases = soul.get("catchphrases", [])
    variation = {
        "motifs": motifs,
        "catchphrase": catchphrases[0] if catchphrases else None,
    }

    messages = build_messages(variant, soul, movie, variation)

    base = {
        "variant": variant["id"],
        "character": char_name,
        "tmdb_id": movie["tmdb_id"],
        "title": movie["title"],
        "run": run_idx + 1,
    }

    try:
        text, elapsed = await call_ollama(ollama_url, model, messages)
        scores = score_result(text, char_name, movie["tmdb_id"], output_lang)
        return {
            **base,
            "elapsed": round(elapsed, 1),
            "text": text,
            **scores,
            "ok": scores["format_ok"],
            "error": None,
        }
    except Exception as exc:
        return {
            **base,
            "elapsed": None,
            "text": None,
            "format_ok": False,
            "rating": None,
            "expected_range": None,
            "calibration_ok": None,
            "word_count": 0,
            "word_count_ok": False,
            "lang_detected": None,
            "lang_correct": False,
            "ok": False,
            "error": str(exc),
        }


# ── Benchmark orchestrator ────────────────────────────────────────────────────


async def run_benchmark(args: argparse.Namespace) -> dict:
    variants_to_run = [v for v in VARIANTS if v["id"] in args.variants]
    chars_to_run = {k: v for k, v in CHARACTERS.items() if k in args.characters}
    total = len(variants_to_run) * len(chars_to_run) * len(MOVIES) * args.runs

    print("\n🔬 Parody Critics — i18n Prompt Language Benchmark")
    print(f"   Modelo   : {args.model}")
    print(f"   Servidor : {args.ollama_url}")
    print(f"   Variantes: {', '.join(v['label'] for v in variants_to_run)}")
    print(f"   Personajes: {', '.join(chars_to_run.keys())}")
    print(f"   Películas : {len(MOVIES)}")
    print(f"   Runs/combo: {args.runs}")
    print(f"   Total     : {total} críticas")
    print()

    all_results: list[dict] = []
    done = 0

    for variant in variants_to_run:
        print(f"{'─' * 60}")
        print(f"▶ Variante {variant['label']}")
        print(f"  {variant['desc']}")
        print()

        for char_name, char_souls in chars_to_run.items():
            for movie in MOVIES:
                for run_idx in range(args.runs):
                    done += 1
                    tag = f"[{done:02d}/{total:02d}]"
                    run_sfx = f" run {run_idx + 1}/{args.runs}" if args.runs > 1 else ""
                    print(f"  {tag} {char_name} × {movie['title']}{run_sfx}...", end=" ", flush=True)

                    result = await run_one(
                        variant=variant,
                        char_name=char_name,
                        char_souls=char_souls,
                        movie=movie,
                        run_idx=run_idx,
                        ollama_url=args.ollama_url,
                        model=args.model,
                    )
                    all_results.append(result)

                    if result["error"]:
                        print(f"❌ ERROR: {result['error']}")
                    else:
                        cal_icon = "✅" if result["calibration_ok"] else ("❌" if result["calibration_ok"] is False else "⚠️")
                        lang_icon = "🌍" if result["lang_correct"] else "⚠️"
                        rating_str = f"{result['rating']}/10" if result["rating"] is not None else "N/A"
                        exp = result.get("expected_range")
                        exp_str = f"[{exp[0]}-{exp[1]}]" if exp else ""
                        print(
                            f"{rating_str}{exp_str} {cal_icon}  "
                            f"{result['word_count']}w  {lang_icon}  {result['elapsed']}s"
                        )

        print()

    print(f"✅ Benchmark completado — {total} críticas generadas")

    return {
        "results": all_results,
        "meta": {
            "model": args.model,
            "ollama_url": args.ollama_url,
            "variants": [v["id"] for v in variants_to_run],
            "characters": list(chars_to_run.keys()),
            "movies": [m["title"] for m in MOVIES],
            "runs": args.runs,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_calls": total,
        },
    }


# ── Markdown report ───────────────────────────────────────────────────────────


def _pct(num: int, den: int) -> str:
    if den == 0:
        return "—"
    return f"{num}/{den} ({100 * num // den}%)"


def generate_markdown_report(data: dict) -> str:
    results: list[dict] = data["results"]
    meta: dict = data["meta"]
    variants_run: list[str] = meta["variants"]
    chars_run: list[str] = meta["characters"]

    # ── Aggregate stats per variant ──────────────────────────────────────────
    stats: dict[str, dict] = {vid: {
        "total": 0, "format_ok": 0,
        "cal_ok": 0, "cal_total": 0,
        "lang_ok": 0, "word_ok": 0,
        "times": [],
    } for vid in variants_run}

    for r in results:
        vid = r["variant"]
        if vid not in stats:
            continue
        s = stats[vid]
        s["total"] += 1
        if r.get("format_ok"):
            s["format_ok"] += 1
        if r.get("calibration_ok") is True:
            s["cal_ok"] += 1
        if r.get("calibration_ok") is not None:
            s["cal_total"] += 1
        if r.get("lang_correct"):
            s["lang_ok"] += 1
        if r.get("word_count_ok"):
            s["word_ok"] += 1
        if r.get("elapsed") is not None:
            s["times"].append(r["elapsed"])

    # ── Per-character calibration grid ────────────────────────────────────────
    # grid[char][title][variant_id] → {ratings: [...], ok: [...]}
    grid: dict[str, dict[str, dict[str, dict]]] = {}
    for r in results:
        c, t, v = r["character"], r["title"], r["variant"]
        grid.setdefault(c, {}).setdefault(t, {}).setdefault(v, {"ratings": [], "ok": []})
        if r.get("rating") is not None:
            grid[c][t][v]["ratings"].append(r["rating"])
        if r.get("calibration_ok") is not None:
            grid[c][t][v]["ok"].append(r["calibration_ok"])

    # ── Build report ──────────────────────────────────────────────────────────
    lines: list[str] = []

    lines += [
        "# Benchmark: i18n Prompt Language Variants",
        "",
        f"**Fecha**: {meta['date']}  ",
        f"**Modelo**: `{meta['model']}`  ",
        f"**Runs por combinación**: {meta['runs']}  ",
        f"**Total críticas**: {meta['total_calls']}  ",
        "",
        "## Variantes",
        "",
    ]
    for v in VARIANTS:
        if v["id"] in variants_run:
            lines.append(f"- **{v['label']}**: {v['desc']}")
    lines += ["", "---", "", "## Resumen ejecutivo", ""]

    # Summary table
    col_headers = " | ".join(f"V-{v}" for v in variants_run)
    lines.append(f"| Métrica | {col_headers} |")
    lines.append("|" + "---|" * (len(variants_run) + 1))

    metrics = [
        ("Formato OK (X/10)", lambda s: _pct(s["format_ok"], s["total"])),
        ("Calibración ideológica", lambda s: _pct(s["cal_ok"], s["cal_total"])),
        ("Idioma correcto", lambda s: _pct(s["lang_ok"], s["total"])),
        ("Word count OK (80-220w)", lambda s: _pct(s["word_ok"], s["total"])),
        ("Tiempo medio (s)", lambda s: (
            f"{sum(s['times'])/len(s['times']):.1f}s" if s["times"] else "—"
        )),
    ]
    for label, fn in metrics:
        row = " | ".join(fn(stats[v]) for v in variants_run)
        lines.append(f"| {label} | {row} |")

    lines += ["", "---", "", "## Calibración ideológica por personaje", ""]
    lines.append("> ✅ = dentro del rango esperado | ❌ = fuera de rango | — = no capturado")
    lines.append("")

    for char_name in chars_run:
        if char_name not in CHARACTERS:
            continue
        emoji = CHARACTERS[char_name]["es"]["emoji"]
        personality = CHARACTERS[char_name]["es"]["personality"]
        expected = EXPECTED_RATINGS.get(char_name, {})

        lines.append(f"### {emoji} {char_name}  *({personality})*")
        lines.append("")

        v_cols = " | ".join(f"V-{v}" for v in variants_run)
        lines.append(f"| Película | Esperado | {v_cols} |")
        lines.append("|" + "---------|" * (len(variants_run) + 2))

        for movie in MOVIES:
            tmdb_id = movie["tmdb_id"]
            title = movie["title"]
            exp = expected.get(tmdb_id)
            exp_str = f"{exp[0]}-{exp[1]}" if exp else "?"

            cells = [title, exp_str]
            for vid in variants_run:
                cell = grid.get(char_name, {}).get(title, {}).get(vid)
                if not cell or not cell["ratings"]:
                    cells.append("—")
                    continue
                avg = sum(cell["ratings"]) / len(cell["ratings"])
                rating_str = str(int(round(avg))) if len(cell["ratings"]) == 1 else f"{avg:.1f}"
                ok_vals = cell["ok"]
                if ok_vals:
                    icon = "✅" if sum(ok_vals) / len(ok_vals) >= 0.5 else "❌"
                else:
                    icon = "⚠️"
                cells.append(f"**{rating_str}** {icon}")
            lines.append(f"| {' | '.join(cells)} |")

        lines.append("")

    # Sample critics (collapsible)
    lines += ["---", "", "## Críticas generadas"]
    lines.append("")

    for vid in variants_run:
        v_meta = next(v for v in VARIANTS if v["id"] == vid)
        lines.append(f"### Variante {v_meta['label']}")
        lines.append("")
        variant_results = [r for r in results if r["variant"] == vid and not r.get("error") and r.get("run", 1) == 1]
        for r in variant_results:
            rating_str = f"{r['rating']}/10" if r.get("rating") is not None else "N/A"
            cal_icon = "✅" if r.get("calibration_ok") else ("❌" if r.get("calibration_ok") is False else "⚠️")
            lang_str = r.get("lang_detected", "?")
            lines += [
                f"#### {r['character']} × {r['title']}",
                f"Rating: **{rating_str}** {cal_icon} &nbsp;|&nbsp; "
                f"Words: {r.get('word_count', 0)} &nbsp;|&nbsp; "
                f"Time: {r.get('elapsed', '?')}s &nbsp;|&nbsp; "
                f"Lang: `{lang_str}`",
                "",
                "```",
                r.get("text") or "(error)",
                "```",
                "",
            ]

    # Verdict template
    lines += [
        "---",
        "",
        "## Veredicto",
        "",
        "| Pregunta | Respuesta |",
        "|----------|-----------|",
        "| ¿El prompt EN (V-B) mejora la calibración respecto al ES (V-A)? | — |",
        "| ¿El soul EN (V-C) mejora la coherencia del personaje? | — |",
        "| ¿El idioma de salida detectado coincide con el esperado? | — |",
        "| Variante recomendada para producción | — |",
        "| ¿Vale la pena el pipeline de traducción (C→traducir)? | — |",
        "",
        "---",
        "",
        "*Generado automáticamente por `testing/benchmark_i18n_prompts.py`*",
    ]

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="i18n Prompt Language Benchmark — ES vs EN system prompt quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--ollama-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama server URL (default: {DEFAULT_OLLAMA_URL})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to benchmark (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=DEFAULT_RUNS,
        help=f"Runs per combination for reliability (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=["A", "B", "C"],
        default=["A", "B", "C"],
        help="Variants to test (default: all three)",
    )
    parser.add_argument(
        "--characters",
        nargs="+",
        default=list(CHARACTERS.keys()),
        choices=list(CHARACTERS.keys()),
        help="Characters to include (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help=f"Output directory for results (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print quick summary only, don't save files",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    args.output_dir = Path(args.output_dir)

    # ── Connection check ──────────────────────────────────────────────────────
    print(f"🔌 Verificando conexión con Ollama en {args.ollama_url}...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{args.ollama_url}/api/tags")
            resp.raise_for_status()
            loaded_models = [m["name"] for m in resp.json().get("models", [])]
        if args.model in loaded_models:
            print(f"✅ Conectado. Modelo '{args.model}' disponible.")
        else:
            print(f"⚠️  Modelo '{args.model}' no encontrado. Disponibles: {', '.join(loaded_models[:6])}")
            print("   Continuando de todas formas (puede cargarse bajo demanda).")
    except Exception as exc:
        print(f"❌ No se puede conectar a Ollama en {args.ollama_url}: {exc}")
        sys.exit(1)

    # ── Run ───────────────────────────────────────────────────────────────────
    data = await run_benchmark(args)

    if args.no_save:
        print("\n📊 Meta:")
        print(json.dumps(data["meta"], indent=2))
        return

    # ── Save results ──────────────────────────────────────────────────────────
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.output_dir / f"i18n-benchmark-{date_str}.json"
    md_path = args.output_dir / f"i18n-benchmark-{date_str}.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 JSON guardado: {json_path}")

    report = generate_markdown_report(data)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"📄 Informe guardado: {md_path}")

    # ── Quick summary table ───────────────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"{'📊 RESUMEN RÁPIDO':^60}")
    print(f"{'─' * 60}")
    variants_run = data["meta"]["variants"]

    # Recompute stats for summary
    summary: dict[str, dict] = {vid: {
        "total": 0, "cal_ok": 0, "cal_total": 0, "format_ok": 0, "times": []
    } for vid in variants_run}
    for r in data["results"]:
        vid = r["variant"]
        if vid not in summary:
            continue
        s = summary[vid]
        s["total"] += 1
        if r.get("format_ok"):
            s["format_ok"] += 1
        if r.get("calibration_ok") is True:
            s["cal_ok"] += 1
        if r.get("calibration_ok") is not None:
            s["cal_total"] += 1
        if r.get("elapsed") is not None:
            s["times"].append(r["elapsed"])

    print(f"  {'Variante':<30} {'Formato':>9} {'Calibración':>13} {'T.medio':>9}")
    print(f"  {'─' * 30} {'─' * 9} {'─' * 13} {'─' * 9}")
    for vid in variants_run:
        s = summary[vid]
        v_label = next(v["label"] for v in VARIANTS if v["id"] == vid)
        avg_t = f"{sum(s['times'])/len(s['times']):.1f}s" if s["times"] else "—"
        print(
            f"  {v_label:<30} "
            f"{_pct(s['format_ok'], s['total']):>9} "
            f"{_pct(s['cal_ok'], s['cal_total']):>13} "
            f"{avg_t:>9}"
        )
    print(f"{'─' * 60}")
    print(f"\n🔍 Ver informe completo: {md_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
