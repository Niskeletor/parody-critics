# Parody Critics — Community Release Design
**Fecha**: 2026-03-02
**Sesión**: Brainstorming con Niskeletor
**Estado**: Aprobado — pendiente de implementación por fases

---

## Visión

El proyecto empezó como sorpresa para familia y amigos, pero ha cogido suficiente fuerza para convertirse en un **add-in real para la comunidad de Jellyfin**. El "momento wow" es doble: la calidad/personalidad de las críticas (A) y tener 14+ críticos distintos opinando sobre cada película (C) — y como consecuencia, que aparezca directamente en Jellyfin sin que el usuario haga nada (B).

---

## Ecosistema a largo plazo

```
parody-critics-api  ←→  parody-critics-hub  (proyecto futuro)
(plugin local)           (web comunitaria)

genera críticas          almacena y distribuye críticas
importa personajes  ←    publica packs de personajes
exporta críticas    →    recibe contribuciones de la comunidad
```

El **hub** es el "IMDB de las críticas paródicas" — abierto, con contribuciones, descargable. Se construye DESPUÉS de que el plugin esté maduro y haya usuarios reales dando feedback.

---

## Arquitectura final (Fase 2)

Patrón **Gelato/aiostreams**: un plugin C# mínimo en el catálogo oficial de Jellyfin que es una cáscara fina — solo hace UI de configuración + llamadas a nuestra API. La lógica real (LLM, SQLite, personajes) sigue en Python/Docker.

```
Catálogo Jellyfin → Plugin C# (cáscara fina)
                           ↕ API calls
                   parody-critics-api (Python, sin cambios)
```

---

## FASE 1 — Community-Ready Plugin

**Objetivo**: publicable en el foro de Jellyfin. Usuarios Linux técnicos pueden instalarlo en <5 minutos.

### 1. Multi-idioma y personajes EN

- **UI i18n**: EN/ES configurable. Selector de idioma en el header.
- **Prompts bilingües**: `prompt_builder.py` con versión EN del `SYSTEM_BLOCK` y bloques de instrucción. El idioma sigue al setting de la UI.
- **Pack de personajes EN** (~10 personajes): Roger Ebert clásico, fanático Marvel, crítico Letterboxd hipster, boomer nostálgico, woke activist EN, nihilist, stoic philosopher... Exportados como JSON descargable en GitHub Releases.
- **Personajes ES actuales no se tocan** — el sistema es multilingüe por diseño (cada personaje genera en el idioma de su `description`).

### 2. Cloud LLM

Soporte para providers cloud además de Ollama. Clave para reducir la barrera de "necesito una GPU de 14GB".

**Providers**: OpenAI, Anthropic, Groq (tiene tier gratuito — importante para onboarding).

**Arquitectura**:
- `CloudLLMClient` en `api/llm_manager.py` implementando la misma interfaz que `_call_ollama_chat()`
- El resto del pipeline (prompt_builder, model_profiles, parse_critic_response) no cambia
- Config en `.env`:
  ```env
  LLM_PROVIDER=ollama          # ollama | openai | anthropic | groq
  LLM_API_KEY=sk-...           # solo si provider != ollama
  LLM_PRIMARY_MODEL=gpt-4o-mini  # nombre del modelo en el provider elegido
  ```
- Perfiles cloud: `think=False`, temperatura estándar, `num_predict` ignorado (los cloud no lo usan igual)
- Fallback: si cloud falla → secondary igual que ahora

### 3. UI — mejoras para release pública

Con la base dark cinema refinada, lo que falta:

- **Selector de idioma** en el header (EN/ES) — cambia UI + idioma de generación
- **Onboarding automático**: si la DB está vacía en primera instalación → redirigir al setup wizard automáticamente. No pantalla en blanco.
- **Vista pública read-only** (`/view`): ruta sin panel admin, solo muestra críticas. Para compartir con familia/amigos sin que toquen la configuración.
- **Mejoras UX del flujo de generación**: a trabajar con `interface-design` skill cuando llegue el momento.

### 4. `install.sh` interactivo

Script que lo hace todo. Flujo:

```bash
1. Detectar OS (Linux/macOS) y Docker instalado
2. ¿Usas Ollama local o cloud LLM?
   → Ollama: verificar que corre, listar modelos disponibles, elegir
   → Cloud: elegir provider (OpenAI/Anthropic/Groq), pedir API key
3. ¿URL de tu Jellyfin? (default: http://localhost:8096)
4. Generar .env con los valores
5. docker compose pull && docker compose up -d
6. Health check: verificar que la API responde en :8003
7. Instrucciones para instalar JS Injector plugin en Jellyfin
8. Opcional: importar pack de personajes (EN / ES / ambos)
```

Objetivo: usuario técnico medio < 5 minutos desde cero.

### 5. Documentación pública

- `README.md` reescrito orientado a la comunidad (actualmente básico)
- `docs/install/` — guía paso a paso con capturas
- `docs/characters/` — cómo crear y compartir personajes (soul wizard + export)
- `CHANGELOG.md` ✅ ya existe
- **GitHub Releases**: `install.sh` + packs de personajes EN/ES como assets descargables

---

## FASE 2 — Plugin oficial Jellyfin (después de Fase 1)

Se aborda SOLO cuando Fase 1 tenga usuarios reales y feedback estabilizado.

- Plugin C# mínimo siguiendo el patrón Gelato/aiostreams
- Aparece en el catálogo oficial de Jellyfin
- UI de configuración dentro de Jellyfin (URL de la API, idioma, etc.)
- El contenedor Python sigue sin cambios — el plugin C# solo es la cáscara de integración
- Compatible Windows/Linux/macOS (Jellyfin maneja eso)

---

## FASE 3 — parody-critics-hub (proyecto paralelo futuro)

Web comunitaria. Se construye cuando el plugin tenga tracción.

- Base de datos pública de críticas para las N películas más populares
- Comunidad puede contribuir críticas generadas con su instalación local
- Descarga de packs de críticas (pre-generated, sin necesidad de LLM)
- Galería y descarga de packs de personajes
- Esto convierte el "necesito LLM" en opcional — opción C+B para la comunidad

---

## Orden de implementación recomendado (Fase 1)

1. `simplify` — limpiar el código antes de añadir más cosas
2. Cloud LLM support — desbloquea el mayor bloqueante de adopción
3. Multi-idioma — EN pack de personajes + UI EN
4. `install.sh` — empaquetado
5. Documentación pública + README
6. Vista read-only `/view`
7. UI/UX improvements (`interface-design`)

---

*— Diseñado por SAL-9000 & Niskeletor, sesión 2026-03-02*
