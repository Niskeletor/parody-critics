# Full Benchmark Design — Prompt × Model Optimization
**Date**: 2026-03-04
**Goal**: Find the best prompt variant + model combination that maximizes authentic character voice and ideological calibration.

---

## Priority

1. **Voz auténtica** (primary) — muletillas, anécdotas personales, referencias características del personaje
2. **Calibración ideológica** (secondary) — el rating refleja la ideología del personaje, no la calidad técnica

---

## Structure: 2 Phases

### Phase 1 — Prompt Battle
Model fixed: `mistral-small3.1:24b`
Goal: find the best prompt variant before spending time across all models.

- 4 variants × 6 characters × 4 films = **96 calls**

### Phase 2 — Model Battle
Prompt fixed: winner from Phase 1
Goal: compare models on equal footing with the best prompt.

- 4 models × 6 characters × 4 films = **96 calls**

**Total: ~192 calls** — estimated 40-60 min on Omnius (RTX 5060 Ti 16GB)

---

## Prompt Variants

| ID | Description |
|----|-------------|
| **V0** | Baseline — current production prompt, no changes |
| **V1** | + voice instruction: explicitly ask for catchphrases, personal comparisons, anecdotes in INSTRUCCIONES block |
| **V2** | + soul anecdotes: 3-4 concrete character-specific references injected into user block |
| **V3** | V1 + V2 combined (full enrichment) |

### V1 voice instruction addition (appended to INSTRUCCIONES):
```
Usa tu voz más característica: incluye alguna muletilla tuya, compara la obra con algo de tu vida
o suelta una anécdota personal. Que se note quién eres, no solo qué piensas.
```

### V2 anecdotes per character (injected after identity block):
- **Marco Aurelio**: referencias a Epicteto, Séneca, su diario personal, la decadencia de Roma
- **Rosario Costras**: su cuñada de Albacete, el precio del aceite, el médico de cabecera, las novelas del corazón
- **Adolf Histeric**: el orden alemán, la pureza racial, el Reich que pudo ser, Wagner
- **Charlie Sheen**: "winning", las goddesses, el Bali Air, los dos hombres y medio
- **Antonio Recio**: el chóped, el mercado de La Boqueria, la familia como institución, los maricones de la tele
- **Beavis**: fuego, Cornholio, heavy metal, cosas que molan (FIRE! FIRE!), cosas que no molan

---

## Models (Phase 2)

| Model | Type | VRAM | Why included |
|-------|------|------|--------------|
| `mistral-small3.1:24b` | Instruction | 14GB | Current primary, best calibration |
| `type32/eva-qwen-2.5-14b` | RP fine-tune | 7GB | Current secondary, fastest |
| `muse-12b:latest` | Narrative RP | 8.6GB | LatitudeGames fine-tune, strong voice |
| `LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M` | RP fine-tune | 8.7GB | Narrative strength, untested for this task |

---

## Characters

| Character | Ideology | Voice markers |
|-----------|----------|---------------|
| Marco Aurelio | Stoic philosopher | Latin quotes, philosophical detachment, resigned wisdom |
| Rosario Costras | Spanish housewife | Local references, gossip tone, domestic comparisons |
| Adolf Histeric | Far-right extremist | Racial purity obsession, order fetish, Germanic references |
| Charlie Sheen | Hedonist celebrity | "Winning", goddesses, Hollywood excess, no filter |
| Antonio Recio | Spanish macho | Chóped pride, anti-everything progressive, market trader energy |
| Beavis | Dumb teenager | Fire, heavy metal, "this sucks/this rules", Cornholio |

---

## Films

| Film | Year | Why chosen |
|------|------|------------|
| Barbie | 2023 | Explicit feminism — triggers Adolf, Antonio Recio; Beavis only sees girls |
| John Wick | 2014 | Pure stylized violence — Beavis ecstatic, Marco Aurelio conflicted |
| Idiocracy | 2006 | Stupidity dystopia — Marco Aurelio prophetic, Beavis feels represented, Adolf sees "degeneration" |
| El Padrino | 1972 | Honor, family, power — Antonio Recio reveres it, Rosario sees a normal family |

---

## Expected Calibration Ranges

| | Barbie | John Wick | Idiocracy | El Padrino |
|--|--------|-----------|-----------|------------|
| **Marco Aurelio** | 4-6 | 3-5 | 7-9 | 5-7 |
| **Rosario Costras** | 5-7 | 4-6 | 3-5 | 7-9 |
| **Adolf Histeric** | 1-2 | 6-8 | 7-9 | 5-7 |
| **Charlie Sheen** | 6-8 | 8-10 | 5-7 | 7-9 |
| **Antonio Recio** | 1-3 | 6-8 | 4-6 | 9-10 |
| **Beavis** | 7-9 | 9-10 | 8-10 | 2-4 |

---

## Metrics

| Metric | Method | Priority |
|--------|--------|----------|
| `voice_score` | LLM-as-judge via `dolphin3` (0-3): counts catchphrases, personal anecdotes, character references | **High** |
| `calibration_ok` | Auto: rating within expected range for character × film pair | Medium |
| `format_ok` | Auto: starts with X/10, word count 80-180 | Low |
| `response_time` | Auto: seconds | Info |

### LLM-as-judge prompt (dolphin3):
```
You are evaluating a parody film critic. The character is: {character_name}.
Score the following text from 0 to 3:
  0 = generic, no personality markers
  1 = some character voice but could be anyone
  2 = clear character voice with at least one specific reference or catchphrase
  3 = strong authentic voice, multiple personal references or anecdotes

Text: {critic_text}

Reply with a single digit (0, 1, 2 or 3) and nothing else.
```

---

## Output Files

- `docs/benchmark-results/YYYY-MM-DD-full-benchmark.json` — raw data (all calls)
- `docs/benchmark-results/YYYY-MM-DD-full-benchmark.md` — human-readable report with rankings
- Winner table: best prompt + model combo per character

---

## Script Location

`testing/full_benchmark.py` — standalone script, calls Ollama directly (no app integration)

```bash
# Run full benchmark
python3 testing/full_benchmark.py

# Phase 1 only (prompt variants)
python3 testing/full_benchmark.py --phase 1

# Phase 2 only with specific prompt variant
python3 testing/full_benchmark.py --phase 2 --variant V3

# Quick test (1 character, 1 film)
python3 testing/full_benchmark.py --quick
```
