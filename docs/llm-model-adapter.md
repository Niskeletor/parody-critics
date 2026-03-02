# LLM Model Adapter — Arquitectura y modelos confirmados
*Implementado: 2026-03-01*

---

## Problema que resuelve

El pipeline LLM era monolítico: cada cambio de modelo (`qwen3→phi4`, `phi4→deepseek`) requería tocar parámetros hardcodeados, cambiar entre `/api/generate` y `/api/chat`, recordar que deepseek prohíbe system prompts, ajustar el budget de tokens manualmente.

---

## Arquitectura (3 responsabilidades separadas)

```
ModelProfile   →  HOW to call each model
PromptBuilder  →  WHAT to say (same content for all models)
LLMClient      →  thin HTTP layer that combines both
```

### `api/model_profiles.py`
Cada modelo tiene un `ModelProfile` con:

| Campo | Descripción |
|-------|-------------|
| `think` | Activar thinking mode en Ollama |
| `temperature` | Temperatura de sampling |
| `num_predict` | Budget de tokens (thinking models necesitan 4096+) |
| `system_in_user` | deepseek-r1: merge system prompt en user message |
| `top_p` / `top_k` | Parámetros de sampling |
| `strip_think` | Stripear `<think>...</think>` si aparecen en content |

Para modelos no registrados, `get_profile(name)` aplica heurística automática basada en el nombre.

### `api/prompt_builder.py`
Construye los mensajes para `/api/chat`. Contenido idéntico para todos los modelos, pero la **colocación del system prompt** varía:

- **Normal**: `[{role: system}, {role: user}]`
- **deepseek** (`system_in_user=True`): `[{role: user, content: SYSTEM + "\n\n" + user_block}]`

Añade dos bloques que no existían en v1:
- **NUNCA block**: prohibiciones explícitas derivadas de `avoid` y `red_flags`
- **RÚBRICA DE PUNTUACIÓN**: ancla el rating a `loves`/`hates`/`red_flags` del personaje

---

## Modelos confirmados — tests en vivo (2026-03-01)

Servidor: Omnius (`http://192.168.2.69:11434`)

| Modelo | Perfil | think | sys_in_user | temp | num_predict | Resultado |
|--------|--------|-------|-------------|------|-------------|-----------|
| `qwen3:14b` | exacto | ✅ | ❌ | 0.60 | 4096 | ✅ rating OK |
| `deepseek-r1:8b` | exacto | ✅ | ✅ | 0.60 | 6144 | ✅ rating OK |
| `phi4:latest` | exacto | ❌ | ❌ | 0.70 | 600 | ✅ rating OK |
| `gemma3:27b` | exacto | ❌ | ❌ | 0.75 | 600 | ✅ rating OK |
| `mistral-small3.1:24b` | exacto | ❌ | ❌ | 0.75 | 600 | ✅ rating OK |
| `parody-phi4:latest` | exacto | ❌ | ❌ | 0.70 | 600 | ✅ rating OK |
| `parody-deepseek:latest` | exacto | ❌* | ✅ | 0.65 | 800 | ✅ rating OK |

*`parody-deepseek` tiene `think=False` intencionalmente — ver nota abajo.

---

## Comportamiento de think mode en Ollama /api/chat

**Resultado de tests directos:**

Cuando se envía `think: true` en el payload, Ollama **separa el razonamiento**:
- `message.thinking` → razonamiento interno (762+ chars en deepseek, similar en qwen3)
- `message.content` → respuesta final limpia (sin `<think>` tags)

`_strip_think_blocks()` existe como código defensivo pero **no es necesario** en condiciones normales con Ollama `/api/chat`. Se activa solo si `message.content` contiene tags literales (comportamiento no estándar).

### Bug conocido: deepseek-r1 con think=True puede devolver content vacío

En prompts muy simples, `deepseek-r1:8b` con `think=True` pone todo el razonamiento en `message.thinking` y devuelve `message.content = ""`. En prompts complejos (como las críticas) esto no ocurre, pero para cubrirlo:

```python
# En _call_ollama_chat:
if not raw_content.strip() and msg.get("thinking"):
    raw_content = msg["thinking"]  # fallback
```

Por esta razón, `parody-deepseek:latest` tiene `think=False` — es un Modelfile custom basado en deepseek-r1 y queremos garantizar `content` siempre poblado.

---

## Añadir un modelo nuevo

1. Añadir entrada en `PROFILES` en `api/model_profiles.py`:
```python
"mi-modelo:tag": ModelProfile(
    think=False,          # True solo si el modelo es reasoning (r1, qwq, qwen3)
    temperature=0.70,
    num_predict=600,      # 4096+ si think=True
    system_in_user=False, # True solo para deepseek-r1 y derivados
),
```

2. Si no se añade, `get_profile()` aplica heurística automática basada en el nombre — funciona para la mayoría de modelos estándar.

3. Cambiar el modelo activo: editar `LLM_PRIMARY_MODEL` en `.env` y reiniciar. El sistema autoaplica el perfil correcto sin más cambios.

---

## Verificación rápida

```bash
# Comprobar perfil que se aplicaría a un modelo
python3 -c "
import sys; sys.path.insert(0, 'api')
from model_profiles import get_profile
p = get_profile('mi-modelo:tag')
print(vars(p))
"

# Test de integración completo (requiere Ollama corriendo)
curl -X POST localhost:8000/api/generate/critic/24428?character=NombrePersonaje
# Buscar en logs: [profile: modelo think=X temp=Y]
```
