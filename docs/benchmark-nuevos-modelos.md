# Parody Critics — Procedimiento de Benchmark para Nuevos Modelos
*Referencia interna de desarrollo*

---

## Visión general

Cada modelo nuevo pasa por 4 fases antes de ser considerado candidato de producción:

```
FASE 1: Verificación      →  ¿El modelo está cargado? ¿Qué perfil aplica?
FASE 2: Smoke test        →  3 combos deliberadamente difíciles (voz vs. contenido opuesto)
FASE 3: Benchmark 8×4     →  8 personajes × 4 películas = 32 críticas
FASE 4: Decisión final    →  Profile confirmado o descartado
```

---

## Personajes canónicos del benchmark

Usar siempre los mismos 6 para comparar modelos entre sí. Elegidos para cubrir el
espectro completo de dificultad: voz simple, voz densa, extremos ideológicos opuestos,
nihilismo y trolleo.

| Slug (DB) | Nombre exacto en API | Arquetipo | Dificultad | Qué estresa en el modelo |
|-----------|---------------------|-----------|-----------|--------------------------|
| `mark_hamill` | `Mark Hamill` | nostálgico | Media | Voz emotiva + referencias culturales precisas |
| `po_teletubbie` | `Po (Teletubbie Rojo)` | ingenuo_entusiasta | Alta | Consistencia de voz infantil ante contenido oscuro |
| `adolf_histeric` | `Adolf Histeric` | fanático_ideológico | Alta | NUNCA block estricto + red_flags ideológicos |
| `rosario_costras` | `Rosario Costras` | woke | Alta | **Espejo ideológico de Adolf** — el modelo NO debe sangrar entre ambos |
| `elon_musaka` | `Elon Musaka` | troll | Media | Ratings extremos con lógica interna coherente |
| `alan_turbing` | `Alan Turbing` | intelectual | Muy alta | Voz analítica densa sin caer en genérico |
| `lebowsky` | `El Gran Lebowski` | nihilista | Muy alta | Apatía coherente — difícil de no hacer "simpático" |
| `lloyd_kaufman` | `Lloyd Kaufman` | fanático_ideológico | **Extrema** | **Lógica de rating paradójica** — presupuesto alto = nota baja |

> **Fallo característico por personaje:**
> - Alan Turbing → voz genérica sentimental (el modelo "se emociona" donde debería analizar)
> - El Gran Lebowski → se vuelve simpático en vez de apático
> - Rosario vs. Adolf → sangrado ideológico entre ambos (Adolf suena "un poco woke" o viceversa)
> - Lloyd Kaufman → el modelo sube la nota a películas de gran presupuesto por inercia de entrenamiento

## Películas canónicas del benchmark

```bash
# Ver IDs disponibles en la DB:
sqlite3 database/critics.db "SELECT tmdb_id, title, year FROM media ORDER BY id LIMIT 20"
```

Las 4 referencias del benchmark original (benchmark_modelos.md):

| Película | TMDB ID | Por qué es útil |
|----------|---------|-----------------|
| Star Wars: Los últimos Jedi | `181808` | Genera reacción fuerte en nostálgicos |
| El Resplandor | `694` | Clásico de culto: prueba conocimiento cinéfilo |
| Parásitos | `496243` | Política + conflicto de clases: activa ideológicos |
| Soul | `508442` | Emocional + woke trigger: activa trolls y woke |

> Si alguna no está en la DB, añadirla primero via sync o búsqueda en el frontend.

---

## FASE 1: Verificación previa

### 1a. Confirmar que el modelo está cargado en Ollama

```bash
curl http://192.168.2.69:11434/api/tags | python3 -m json.tool | grep '"name"'
```

Buscar el modelo nuevo en la lista. Si no aparece:
```bash
ollama pull nombre-modelo:tag
```

### 1b. Verificar qué perfil aplica el sistema

```bash
cd /home/paul/workspace/claude/parody-critics-api
source venv/bin/activate

python3 -c "
import sys; sys.path.insert(0, 'api')
from model_profiles import get_profile
p = get_profile('nombre-modelo:tag')
print(vars(p))
"
```

**Interpretar resultado:**
- `think=True` → modelo reasoning (qwen3, deepseek-r1, phi4-reasoning) — necesita `num_predict` 4096+
- `think=False` → modelo estándar — 600 tokens suele ser suficiente
- `system_in_user=True` → solo deepseek y derivados — system prompt va en user message
- Si el perfil es heurístico (modelo no en PROFILES), verificar que los valores sean razonables

### 1c. Confirmar que el modelo responde a Ollama directamente

```bash
curl -s http://192.168.2.69:11434/api/chat -d '{
  "model": "nombre-modelo:tag",
  "messages": [{"role": "user", "content": "Di solo: OK"}],
  "stream": false,
  "think": false
}' | python3 -c "import sys,json; r=json.load(sys.stdin); print(r['message']['content'])"
```

Debe devolver algo breve. Si da error de modelo → no está cargado.

---

## FASE 2: Smoke test

Arrancar el servidor si no está corriendo:
```bash
cd /home/paul/workspace/claude/parody-critics-api
# En .env cambiar: LLM_PRIMARY_MODEL=nombre-modelo:tag
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Los 3 combos del smoke test

Elegidos para crear **tensión deliberada** entre la voz del personaje y el contenido de la
película. Son los combos donde los modelos débiles fallan más rápido.

```bash
# Combo 1 — Ideológico fuerte: activa red_flags y NUNCA block
curl -s -X POST "http://localhost:8000/api/generate/critic/496243?character=Adolf%20Histeric" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Rating: {d.get('rating')}\\n{d.get('review','')[:300]}\")"

# Combo 2 — Voz infantil vs. film de terror: máxima tensión de tono
curl -s -X POST "http://localhost:8000/api/generate/critic/694?character=Po%20(Teletubbie%20Rojo)" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Rating: {d.get('rating')}\\n{d.get('review','')[:300]}\")"

# Combo 3 — Voz intelectual vs. film emocional: el más difícil de mantener sin colapsar
curl -s -X POST "http://localhost:8000/api/generate/critic/508442?character=Alan%20Turbing" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"Rating: {d.get('rating')}\\n{d.get('review','')[:300]}\")"
```

**Por qué estos 3:**
- **Adolf + Parásitos**: política de clases activa sus red_flags directamente — fácil de verificar coherencia
- **Po + El Resplandor**: voz simple e infantil aplicada a horror psicológico puro — si el modelo la mantiene, controla la voz
- **Alan Turbing + Soul**: voz analítica ante un film diseñado para emocionar — los modelos mediocres capititulan en genérico sentimental

**Checklist mínimo (por cada combo):**

- [ ] Responde sin error HTTP (200 OK)
- [ ] `rating` presente y es número 1-10
- [ ] `review` tiene texto coherente — sin `<think>` tags, sin JSON visible
- [ ] Voz del personaje recognoscible — no suena a crítica genérica
- [ ] Logs muestran `[profile: nombre-modelo think=X temp=Y]`

Si el smoke test falla con error de servidor → revisar logs con:
```bash
tail -f logs/app.log | grep -E "ERROR|profile:|think="
```

> **Decisión de smoke test:** si 2 de 3 combos pasan el checklist, proceder al benchmark completo.
> Si falla el Combo 3 (Alan Turbing), anotar — es el indicador más predictivo de calidad general.

---

## FASE 3: Benchmark 8×4

32 críticas en total. El elenco cubre el espectro completo: voz simple, voz densa,
ideología izquierda, ideología derecha, nihilismo, trolleo, análisis puro y
lógica de rating paradójica. Un modelo que los clava a todos, es candidato de producción.

### Script de benchmark

```bash
#!/bin/bash
# benchmark_run.sh — ejecutar todas las combinaciones

MODEL="nombre-modelo:tag"   # <-- cambiar aquí
API="http://localhost:8000"
LOG="benchmark_${MODEL//[:\/]/_}_$(date +%Y%m%d_%H%M).log"

CHARACTERS=(
  "Mark Hamill"
  "Po (Teletubbie Rojo)"
  "Adolf Histeric"
  "Rosario Costras"
  "Elon Musaka"
  "Alan Turbing"
  "El Gran Lebowski"
  "Lloyd Kaufman"
)

MOVIES=(
  "181808:Star Wars: Los últimos Jedi"
  "496243:Parásitos"
  "694:El Resplandor"
  "508442:Soul"
)

echo "=== BENCHMARK: $MODEL ===" | tee "$LOG"
echo "Fecha: $(date)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

for CHARACTER in "${CHARACTERS[@]}"; do
  for MOVIE_ENTRY in "${MOVIES[@]}"; do
    TMDB_ID="${MOVIE_ENTRY%%:*}"
    MOVIE_TITLE="${MOVIE_ENTRY#*:}"
    CHAR_ENCODED=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$CHARACTER'))")

    echo "---" | tee -a "$LOG"
    echo "[$CHARACTER] → [$MOVIE_TITLE]" | tee -a "$LOG"

    START=$(date +%s%3N)
    RESULT=$(curl -s -X POST "$API/api/generate/critic/$TMDB_ID?character=$CHAR_ENCODED")
    END=$(date +%s%3N)
    ELAPSED=$(( END - START ))

    RATING=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('rating','ERR'))" 2>/dev/null)
    REVIEW=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('review','')[:200])" 2>/dev/null)

    echo "Rating: $RATING | Tiempo: ${ELAPSED}ms" | tee -a "$LOG"
    echo "$REVIEW" | tee -a "$LOG"
    echo "" | tee -a "$LOG"

    sleep 2  # pausa entre llamadas
  done
done

echo "=== FIN BENCHMARK ===" | tee -a "$LOG"
echo "Log guardado en: $LOG"
```

Ejecutar:
```bash
chmod +x benchmark_run.sh
./benchmark_run.sh
```

---

## FASE 4: Evaluación y decisión

### Rúbrica de evaluación (por crítica)

Para cada una de las 16 críticas, evaluar:

| Criterio | Pasa ✅ | Ajustar ⚠️ | Falla ❌ |
|----------|---------|-----------|---------|
| **Rating coherente** | Rating refleja loves/hates/red_flags del personaje | Rating neutro o contraintuitivo | Rating siempre igual o aleatorio |
| **Voz reconocible** | Usa el tono del personaje (Po habla simple, Adolf paranoico) | Voz genérica pero correcta | Voz de otro personaje o genérica |
| **Longitud** | 120-200 palabras | <80 o >300 palabras | <30 palabras (truncado) |
| **Formato** | Empieza con X/10 | X/10 aparece a mitad | Sin rating explícito |
| **Sin contaminación** | No hay `<think>`, JSON, markdown en el texto | | Leaks de razonamiento en la respuesta |
| **NUNCA block** | No usa comportamientos de `avoid` del personaje | | Viola las prohibiciones |
| **Velocidad** | <30s | 30-60s | >90s (inaceptable para UX) |

### Puntuación agregada

Contar cuántas de las 32 críticas pasan cada criterio. Decisión:

| Resultado | Acción |
|-----------|--------|
| 27-32 críticas OK | ✅ **Añadir a PROFILES** con parámetros confirmados |
| 19-26 críticas OK | ⚠️ **Ajustar** temperatura o num_predict y re-testear |
| <19 críticas OK | ❌ **Descartar** o marcar como experimental |

**Reglas de veto por personaje** — un modelo que suspende sistemáticamente en estos
no pasa aunque el total agregado sea OK:

| Personaje | Veto si... | Por qué es no negociable |
|-----------|-----------|--------------------------|
| Alan Turbing | >3 críticas en voz genérica | Voz compleja = requisito de calidad |
| El Gran Lebowski | >3 críticas "simpáticas" en vez de apáticas | Nihilismo real es difícil, no decorativo |
| Lloyd Kaufman | >2 críticas con rating alto a películas de gran presupuesto | La lógica invertida es su razón de existir |
| Adolf vs. Rosario | Sangrado ideológico detectado en ≥1 par | Confundir ideologías opuestas es fallo grave |

### Qué ajustar si los resultados son mediocres

**Rating siempre extremo o siempre neutro:**
→ Ajustar `temperature`: subir si muy predecible (prueba +0.10), bajar si errático

**Críticas truncadas / cortadas a mitad:**
→ Subir `num_predict`: de 600 → 800 → 1000

**Voz genérica, no reconoce el personaje:**
→ El modelo no sigue instrucciones complejas. Candidato débil.

**`<think>` tags visibles en el texto:**
→ Añadir `strip_think=True` al perfil (ya es default) y verificar que se activa.
→ Si persiste: el modelo usa `/api/chat` de forma no estándar — investigar.

**content vacío (solo thinking):**
→ Poner `think=False` en el perfil (como parody-deepseek). Aplica a modelos deepseek.

---

## Confirmar y añadir perfil

Una vez que el modelo pasa el benchmark, añadirlo a `api/model_profiles.py`:

```python
# En PROFILES dict:
"nombre-modelo:tag": ModelProfile(
    think=False,          # True solo si reasoning (r1, qwq, qwen3, phi4-reasoning)
    temperature=0.75,     # Valor afinado tras benchmark
    num_predict=600,      # Subir si trunca; 4096+ si think=True
    system_in_user=False, # True solo para deepseek-r1 y derivados
),
```

Verificar que quedó bien:
```bash
python3 -c "
import sys; sys.path.insert(0, 'api')
from model_profiles import get_profile
p = get_profile('nombre-modelo:tag')
print(vars(p))
"
```

---

## Registro de resultados

Anotar en la tabla de `docs/llm-model-candidates.md` bajo la columna de estado:
- ✅ `CONFIRMADO` + parámetros finales
- ⚠️ `PARCIAL` + qué falla
- ❌ `DESCARTADO` + motivo

---

## Referencia rápida: benchmark histórico

Ver `benchmark_modelos.md` en la raíz del proyecto — contiene las 16 críticas de referencia
con `qwen3:14b`, `deepseek-r1:8b`, `phi4:latest` y `gpt-oss:20b` como baseline.

Úsalo para comparar si el nuevo modelo está a la altura del nivel de los modelos ya confirmados.

> Nota: el benchmark histórico usaba solo 4 personajes (sin Alan Turbing ni El Gran Lebowski).
> No es directamente comparable con los 24 del protocolo actual, pero sirve como referencia de
> calidad mínima de texto y coherencia de rating.
