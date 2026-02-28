"""
🔮 Soul Generator — DDG + LLM pipeline for character creation
"""

import asyncio
import json
import re
from typing import Any

import httpx

from utils.logger import get_logger
from config import Config

logger = get_logger("soul_generator")

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

_FIELD_HINTS = {
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


class SoulGenerator:
    """Generates character soul fields via DDG search + local LLM."""

    def __init__(self):
        config = Config()
        self.endpoints = [
            {
                "url": "http://192.168.2.69:11434",
                "model": "phi4:latest",
                "label": "secondary/phi4",
            },
            {
                "url": config.LLM_OLLAMA_URL,
                "model": config.LLM_PRIMARY_MODEL,
                "label": f"primary/{config.LLM_PRIMARY_MODEL}",
            },
        ]
        self._endpoint_cache: dict | None = None

    # ── Endpoint discovery ────────────────────────────────────────────────────

    async def _find_endpoint(self) -> dict | None:
        """Return first reachable endpoint with its model loaded."""
        if self._endpoint_cache:
            return self._endpoint_cache

        for ep in self.endpoints:
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    r = await client.get(f"{ep['url']}/api/tags")
                    r.raise_for_status()
                    models = [m["name"] for m in r.json().get("models", [])]
                    if ep["model"] in models:
                        logger.info(f"Soul generator using {ep['label']}")
                        self._endpoint_cache = ep
                        return ep
                    logger.debug(f"{ep['label']}: model not loaded (available: {models})")
            except Exception as e:
                logger.debug(f"{ep['label']} unreachable: {e}")

        logger.error("No LLM endpoint available for soul generation")
        return None

    # ── DDG context fetch ─────────────────────────────────────────────────────

    async def fetch_context(self, real_name: str) -> list[str]:
        """Run two DDG queries for the person and return deduplicated snippets."""
        logger.info(f"DDG search for: {real_name!r}")
        queries = [
            f"{real_name} wikipedia personalidad características",
            f"{real_name} controversias frases opiniones polémicas",
        ]

        all_snippets: list[str] = []
        for q in queries:
            try:
                results = await asyncio.to_thread(self._ddg_search, q, 4)
                for r in results:
                    body = r.get("body", "").strip()
                    if body and len(body) > 40:
                        all_snippets.append(body[:300])
            except Exception as e:
                logger.warning(f"DDG query failed ({q!r}): {e}")

        # Deduplicate preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for s in all_snippets:
            key = s[:80]
            if key not in seen:
                seen.add(key)
                unique.append(s)

        logger.info(f"DDG: {len(unique)} snippets for {real_name!r}")
        return unique[:8]

    @staticmethod
    def _ddg_search(query: str, max_results: int) -> list[dict]:
        from ddgs import DDGS

        with DDGS() as d:
            return list(d.text(query, max_results=max_results)) or []

    # ── LLM calls ─────────────────────────────────────────────────────────────

    async def _call_llm(self, prompt: str) -> str:
        ep = await self._find_endpoint()
        if not ep:
            raise RuntimeError("No LLM endpoint available")

        payload = {
            "model": ep["model"],
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.85, "top_p": 0.9},
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{ep['url']}/api/generate", json=payload)
            resp.raise_for_status()
        return resp.json().get("response", "")

    # ── JSON parsing ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_json(raw: str) -> dict | None:
        # Strip think-blocks (qwen3, deepseek)
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None

    # ── Prompt builders ───────────────────────────────────────────────────────

    def _soul_prompt(self, real_name: str, snippets: list[str], archetype: str | None) -> str:
        snippets_block = "\n".join(f"- {s}" for s in snippets) if snippets else "(sin contexto externo)"
        archetype_line = (
            f'El arquetipo ha sido preseleccionado: "{archetype}". Usa EXACTAMENTE ese valor en "personality".'
            if archetype
            else f"Elige el arquetipo más apropiado de esta lista: {', '.join(ARCHETYPES)}."
        )
        return f"""Eres un sistema de generación de personajes paródicos de crítica cinematográfica.

PERSONA REAL A PARODIAR:
Nombre real: {real_name}

CONTEXTO (fragmentos web):
{snippets_block}

INSTRUCCIONES:
Crea un personaje paródico basado en "{real_name}". Es una caricatura exagerada de sus
características más conocidas, enfocadas en cómo vería el CINE.
{archetype_line}

Genera un JSON válido con EXACTAMENTE estos campos:
{{
  "caricature_name": "Apodo creativo y divertido (no el nombre real, algo inventado y gracioso)",
  "emoji": "Un ÚNICO emoji que represente al personaje (solo un carácter emoji, sin más)",
  "color": "#RRGGBB — color hex que evoque la esencia del personaje",
  "personality": "uno de: {', '.join(ARCHETYPES)}",
  "description": "2-3 frases en 2ª persona. Empieza con 'Eres...' Describe quién es como crítico de cine, qué le mueve y cómo habla.",
  "loves": ["4 a 6 cosas que el personaje AMA en el cine"],
  "hates": ["4 a 6 cosas que el personaje ODIA en el cine"],
  "motifs": ["6 a 8 temas recurrentes en sus críticas (palabras clave cortas)"],
  "catchphrases": ["2 o 3 frases que usa habitualmente al criticar"],
  "avoid": ["2 o 3 comportamientos a evitar en sus críticas"],
  "red_flags": ["3 a 5 cosas que le provocan reacción intensa"]
}}

IMPORTANTE:
- Todos los campos deben ser COHERENTES entre sí
- El foco es cómo esta persona vería el CINE, no su vida en general
- Responde SOLO con el JSON válido, sin texto adicional ni bloques markdown""".strip()

    def _regen_prompt(self, field: str, current_soul: dict, real_name: str) -> str:
        context = {k: v for k, v in current_soul.items() if k != field}
        return f"""Eres un sistema de generación de personajes paródicos.

PERSONAJE: basado en "{real_name}"

ALMA ACTUAL (NO modificar estos campos):
{json.dumps(context, ensure_ascii=False, indent=2)}

TAREA: Regenera ÚNICAMENTE el campo "{field}".
Tipo esperado: {_FIELD_HINTS.get(field, 'ver esquema')}

El nuevo valor debe ser COHERENTE con todos los campos existentes.
Responde SOLO con: {{"{field}": <nuevo_valor>}}""".strip()

    # ── Public API ────────────────────────────────────────────────────────────

    async def generate_soul(self, real_name: str, archetype: str | None = None) -> dict:
        """
        Full pipeline: DDG → LLM → validated soul dict.
        Returns the soul dict on success.
        Raises RuntimeError on failure.
        """
        snippets = await self.fetch_context(real_name)
        prompt = self._soul_prompt(real_name, snippets, archetype)

        logger.info(f"Generating soul for {real_name!r} (archetype={archetype})")
        raw = await self._call_llm(prompt)

        soul = self._extract_json(raw)
        if soul is None:
            raise RuntimeError("LLM did not return valid JSON for soul generation")

        # Ensure emoji is single char (take first grapheme cluster)
        if "emoji" in soul and isinstance(soul["emoji"], str):
            soul["emoji"] = soul["emoji"].strip()[:2]  # emoji can be 2 bytes

        # Ensure archetype matches if pre-selected
        if archetype and soul.get("personality") != archetype:
            soul["personality"] = archetype

        logger.info(f"Soul generated for {real_name!r}: personality={soul.get('personality')}")
        return soul

    async def regen_field(self, field: str, current_soul: dict, real_name: str) -> Any:
        """
        Regenerate a single soul field keeping all others as context.
        Returns the new field value.
        Raises ValueError for unknown fields, RuntimeError on LLM failure.
        """
        if field not in SOUL_FIELDS:
            raise ValueError(f"Unknown soul field: {field!r}")

        prompt = self._regen_prompt(field, current_soul, real_name)
        logger.info(f"Regenerating field '{field}' for {real_name!r}")
        raw = await self._call_llm(prompt)

        result = self._extract_json(raw)
        if result is None or field not in result:
            raise RuntimeError(f"LLM did not return valid JSON for field '{field}'")

        value = result[field]

        # Post-process emoji
        if field == "emoji" and isinstance(value, str):
            value = value.strip()[:2]

        # Enforce archetype if provided
        if field == "personality" and "personality" in current_soul:
            # Allow free regen of personality — caller decides
            pass

        return value
