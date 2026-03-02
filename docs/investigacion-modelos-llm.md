# Investigación Interna — Modelos LLM para Parody Critics

**Período**: 2026-02-28 → 2026-03-02
**Hardware de prueba**: Omnius — RTX 5060 Ti 16GB VRAM @ 192.168.2.69:11434
**Protocolo**: 8 personajes canónicos × 4 películas canónicas = 32 críticas por modelo
**Resultados completos**: `docs/benchmark-results/` (`.md` + `.json` por modelo)

---

## Lo que aprendimos

### 1. Parámetros vs Fine-tuning: el hallazgo clave

El descubrimiento más importante de esta investigación no es qué modelo ganó, sino **por qué**.

**La ley de escalado funciona**: a más parámetros, mayor capacidad de seguir instrucciones complejas.
La lógica ideológica que necesitamos ("Adolf odia el cine coreano por razones racistas, por tanto
Parásitos = 1/10") requiere razonamiento multi-paso encadenado. Los modelos pequeños lo simplifican
al patrón de sus datos de entrenamiento: "crítica de película = ~7/10".

| Rango | Modelos | Calibración ideológica |
|-------|---------|------------------------|
| 4-8B | dolphin3, deepseek-r1, phi4 | Baja-media (sesgo hacia 7/10 o exceso negativo) |
| 12B | muse-12b, magnum-v4 | Pésima (ver punto 2) |
| 14B | eva-qwen, qwen3, phi4 | Buena si el modelo base es sólido |
| 24B | mistral-small3.1 | Muy buena |
| 27B | gemma3 | Excelente |

**Pero los parámetros no lo son todo.** muse-12b (12B) es peor que eva-qwen (14B) a pesar de ser
de tamaño similar. La diferencia está en el fine-tuning.

---

### 2. El problema de los fine-tunes narrativos (RP models)

`muse-12b` y `MAGNUM_V4-Mistral_Small` son fine-tunes especializados en **roleplay y narrativa**.
Escriben prosa preciosa, mantienen voces de personajes, son fluidos y creativos. Pero tienen un
problema fatal para nuestro caso de uso:

**El fine-tune RP sobreescribe el instruction-following.**

Durante su entrenamiento se les enseñó implícitamente que el objetivo es "escribir bonito en primera
persona". Nadie les pidió jamás razonar sobre por qué un personaje fascista odiaría el cine coreano.
El resultado: ratings planos alrededor de 7/10 independientemente del personaje o la película.
El texto suena en personaje, pero el número sale del promedio estadístico de críticas de cine.

**Analogía**: es como coger a un actor de método excelente y pedirle que sea juez en un tribunal.
El papel lo borda. La sentencia, no.

**Consecuencia práctica**: muse-12b y magnum-v4 son útiles como referencia de calidad narrativa,
pero no sirven para producción mientras el rating ideológico sea el core del sistema.

---

### 3. Think mode: ayuda pero tiene coste

Los modelos con think mode (`qwen3:14b`, `deepseek-r1:8b`) razonan antes de responder. En teoría
esto debería mejorar la calibración ideológica. En la práctica tiene trade-offs:

**Pros:**
- Mayor coherencia entre texto y rating
- Encadenamiento ideológico más explícito

**Contras:**
- Los tokens de thinking consumen el budget de `num_predict`
- Con 4096 tokens: ~2000-3000 thinking + ~100-150 respuesta → textos muy cortos
- `qwen3:14b` producía críticas de ~100 palabras (apenas sobre el mínimo de 40)
- Sesgo: el razonamiento interno tiende a sobreponderar los aspectos negativos → todos los personajes
  acaban siendo demasiado críticos

**Lección**: para generación de texto creativo, think mode no es necesariamente mejor.
Un modelo base grande bien entrenado (gemma3:27b, mistral-small3.1:24b) sin thinking supera
a un modelo más pequeño con thinking.

---

### 4. VRAM y spillover a CPU

La RTX 5060 Ti tiene 16GB de VRAM. Esto define qué modelos son viables:

| Situación | Ejemplo | VRAM usada | Velocidad | Veredicto |
|-----------|---------|------------|-----------|-----------|
| Cabe entero | phi4:latest (8GB) | 8GB | ~60 tok/s | ✅ Óptimo |
| Spillover pequeño | gemma3:27b (18.5GB) | 14.5GB + 4GB CPU | ~15 tok/s | ⚠️ Lento pero viable |
| Spillover grande | qwen3.5:27b (22.5GB) | 12.9GB + 10.6GB CPU | ~5 tok/s | ❌ Inviable |
| No cabe | qwen3.5:35b (23GB+) | — | — | ❌ Inviable |

**Ollama siempre usa algo de VRAM para el KV cache** (el contexto activo), por eso un modelo de
16GB no cabe exactamente en 16GB de VRAM — hay que dejar margen.

**Regla práctica**: modelo viable = tamaño GGUF ≤ 14GB para dejar margen al KV cache.
gemma3:27b (16GB GGUF) pasa con 4GB spillover — lento pero funcional. qwen3.5:27b (22.5GB) no pasa.

---

### 5. El bug de hf.co/ en Ollama

Los modelos descargados con la URL `hf.co/user/model:tag` en Ollama tienen un bug conocido:
Ollama no les asigna GPU layers correctamente → carga ~2GB en VRAM (funciona por CPU) → 1.4 tok/s.

**Fix probado y funcionando** (aplicado a muse-12b):
```bash
# 1. Localizar el blob del modelo
ls /opt/ollama/models/llm/blobs/

# 2. Hard link del blob a un path local
ln /opt/ollama/models/llm/blobs/sha256-XXX /opt/ollama/models/llm/muse-12b/muse-12b.gguf

# 3. Crear Modelfile local
cat > /tmp/Modelfile_muse << 'EOF'
FROM /opt/ollama/models/llm/muse-12b/muse-12b.gguf
PARAMETER num_gpu 999
EOF

# 4. Registrar con nombre limpio
ollama create muse-12b -f /tmp/Modelfile_muse
```

Resultado: muse-12b pasó de 1890MB VRAM (23%, CPU) → 8611MB VRAM (100% GPU) → de 200s a 7s por crítica.

---

### 6. phi4-reasoning: el falso positivo

`phi4-reasoning:14b` aparecía como candidato prometedor (reasoning distilado de o3-mini).
Descartado por razón técnica específica:

Ollama no soporta el parámetro `think` para este modelo. Genera el razonamiento **dentro del campo
`content`** en lugar del campo `thinking` separado. Esto significa que los ~1000-3000 tokens de
razonamiento consumen directamente el `num_predict`, dejando apenas tokens para la respuesta.

Con `num_predict=1200`: Adolf + Parásitos tomó **20 minutos** para producir una crítica de ~100 palabras.
Inviable a cualquier escala.

---

## Resultados Benchmark — Tabla Maestra de Ratings

> Personajes: Mark Hamill (MH), Po (Po), Adolf Histeric (AH), Rosario Costras (RC),
> Elon Musaka (EM), Alan Turbing (AT), El Gran Lebowski (GL), Lloyd Kaufman (LK)
> Películas: SW=Star Wars UJ, Pa=Parásitos, Re=El resplandor, So=Soul

### Expectativas ideológicas

| Personaje | SW | Parásitos | Resplandor | Soul | Razón |
|-----------|-----|-----------|------------|------|-------|
| Mark Hamill | **bajo** | alto | alto | medio | Odia lo que hicieron con Luke |
| Po | alto | medio | **bajo** | **muy alto** | Todo es bonito excepto el miedo |
| Adolf Histeric | **bajo** | **muy bajo** | bajo | **muy bajo** | Rey→mujer, Parásitos→Korea, Soul→jazz negro |
| Rosario Costras | alto | alto | **bajo** | **alto** | Feminista, adora Soul y diversidad |
| Elon Musaka | **bajo** | **muy bajo** | medio | bajo | SW=woke, Parásitos=comunismo |
| Alan Turbing | medio | **alto** | **alto** | medio | Aprecia estructura y lógica cinematográfica |
| El Gran Lebowski | bajo | **alto** | alto | medio | Anti-blockbuster, adora cine alternativo |
| Lloyd Kaufman | **muy bajo** | **muy alto** | bajo | bajo | Anti-Hollywood, adora cine independiente |

### Resultados reales por modelo

| Modelo | MH·SW | AH·Pa | AH·So | RC·Re | EM·Pa | GL·Pa | LK·SW | LK·Pa |
|--------|-------|-------|-------|-------|-------|-------|-------|-------|
| *Esperado* | *bajo* | *bajo* | *bajo* | *bajo* | *bajo* | *alto* | *bajo* | *alto* |
| muse-12b | 7 ❌ | 3 ✅ | 7 ❌ | 7 ❌ | 7 ❌ | 8 ✅ | 7 ❌ | 7 |
| magnum-v4 | 7 ❌ | 7 ❌ | 7 ❌ | 7 ❌ | 3 ✅ | 7 | 9 ❌ | 4 ❌ |
| eva-qwen | 4 ✅ | 4 ✅ | 10 🤩 | 1 ✅ | 7 ❌ | 6 | 5 | 9 ✅ |
| qwen3-abl | 3 ✅ | 6 ❌ | 6 ❌ | 7 ❌ | 3 ✅ | 3 ❌ | 1 ✅ | 7 |
| qwen3:14b | 1 ✅ | 1 ✅ | 3 ✅ | 2 ✅ | 2 ✅ | 2 ❌ | 1 ✅ | 2 ❌ |
| phi4 | 1 ✅ | — | — | 1 ✅ | 2 ✅ | 3 ❌ | 1 ✅ | 7 |
| deepseek-r1 | 2 ✅ | 6 ❌ | 2 ✅ | 6 ❌ | 2 ✅ | 2 ❌ | 2 ✅ | 2 ❌ |
| mistral-small | 1 ✅ | 1 ✅ | 1 ✅ | 5 | 2 ✅ | — | 1 ✅ | 8 ✅ |
| gemma3:27b | 1 ✅ | 1 ✅ | 1 ✅ | 2 ✅ | 2 ✅ | 3 ❌ | 1 ✅ | 3 ❌ |

**Notas:**
- `eva-qwen`: Adolf da 10/10 a Soul — ideológicamente brillante (reinterpreta el jazz negro como
  oda a la "disciplina de la raza superior"). El mejor ejemplo de calibración creativa.
- `qwen3:14b`: el thinking mode produce calibración correcta pero textos muy cortos (~100w) por
  consumo de tokens en el bloque de razonamiento.
- `gemma3:27b`: calibración perfecta en Adolf y Elon, pero Lebowski y Lloyd no reconocen Parásitos
  como cine alternativo (3/10 cuando deberían ser 7-8/10). Pendiente revisión con prompt mejorado.

---

## Veredictos finales

### Producción actual (RTX 5060 Ti 16GB)

**Modelo principal recomendado**: `type32/eva-qwen-2.5-14b:latest`
- 32/32 OK, ~8s/crítica, 7GB VRAM
- Mejor balance velocidad-calidad-fiabilidad
- Calibración ideológica buena sin ser extrema
- Fácil `ollama pull`

**Alternativa calidad**: `mistral-small3.1:24b`
- 30/32 OK, ~20s/crítica, 14GB VRAM
- Calibración ideológica más fuerte (Adolf/Elon perfectos)
- Más lento, puede causar timeout en UI si el usuario no tiene paciencia
- Bueno para generación en batch

**Fallback rápido**: `phi4:latest`
- 32/32 OK, ~7s/crítica, 8GB VRAM
- Algunos personajes con sesgo negativo excesivo (Alan, Lebowski)
- Sólido como backup

### Futuro (2x RTX 5060 Ti o upgrade GPU)

**Modelo ideal**: `gemma3:27b`
- Actualmente: ~70s/crítica (4GB spillover a CPU)
- Con 32GB VRAM: ~8-10s/crítica, calibración perfecta
- Es el modelo que hay que apuntar para la siguiente generación de hardware

**También interesantes con más VRAM**: `qwen3.5:27b`, `qwen3.5:35b` (pendiente benchmark)

### Descartados

| Modelo | Razón | ¿Revisar? |
|--------|-------|-----------|
| `dolphin3` | Flat 7/10, no sigue ideología | No |
| `phi4-reasoning:14b` | 20min/crítica por bug think en Ollama | Con Ollama actualizado |
| `qwen3:14b` think=True | Textos cortos, sesgo negativo | Con num_predict=8192 |
| `muse-12b`, `magnum-v4` | RP fine-tune sobreescribe instruction-following | Como voice reference |
| `qwen3.5:27b/35b` | CPU spillover inviable, 10GB+ en RAM | Con 2x GPU |

---

## Configuración técnica por modelo (`api/model_profiles.py`)

```python
# Modelos de producción recomendados
"type32/eva-qwen-2.5-14b:latest": ModelProfile(
    think=False, temperature=0.75, num_predict=600, system_in_user=False
)
"mistral-small3.1:24b": ModelProfile(
    think=False, temperature=0.75, num_predict=600, system_in_user=False
)
"phi4:latest": ModelProfile(
    think=False, temperature=0.70, num_predict=600, system_in_user=False
)

# Pendientes de re-benchmark con prompt mejorado
"richardyoung/qwen3-14b-abliterated:latest": ModelProfile(
    think=False, temperature=0.65, num_predict=2000, system_in_user=False
    # num_predict=2000 necesario — el modelo quiere escribir 500-600w
)
"gemma3:27b": ModelProfile(
    think=False, temperature=0.75, num_predict=600, system_in_user=False
)

# Think mode — solo para producción con budget adecuado
"qwen3:14b": ModelProfile(
    think=True, temperature=0.60, num_predict=4096, system_in_user=False
    # Considerar num_predict=8192 para respuestas más largas
)
```

---

## Test de película 2026 — validación del contexto enriquecido

**Fecha**: 2026-03-02
**Objetivo**: Verificar que el sistema de enriquecimiento via DuckDuckGo permite a los modelos
generar críticas coherentes de películas fuera de su training cutoff.
**Película**: *28 años después: El templo de los huesos* (tmdb: 1272837, dir. Nia DaCosta, 2026)
**Resultado completo**: `docs/benchmark-results/TEST_2026_templo_huesos_2026-03-02_0957.md`
**Script**: `test_new_film.py`

### Metodología

Los tres modelos top se enfrentaron a una película de 2026 que ninguno puede conocer por training.
El contexto enriquecido (fetcheado por DuckDuckGo el 2026-02-27) contiene: director, reparto completo,
keywords del argumento (satanism, satanist, zombie apocalypse, survival horror, northumberland) y
snippets sociales de Letterboxd.

Si los modelos mencionan estos datos en las críticas, el pipeline de contexto está funcionando.

### Ratings obtenidos

| Personaje | phi4 | eva-qwen | mistral-small | Esperado |
|-----------|------|----------|---------------|---------|
| Mark Hamill | 8 🔍 | 3 | 9 🔍 | medio-alto (aprecia el género) |
| Po | 1 🔍 | **10** 🔍 | 1 | alto (emoción y aventura) |
| Adolf Histeric | 1 🔍 | 4 🔍 | 1 🔍 | bajo (directora mujer, culto satánico) |
| Rosario Costras | 3 🔍 | 7 🔍 | 7 🔍 | medio (horror violento ≠ feminista) |
| Elon Musaka | 2 | 7 🔍 | 1 🔍 | bajo-medio |
| Alan Turbing | 3 🔍 | 7 🔍 | 3 🔍 | medio (aprecia estructura narrativa) |
| El Gran Lebowski | 2 🔍 | 3 🔍 | 3 🔍 | medio (no es su género favorito) |
| Lloyd Kaufman | 1 🔍 | 4 🔍 | 7 🔍 | alto (horror de bajo presupuesto es su mundo) |

🔍 = la crítica menciona datos específicos del contexto enriquecido

### Conclusiones

**✅ El pipeline de enriquecimiento funciona — confirmado.**

21 de 24 críticas (87.5%) mencionaron datos concretos que los modelos solo pueden saber por el
contexto inyectado: Ralph Fiennes, Jack O'Connell, Alfie Williams, Nia DaCosta como directora,
y la keyword `satanism` — elementos del argumento que ningún modelo conoce de su training.

Los casos más llamativos:
- Rosario menciona el culto satánico como elemento perturbador para su ideología feminista
- Elon lo usa para rechazar la película por "nihilismo anticapitalista"
- mistral-small cita los tres actores del reparto + directora + satanism en la misma crítica

**⚠️ Solo 3 críticas sin referencias al contexto** (Po×phi4, Po×mistral, Mark×eva-qwen).
Son los personajes que generan críticas más emocionales/reactivas en lugar de analíticas —
no necesitan nombrar al reparto para estar en personaje.

**Calibración ideológica sobre película desconocida**: consistente con los benchmarks previos.
Adolf da 1/10 en 2 de 3 modelos. Lloyd da ratings bajos en phi4/eva pero 7/10 en mistral
(mistral entiende que Lloyd aprecia el horror de género). Ningún modelo "inventa" datos de la
película ni confunde esta secuela de 2026 con la original de 2002.

### Nota técnica

El detector de contexto en `test_new_film.py` busca coincidencias de cast, director y keywords
en el texto generado. Es una heurística simple — una mención de "Fiennes" cuenta como hit.
No mide calidad de uso del contexto (podría mencionar el nombre pero ignorar el argumento),
pero es suficiente para confirmar que el contexto llega al modelo y se usa.

---

## Próximos pasos de investigación

1. **Fix del prompt de calibración de ratings** — el problema de flat 7s y sesgo negativo es
   principalmente de prompt, no de modelo. Una rúbrica explícita con ejemplos por personaje
   debería elevar todos los modelos. Re-benchmark top 3 después del fix.

2. **qwen3-abliterated con num_predict=2000** — ya actualizado en model_profiles.py.
   Re-benchmark para ver si Rosario mejora con textos completos.

3. **Salamandra 7B** — único modelo entrenado nativamente en español. Vale la pena testear
   la naturalidad del output aunque la calibración ideológica sea peor.

4. **gemma3:27b con prompt mejorado** — actualmente falla en Lebowski+Parásitos y Lloyd+Parásitos.
   Con rúbrica explícita podría alcanzar calibración perfecta.

5. **Hardware**: segunda RTX 5060 Ti 16GB → gemma3:27b como modelo principal en producción.
