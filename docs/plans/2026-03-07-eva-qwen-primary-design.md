# eva-qwen PRIMARY Validation Design

**Date:** 2026-03-07
**Goal:** Validate type32/eva-qwen-2.5-14b as replacement for mistral-small3.1:24b as PRIMARY model.

## Context

Benchmark ronda 2 (2026-03-04, 96 llamadas con V2):
- eva-qwen: voice 2.33/3, calibration 45%, speed ~8s
- mistral:  voice 2.21/3, calibration 25%, speed ~24s

## Validation Run

```bash
python3 testing/full_benchmark.py \
  --phase 2 \
  --variant V2 \
  --phase2-models mistral-small3.1:24b type32/eva-qwen-2.5-14b:latest \
  --characters "Marco Aurelio" "Rosario Costras" "Adolf Histeric" "Charlie Sheen" "Antonio Recio" "Beavis"
```

6 chars × 4 films × 2 models = 48 llamadas, ~10-15 min.

## Decision Criteria

eva-qwen becomes PRIMARY if ALL three conditions met:
1. `voice_score` avg ≥ mistral OR difference < 0.2
2. `calibration%` ≥ mistral
3. `format_ok` = 100%

Otherwise mistral stays PRIMARY.

## If eva-qwen wins

Update on DUNE:
```env
LLM_PRIMARY_MODEL=type32/eva-qwen-2.5-14b:latest
LLM_SECONDARY_MODEL=mistral-small3.1:24b
```

Restart container. Mistral becomes fallback.
