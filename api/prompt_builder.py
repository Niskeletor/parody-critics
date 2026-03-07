"""
📝 Prompt Builder — model-aware message construction for critic generation
Knows WHAT to say (content); ModelProfile knows HOW to call the model.
"""
import json
from typing import Any

try:
    from model_profiles import ModelProfile  # noqa: E402
except ImportError:
    from api.model_profiles import ModelProfile  # noqa: E402
from utils.logger import get_logger

logger = get_logger("prompt_builder")

SYSTEM_BLOCK = """You are a parody film criticism system.
Your rating ALWAYS reflects the character's ideological perspective, NEVER technical quality.
BEFORE writing a single word: evaluate the work against the character's loves, hates and red_flags.
That analysis determines the number. The number is not an opinion about quality — it is an ideological judgment.
A 5 or 6 is only valid if no love, hate or red_flag applies AND you have explicit reason for it.
You are never neutral by default. Respond ONLY with the critic. Respond in {output_language}."""

_LANGUAGE_NAMES = {
    "es": "Spanish",
    "en": "English",
}


def build_messages(
    character_data: dict,
    media_info: dict[str, Any],
    profile: ModelProfile,
    variation: dict,
    language: str = "es",
) -> list[dict]:
    """
    Build the messages list for /api/chat.
    Handles system-prompt placement based on model profile.
    language: output language code ('es' | 'en')
    """
    output_language = _LANGUAGE_NAMES.get(language, "Spanish")
    system = SYSTEM_BLOCK.format(output_language=output_language)
    user_block = _render_user_block(character_data, media_info, variation)

    if profile.system_in_user:
        # deepseek-r1 and similar: system role is forbidden — merge into user
        return [{"role": "user", "content": system + "\n\n" + user_block}]

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_block},
    ]


def _render_user_block(
    character_data: dict,
    media_info: dict[str, Any],
    variation: dict,
) -> str:
    """Build the user message block — same content for all models."""

    title = media_info.get("title", "Obra sin título")
    year = media_info.get("year", "Año desconocido")
    media_type = media_info.get("type", "movie")
    genres = media_info.get("genres", "Géneros desconocidos")
    synopsis = media_info.get("synopsis", "Sin sinopsis disponible")
    type_label = "película" if media_type == "movie" else "serie"

    emoji = character_data.get("emoji", "🎭")
    character_name = character_data.get("name", "Crítico")
    description = character_data.get("description", "")
    personality = character_data.get("personality", "")

    # Identity block
    if description:
        identity = description
    else:
        identity = f"Eres {character_name} {emoji}. Arquetipo: {personality}."

    # Variation pack
    variation_lines = []
    if variation.get("motifs"):
        variation_lines.append(
            f"Para esta crítica, enfoca tu análisis usando estos conceptos: {', '.join(variation['motifs'])}."
        )
    if variation.get("catchphrase"):
        variation_lines.append(
            f"Puedes usar esta frase si encaja: \"{variation['catchphrase']}\""
        )
    variation_block = "\n".join(variation_lines)

    # Parsed arrays from character data
    avoid = json.loads(character_data.get("avoid") or "[]")
    red_flags = json.loads(character_data.get("red_flags") or "[]")
    loves = json.loads(character_data.get("loves") or "[]")
    hates = json.loads(character_data.get("hates") or "[]")

    # NUNCA block — prohibitions that reinforce the character boundary
    nunca_lines = []
    if avoid:
        nunca_lines.append(f"NUNCA: {'; '.join(avoid)}.")
    if red_flags:
        nunca_lines.append(
            f"Si detectas alguno de estos elementos reacciona con intensidad negativa: {'; '.join(red_flags)}."
        )
    nunca_block = "\n".join(nunca_lines)

    # Rating rubric — explicit decision tree derived from soul
    rubric_lines = ["DECIDE EL RATING ANTES DE ESCRIBIR — en este orden:"]
    if red_flags:
        rubric_lines.append(f"→ ¿La obra activa alguno de estos red_flags? {', '.join(red_flags[:4])} → pon 1-3")
    if hates:
        rubric_lines.append(f"→ ¿La obra encarna algo que odias? {', '.join(hates[:6])} → pon 1-4")
    if loves:
        rubric_lines.append(f"→ ¿La obra encarna algo que amas? {', '.join(loves[:6])} → pon 7-10")
    rubric_lines.append("→ ¿Ninguna aplica con claridad? → justifica explícitamente por qué el número es 5 o 6")
    rubric_block = "\n".join(rubric_lines)

    # Enriched context (TMDB + Brave snippets, cached in DB)
    enriched_block = ""
    raw_enriched = media_info.get("enriched_context")
    if raw_enriched:
        try:
            ec = json.loads(raw_enriched) if isinstance(raw_enriched, str) else raw_enriched
            parts = []
            if ec.get("director"):
                parts.append(f"Director: {ec['director']}")
            if ec.get("cast"):
                parts.append(f"Reparto: {', '.join(ec['cast'])}")
            if ec.get("tagline"):
                parts.append(f"Tagline: \"{ec['tagline']}\"")
            if ec.get("overview_full") and len(ec["overview_full"]) > len(synopsis):
                parts.append(f"Sinopsis completa: {ec['overview_full'][:500]}")
            if ec.get("keywords"):
                parts.append(f"Keywords temáticas: {', '.join(ec['keywords'][:12])}")
            if ec.get("social_snippets"):
                snips = "\n".join(f"- {s}" for s in ec["social_snippets"][:4])
                parts.append(f"Contexto crítico y social:\n{snips}")
            if parts:
                enriched_block = "\n\nCONTEXTO ENRIQUECIDO:\n" + "\n".join(parts)
        except Exception as e:
            logger.warning(f"Could not parse enriched_context: {e}")

    parts = [identity]
    if variation_block:
        parts.append(variation_block)
    if nunca_block:
        parts.append(nunca_block)
    if rubric_block:
        parts.append(f"\nRÚBRICA DE PUNTUACIÓN:\n{rubric_block}")

    parts.append(f"""
OBRA A CRITICAR:
Título: "{title}" ({year})
Tipo: {type_label.capitalize()}
Géneros: {genres}
Sinopsis: {synopsis}{enriched_block}

INSTRUCCIONES:
Escribe una crítica de máximo 150 palabras como {character_name} {emoji}.
TU PRIMERA PALABRA debe ser el número: "X/10 — " seguido de tu primera frase.
Basa tu análisis en los datos reales de la obra que te hemos dado arriba.
No inventes tramas, personajes ni elementos que no aparezcan en la sinopsis.
Escribe desde tu perspectiva ideológica con tu tono auténtico.
Sé directo y personal.""")

    return "\n\n".join(parts)
