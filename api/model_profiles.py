"""
🤖 Model Profiles — per-model LLM call configuration
Each profile tells the LLM client HOW to call a given model:
think mode, temperature, token budget, and prompt format quirks.
"""
from dataclasses import dataclass


@dataclass
class ModelProfile:
    think: bool          # Activate thinking mode (qwen3, deepseek-r1)
    temperature: float
    num_predict: int     # Must be large for thinking models (4096+)
    system_in_user: bool # deepseek: merge system prompt into user message
    top_p: float = 0.95
    top_k: int = 20
    strip_think: bool = True  # Strip <think>...</think> from final response


PROFILES: dict[str, ModelProfile] = {
    "qwen3:8b": ModelProfile(
        think=True, temperature=0.60, num_predict=4096, system_in_user=False
    ),
    "qwen3:14b": ModelProfile(
        think=True, temperature=0.60, num_predict=4096, system_in_user=False
    ),
    "deepseek-r1:8b": ModelProfile(
        think=True, temperature=0.60, num_predict=6144, system_in_user=True
    ),
    "phi4:latest": ModelProfile(
        think=False, temperature=0.70, num_predict=600, system_in_user=False
    ),
    "mistral-small3.1:24b": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    "gemma3:27b": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    # parody-* custom Modelfiles (phi4 base, good params baked in)
    "parody-phi4:latest": ModelProfile(
        think=False, temperature=0.70, num_predict=600, system_in_user=False
    ),
    "parody-qwen3": ModelProfile(
        think=True, temperature=0.60, num_predict=4096, system_in_user=False
    ),
    # Muse-12B by LatitudeGames — narrative RP fine-tune, needs high num_predict
    "hf.co/LatitudeGames/Muse-12B-GGUF:Q4_K_M": ModelProfile(
        think=False, temperature=0.75, num_predict=2000, system_in_user=False
    ),
    "muse-12b:latest": ModelProfile(
        think=False, temperature=0.75, num_predict=2000, system_in_user=False
    ),
    # Magnum V4 Mistral Small 12B — RP/narrative fine-tune
    "LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M": ModelProfile(
        think=False, temperature=0.75, num_predict=2000, system_in_user=False
    ),
    # phi4-reasoning: Ollama doesn't support think=True for this model, generates
    # reasoning internally regardless — use larger num_predict for the full output
    "phi4-reasoning:14b": ModelProfile(
        think=False, temperature=0.70, num_predict=1200, system_in_user=False
    ),
    # qwen3.5:27b — 22.5GB model, only 12.9GB fits in VRAM (10.6GB CPU spillover)
    # think=False mandatory — CPU spillover + thinking = too slow for production
    "qwen3.5:27b": ModelProfile(
        think=False, temperature=0.65, num_predict=800, system_in_user=False
    ),
    # qwen3.5:35b — even larger, will need even more CPU offloading
    "qwen3.5:35b": ModelProfile(
        think=False, temperature=0.65, num_predict=800, system_in_user=False
    ),
    # qwen3-14b abliterated — think mode stripped during abliteration, use think=False
    # needs num_predict=2000 — model naturally writes 500-600w, truncates at 800 tokens
    "richardyoung/qwen3-14b-abliterated:latest": ModelProfile(
        think=False, temperature=0.65, num_predict=2000, system_in_user=False
    ),
    # mis-firefly-22b — 22B Mistral fine-tune, 13GB GGUF
    # BENCHMARKED: leaks system prompt artifacts ([/INST], examples), flat calibration
    # DESCARTADO — kept so it works if manually selected
    "mis-firefly-22b:latest": ModelProfile(
        think=False, temperature=0.75, num_predict=800, system_in_user=False
    ),
    # eva-qwen-2.5-14b by type32 — RP/uncensored fine-tune of Qwen2.5-14B
    # TOP 1 benchmark: 32/32 OK, ~8s/crítica, 7GB VRAM — best speed/quality balance
    "type32/eva-qwen-2.5-14b:latest": ModelProfile(
        think=False, temperature=0.75, num_predict=800, system_in_user=False
    ),
    # dolphin3 — uncensored Llama3 fine-tune, 4GB, fast (~7s)
    # BENCHMARKED: 28/32 OK but calibration flat (all 7/10) — DESCARTADO for production
    # Profile kept so it works if manually selected
    "dolphin3:latest": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    # parody-deepseek: based on deepseek-r1, think=False to guarantee content output
    "parody-deepseek:latest": ModelProfile(
        think=False, temperature=0.65, num_predict=800, system_in_user=True
    ),
    # ── Cloud models ────────────────────────────────────────────────────────────
    # num_predict is ignored by cloud callers (they use max_tokens=600 directly)
    # OpenAI
    "gpt-4o-mini": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    "gpt-4o": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    # Anthropic
    "claude-haiku-4-5-20251001": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    "claude-sonnet-4-6": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    # Groq free tier
    "llama-3.3-70b-versatile": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    "llama-3.1-8b-instant": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
    "gemma2-9b-it": ModelProfile(
        think=False, temperature=0.75, num_predict=600, system_in_user=False
    ),
}


def get_profile(model_name: str) -> ModelProfile:
    """Return profile for model_name. Falls back to heuristic for unknown models."""
    if model_name in PROFILES:
        return PROFILES[model_name]
    # Try with :latest suffix (Ollama adds it when tag is omitted in config)
    with_tag = model_name if ":" in model_name else f"{model_name}:latest"
    if with_tag in PROFILES:
        return PROFILES[with_tag]

    # Heuristic for unknown/custom models
    name = model_name.lower()
    think = any(k in name for k in ["r1", "think", "reason", "qwq", "qwen3"])
    return ModelProfile(
        think=think,
        temperature=0.60 if think else 0.75,
        num_predict=4096 if think else 600,
        system_in_user="deepseek" in name,
    )
