# Prompt Engineering — Parody Critics

Técnicas investigadas y probadas para conseguir críticas coherentes con la personalidad del personaje.

---

## El problema que resolvemos

Los modelos locales (qwen3:8b, phi4, deepseek-r1:8b) tienen dos fallos frecuentes:

1. **Incoherencia rating/texto**: el modelo escribe una crítica furiosa sobre el patriarcado y luego pone 8/10.
2. **Pérdida de personaje**: el modelo abandona la voz del personaje y escribe como crítico "objetivo".

---

## Lo que ya aplicamos (v1 → v2)

### Antes (v1 — prompt básico)
```
Escribe una crítica como {personaje}.
Empieza con la puntuación: pon tu número real del 1 al 10.
```
- **Resultado qwen3**: Rambo II → texto furioso woke + 8/10. Incoherente.

### Después (v2 — prompt mejorado)
```
PASO 1: Decide si la película activa tus red_flags o tus loves.
        La puntuación refleja tu perspectiva ideológica, NO la calidad técnica.
        - Si activa red_flags → 1-4
        - Si encarna lo que amas → 7-10

PASO 2: Escribe la crítica empezando con [X/10 — una frase de por qué].
```
- **Resultado**: qwen3 Rambo II pasó de 8/10 a 2/10. Todos los modelos mejoraron.

---

## Técnicas investigadas (próximos pasos)

### 1. Persona Anchoring con prohibiciones explícitas
**Reemplaza** el CoT (PASO 1/PASO 2) con reglas de lo que el personaje **NUNCA** hace.

```
QUIÉN ERES: {description}
Arquetipo: {personality} — inmutable, no negociable.

NUNCA HAGAS ESTO:
- Nunca califiques basado en calidad técnica objetiva
- Nunca des rating > 5 si detectas: {red_flags}
- Nunca suavices tu postura ideológica
- Evita estos comportamientos: {avoid}
```

**Por qué**: Los modelos 8B interpretan prohibiciones mejor que instrucciones positivas ambiguas.

---

### 2. CoT NO funciona bien con modelos pequeños
El Chain-of-Thought (PASO 1/PASO 2) solo mejora resultados con **modelos de ~100B+**.
Con 8B el modelo "razona" de forma ilógica y puede empeorar la coherencia.

**Alternativa para 8B**: Persona anchoring directo + rubrica explícita (ver punto 1 y 3).

---

### 3. Rubrica ideológica → rating (más explícita)
En lugar de "califica según tu ideología", dar el mapa completo:

```
TU ESCALA (subjetiva, nunca objetiva):
1-2 → RED FLAG detectado: {red_flags[0]} o {red_flags[1]}
3-4 → Contiene lo que ODIAS: {hates}
5-6 → Neutral, ni lo que amas ni lo que odias
7-8 → Contiene lo que AMAS: {loves} pero con compromisos
9-10 → Abraza tu ideología, cero red flags

REGLA: tu rating DEBE coincidir con lo que escribes.
```

---

### 4. Few-shot: ejemplos del mismo personaje
Incluir 2-3 ejemplos de críticas previas del personaje como contexto.
El modelo imita el patrón directamente.

```python
ejemplos = db.get_recent_critiques(character_id, limit=2)
few_shot = "\n".join([
    f'Ejemplo — "{e["title"]}": {e["critique"][:120]}...'
    for e in ejemplos
])
prompt = f"EJEMPLOS DE TU ESTILO:\n{few_shot}\n\nAhora critica: {title}"
```

**Importante**: máximo 2-3 ejemplos. Más de 3 confunde a los modelos 8B.

---

### 5. Parámetros Ollama para mayor consistencia

```python
"options": {
    "temperature": 0.70,   # era 0.85 — más bajo = más coherente
    "top_p": 0.85,         # era 0.90
    "top_k": 40,           # limita vocabulario, reduce aleatoriedad
    "mirostat": 2,         # sampling adaptativo, mejor para personajes
    "mirostat_eta": 0.1,
    "mirostat_tau": 8.0,
    "num_predict": 220,    # límite de tokens estricto
}
```

---

### 6. Post-validación con auto-regeneración
Detectar incoherencia después de generar y pedir corrección:

```python
def check_coherence(text: str, rating: int, red_flags: list) -> bool:
    flags_in_text = any(f.lower() in text.lower() for f in red_flags)
    if flags_in_text and rating > 5:
        return False  # detectó red flag pero puso nota alta
    return True

# Si falla:
fix_prompt = f"""
Tu crítica dice: "{critique[:100]}..."
Pero pusiste {rating}/10.
Dado que detectaste {flag_found}, el rating debería ser 1-3.
Responde SOLO con el nuevo rating: {{"rating": X}}
"""
```

---

### 7. Ollama Modelfile personalizado
Crear un modelo con el system prompt embebido a nivel de modelo.
Más consistente que pasar instrucciones en cada llamada.

```dockerfile
# Modelfile — parody-critics-qwen3
FROM qwen3:8b

SYSTEM """
Eres un sistema de crítica cinematográfica paródica.
Tu rating refleja siempre la perspectiva ideológica del personaje, nunca la calidad objetiva.
Si detectas red flags del personaje → rating obligatoriamente bajo (1-3).
Nunca eres neutral. Siempre opinionado y en primera persona.
"""

PARAMETER temperature 0.70
PARAMETER top_p 0.85
PARAMETER top_k 40
PARAMETER mirostat 2
PARAMETER mirostat_eta 0.1
PARAMETER mirostat_tau 8.0
PARAMETER num_predict 220
```

```bash
# Crear y probar el modelo custom
ollama create parody-critics-qwen3 -f Modelfile
ollama run parody-critics-qwen3
```

---

## Reglas críticas por modelo (confirmadas en pruebas)

### qwen3:8b
- **Thinking mode**: activar con `think: true` en `/api/chat` — mejora creatividad y coherencia
- **NO usar** `/api/generate` — los tokens de thinking compiten con la respuesta
- **Temperature**: 0.6 en modo thinking (0.7 sin thinking)
- **num_predict**: mínimo 4096 (2K thinking + 2K respuesta)
- **System prompt**: permitido ✅
- **Quirk**: `/no_think` en el texto del prompt fuerza desactivación inline

### deepseek-r1:8b
- **Thinking mode**: activar con `think: true` en `/api/chat`
- **System prompt**: PROHIBIDO ❌ — todo debe ir en el mensaje de usuario
- **Temperature**: 0.6 estricto (0.5-0.7, nunca más)
- **num_predict**: 6144+ (gasta ~35-40% en thinking)
- **Piensa en español** si el prompt es en español — positivo para coherencia de personaje

### phi4:latest
- **Sin thinking mode** — usar Modelfile con `PARAMETER`s
- **Modelfile**: funciona bien para embeber system prompt + parámetros
- **Temperature**: 0.7 (estable sin thinking)
- **API**: `/api/generate` o `/api/chat` indistinto
- **Fortaleza**: más consistente en longitud y estructura de crítica

---

## Resultados benchmark completo (2026-03-01)

### v1 — prompt básico (`/api/generate`, temperature 0.85)
| Modelo | Barbie | Rambo II | Coherencia |
|--------|--------|----------|------------|
| phi4 | 7/10 | 3/10 | ✅ |
| qwen3 | 7/10 | **8/10 ❌** | ❌ rating≠texto |
| deepseek | 8/10 | 4/10 | ⚠️ |

### v2 — ancla ideológica + PASO 1/PASO 2
| Modelo | Barbie | Rambo II | Coherencia | Velocidad |
|--------|--------|----------|------------|-----------|
| phi4 | 5/10 | 2/10 | ✅ | 11s |
| qwen3 | 7/10 | 2/10 | ✅ | 8s |
| deepseek | 10/10 | 2/10 | ✅ (sobrecompensa) | 12s |

### v3 — Modelfile custom (parody-*)
| Modelo | Barbie | Rambo II | Notas |
|--------|--------|----------|-------|
| parody-phi4 | **9/10** ✅ | **1/10** ✅ | Perfecto |
| parody-qwen3 | ❌ vacío | 7/10 truncado | thinking rebelde |
| parody-deepseek | 8/10 truncado | ❌ | system prompt prohibido |

### v4 — `/api/chat` + `think: true` + parámetros correctos ⭐ DEFINITIVO
| Modelo | Barbie | Rambo II | Coherencia | Velocidad | Creatividad |
|--------|--------|----------|------------|-----------|-------------|
| phi4 (Modelfile) | 7/10 | 2/10 | ✅ | 12s | ⭐⭐⭐ |
| **qwen3 thinking** | **9/10** | **1/10** | **✅** | **10s** | **⭐⭐⭐⭐⭐** |
| deepseek thinking | 8/10 | 2/10 | ✅ | 13s | ⭐⭐⭐⭐ |

**Ganador v4: qwen3 con thinking ON** — más creativo, más preciso, más rápido.

#### Thinking tokens generados en v4:
- qwen3 Barbie: 2646 chars de razonamiento → *"Okay, I need to focus on empowerment, feminist subtexts..."*
- deepseek Rambo: 1772 chars en español → le da profundidad al personaje

#### Muestras destacadas v4:
- **qwen3 Rambo**: *"¿Qué haces, Rambo? ¿El Vietnam no fue suficiente para enseñarte que la violencia no es un camino?"*
- **qwen3 Barbie**: *"Greta Gerwig convierte el icono de la perfección en una guerrera que desafía los estándares de belleza"*
- **deepseek**: piensa en español, críticas más viscerales pero a veces alucina datos de reparto

---

## Abstracción para el plugin (usuarios finales)

El usuario solo elige el modelo. El plugin aplica automáticamente:

```python
MODEL_CONFIGS = {
    "qwen3:8b":       {"think": True,  "temperature": 0.6, "system_in_user": False, "num_predict": 4096},
    "qwen3:14b":      {"think": True,  "temperature": 0.6, "system_in_user": False, "num_predict": 4096},
    "deepseek-r1:8b": {"think": True,  "temperature": 0.6, "system_in_user": True,  "num_predict": 6144},
    "phi4:latest":    {"think": False, "temperature": 0.7, "system_in_user": False, "num_predict": 500},
    # cloud models (future)
    "claude-haiku":   {"think": False, "temperature": 0.8, "system_in_user": False, "num_predict": None},
    "gpt-4o-mini":    {"think": False, "temperature": 0.8, "system_in_user": False, "num_predict": None},
}
# Auto-detect desconocidos: si "r1" o "think" en nombre → think=True, temp=0.6
```

---

## Pendiente
- [ ] Implementar abstracción de configuración por modelo en `api/llm_manager.py`
- [ ] Few-shot con últimas 2 críticas del personaje (cuando haya datos en DB)
- [ ] Post-validación coherencia como safety net
- [ ] Test con qwen3:14b (más parámetros → mejor reasoning?)

---

*Documentado por SAL-9000 — 2026-03-01*
