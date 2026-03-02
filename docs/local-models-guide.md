# Local Models Guide — Parody Critics

Parody Critics works with **local LLMs via [Ollama](https://ollama.com)**. No API keys, no cloud,
no subscriptions. Your hardware, your models.

This guide covers the models we've tested, what to expect from each, and how to get started.

---

## Quick start

1. Install [Ollama](https://ollama.com/download)
2. Pull a recommended model (see below)
3. Set the Ollama URL in the plugin settings (`http://localhost:11434` by default)
4. Done — the plugin auto-detects the model and applies the right parameters

---

## At a glance

| Model | VRAM needed | Speed | Quality | Install |
|-------|-------------|-------|---------|---------|
| `type32/eva-qwen-2.5-14b` | **8 GB** | ⚡ ~8s | ⭐⭐⭐⭐ | `ollama pull type32/eva-qwen-2.5-14b` |
| `mistral-small3.1:24b` | **16 GB** | 🐢 ~20s | ⭐⭐⭐⭐⭐ | `ollama pull mistral-small3.1:24b` |
| `gemma3:27b` | **24 GB** ⚠️ | ⚡ ~8s | ⭐⭐⭐⭐⭐ | `ollama pull gemma3:27b` |

> ⚠️ `gemma3:27b` runs on 16 GB cards but slowly (~70s/review due to partial CPU offloading).
> Full performance requires 24 GB VRAM.

**Don't know your GPU's VRAM?** Check your GPU model:
- RTX 3060 / RX 6700 → 12 GB → `eva-qwen` works great
- RTX 3080 / RTX 4070 → 12-16 GB → `eva-qwen` or `mistral-small`
- RTX 3090 / RTX 4090 / RX 7900 XTX → 24 GB → `gemma3:27b` recommended
- No GPU or integrated graphics → any model works via CPU, expect 5-10× slower

---

## Recommended models

These are models we've tested extensively with the full character roster and a set of reference films.
All install with a single `ollama pull` command.

### Best quality — `mistral-small3.1:24b`

```bash
ollama pull mistral-small3.1:24b
```

| | |
|-|-|
| **Size** | ~14 GB VRAM |
| **Speed** | ~15-20s per review |
| **Why it works** | Strongest ideological consistency of all tested models. Characters feel genuinely distinct. |
| **Minimum hardware** | 16 GB VRAM recommended |

Our top pick for quality. Adolf gives `1/10` to everything that contradicts his worldview — and
the reasons change per film. Po is terrified by The Shining (`1/10`) but loves Soul (`10/10`).
Elon dismisses anything that isn't a productivity win (`1/10`). The ideological logic is tight.

---

### Best speed — `type32/eva-qwen-2.5-14b`

```bash
ollama pull type32/eva-qwen-2.5-14b
```

| | |
|-|-|
| **Size** | ~7 GB VRAM |
| **Speed** | ~8s per review |
| **Why it works** | Strong instruction-following, good ideological calibration, consistent character voices |
| **Minimum hardware** | 8 GB VRAM (GPU) or 16 GB RAM (CPU, much slower) |

Best if speed matters. Characters give ideologically coherent ratings with good range.
Highlight: Adolf gives `10/10` to Soul — ideologically justified (order, harmony, discipline).
One quirk: El Gran Lebowski tends to float around 6-7/10 across most films.

---

### For future hardware — `gemma3:27b`

```bash
ollama pull gemma3:27b
```

| | |
|-|-|
| **Size** | ~16 GB VRAM (needs dedicated GPU) |
| **Speed** | ~8-10s with 24+ GB VRAM / ~70s with 16 GB (partial CPU offload) |
| **Why it works** | Best ideological calibration of all models tested — by a clear margin |
| **Minimum hardware** | 24 GB VRAM for full performance |

This is the best model we've tested, full stop. If you have a 24 GB GPU (RTX 3090, RTX 4090,
or equivalent), pull this and don't look back. On 16 GB cards it runs but slowly — each review
takes around a minute due to partial CPU offloading.

We're keeping this as our target for when we upgrade hardware.

---

## Not recommended

We tested these and they don't work well for this use case — saving you the download:

| Model | Problem |
|-------|---------|
| `phi4:latest` | Confirmed negative bias — gives 1/10 to everything regardless of character (Po gives 2/10 to Star Wars) |
| `dolphin3` | Gives ~7/10 to everything regardless of character ideology |
| `phi4-reasoning:14b` | Takes 20+ minutes per review due to how Ollama handles its thinking tokens |
| `mis-firefly-22b` | Leaks system prompt artifacts in output (`[/INST]`, examples), flat calibration |
| `qwen3:14b` (default settings) | Reviews are very short (~100 words) because thinking tokens eat the budget |
| RP/narrative fine-tunes in general | Trained to write beautiful prose, not to reason ideologically — flat ratings |

---

## Understanding the speed vs quality trade-off

There's a consistent pattern across everything we tested:

**More parameters = better ideological reasoning.** A 27B model understands why a libertarian
tech billionaire character would give 1/10 to a Korean film about class struggle. An 8B model
tends to average toward "it's a well-made film, 7/10".

**Fine-tuned RP models are the exception.** Models specifically trained for roleplay and narrative
(like muse-12b or Magnum V4) write beautiful character prose but lose the ability to reason about
*why* a character would give a specific rating. Their instruction-following gets overwritten by
their training objective. The text sounds great, the number is meaningless.

**Think mode is not always better.** Models that reason step-by-step before answering (DeepSeek-R1,
Qwen3) can actually produce *shorter* reviews because their thinking tokens consume the generation
budget. For creative text generation, a larger non-thinking model usually wins.

---

---

## Ollama settings

The plugin auto-configures temperature, token budget and other parameters for each supported model.
You just need to set the correct model name in the plugin settings.

If you're using a model not in our list, the plugin falls back to sensible defaults — but results
may vary. Feel free to open an issue if you find a model that works well and isn't listed here.

---

*Models tested on: RTX 5060 Ti 16 GB — 2026-03-01*
