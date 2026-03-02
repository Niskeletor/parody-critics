# Candidatos LLM para Parody Critics
*Investigado: 2026-03-01 (ronda 1) + 2026-03-01 (ronda 2 — HuggingFace deep dive) | Estado: pendiente de benchmark en nuevo server*

Hardware objetivo: **RTX 5060 Ti 16GB VRAM** (Omnius/Perseus)
Modelos ya en producción en Omnius: qwen3:14b, deepseek-r1:8b, phi4:latest, gemma3:27b, mistral-small3.1:24b, parody-phi4:latest, parody-deepseek:latest

---

## Hallazgos destacados — resumen ejecutivo

### La joya que no esperábamos encontrar
**`richardyoung/qwen3-14b-abliterated`** — es literalmente `qwen3:14b` (nuestro mejor modelo en producción) con las restricciones borradas quirúrgicamente mediante abliteración. Misma VRAM (~9GB), mismo think mode intacto, mismo perfil de parámetros. Los personajes más extremos ya no generan resistencia interna del modelo. La abliteración de mlabonne reduce refusals de 97/100 a 19/100 con KL divergence ~0.98 (calidad prácticamente idéntica al base). Disponible con `ollama pull` directo. **Riesgo cero** — el perfil ya existe en `model_profiles.py`.

### Magnum v4 disponible en Ollama directo (sorpresa logística)
Magnum v4 es el fine-tune de `anthracite-org` que replica calidad de prosa de Claude 3. Pensábamos que solo era accesible vía HuggingFace, pero `LESSTHANSUPER` lo tiene publicado en Ollama en formato 9B, 12B y 22B. El 12B a Q5_K_M (~9GB) es el punto óptimo para 16GB: alta calidad de escritura literaria, instalación en un comando.

### Salamandra — el único modelo pensado en español desde el origen
Del Barcelona Supercomputing Center, financiado públicamente, entrenado con corpus que prioriza español peninsular, catalán, gallego y euskera. 7B, ~5GB VRAM, `ollama pull` directo. Todos los demás modelos del listado escriben español como segunda lengua; Salamandra lo tiene como primera. Vale la pena comparar la naturalidad del output aunque el modelo sea más pequeño.

### DavidAU/Gemma-The-Writer — prosa diferente a todo lo demás
Merge de los 4 mejores modelos de storytelling sobre Gemma 10B con técnica "Brainstorm 5x". Reduce GPT-ismos, varía estructura de párrafos, produce textos más largos y con más riqueza léxica que cualquier modelo base. 11.8k descargas. El riesgo es que al ser Gemma puede tener un formato de respuesta diferente — hay que verificar que sigue el system prompt correctamente.

---

## Criterios de selección

Para que un modelo valga la pena en Parody Critics necesita:
1. **Seguir system prompt** — mantener voz del personaje durante 150 palabras
2. **Rating consistente** — el X/10 tiene que ser coherente con el texto
3. **Español fluido** — sin calcos del inglés, naturalidad coloquial
4. **Instrucción seguible** — respeta `NUNCA`, rubrica, motifs sin inventarse cosas
5. **Velocidad razonable** — menos de 30s para 150 palabras es aceptable

---

## Prioridad ALTA — descargar primero

### `phi4-reasoning:14b`
- **VRAM**: ~11GB (Q4 por defecto en Ollama)
- **Por qué**: Distilado del proceso de razonamiento de o3-mini de OpenAI. En benchmarks supera a DeepSeek-R1 distill de 70B siendo 5x más pequeño. Si funciona bien para críticas, es el mejor ratio calidad/VRAM de todos.
- **Quirk importante**: usa `<think>...</think>` en `message.content` (no en campo `thinking` separado como qwen3). El `_strip_think_blocks()` ya lo maneja correctamente.
- **Perfil a añadir en model_profiles.py**:
  ```python
  "phi4-reasoning:14b": ModelProfile(think=True, temperature=0.60, num_predict=4096, system_in_user=False)
  ```
- **Descargar**: `ollama pull phi4-reasoning:14b`

---

### `dolphin3:8b`
- **VRAM**: ~5GB
- **Por qué**: Serie Dolphin de Eric Hartford — el referente histórico de modelos uncensored. "You decide the guidelines" — el system prompt lo controla completamente, sin resistencia interna. Perfecto para personajes edgy o provocadores. Rápido y ligero, ideal como modelo secundario siempre cargado.
- **Variante más agresiva**: `huihui_ai/dolphin3-abliterated` (abliteración quirúrgica de restricciones)
- **Perfil a añadir**:
  ```python
  "dolphin3:8b": ModelProfile(think=False, temperature=0.80, num_predict=700, system_in_user=False)
  ```
- **Descargar**: `ollama pull dolphin3`

---

### `type32/eva-qwen-2.5-14b`
- **VRAM**: ~9-10GB (Q4)
- **Por qué**: EVA es un fine-tune de Qwen2.5-14B específicamente para roleplay y escritura creativa sin censura. Destaca en mantener personalidades consistentes, profundidad emocional y contexto extendido. Diseñado exactamente para el caso de uso de Parody Critics.
- **Perfil a añadir**:
  ```python
  "eva-qwen2.5-14b": ModelProfile(think=False, temperature=0.75, num_predict=700, system_in_user=False)
  "type32/eva-qwen-2.5-14b": ModelProfile(think=False, temperature=0.75, num_predict=700, system_in_user=False)
  ```
- **Descargar**: `ollama pull type32/eva-qwen-2.5-14b`

---

## Prioridad MEDIA — segunda ronda

### `magistral:24b`
- **VRAM**: ~15-16GB (Q4) — borderline, puede necesitar reducir contexto
- **Por qué**: Primer modelo reasoning de Mistral. Multilingüe con soporte explícito de español. Razonamiento con chain-of-thought trazable. Contexto 128k (aunque recomiendan cap en 40k).
- **Perfil a añadir**:
  ```python
  "magistral:24b": ModelProfile(think=True, temperature=0.60, num_predict=4096, system_in_user=False)
  ```
- **Descargar**: `ollama pull magistral`
- **Nota**: si no carga completo en 16GB, probar `magistral:24b-small-2506-q4_0`

---

### `aya-expanse:8b`
- **VRAM**: ~5GB
- **Por qué**: Modelo de Cohere entrenado explícitamente para 23 idiomas incluyendo español. Puede ser el mejor para personajes cuya voz coloquial española es crítica. Ligero y rápido.
- **Variante grande**: `aya-expanse:32b` (~16GB en Q3, ajustado)
- **Perfil a añadir**:
  ```python
  "aya-expanse:8b": ModelProfile(think=False, temperature=0.75, num_predict=700, system_in_user=False)
  ```
- **Descargar**: `ollama pull aya-expanse`

---

### `huihui_ai/qwen2.5-abliterate:32b-instruct`
- **VRAM**: ~16GB (IQ3/Q3) — muy justo
- **Por qué**: Qwen2.5-32B con abliteración — borrado quirúrgico de restricciones sin reentrenar. Mayor capacidad que los 14B pero sin censura. Si cabe en VRAM puede dar muy buen resultado.
- **Alternativa si no cabe**: `huihui_ai/qwen2.5-abliterate:14b-instruct`
- **Descargar**: `ollama pull huihui_ai/qwen2.5-abliterate:32b-instruct`

---

### `qwq:32b` (versión quantizada)
- **VRAM**: ~16GB (IQ3_XS/Q3_K_M) — en el límite absoluto
- **Por qué**: El flagship de razonamiento de Qwen, competitivo con DeepSeek-R1 y o1-mini. Si cabe en 16GB con IQ3, es potencialmente el mejor reasoning disponible.
- **Versión recomendada para 16GB**: `clore/qwq-32b-q4` o buscar IQ3_XS
- **Perfil a añadir**:
  ```python
  "qwq:32b": ModelProfile(think=True, temperature=0.60, num_predict=4096, system_in_user=False)
  ```
- **Nota**: si no entra completo en VRAM, Ollama hará offload a RAM — las críticas cortas (150 palabras) pueden seguir siendo aceptables en velocidad

---

## Prioridad BAJA — requieren Modelfile manual (solo en HuggingFace)

### `RP-INK Qwen2.5-32B` — la joya del roleplay
- **HuggingFace**: `allura-org/Qwen2.5-32b-RP-Ink`
- **Ollama**: `LESSTHANSUPER/RP-INK-Qwen2.5-32b:IQ4_XS` (18GB — no cabe en 16GB)
- **Por qué**: La comunidad lo considera mejor que Magnum V4 para escritura creativa. "Sigue el estilo de escritura del prompt mejor que cualquier otro modelo disponible."
- **Workaround para 16GB**: descargar GGUF Q3_K_M desde HuggingFace y crear Modelfile manual
- **Pendiente**: encontrar quant Q3 (~14-15GB) que entre en 16GB

### `Novaciano/L3.2-2025-SuperUncensored`
- **HuggingFace**: `Novaciano/L3.2-2025-SuperUncensored-GGUF`
- **Por qué**: Menciona soporte explícito de español + uncensored + roleplay. Basado en Llama 3.2. Interesante por el soporte ES nativo.
- **Cómo usar con Ollama**: descargar GGUF Q4 y crear Modelfile

---

## Tabla resumen

| Modelo | VRAM | Ollama directo | Think | Uncensored | Prioridad |
|--------|------|----------------|-------|------------|-----------|
| `phi4-reasoning:14b` | 11GB | ✅ | ✅ | ❌ | 🔴 Alta |
| `dolphin3:8b` | 5GB | ✅ | ❌ | ✅ | 🔴 Alta |
| `type32/eva-qwen-2.5-14b` | 9-10GB | ✅ | ❌ | ✅ | 🔴 Alta |
| `magistral:24b` | ~15-16GB | ✅ | ✅ | ❌ | 🟡 Media |
| `aya-expanse:8b` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `huihui_ai/qwen2.5-abliterate:32b` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media |
| `qwq:32b` (Q3) | ~16GB | ✅ (quant) | ✅ | ❌ | 🟡 Media |
| `RP-INK Qwen2.5-32b` (Q3) | ~14-15GB | ⚠️ HF | ❌ | ⚠️ | 🟢 Baja |
| `Novaciano/SuperUncensored` | ~5GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |

---

## Script de descarga (prioridad alta)

```bash
# En Omnius / nuevo server con Ollama corriendo
ollama pull phi4-reasoning:14b
ollama pull dolphin3
ollama pull type32/eva-qwen-2.5-14b

# Segunda ronda
ollama pull magistral
ollama pull aya-expanse
ollama pull huihui_ai/qwen2.5-abliterate:32b-instruct

# Verificar que cargan en GPU (no offload a RAM)
ollama run phi4-reasoning:14b "Di hola en español"
```

---

---

## Ronda 2 — HuggingFace deep dive (2026-03-01)
*Fuentes: repos de Sao10K, DavidAU, mlabonne, huihui-ai, anthracite-org, BSC-LT*

---

### 🏆 JOYA INESPERADA: `richardyoung/qwen3-14b-abliterated` (Ollama directo)

- **VRAM**: ~9GB (Q4_K_M) — mismo que qwen3:14b base
- **Por qué es especial**: Es qwen3:14b **con think mode intacto** + abliterado. Lo tienen mlabonne, huihui-ai y richardyoung. La abliteración de mlabonne reduce los refusals de 97/100 a 19/100 con KL divergence de ~0.98 (calidad casi idéntica al base). Es literalmente qwen3:14b sin filtros, con el mismo perfil de parámetros.
- **Relevancia para Parody Critics**: personajes extremos (trolls, radicales, provocadores) sin que el modelo se resista. El que ya funciona mejor en producción, pero sin cortapisas.
- **Quirk**: mismos quirks que qwen3:14b (think va a `message.thinking`). Mismo perfil en model_profiles.
- **Descargar**: `ollama pull richardyoung/qwen3-14b-abliterated` (disponible directo en Ollama)
- **Alternativa HF**: `bartowski/huihui-ai_Qwen3-14B-abliterated-GGUF` (quants variadas)

---

### `Gemma-The-Writer` (DavidAU) — merge de escritura creativa

- **Modelo**: `DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF`
- **VRAM**: ~7GB (Q4) — muy cómodo
- **Por qué**: Merge de los **4 mejores modelos de storytelling** sobre base Gemma 10B. Incorpora "Brainstorm 5x" que mejora prosa, reduce GPT-ismos, varía estructura de párrafos, aumenta longitud y riqueza del output. 11.8k descargas. Diseñado para escritura de ficción y roleplay. También existe `V2-Enhanced32` (versión mejorada con float32 imatrix).
- **Variantes disponibles**: base, V2-Enhanced32, DEADLINE (más oscuro/extremo)
- **Limitación**: basado en Gemma — puede tener formato de respuesta diferente. Hay que verificar que respeta system prompt correctamente.
- **Cómo instalar**: solo en HuggingFace → descargar GGUF Q4 + crear Modelfile en Ollama
  ```bash
  ollama create gemma-writer -f Modelfile  # Modelfile apunta al GGUF local
  ```

---

### `Sao10K/14B-Qwen2.5-Kunou-v1` — fine-tune RP sobre Qwen2.5

- **VRAM**: ~9-10GB (Q4_K_M)
- **Por qué**: Fine-tune de Qwen2.5-14B-Instruct por Sao10K, uno de los mejores creadores de modelos RP de la comunidad (también hace Euryale, Stheno, Fimbulvetr). La serie Kunou es su apuesta para modelos medianos con foco en roleplay y escritura creativa. Qwen2.5 base tiene buena base en español.
- **GGUF disponible**: `DevQuasar/Sao10K.14B-Qwen2.5-Kunou-v1-GGUF`, `mradermacher/14B-Qwen2.5-Kunou-v1-GGUF`
- **Cómo instalar**: descargar Q4_K_M desde HF + crear Modelfile en Ollama

---

### `MAGNUM_V4-Mistral_Small` (Ollama directo, varias tallas)

- **Por qué es importante**: Magnum v4 es el fine-tune de anthracite-org que **"replica la calidad de prosa de Claude 3"** — pensado específicamente para escritura literaria de alta calidad. Hay versiones sobre Mistral Nemo/Small en varios tamaños, todos disponibles directamente en Ollama.
- **Tallas disponibles en Ollama** (LESSTHANSUPER):

| Tag Ollama | VRAM est. | Recomendación |
|------------|-----------|---------------|
| `LESSTHANSUPER/MAGNUM_V4-Mistral_Small:9b_Q6_K` | ~7GB | ✅ cómodo |
| `LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M` | ~9GB | ✅ óptimo |
| `LESSTHANSUPER/MAGNUM_V4-Mistral_Small:22b_IQ4_XS` | ~14GB | ⚠️ borderline |
| `LESSTHANSUPER/MAGNUM_V4-Mistral_Small:27b_IQ4_XS` | ~18GB | ❌ no cabe |

- **Primera prueba recomendada**: `12b_Q5_K_M` — mejor calidad dentro del rango seguro
- **Descargar**: `ollama pull LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M`

---

### `DavidAU/Gemma-3-12B-Polaris-Heretic-Uncensored-Thinking` — Gemma 3 con thinking

- **VRAM**: ~8GB (Q4)
- **Por qué**: Gemma 3 12B con **thinking mode** + uncensored (abliterado). DavidAU acaba de sacar esta línea "Heretic-Uncensored-Thinking". Si funciona bien, combina razonamiento con escritura creativa sin restricciones. Muy reciente (6 días en el momento de la investigación).
- **Versión 16B**: `Gemma-3-16b-it-BIG-G-GLM4.7-Flash-Valhalla-Heretic-Uncensored-Deep-Thinking` (~11GB) — aún más capaz
- **Quirk potencial**: Gemma 3 puede devolver los think-blocks en content (a verificar) → `_strip_think_blocks()` ya lo cubre
- **Solo en HF**: descargar GGUF + Modelfile

---

### `DavidAU` MoE uncensored — más parámetros, misma VRAM

- **Modelo**: `Llama-3.2-8X3B-MOE-Dark-Champion-Instruct-uncensored-abliterated-18.4B-GGUF`
- **VRAM efectiva**: ~10-12GB (18.4B total, pero MoE activa ~6B por token)
- **Por qué**: Architecture MoE (Mixture of Experts) — activa solo una fracción de parámetros por inferencia. Da calidad de modelo grande con consumo de modelo pequeño. Diseñado para "fiction writing, roleplay, creative prose — OFF THE SCALE". Uncensored + abliterado.
- **Riesgo**: MoE a veces tiene salidas más inconsistentes. Hay que testear con nuestros prompts específicos.
- **Solo en HF**: `DavidAU/Llama-3.2-8X3B-MOE-Dark-Champion-Instruct-uncensored-abliterated-18.4B-GGUF`

---

### `Salamandra-7B-instruct` (BSC Barcelona) — español nativo institucional

- **VRAM**: ~5GB
- **Por qué**: Desarrollado por el **Barcelona Supercomputing Center** con financiación pública. Entrenado con 2.4 billones de tokens priorizando **español, catalán, gallego y euskera**. El único modelo del listado creado específicamente pensando en el español peninsular, no como adaptación del inglés.
- **Limitación importante**: 7B base — capacidad de instrucción limitada. Puede perder el personaje en prompts complejos. Vale la pena como experimento y para comparar calidad de español.
- **Disponible en Ollama**: `ollama pull hdnh2006/salamandra-7b-instruct` o `ollama pull cas/salamandra-7b-instruct`

---

### `huihui_ai/llama3.3-abliterated:70b-instruct-q2_K` — el único 70B que entra en 16GB
*Encontrado por Kimi en investigación paralela*

- **VRAM**: ~15-16GB (Q2_K — cuantización 2-bit, muy agresiva)
- **Por qué**: Es el único modelo de 70B parámetros que cabe en 16GB. Llama 3.3 abliterado — sin censura + arquitectura grande. La pregunta real para nuestro caso de uso es si un 70B degradado a Q2 supera a un 14B en Q4_K_M. Para textos cortos de 150 palabras probablemente sí en coherencia de personaje, pero el español puede sufrir con Q2.
- **Riesgo real**: Q2_K es la cuantización más agresiva viable. Puede producir frases extrañas, perder el hilo del personaje en prompts complejos, o generar calcos del inglés. **Hay que testear antes de confiar.**
- **Descargar**: `ollama pull huihui_ai/llama3.3-abliterated:70b-instruct-q2_K`
- **Veredicto**: Candidato interesante para benchmark, pero las expectativas deben ser moderadas.

---

### `TheDrummer/Maidona-24B-v4.3` — roleplay especializado 24B
*Encontrado por Kimi en investigación paralela*

- **VRAM**: ~14-15GB (Q4_K_M) — entra cómodo en 16GB
- **Por qué**: TheDrummer es creador reconocido en la comunidad de roleplay. Maidona v4.3 está verificado por la comunidad para consistencia de personaje en textos largos. 24B da más capacidad que los modelos de 14B para mantener la voz del personaje.
- **Cómo instalar**: buscar GGUF en HuggingFace → `TheDrummer/Maidona-24B-v4.3-GGUF` o equivalente + Modelfile en Ollama
- **Pendiente**: verificar disponibilidad exacta del GGUF y si está en Ollama directo

---

### `DavidAU/Llama-3.2-4X3B-MOE` (~10B activo) — MoE pequeño
*Encontrado por Kimi — variante más conservadora del MoE que yo encontré (8X3B)*

- **VRAM efectiva**: ~6-8GB
- **Por qué**: Versión más pequeña del MoE de DavidAU. Activa ~4B parámetros por token pero tiene el contexto completo de un modelo mayor. Menos riesgo de incoherencias que el 8X3B. Uncensored + abliterado, diseñado para creative writing.
- **Solo en HF**: buscar `DavidAU` + `4X3B-MOE` en huggingface.co

---

### `Sao10K/L3.3-70B-Euryale-v2.3` — el flagship RP, para cuando haya más VRAM

- **VRAM**: mínimo ~19GB (IQ2_XXS) — **no cabe en 16GB solo GPU**
- **Por qué documentarlo**: Es el modelo de roleplay más respetado de la comunidad en el rango 70B. Si Perseus consigue más VRAM en el futuro, o si se implementa offload GPU+RAM, es el candidato obvio.
- **Con offload parcial**: Ollama puede usar RAM+GPU. Para críticas cortas (150 palabras) puede ser viable aunque lento (~60-90s).
- **Disponible en Ollama**: `ollama pull nchapman/l3.3-70b-euryale-v2.3`

---

## Tabla resumen completa (ronda 1 + ronda 2)

| Modelo | VRAM | Ollama directo | Think | Uncensored | Prioridad |
|--------|------|----------------|-------|------------|-----------|
| `phi4-reasoning:14b` | 11GB | ✅ | ✅ | ❌ | 🔴 Alta |
| `dolphin3:8b` | 5GB | ✅ | ❌ | ✅ | 🔴 Alta |
| `type32/eva-qwen-2.5-14b` | 9-10GB | ✅ | ❌ | ✅ | 🔴 Alta |
| **`richardyoung/qwen3-14b-abliterated`** | **9GB** | **✅** | **✅** | **✅** | **🔴 Alta — JOYA** |
| `MAGNUM_V4-Mistral_Small:12b` | 9GB | ✅ | ❌ | ❌ | 🔴 Alta |
| `magistral:24b` | ~15-16GB | ✅ | ✅ | ❌ | 🟡 Media |
| `aya-expanse:8b` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `huihui_ai/qwen2.5-abliterate:32b` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media |
| `qwq:32b` (Q3) | ~16GB | ✅ (quant) | ✅ | ❌ | 🟡 Media |
| `hdnh2006/salamandra-7b-instruct` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `Gemma-The-Writer-10B` (DavidAU) | 7GB | ⚠️ HF | ❌ | ✅ | 🟡 Media |
| `Sao10K/14B-Qwen2.5-Kunou-v1` | 9-10GB | ⚠️ HF | ❌ | ❌ | 🟡 Media |
| `Gemma-3-12B-Heretic-Thinking` (DavidAU) | 8GB | ⚠️ HF | ✅ | ✅ | 🟡 Media |
| `DavidAU MoE Dark-Champion 18.4B` | ~10-12GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `RP-INK Qwen2.5-32b` (Q3) | ~14-15GB | ⚠️ HF | ❌ | ⚠️ | 🟢 Baja |
| `Novaciano/SuperUncensored` | ~5GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `L3.3-70B-Euryale-v2.3` | 19GB+ | ✅ (offload) | ❌ | ❌ | 🟢 Futura |

---

## Script de descarga ampliado

```bash
# PRIORIDAD ALTA — todos en Ollama directo
ollama pull phi4-reasoning:14b
ollama pull dolphin3
ollama pull type32/eva-qwen-2.5-14b
ollama pull richardyoung/qwen3-14b-abliterated    # JOYA: qwen3 sin filtros + think
ollama pull LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M

# MEDIA — también directos
ollama pull magistral
ollama pull aya-expanse
ollama pull hdnh2006/salamandra-7b-instruct
ollama pull huihui_ai/qwen2.5-abliterate:32b-instruct

# HuggingFace (requieren descargar GGUF + crear Modelfile)
# DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF  → Q4_K_M
# DevQuasar/Sao10K.14B-Qwen2.5-Kunou-v1-GGUF                    → Q4_K_M
```

---

---

## Ronda 3 — Informe ChatGPT (2026-03-01)
*Evaluación: 4 hallazgos genuinamente nuevos + confirmaciones + relleno descartado*

### Qué confirmó ChatGPT (no añade nada nuevo)
- `huihui_ai/qwen3-abliterated:14b` → nuestra JOYA, ya documentada (publisher diferente, mismo modelo)
- `cas/salamandra-7b-instruct` → mismo modelo que `hdnh2006/salamandra`, ya en ronda 2
- Llama 3.3 70B Q2_K de 26.4GB → ya en Kimi, ChatGPT confirma que no entra en 16GB
- `gpt-oss:latest` → ya está en nuestro sistema y benchmark histórico

### Descartado del informe ChatGPT
- Modelos 2-3B (Aitana, Jamba) — demasiado pequeños para voz consistente en 150 palabras
- `exaone-deep`, `falcon-h1r`, `granite3.2` como generadores — reasoning para math/coding, no RP
- `GLM-4.7-Flash-REAP` — el propio ChatGPT reporta riesgo de gibberish, descartado
- Uncensored Llama 3.1 genéricos (DarkIdol, mannix) — nada que dolphin3 no cubra mejor

---

### `LatitudeGames/Muse-12B-GGUF` ⭐ — el hallazgo más valioso del informe
- **VRAM**: ~7.1GB (Q4_K_M) — muy cómodo
- **Por qué**: LatitudeGames son los creadores de **AI Dungeon** — llevan más de una década especializándose en RP y narrativa interactiva. Muse-12B es su modelo propio, etiquetado explícitamente como "roleplay/text adventure". Base Mistral Nemo, 12B es el punto dulce para voz consistente. Nadie en nuestras rondas anteriores lo tenía.
- **Para Parody Critics**: un modelo construido por gente que vive del roleplay tiene más garantías de mantener la voz del personaje durante 150 palabras que un merge genérico.
- **Descargar**: `ollama run hf.co/LatitudeGames/Muse-12B-GGUF:Q4_K_M`

---

### `tensorblock/L3-8B-Stheno-v3.2-GGUF` — Stheno puro, el referente RP de 8B
- **VRAM**: ~4.58GB (Q4_K_M) — el más ligero de todos los candidatos serios
- **Por qué**: Stheno es de **Sao10K** (el mismo autor que nuestro candidato Kunou-v1). El Stheno v3.2 es su versión más reciente y canónica para RP en 8B. En ronda 1 teníamos un merge Hermes+Stheno (Triangle104) — este es el Stheno directo, más puro y más probado por la comunidad.
- **Limitación conocida**: tiende a alargarse. Ser estricto con el `num_predict` para mantener las 150 palabras.
- **Descargar**: `ollama run hf.co/tensorblock/L3-8B-Stheno-v3.2-GGUF:Q4_K_M`

---

### `sdocio/Llama-3.1-Carballo-Instr3-Q4_K_M-GGUF` — ibérico sobre base fuerte
- **VRAM**: ~5GB (Q4_K_M)
- **Por qué**: Modelo instruido para **gallego, portugués, español, catalán e inglés** sobre base Llama 3.1-8B. Diferente de Salamandra: Salamandra es más nativo en español pero tiene base propia más débil; Carballo usa Llama 3.1 (base más fuerte en instrucción) con finetuning ibérico. Para personajes con voz coloquial muy española, podría superar a ambos.
- **Limitación**: no está afinado para RP explícito — hay que empujar la sátira desde el prompt.
- **Descargar**: `ollama run hf.co/sdocio/Llama-3.1-Carballo-Instr3-Q4_K_M-GGUF`

---

### `bartowski/Lumimaid-Magnum-v4-12B-GGUF` — Magnum v4 con capa RP encima
- **VRAM**: ~8GB (Q4) — cómodo
- **Por qué**: Ya tenemos `LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b` documentado (Magnum v4 base). Esta variante añade **Lumimaid** encima — una capa de fine-tune RP sobre el Magnum. Puede ser la combinación perfecta: prosa estilo Claude (Magnum) + adherencia de personaje (Lumimaid). Vale la pena comparar ambas variantes en benchmark.
- **Limitación**: al combinar dos capas puede volverse verboso. Controlar temperatura y `num_predict`.
- **Descargar**: `ollama run hf.co/bartowski/Lumimaid-Magnum-v4-12B-GGUF:Q4_K_M`

---

## Tabla resumen completa (rondas 1 + 2 + 3)

| Modelo | VRAM | Ollama directo | Think | Uncensored | Prioridad |
|--------|------|----------------|-------|------------|-----------|
| `phi4-reasoning:14b` | 11GB | ✅ | ✅ | ❌ | 🔴 Alta |
| `dolphin3:8b` | 5GB | ✅ | ❌ | ✅ | 🔴 Alta |
| `type32/eva-qwen-2.5-14b` | 9-10GB | ✅ | ❌ | ✅ | 🔴 Alta |
| **`richardyoung/qwen3-14b-abliterated`** | **9GB** | **✅** | **✅** | **✅** | **🔴 Alta — JOYA** |
| `MAGNUM_V4-Mistral_Small:12b` | 9GB | ✅ | ❌ | ❌ | 🔴 Alta |
| **`LatitudeGames/Muse-12B`** | **7GB** | **✅ (HF)** | **❌** | **❌** | **🔴 Alta — RP especialistas** |
| `magistral:24b` | ~15-16GB | ✅ | ✅ | ❌ | 🟡 Media |
| `aya-expanse:8b` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `huihui_ai/qwen2.5-abliterate:32b` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media |
| `qwq:32b` (Q3) | ~16GB | ✅ (quant) | ✅ | ❌ | 🟡 Media |
| `hdnh2006/salamandra-7b-instruct` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `tensorblock/L3-8B-Stheno-v3.2` | 4.6GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `sdocio/Llama-3.1-Carballo-Instr3` | 5GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `bartowski/Lumimaid-Magnum-v4-12B` | 8GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `Gemma-The-Writer-10B` (DavidAU) | 7GB | ⚠️ HF | ❌ | ✅ | 🟡 Media |
| `Sao10K/14B-Qwen2.5-Kunou-v1` | 9-10GB | ⚠️ HF | ❌ | ❌ | 🟡 Media |
| `Gemma-3-12B-Heretic-Thinking` (DavidAU) | 8GB | ⚠️ HF | ✅ | ✅ | 🟡 Media |
| `huihui_ai/llama3.3-abliterated:70b-q2_K` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media (expectativas moderadas) |
| `TheDrummer/Maidona-24B-v4.3` | ~14-15GB | ⚠️ HF | ❌ | ❌ | 🟡 Media |
| `DavidAU MoE Dark-Champion 18.4B` | ~10-12GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `DavidAU/Llama-3.2-4X3B-MOE` | ~6-8GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `RP-INK Qwen2.5-32b` (Q3) | ~14-15GB | ⚠️ HF | ❌ | ⚠️ | 🟢 Baja |
| `Novaciano/SuperUncensored` | ~5GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `L3.3-70B-Euryale-v2.3` | 19GB+ | ✅ (offload) | ❌ | ❌ | 🟢 Futura |

---

## Script de descarga ampliado

```bash
# PRIORIDAD ALTA — todos en Ollama directo o HF directo
ollama pull phi4-reasoning:14b
ollama pull dolphin3
ollama pull type32/eva-qwen-2.5-14b
ollama pull richardyoung/qwen3-14b-abliterated    # JOYA: qwen3 sin filtros + think
ollama pull LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M

# Ronda 3 — nuevos (via hf.co directo en Ollama)
ollama run hf.co/LatitudeGames/Muse-12B-GGUF:Q4_K_M
ollama run hf.co/tensorblock/L3-8B-Stheno-v3.2-GGUF:Q4_K_M
ollama run hf.co/sdocio/Llama-3.1-Carballo-Instr3-Q4_K_M-GGUF
ollama run hf.co/bartowski/Lumimaid-Magnum-v4-12B-GGUF:Q4_K_M

# MEDIA — también directos en Ollama
ollama pull magistral
ollama pull aya-expanse
ollama pull hdnh2006/salamandra-7b-instruct
ollama pull huihui_ai/qwen2.5-abliterate:32b-instruct
ollama pull huihui_ai/llama3.3-abliterated:70b-instruct-q2_K

# HuggingFace (requieren descargar GGUF + crear Modelfile)
# DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF  → Q4_K_M
# DevQuasar/Sao10K.14B-Qwen2.5-Kunou-v1-GGUF                    → Q4_K_M
# TheDrummer/Maidona-24B-v4.3-GGUF                               → Q4_K_M
```

---

---

## Ronda 4 — Informe Perplexity (2026-03-01)
*El más detallado de los tres informes. Mucho solapamiento con rondas anteriores. 2 hallazgos nuevos reales.*

### Qué confirmó Perplexity (ya documentado)
- `richardyoung/qwen3-14b-abliterated` → JOYA, tercera confirmación independiente
- `salamandra-7b-instruct` → ronda 2
- `Carballo-Instr3` → ronda 3 (ChatGPT)
- `anthracite-org/magnum-v4-12b` → mismo modelo que LESSTHANSUPER/MAGNUM_V4, diferente fuente
- Llama 3.3 70B abliterated Q4_K_M → 42GB, imposible en 16GB (descartado en ronda 2)
- `gpt-oss` → ya en el sistema histórico

### Descartado del informe Perplexity
- `DeepHermes-3-3B`, `Reasoning-Llama-3b-v0.1` → 3B, demasiado pequeños para generación principal
- `Aetherwiing/starcannon-12b` → sin GGUF publicado, inviable en Ollama
- `ParasiticRogue/Magnum-Instruct-DPO-12B` → mismo territorio que Inferor (abajo) pero más genérico

---

### `Infermatic/MN-12B-Inferor-v0.0` ⭐ — merge de los top modelos RP de Nemo
- **VRAM**: ~9-11GB (Q4_K_M, fichero ~7.6GB)
- **Por qué**: Merge de los mejores modelos RP sobre Mistral Nemo 12B usando **Model Stock** — una técnica de merging más sofisticada que TIES/SLERP. Combina Magnum V4 12B, Celeste 12B y otros modelos RP top de la comunidad. Diseñado explícitamente para narrativa inmersiva y storytelling de larga duración.
- **Para Parody Critics**: si Muse-12B (LatitudeGames) es el especialista RP con pedigree de empresa, Inferor es el equivalente destilado de la comunidad HuggingFace — ambos son 12B Nemo, ambos RP, pero de filosofías distintas. Vale la pena comparar ambos en benchmark.
- **Limitación conocida**: en contextos >5k tokens puede derivar. Para 150 palabras es irrelevante.
- **GGUF**: `mradermacher/MN-12B-Inferor-v0.0-GGUF`
- **Descargar**: `ollama run hf.co/mradermacher/MN-12B-Inferor-v0.0-GGUF:Q4_K_M`

---

### `vicgalle/Roleplay-Hermes-3-Llama-3.1-8B` — DPO específico de roleplay
- **VRAM**: ~7-9GB (Q4_K_M, fichero ~5-6GB)
- **Por qué**: Fine-tune DPO sobre Hermes-3/Llama-3.1-8B con datasets específicos de roleplay (`Weyaxi humanish DPO` + `NSFW_RP_Format_DPO`). El objetivo declarado es que el modelo suene a persona real y no a asistente genérico — justo el fallo más común en nuestro benchmark. Diferente del `hermes-stheno-8B` merge que teníamos (ese mezclaba Hermes y Stheno, este es Hermes con DPO de RP puro).
- **Para Parody Critics**: candidato para el personaje más difícil del benchmark — si mantiene voz de Alan Turbing sin colapsar en genérico analítico, es un modelo serio a 8B.
- **Limitación**: muy orientado a RP en inglés — necesita ejemplos en español en el prompt.
- **GGUF**: `Triangle104/Roleplay-Hermes-3-Llama-3.1-8B-Q4_K_M-GGUF`
- **Descargar**: `ollama run hf.co/Triangle104/Roleplay-Hermes-3-Llama-3.1-8B-Q4_K_M-GGUF:roleplay-hermes-3-llama-3.1-8b-q4_k_m.gguf`

---

## Tabla resumen completa (rondas 1 + 2 + 3 + 4)

| Modelo | VRAM | Ollama directo | Think | Uncensored | Prioridad |
|--------|------|----------------|-------|------------|-----------|
| `phi4-reasoning:14b` | 11GB | ✅ | ✅ | ❌ | 🔴 Alta |
| `dolphin3:8b` | 5GB | ✅ | ❌ | ✅ | 🔴 Alta |
| `type32/eva-qwen-2.5-14b` | 9-10GB | ✅ | ❌ | ✅ | 🔴 Alta |
| **`richardyoung/qwen3-14b-abliterated`** | **9GB** | **✅** | **✅** | **✅** | **🔴 Alta — JOYA** |
| `MAGNUM_V4-Mistral_Small:12b` | 9GB | ✅ | ❌ | ❌ | 🔴 Alta |
| **`LatitudeGames/Muse-12B`** | **7GB** | **✅ (HF)** | **❌** | **❌** | **🔴 Alta — RP especialistas** |
| `magistral:24b` | ~15-16GB | ✅ | ✅ | ❌ | 🟡 Media |
| `aya-expanse:8b` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `huihui_ai/qwen2.5-abliterate:32b` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media |
| `qwq:32b` (Q3) | ~16GB | ✅ (quant) | ✅ | ❌ | 🟡 Media |
| `hdnh2006/salamandra-7b-instruct` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `tensorblock/L3-8B-Stheno-v3.2` | 4.6GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `sdocio/Llama-3.1-Carballo-Instr3` | 5GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `bartowski/Lumimaid-Magnum-v4-12B` | 8GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| **`Infermatic/MN-12B-Inferor-v0.0`** | **9-11GB** | **✅ (HF)** | **❌** | **❌** | **🟡 Media — RP community top** |
| **`vicgalle/Roleplay-Hermes-3-Llama-3.1-8B`** | **7-9GB** | **✅ (HF)** | **❌** | **⚠️** | **🟡 Media — DPO humanish** |
| `Gemma-The-Writer-10B` (DavidAU) | 7GB | ⚠️ HF | ❌ | ✅ | 🟡 Media |
| `Sao10K/14B-Qwen2.5-Kunou-v1` | 9-10GB | ⚠️ HF | ❌ | ❌ | 🟡 Media |
| `Gemma-3-12B-Heretic-Thinking` (DavidAU) | 8GB | ⚠️ HF | ✅ | ✅ | 🟡 Media |
| `huihui_ai/llama3.3-abliterated:70b-q2_K` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media (expectativas moderadas) |
| `TheDrummer/Maidona-24B-v4.3` | ~14-15GB | ⚠️ HF | ❌ | ❌ | 🟡 Media |
| `DavidAU MoE Dark-Champion 18.4B` | ~10-12GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `DavidAU/Llama-3.2-4X3B-MOE` | ~6-8GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `RP-INK Qwen2.5-32b` (Q3) | ~14-15GB | ⚠️ HF | ❌ | ⚠️ | 🟢 Baja |
| `Novaciano/SuperUncensored` | ~5GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `L3.3-70B-Euryale-v2.3` | 19GB+ | ✅ (offload) | ❌ | ❌ | 🟢 Futura |

---

## Script de descarga ampliado

```bash
# PRIORIDAD ALTA — todos en Ollama directo o HF directo
ollama pull phi4-reasoning:14b
ollama pull dolphin3
ollama pull type32/eva-qwen-2.5-14b
ollama pull richardyoung/qwen3-14b-abliterated    # JOYA: qwen3 sin filtros + think
ollama pull LESSTHANSUPER/MAGNUM_V4-Mistral_Small:12b_Q5_K_M

# Ronda 3 (ChatGPT) — via hf.co directo
ollama run hf.co/LatitudeGames/Muse-12B-GGUF:Q4_K_M
ollama run hf.co/tensorblock/L3-8B-Stheno-v3.2-GGUF:Q4_K_M
ollama run hf.co/sdocio/Llama-3.1-Carballo-Instr3-Q4_K_M-GGUF
ollama run hf.co/bartowski/Lumimaid-Magnum-v4-12B-GGUF:Q4_K_M

# Ronda 4 (Perplexity) — via hf.co directo
ollama run hf.co/mradermacher/MN-12B-Inferor-v0.0-GGUF:Q4_K_M
ollama run hf.co/Triangle104/Roleplay-Hermes-3-Llama-3.1-8B-Q4_K_M-GGUF:roleplay-hermes-3-llama-3.1-8b-q4_k_m.gguf

# MEDIA — también directos en Ollama
ollama pull magistral
ollama pull aya-expanse
ollama pull hdnh2006/salamandra-7b-instruct
ollama pull huihui_ai/qwen2.5-abliterate:32b-instruct
ollama pull huihui_ai/llama3.3-abliterated:70b-instruct-q2_K

# HuggingFace (requieren descargar GGUF + crear Modelfile)
# DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored-GGUF  → Q4_K_M
# DevQuasar/Sao10K.14B-Qwen2.5-Kunou-v1-GGUF                    → Q4_K_M
# TheDrummer/Maidona-24B-v4.3-GGUF                               → Q4_K_M
```

---

## Ronda 5 — Informe DeepSeek (2026-03-01)
*El más flojo de los cuatro. 2 hallazgos reales + 1 en baja prioridad. Mucho relleno sin GGUF.*

### Descartado del informe DeepSeek
- MoE sin GGUF (`jsfs11-MixtureofMerges`, `CognitiveFusion2`, `Multilingual-mistral`) → requieren conversión manual desde safetensors, inviable en la práctica
- Novaciano 1B → demasiado pequeño para voz consistente en 150 palabras
- Llama 3.3 70B abliterated → ya en nuestra tabla (ronda 2, Kimi), confirmado Q2_K con expectativas moderadas

---

### `invisietch/MiS-Firefly-v0.2-22B` ⭐ — el 22B más cómodo en 16GB
- **VRAM**: ~13GB (Q4_K_M) — entra con margen en 16GB
- **Por qué**: Fine-tune de **Mistral Small 22B** específicamente para creative writing y roleplay. "Largely uncensored", probado hasta 16k de contexto con "amplia competencia y coherencia". 22B es un salto de calidad real respecto a todos los candidatos de 12-14B — si cabe en VRAM con margen, es el punto dulce para voces complejas sostenidas.
- **Para Parody Critics**: candidato directo para los personajes más difíciles del benchmark (Alan Turbing, El Gran Lebowski). Si lo clava a 22B cuando los 12B fallan, tenemos nuestro modelo de producción para casos límite.
- **Sin pull directo** — descargar GGUF desde HF + Modelfile
- **GGUF**: `invisietch/MiS-Firefly-v0.2-22B-Q4_K_M-GGUF`

---

### `DavidAU/L3.1-RP-Hero-InBetween-8B-GGUF` — DavidAU dedicado a RP
- **VRAM**: ~5-6GB (Q4_K_M) — muy ligero
- **Por qué**: DavidAU (conocemos al autor: Gemma-The-Writer, MoE Dark-Champion) con un modelo dedicado **exclusivamente a roleplay** sobre Llama 3.1-8B. Énfasis en "prosa vívida", detalles y seguimiento de instrucciones descrito como "relativamente a prueba de balas". Más ligero que los candidatos de 12B pero con foco RP más afilado.
- **Para Parody Critics**: candidato para benchmark de velocidad — si a 8B específico de RP clava la voz mejor que genéricos de 12B, es el modelo ideal para el secondary endpoint siempre cargado.
- **Sin pull directo** — descargar GGUF desde HF + Modelfile
- **GGUF**: `DavidAU/L3.1-RP-Hero-InBetween-8B-GGUF`

---

### `Delta-Vector/Archaeo-12B-GGUF` — SLERP de bases poco conocidas
- **VRAM**: ~7-8GB (Q4_K_M)
- **Por qué**: Merge SLERP de Rei-12B y Francois-Huali-12B para creative writing y RP. Las bases no son modelos de referencia de la comunidad — es una apuesta más arriesgada que Inferor o Muse.
- **Sin pull directo** — descargar GGUF + Modelfile
- **Prioridad**: Baja — solo testear si los 12B conocidos no convencen

---

## Tabla resumen completa (rondas 1–5)

| Modelo | VRAM | Ollama directo | Think | Uncensored | Prioridad |
|--------|------|----------------|-------|------------|-----------|
| `phi4-reasoning:14b` | 11GB | ✅ | ✅ | ❌ | 🔴 Alta |
| `dolphin3:8b` | 5GB | ✅ | ❌ | ✅ | 🔴 Alta |
| `type32/eva-qwen-2.5-14b` | 9-10GB | ✅ | ❌ | ✅ | 🔴 Alta |
| **`richardyoung/qwen3-14b-abliterated`** | **9GB** | **✅** | **✅** | **✅** | **🔴 Alta — JOYA** |
| `MAGNUM_V4-Mistral_Small:12b` | 9GB | ✅ | ❌ | ❌ | 🔴 Alta |
| **`LatitudeGames/Muse-12B`** | **7GB** | **✅ (HF)** | **❌** | **❌** | **🔴 Alta — RP especialistas** |
| **`invisietch/MiS-Firefly-v0.2-22B`** | **13GB** | **⚠️ HF** | **❌** | **✅** | **🔴 Alta — 22B RP Mistral Small** |
| `magistral:24b` | ~15-16GB | ✅ | ✅ | ❌ | 🟡 Media |
| `aya-expanse:8b` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `huihui_ai/qwen2.5-abliterate:32b` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media |
| `qwq:32b` (Q3) | ~16GB | ✅ (quant) | ✅ | ❌ | 🟡 Media |
| `hdnh2006/salamandra-7b-instruct` | 5GB | ✅ | ❌ | ❌ | 🟡 Media |
| `tensorblock/L3-8B-Stheno-v3.2` | 4.6GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `sdocio/Llama-3.1-Carballo-Instr3` | 5GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `bartowski/Lumimaid-Magnum-v4-12B` | 8GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `Infermatic/MN-12B-Inferor-v0.0` | 9-11GB | ✅ (HF) | ❌ | ❌ | 🟡 Media |
| `vicgalle/Roleplay-Hermes-3-Llama-3.1-8B` | 7-9GB | ✅ (HF) | ❌ | ⚠️ | 🟡 Media |
| `DavidAU/L3.1-RP-Hero-InBetween-8B` | 5-6GB | ⚠️ HF | ❌ | ✅ | 🟡 Media |
| `Gemma-The-Writer-10B` (DavidAU) | 7GB | ⚠️ HF | ❌ | ✅ | 🟡 Media |
| `Sao10K/14B-Qwen2.5-Kunou-v1` | 9-10GB | ⚠️ HF | ❌ | ❌ | 🟡 Media |
| `Gemma-3-12B-Heretic-Thinking` (DavidAU) | 8GB | ⚠️ HF | ✅ | ✅ | 🟡 Media |
| `huihui_ai/llama3.3-abliterated:70b-q2_K` | ~16GB | ✅ | ❌ | ✅ | 🟡 Media (expectativas moderadas) |
| `TheDrummer/Maidona-24B-v4.3` | ~14-15GB | ⚠️ HF | ❌ | ❌ | 🟡 Media |
| `DavidAU MoE Dark-Champion 18.4B` | ~10-12GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `DavidAU/Llama-3.2-4X3B-MOE` | ~6-8GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `RP-INK Qwen2.5-32b` (Q3) | ~14-15GB | ⚠️ HF | ❌ | ⚠️ | 🟢 Baja |
| `Novaciano/SuperUncensored` | ~5GB | ⚠️ HF | ❌ | ✅ | 🟢 Baja |
| `Delta-Vector/Archaeo-12B` | 7-8GB | ⚠️ HF | ❌ | ❌ | 🟢 Baja |
| `L3.3-70B-Euryale-v2.3` | 19GB+ | ✅ (offload) | ❌ | ❌ | 🟢 Futura |

---

## Siguiente paso tras descargar

Correr el benchmark estándar (ver `docs/benchmark-nuevos-modelos.md`) contra los 8 personajes × 4 películas y añadir los perfiles confirmados a `api/model_profiles.py`.

El criterio de éxito: **rating coherente con el texto + voz de personaje mantenida durante 150 palabras**.
