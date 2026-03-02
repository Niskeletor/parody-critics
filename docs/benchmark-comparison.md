# Benchmark Comparativo — Todos los Modelos

**Fecha**: 2026-03-01 | **Re-benchmark top 3**: 2026-03-02
**Protocolo**: 8 personajes × 4 películas = 32 críticas por modelo
**Hardware**: Omnius — RTX 5060 Ti 16GB VRAM (192.168.2.69)

---

## Tabla General

| Modelo | Tamaño | Velocidad | OK/32 | Calibración | Veredicto |
|--------|--------|-----------|-------|-------------|-----------|
| `dolphin3:latest` | 4GB | ~7s | 28/32 | ❌ flat 7/10 | **DESCARTADO** |
| `phi4-reasoning:14b` | 10GB | ~1200s | — | — | **DESCARTADO** (muy lento) |
| `mis-firefly-22b:latest` | 13GB | ~25s | — | ❌ leaks prompt artifacts | **DESCARTADO** |
| `phi4:latest` | 8GB | ~7s | 32/32 | ❌ sesgo negativo confirmado | **DESCARTADO** |
| `muse-12b:latest` | 6GB | ~7s | 30/32 | ⚠️ flat 7, voz OK | Voice-only |
| `LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M` | 8GB | ~6s | 32/32 | ⚠️ flat 7, voz OK | Voice-only |
| `deepseek-r1:8b` | 4GB | ~10s | 32/32 | 🔶 mixto | Candidato |
| `richardyoung/qwen3-14b-abliterated:latest` | 8GB | ~10s | 31/32 | 🔶 Rosario plana | Candidato |
| `qwen3:14b` | 8GB | ~20s | 32/32 | 🔶 muy negativo, respuestas cortas | Descartable |
| `type32/eva-qwen-2.5-14b:latest` | 7GB | ~8s | 31/32 | ✅ buen balance | **TOP 1 velocidad** |
| `mistral-small3.1:24b` | 14GB | ~15-20s | 32/32 | ✅✅✅ excelente | **TOP 1 calidad** |
| `gemma3:27b` | 16GB | ~70s | 32/32 | ✅✅✅ mejor | Futuro hardware |
| `qwen3.5:27b` | 22GB | ∞ | — | — | **Necesita 2x16GB** |
| `qwen3.5:35b` | 23GB | ∞ | — | — | **Necesita 2x16GB** |

---

## Detalle: Ratings por Personaje × Película

> ✅ = correcto ideológicamente | ❌ = incorrecto | — = no capturado | ⚠️ = fallo

### Mark Hamill
*(Espera: SW=bajo, Parásitos=alto, Resplandor=alto, Soul=medio)*

| Modelo | SW:UJ | Parásitos | Resplandor | Soul |
|--------|-------|-----------|------------|------|
| muse-12b | 7 | 7 | 8 | 7 |
| magnum-v4 | 7 | 8 | 7 | 7 |
| eva-qwen | **4** ✅ | 4 | 7 | 6 |
| qwen3-abl | **3** ✅ | 7 | 8 | 7 |
| qwen3:14b | **1** ✅✅ | **9** ✅ | 8 | 7 |
| phi4 | **1** ✅✅ | **9** ✅ | 9 | 9 |
| deepseek-r1 | 2 ✅ | — | — | — |
| mistral-small | **1** ✅✅ | — | — | — |
| gemma3:27b | **1** ✅✅ | **9** ✅ | 9 | 8 |

### Adolf Histeric
*(Espera: todo bajo — especialmente Parásitos y Soul)*

| Modelo | SW:UJ | Parásitos | Resplandor | Soul |
|--------|-------|-----------|------------|------|
| muse-12b | 7 | 3 | 7 | 7 |
| magnum-v4 | 3 ✅ | 7 | 8 | 2 ✅ |
| eva-qwen | 3 ✅ | **4** ✅ | 4 ✅ | **10** 🤩 |
| qwen3-abl | — | 6 | 3 ✅ | 6 |
| qwen3:14b | 3 ✅ | **1** ✅✅ | 2 ✅ | 3 ✅ |
| phi4 | **1** ✅✅ | — | — | — |
| deepseek-r1 | — | 6 ❌ | 4 | 2 ✅ |
| mistral-small | **1** ✅✅ | **1** ✅✅ | 3 ✅ | **1** ✅✅ |
| gemma3:27b | 2 ✅ | **1** ✅✅ | 2 ✅ | **1** ✅✅ |

### Elon Musaka
*(Espera: SW=bajo, Parásitos=muy bajo, Resplandor=medio, Soul=bajo)*

| Modelo | SW:UJ | Parásitos | Resplandor | Soul |
|--------|-------|-----------|------------|------|
| muse-12b | 9 ❌ | 7 ❌ | 9 ❌ | 7 |
| magnum-v4 | 3 ✅ | 3 ✅ | 3 ✅ | 5 |
| eva-qwen | 3 ✅ | 7 ❌ | 7 | 7 |
| qwen3-abl | 4 ✅ | **3** ✅✅ | 3 ✅ | 3 ✅ |
| qwen3:14b | 2 ✅ | 2 ✅ | 2 | 2 |
| phi4 | 2 ✅ | 2 ✅ | 2 | 2 |
| deepseek-r1 | **8** ❌❌ | 2 ✅ | 2 | 3 |
| mistral-small | **1** ✅ | **2** ✅✅ | 1 | 1 |
| gemma3:27b | 2 ✅ | **2** ✅✅ | 2 ✅ | 2 ✅ |

### Rosario Costras
*(Espera: SW=alto, Parásitos=alto, Resplandor=bajo, Soul=alto)*

| Modelo | SW:UJ | Parásitos | Resplandor | Soul |
|--------|-------|-----------|------------|------|
| muse-12b | 9 ✅ | 8 ✅ | 7 | 4 |
| magnum-v4 | 8 ✅ | 2 ❌ | 7 | 7 |
| eva-qwen | 7 ✅ | 7 ✅ | **1** ✅✅ | 6 |
| qwen3-abl | 7 ✅ | 7 ✅ | 7 ❌ | 7 |
| qwen3:14b | 6 ✅ | 7 ✅ | **2** ✅✅ | 6 |
| phi4 | 3 ❌ | **8** ✅ | **1** ✅✅ | 3 ❌ |
| deepseek-r1 | 5 | **10** ✅✅ | 6 | 5 |
| mistral-small | 7 ✅ | 7 ✅ | 5 | **9** ✅✅ |
| gemma3:27b | 6 ✅ | 7 ✅ | **2** ✅✅ | 4 |

### Alan Turbing
*(Espera: apreciación intelectual — SW=medio, buenas películas=alto)*

| Modelo | SW:UJ | Parásitos | Resplandor | Soul |
|--------|-------|-----------|------------|------|
| muse-12b | 5 | 6 | 9 ✅ | 5 |
| magnum-v4 | 7 | 2 ❌ | 7 | 7 |
| eva-qwen | 6 | 6 | 7 | 4 |
| qwen3-abl | 7 | 7 | 7 | 6 |
| qwen3:14b | 6 | 7 | 7 | 6 |
| phi4 | 3 ❌ | 4 | 2 ❌ | 3 ❌ |
| deepseek-r1 | 8 ✅ | **10** ✅✅ | 8 ✅ | 6 |
| mistral-small | 7 | 8 | **9** ✅ | 7 |
| gemma3:27b | 2 ❌ | — | — | 2 ❌ |

### Lloyd Kaufman
*(Espera: SW=muy bajo, Parásitos=muy alto, Resplandor=bajo, Soul=bajo)*

| Modelo | SW:UJ | Parásitos | Resplandor | Soul |
|--------|-------|-----------|------------|------|
| muse-12b | 7 | 7 | 8 | 4 |
| magnum-v4 | 9 ❌ | 4 | 7 | 7 |
| eva-qwen | 5 | **9** ✅✅ | 7 | 7 |
| qwen3-abl | **1** ✅✅ | 7 | 3 | 1 |
| qwen3:14b | **1** ✅✅ | 2 ❌ | 2 | 1 |
| phi4 | **1** ✅✅ | 7 | 3 | 1 |
| deepseek-r1 | 2 ✅ | 2 ❌ | 3 | 2 |
| mistral-small | **1** ✅✅ | **8** ✅✅ | 7 | 1 |
| gemma3:27b | **1** ✅✅ | 3 ❌ | 2 | 2 |

---

## Análisis por Modelo

### 🟢 TOP CANDIDATOS

#### `mistral-small3.1:24b` ⭐⭐⭐⭐⭐ — TOP 1 calidad
- **Velocidad**: ~15-20s/crítica (aceptable)
- **Fiabilidad**: 32/32 OK (re-benchmark 2026-03-02)
- **Calibración**: **La mejor entre los modelos viables**. Adolf `2,1,3,1` — cada película con lógica propia. Po `9,4,1,10` — ama SW, aterrado con El Resplandor, adora Soul. Elon `1,3,3,1`. Mark `1,9,8,7`.
- **Recomendación**: **Modelo principal de producción**

#### `type32/eva-qwen-2.5-14b:latest` ⭐⭐⭐⭐ — TOP 1 velocidad
- **Velocidad**: ~8s/crítica (excelente)
- **Fiabilidad**: 31/32 OK (re-benchmark 2026-03-02)
- **Calibración**: Buena. Personajes diferenciados, ratings con rango real.
- **Highlight**: Adolf da 10/10 a Soul (justificado ideológicamente — brillante)
- **Debilidad**: Lebowski un poco plano (6-7/10 a todo), 1 fallo de parseo
- **Recomendación**: **Mejor opción si la velocidad es prioritaria**

### 🟡 CANDIDATOS SECUNDARIOS

#### `deepseek-r1:8b` ⭐⭐
- **Velocidad**: ~10s/crítica
- **Fiabilidad**: 32/32 OK
- **Calibración**: Alan y Rosario brillantes, pero Elon da 8/10 a SW (fail grave)
- **Recomendación**: Candidato pero necesita más prompt tuning

#### `richardyoung/qwen3-14b-abliterated` ⭐⭐
- **Velocidad**: ~10s/crítica (varía mucho: 4-20s)
- **Fiabilidad**: 31/32 OK
- **Calibración**: Elon es el mejor de todos los modelos. Rosario plana.
- **Necesita**: `num_predict=2000` (se trunca con 800)
- **Recomendación**: Candidato si se ajusta num_predict

### 🔵 VOICE-ONLY (sin calibración ideológica)

#### `muse-12b:latest` + `MAGNUM_V4-Mistral_Small`
- Excelentes voces y narrativa, pero ratings planos ~7/10
- Útiles para: tests de voz de personajes, narrativa de crítica
- No aptos para: producción (el rating es la gracia del sistema)

### 🔴 DESCARTADOS

| Modelo | Razón |
|--------|-------|
| `phi4:latest` | Sesgo negativo confirmado — da 1/10 a todo independientemente del personaje |
| `dolphin3` | Flat 7/10, no sigue lógica ideológica |
| `phi4-reasoning:14b` | 20min/crítica (thinking tokens consumen budget) |
| `mis-firefly-22b` | Filtra artefactos del prompt (`[/INST]`), calibración plana |
| `qwen3:14b` | Respuestas muy cortas (~100w), sesgo negativo |
| `qwen3.5:27b` | 10.6GB en CPU — velocidad impráctica |
| `qwen3.5:35b` | 23GB total — velocidad impráctica |

### 🔮 FUTURO (más VRAM)

#### `gemma3:27b` ⭐⭐⭐⭐ (con hardware adecuado)
- **Velocidad actual**: ~70s/crítica (4GB spillover a CPU)
- **Fiabilidad**: 32/32 OK
- **Calibración**: **LA MEJOR** — Adolf, Elon, Mark perfectos
- **Con 2x16GB o 3080**: ~8-10s/crítica → modelo TOP absoluto
- **Recomendación**: Prioridad cuando llegue el nuevo hardware

#### `qwen3.5:27b` + `qwen3.5:35b`
- Con 2x RTX 5060 Ti 16GB (32GB VRAM) → caben perfectamente
- Think=True disponible → calibración esperada muy alta

---

## Próximos Pasos

1. **Producción**: `mistral-small3.1:24b` como modelo principal, `eva-qwen` como fallback rápido

2. **Plugin Jellyfin**: integrar la API en el plugin JS — objetivo final del proyecto

3. **Hardware futuro**: RTX 3080 (192.168.45.161) + RTX 5060 Ti → 26GB pool → `gemma3:27b` como modelo principal

