# install.sh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `install.sh` — an interactive bash wizard that takes a user from zero to running Parody Critics in under 5 minutes, with safe rollback if deploy fails.

**Architecture:** Single bash script (~350 lines) with helper functions. Phases run sequentially. Validation gates each phase — model picker only appears after connection is confirmed. `.env.new` staging prevents corrupting existing config on failure.

**Tech Stack:** bash 4+, curl, python3 (JSON parsing), fzf (model picker, with `select` fallback), docker compose v2.

**Design doc:** `docs/plans/2026-03-07-install-sh-design.md`

---

### Task 1: Scaffold + colors + section headers

**Files:**
- Create: `install.sh`

**Step 1: Create script skeleton with color helpers**

```bash
#!/usr/bin/env bash
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
err()  { echo -e "${RED}  ✗${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
info() { echo -e "${BLUE}  →${NC} $*"; }
section() { echo -e "\n${BOLD}=== $* ===${NC}\n"; }

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo -e "${BOLD}"
cat << 'BANNER'
  ____                      _
 |  _ \ __ _ _ __ ___   __| |_   _
 | |_) / _` | '__/ _ \ / _` | | | |
 |  __/ (_| | | | (_) | (_| | |_| |
 |_|   \__,_|_|  \___/ \__,_|\__, |
   ____      _ _   _          |___/
  / ___|_ __(_) |_(_) ___ ___
 | |   | '__| | __| |/ __/ __|
 | |___| |  | | |_| | (__\__ \
  \____|_|  |_|\__|_|\___|___/
BANNER
echo -e "${NC}"
echo -e "${BOLD}  Parody Critics — Interactive Installer${NC}"
echo -e "  The spice must flow... and so must the setup!\n"
```

**Step 2: Verify syntax is valid**

```bash
bash -n install.sh
echo "Syntax OK"
```

Expected: no errors.

**Step 3: Make executable and run banner test**

```bash
chmod +x install.sh
./install.sh 2>&1 | head -20
```

Expected: banner printed, exits cleanly (with error since phases not yet implemented).

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh scaffold with banner and color helpers"
```

---

### Task 2: Phase 0 — Prerequisites check

**Files:**
- Modify: `install.sh`

**Step 1: Add `check_prerequisites` function after banner**

```bash
# ── State ─────────────────────────────────────────────────────────────────────
USE_FZF=0
PREV_CONTAINER_ID=""
PREV_IMAGE_ID=""

check_prerequisites() {
    section "FASE 0: Prerequisitos"

    # Docker daemon
    if ! docker info > /dev/null 2>&1; then
        err "Docker no está instalado o el daemon no está corriendo."
        err "Instala Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi
    ok "Docker corriendo"

    # docker compose v2
    if ! docker compose version > /dev/null 2>&1; then
        err "docker compose v2 no disponible."
        err "Actualiza Docker Desktop o instala el plugin: https://docs.docker.com/compose/install/"
        exit 1
    fi
    ok "docker compose v2 disponible"

    # curl
    if ! command -v curl > /dev/null 2>&1; then
        err "curl no está instalado. Instálalo: apt install curl"
        exit 1
    fi
    ok "curl disponible"

    # python3 (for JSON parsing)
    if ! command -v python3 > /dev/null 2>&1; then
        err "python3 no está instalado. Instálalo: apt install python3"
        exit 1
    fi
    ok "python3 disponible"

    # fzf (optional)
    if command -v fzf > /dev/null 2>&1; then
        USE_FZF=1
        ok "fzf disponible — model picker interactivo activado"
    else
        warn "fzf no encontrado — usando menú numerado (recomendado: apt install fzf)"
    fi

    # Existing install detection
    PREV_CONTAINER_ID=$(docker ps -q -f name=parody-critics-api 2>/dev/null || true)
    if [ -n "$PREV_CONTAINER_ID" ]; then
        PREV_IMAGE_ID=$(docker inspect parody-critics-api --format '{{.Image}}' 2>/dev/null || true)
        warn "Instalación existente detectada (container: ${PREV_CONTAINER_ID:0:12})"
        warn "Esta instalación la actualizará. El servicio se reiniciará."
    fi
}
```

**Step 2: Call it from main and test**

Add at end of script:
```bash
check_prerequisites
```

Run:
```bash
./install.sh
```

Expected: All checks pass (green ticks), fzf detected, exits after phase 0 (no more phases yet).

**Step 3: Test failure path — temporarily rename docker**

```bash
# Simulate docker missing (don't actually remove it)
PATH_BACKUP=$PATH
export PATH=/tmp/fake_path
./install.sh 2>&1 | head -5
export PATH=$PATH_BACKUP
```

Expected: red ✗ and exit 1.

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh phase 0 prerequisites check"
```

---

### Task 3: Helper functions — ask_input and pick_model

**Files:**
- Modify: `install.sh`

**Step 1: Add `ask_input` helper (add before `check_prerequisites`)**

```bash
# ask_input VAR_NAME "prompt" "default" [secret]
# Reads input into variable named VAR_NAME
ask_input() {
    local var="$1" prompt="$2" default="$3" secret="${4:-}"
    local value=""
    while true; do
        if [ -n "$default" ]; then
            printf "  %s [%s]: " "$prompt" "$default"
        else
            printf "  %s: " "$prompt"
        fi
        if [ "$secret" = "secret" ]; then
            read -rs value; echo
        else
            read -r value
        fi
        value="${value:-$default}"
        if [ -n "$value" ]; then
            printf -v "$var" '%s' "$value"
            return 0
        fi
        warn "Este campo es obligatorio."
    done
}

# ask_optional VAR_NAME "prompt"
# Empty is valid
ask_optional() {
    local var="$1" prompt="$2"
    printf "  %s (Enter para omitir): " "$prompt"
    local value=""
    read -r value
    printf -v "$var" '%s' "$value"
}
```

**Step 2: Add `pick_model` helper**

```bash
# pick_model VAR_NAME "prompt title" "newline-separated model list"
pick_model() {
    local var="$1" title="$2" models_str="$3"
    local chosen=""

    if [ "$USE_FZF" = "1" ]; then
        chosen=$(echo "$models_str" | fzf \
            --prompt="  $title > " \
            --height=14 \
            --border=rounded \
            --header="Usa flechas para navegar, Enter para seleccionar" \
            --no-info)
    else
        info "$title"
        local arr=()
        while IFS= read -r line; do
            [ -n "$line" ] && arr+=("$line")
        done <<< "$models_str"
        PS3="  Número: "
        select chosen in "${arr[@]}"; do
            [ -n "$chosen" ] && break
            warn "Selección inválida."
        done
    fi

    if [ -z "$chosen" ]; then
        err "No se seleccionó ningún modelo."
        exit 1
    fi
    ok "Modelo seleccionado: $chosen"
    printf -v "$var" '%s' "$chosen"
}
```

**Step 3: Test helpers in isolation**

```bash
# Quick syntax + logic test
bash -c '
source <(sed -n "/ask_input/,/^}/p" install.sh 2>/dev/null || true)
echo "Helpers loaded OK"
'
bash -n install.sh && echo "Syntax OK"
```

Expected: Syntax OK.

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh helper functions ask_input and pick_model"
```

---

### Task 4: Phase 1a — Ollama LLM flow

**Files:**
- Modify: `install.sh`

**Step 1: Add Ollama model fetcher function**

```bash
fetch_ollama_models() {
    local url="$1"
    curl -sf "$url/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print('\n'.join(models))
"
}
```

**Step 2: Add `configure_llm_ollama` function**

```bash
configure_llm_ollama() {
    LLM_PROVIDER="ollama"
    LLM_API_KEY=""

    # URL
    ask_input LLM_OLLAMA_URL "URL de Ollama" "http://localhost:11434"

    # Validate connectivity + fetch models
    info "Conectando con Ollama en $LLM_OLLAMA_URL ..."
    local attempt=0
    local models_str=""
    while true; do
        if models_str=$(fetch_ollama_models "$LLM_OLLAMA_URL" 2>/dev/null) && [ -n "$models_str" ]; then
            ok "Conectado. $(echo "$models_str" | wc -l) modelos disponibles."
            break
        fi
        attempt=$((attempt + 1))
        if [ $attempt -ge 3 ]; then
            err "No se pudo conectar con Ollama tras 3 intentos."
            err "Verifica que Ollama esté corriendo: curl $LLM_OLLAMA_URL/api/tags"
            exit 1
        fi
        warn "Fallo de conexión. ¿Reintentar? Corrige la URL si es necesario."
        ask_input LLM_OLLAMA_URL "URL de Ollama" "$LLM_OLLAMA_URL"
    done

    # Model picker — PRIMARY
    echo ""
    info "Selecciona el modelo PRIMARIO:"
    pick_model LLM_PRIMARY_MODEL "Modelo primario" "$models_str"

    # Model picker — SECONDARY
    echo ""
    info "Selecciona el modelo SECUNDARIO (fallback):"
    pick_model LLM_SECONDARY_MODEL "Modelo secundario" "$models_str"
}
```

**Step 3: Test Ollama flow against live server**

Temporarily add at end of script:
```bash
configure_llm_ollama
echo "PRIMARY: $LLM_PRIMARY_MODEL"
echo "SECONDARY: $LLM_SECONDARY_MODEL"
```

Run (requires Ollama at default URL or configured URL):
```bash
./install.sh
```

Expected: Shows model list via fzf/select, stores selections, prints them.

Remove the test lines after verifying.

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh phase 1 Ollama flow with dynamic model picker"
```

---

### Task 5: Phase 1b — Cloud LLM flows (Groq / OpenAI / Anthropic)

**Files:**
- Modify: `install.sh`

**Step 1: Add cloud model lists and validators**

```bash
# Curated model lists for providers without full discovery
OPENAI_MODELS="gpt-4o-mini
gpt-4o
gpt-3.5-turbo"

ANTHROPIC_MODELS="claude-haiku-4-5-20251001
claude-sonnet-4-6
claude-opus-4-6"

validate_groq_key() {
    local key="$1"
    local resp
    resp=$(curl -sf "https://api.groq.com/openai/v1/models" \
        -H "Authorization: Bearer $key" 2>/dev/null)
    [ $? -eq 0 ] && echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
exclude = ['whisper','guard','safeguard','arabic','orpheus','compound']
models = [m['id'] for m in data.get('data',[]) if not any(x in m['id'].lower() for x in exclude)]
print('\n'.join(sorted(models)))
"
}

validate_openai_key() {
    local key="$1"
    curl -sf "https://api.openai.com/v1/models" \
        -H "Authorization: Bearer $key" > /dev/null 2>&1
}

validate_anthropic_key() {
    local key="$1"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "https://api.anthropic.com/v1/messages" \
        -H "x-api-key: $key" \
        -H "anthropic-version: 2023-06-01" \
        -H "content-type: application/json" \
        -d '{"model":"claude-haiku-4-5-20251001","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}')
    [ "$http_code" != "401" ] && [ "$http_code" != "403" ]
}
```

**Step 2: Add `configure_llm_cloud` function**

```bash
configure_llm_cloud() {
    local provider="$1"
    LLM_PROVIDER="$provider"
    LLM_OLLAMA_URL=""
    LLM_SECONDARY_MODEL=""

    ask_input LLM_API_KEY "API Key de $provider" "" "secret"

    info "Validando API key con $provider ..."
    local models_str=""
    local attempt=0

    while true; do
        case "$provider" in
            groq)
                models_str=$(validate_groq_key "$LLM_API_KEY")
                local valid=$?
                ;;
            openai)
                validate_openai_key "$LLM_API_KEY" && models_str="$OPENAI_MODELS" && valid=0 || valid=1
                ;;
            anthropic)
                validate_anthropic_key "$LLM_API_KEY" && models_str="$ANTHROPIC_MODELS" && valid=0 || valid=1
                ;;
        esac

        if [ "${valid:-1}" -eq 0 ] && [ -n "$models_str" ]; then
            ok "API key válida. $(echo "$models_str" | wc -l) modelos disponibles."
            break
        fi

        attempt=$((attempt + 1))
        [ $attempt -ge 3 ] && err "API key inválida tras 3 intentos." && exit 1
        warn "API key inválida o error de conexión."
        ask_input LLM_API_KEY "API Key de $provider" "" "secret"
    done

    echo ""
    info "Selecciona el modelo PRIMARIO:"
    pick_model LLM_PRIMARY_MODEL "Modelo primario ($provider)" "$models_str"
}
```

**Step 3: Add `configure_llm` router + provider menu**

```bash
configure_llm() {
    section "FASE 1: Proveedor LLM"

    echo "  ¿Qué proveedor LLM quieres usar?"
    echo ""
    echo "  1) Ollama   — local, requiere GPU"
    echo "  2) Groq     — cloud, tier gratuito disponible"
    echo "  3) OpenAI   — cloud, de pago"
    echo "  4) Anthropic — cloud, de pago"
    echo ""
    local choice
    while true; do
        read -rp "  Opción [1-4]: " choice
        case "$choice" in
            1) configure_llm_ollama; break ;;
            2) configure_llm_cloud "groq"; break ;;
            3) configure_llm_cloud "openai"; break ;;
            4) configure_llm_cloud "anthropic"; break ;;
            *) warn "Opción inválida. Elige 1-4." ;;
        esac
    done
}
```

**Step 4: Test Groq flow (validates against live API)**

Temporarily add at end of script:
```bash
configure_llm
echo "PROVIDER: $LLM_PROVIDER"
echo "PRIMARY: $LLM_PRIMARY_MODEL"
```

Run and select Groq (option 2), enter the test key.

Expected: Key validates, Groq models appear in fzf/select, selection stored.

Remove test lines after verifying.

**Step 5: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh phase 1 cloud LLM flows with key validation"
```

---

### Task 6: Phase 2 — Jellyfin configuration

**Files:**
- Modify: `install.sh`

**Step 1: Add `configure_jellyfin` function**

```bash
configure_jellyfin() {
    section "FASE 2: Jellyfin"

    # URL
    ask_input JELLYFIN_URL "URL de Jellyfin" "http://localhost:8096"

    info "Verificando conectividad con Jellyfin ..."
    local attempt=0
    while true; do
        if curl -sf "$JELLYFIN_URL/System/Info/Public" > /dev/null 2>&1; then
            ok "Jellyfin accesible en $JELLYFIN_URL"
            break
        fi
        attempt=$((attempt + 1))
        [ $attempt -ge 3 ] && err "No se pudo conectar con Jellyfin." && exit 1
        warn "No hay respuesta. Verifica la URL."
        ask_input JELLYFIN_URL "URL de Jellyfin" "$JELLYFIN_URL"
    done

    # API Token
    ask_input JELLYFIN_API_TOKEN "Jellyfin API Token" "" "secret"

    info "Validando API token ..."
    attempt=0
    while true; do
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            "$JELLYFIN_URL/System/Info" \
            -H "X-Emby-Token: $JELLYFIN_API_TOKEN")
        if [ "$http_code" = "200" ]; then
            ok "API token válido."
            break
        fi
        attempt=$((attempt + 1))
        [ $attempt -ge 3 ] && err "Token inválido tras 3 intentos." && exit 1
        warn "Token inválido (HTTP $http_code). Genera uno en Jellyfin → Dashboard → API Keys."
        ask_input JELLYFIN_API_TOKEN "Jellyfin API Token" "" "secret"
    done

    # DB path
    ask_input JELLYFIN_DB_PATH "Ruta a library.db de Jellyfin" ""
    if [ ! -f "$JELLYFIN_DB_PATH" ]; then
        warn "El archivo no existe en esa ruta. Verifica que la ruta sea correcta."
        warn "Puedes continuar pero el sync de biblioteca no funcionará."
    else
        ok "Archivo DB encontrado."
    fi
}
```

**Step 2: Add to main flow and test**

```bash
configure_jellyfin
echo "JELLYFIN_URL: $JELLYFIN_URL"
```

Run with your local Jellyfin URL and token.
Expected: Both URL and token validated, DB path checked.

Remove test lines after verifying.

**Step 3: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh phase 2 Jellyfin config with validation"
```

---

### Task 7: Phase 3 — API config and optionals

**Files:**
- Modify: `install.sh`

**Step 1: Add `configure_api` function**

```bash
configure_api() {
    section "FASE 3: Configuración API"

    # Port
    ask_input PARODY_CRITICS_PORT "Puerto de la API" "8003"

    # Validate port is free
    if ss -tlnp 2>/dev/null | grep -q ":$PARODY_CRITICS_PORT "; then
        warn "El puerto $PARODY_CRITICS_PORT está en uso."
        if docker ps --format '{{.Names}}' | grep -q parody-critics; then
            ok "Es el container de Parody Critics existente — se reemplazará."
        else
            warn "Otro proceso usa ese puerto. Considera cambiarlo."
            ask_input PARODY_CRITICS_PORT "Puerto alternativo" "$PARODY_CRITICS_PORT"
        fi
    else
        ok "Puerto $PARODY_CRITICS_PORT disponible."
    fi

    # TMDB
    echo ""
    info "TMDB enriquece las sinopsis con más contexto (opcional)."
    info "Obtén tu token gratuito en: https://www.themoviedb.org/settings/api"
    ask_optional TMDB_ACCESS_TOKEN "TMDB Access Token"
    [ -n "$TMDB_ACCESS_TOKEN" ] && ok "TMDB configurado." || info "TMDB omitido."

    # Brave
    echo ""
    info "Brave Search añade contexto de críticas sociales (opcional, 2000 req/mes gratis)."
    ask_optional BRAVE_API_KEY "Brave Search API Key"
    [ -n "$BRAVE_API_KEY" ] && ok "Brave configurado." || info "Brave omitido."
}
```

**Step 2: Test interactively**

```bash
./install.sh
```

Walk through phases 0-3. Check all prompts and validations.

**Step 3: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh phase 3 API config and optional enrichment keys"
```

---

### Task 8: Summary screen before deploy

**Files:**
- Modify: `install.sh`

**Step 1: Add `show_summary` function**

```bash
mask() { echo "${1:0:4}****${1: -4}"; }

show_summary() {
    section "RESUMEN — Revisa antes de continuar"

    echo -e "  ${BOLD}LLM:${NC}"
    echo "    Provider:   $LLM_PROVIDER"
    [ -n "$LLM_OLLAMA_URL" ] && echo "    Ollama URL: $LLM_OLLAMA_URL"
    [ -n "$LLM_API_KEY"    ] && echo "    API Key:    $(mask "$LLM_API_KEY")"
    echo "    Modelo 1:   $LLM_PRIMARY_MODEL"
    [ -n "$LLM_SECONDARY_MODEL" ] && echo "    Modelo 2:   $LLM_SECONDARY_MODEL"

    echo -e "\n  ${BOLD}Jellyfin:${NC}"
    echo "    URL:        $JELLYFIN_URL"
    echo "    Token:      $(mask "$JELLYFIN_API_TOKEN")"
    echo "    DB path:    $JELLYFIN_DB_PATH"

    echo -e "\n  ${BOLD}API:${NC}"
    echo "    Puerto:     $PARODY_CRITICS_PORT"
    [ -n "$TMDB_ACCESS_TOKEN" ] && echo "    TMDB:       $(mask "$TMDB_ACCESS_TOKEN")" || echo "    TMDB:       (no configurado)"
    [ -n "$BRAVE_API_KEY"     ] && echo "    Brave:      $(mask "$BRAVE_API_KEY")" || echo "    Brave:      (no configurado)"

    echo ""
    read -rp "  ¿Continuar con el deploy? [S/n]: " confirm
    case "${confirm,,}" in
        n|no) echo "Instalación cancelada."; exit 0 ;;
        *)    info "Iniciando deploy..." ;;
    esac
}
```

**Step 2: Test summary output**

Add mock values and call `show_summary`, verify masking and layout.

**Step 3: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh summary screen with key masking before deploy"
```

---

### Task 9: Phase 4 — Safe deploy with rollback

**Files:**
- Modify: `install.sh`

**Step 1: Add `write_env` function**

```bash
write_env() {
    # Backup existing .env
    [ -f .env ] && cp .env .env.bak && info "Backup de .env anterior guardado en .env.bak"

    cat > .env.new << EOF
# Generated by install.sh on $(date)
PARODY_CRITICS_ENV=production
PARODY_CRITICS_HOST=0.0.0.0
PARODY_CRITICS_PORT=${PARODY_CRITICS_PORT}
PARODY_CRITICS_DB_PATH=/app/data/critics.db

LLM_PROVIDER=${LLM_PROVIDER}
LLM_OLLAMA_URL=${LLM_OLLAMA_URL:-}
LLM_API_KEY=${LLM_API_KEY:-}
LLM_PRIMARY_MODEL=${LLM_PRIMARY_MODEL}
LLM_SECONDARY_MODEL=${LLM_SECONDARY_MODEL:-}
LLM_TIMEOUT=180
LLM_MAX_RETRIES=2
LLM_ENABLE_FALLBACK=true

JELLYFIN_URL=${JELLYFIN_URL}
JELLYFIN_API_TOKEN=${JELLYFIN_API_TOKEN}
JELLYFIN_DB_PATH=${JELLYFIN_DB_PATH}

TMDB_ACCESS_TOKEN=${TMDB_ACCESS_TOKEN:-}
BRAVE_API_KEY=${BRAVE_API_KEY:-}

SYNC_BATCH_SIZE=100
SYNC_MAX_CONCURRENT=5
PARODY_CRITICS_CACHE_DURATION=300
PARODY_CRITICS_LOG_LEVEL=INFO
EOF
    mv .env.new .env
    ok ".env escrito."
}
```

**Step 2: Add `deploy_container` function with health check and rollback**

```bash
deploy_container() {
    section "FASE 4: Deploy"

    write_env

    # Pull image (GHCR) or build locally if no registry
    info "Descargando imagen..."
    if ! docker compose pull 2>/dev/null; then
        info "No se pudo hacer pull. Construyendo imagen localmente..."
        docker compose build
    fi

    # Start container
    info "Iniciando container..."
    docker compose up -d --force-recreate

    # Health check — 10 attempts × 3s = 30s timeout
    info "Esperando health check (máx 30s)..."
    local healthy=0
    for i in $(seq 1 10); do
        sleep 3
        if curl -sf "http://localhost:${PARODY_CRITICS_PORT}/api/health" > /dev/null 2>&1; then
            healthy=1
            break
        fi
        printf "  Intento %d/10...\r" "$i"
    done
    echo ""

    if [ "$healthy" = "1" ]; then
        ok "Container saludable en http://localhost:${PARODY_CRITICS_PORT}"
        return 0
    fi

    # Rollback
    err "Health check fallido. Haciendo rollback..."
    docker compose down 2>/dev/null || true
    [ -f .env.bak ] && mv .env.bak .env && warn ".env anterior restaurado."
    if [ -n "$PREV_CONTAINER_ID" ]; then
        docker start "$PREV_CONTAINER_ID" 2>/dev/null && ok "Container anterior restaurado." || true
    fi
    err "Deploy fallido. Revisa los logs: docker logs parody-critics-api"
    err "Tu servicio anterior (si existía) sigue activo."
    exit 1
}
```

**Step 3: Test deploy against real docker-compose.yml**

```bash
# Dry run — verify .env is written correctly
source install.sh  # won't work directly, test write_env with mocked vars
LLM_PROVIDER=ollama LLM_OLLAMA_URL=http://localhost:11434 \
LLM_PRIMARY_MODEL=mistral-small3.1:24b LLM_SECONDARY_MODEL=eva-qwen \
JELLYFIN_URL=http://localhost:8096 JELLYFIN_API_TOKEN=test \
JELLYFIN_DB_PATH=/tmp/test.db PARODY_CRITICS_PORT=8003 \
bash -c 'source install.sh; write_env; cat .env'
```

Expected: `.env` written with all values, no literal `${}` unexpanded.

**Step 4: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh phase 4 deploy with health check and rollback"
```

---

### Task 10: Phase 5 — JS plugin generation + main wiring

**Files:**
- Modify: `install.sh`

**Step 1: Add `generate_plugin` function**

```bash
generate_plugin() {
    section "FASE 5: Plugin para Jellyfin"

    local src="frontend/parody-critics-api-client.js"
    local out="parody-critics-plugin.js"

    if [ ! -f "$src" ]; then
        warn "No se encontró $src. Asegúrate de ejecutar install.sh desde el directorio raíz del proyecto."
        return
    fi

    cp "$src" "$out"
    # Replace hardcoded port 8000 with configured port
    sed -i "s/:8000\/api/:${PARODY_CRITICS_PORT}\/api/g" "$out"
    ok "Plugin generado: $out"

    echo ""
    echo -e "  ${BOLD}Cómo instalarlo en Jellyfin:${NC}"
    echo ""
    echo "  1. Copia el archivo a tu directorio de plugins de Jellyfin:"
    echo "       cp $out /ruta/a/jellyfin-web/plugins/"
    echo ""
    echo "  2. La URL de la API configurada es:"
    echo "       http://<ip-del-servidor>:${PARODY_CRITICS_PORT}/api"
    echo "     El plugin la detecta automáticamente desde el host de Jellyfin."
    echo ""
    echo "  3. Reinicia Jellyfin y navega a cualquier película para ver las críticas."
    echo ""
}
```

**Step 2: Wire all phases in main**

Add at the bottom of the script (replacing any test calls):

```bash
# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    check_prerequisites
    configure_llm
    configure_jellyfin
    configure_api
    show_summary
    deploy_container
    generate_plugin

    section "INSTALACION COMPLETADA"
    ok "Parody Critics está corriendo en http://localhost:${PARODY_CRITICS_PORT}"
    ok "UI de administración: http://localhost:${PARODY_CRITICS_PORT}/static/index.html"
    echo ""
    echo "  Comandos útiles:"
    echo "    Logs:    docker logs parody-critics-api -f"
    echo "    Estado:  curl http://localhost:${PARODY_CRITICS_PORT}/api/health"
    echo "    Parar:   docker compose down"
    echo ""
    echo -e "  ${BOLD}The spice must flow... and so must the data!${NC}"
    echo ""
}

main "$@"
```

**Step 3: Full end-to-end test**

```bash
bash -n install.sh && echo "Syntax OK"
./install.sh
```

Walk through all 5 phases completely. Verify:
- Model picker appears only after connection validated
- Summary shows masked keys
- `.env` written correctly
- Container starts and health check passes
- Plugin generated with correct port

**Step 4: Final commit**

```bash
git add install.sh
git commit -m "feat: install.sh complete — all phases wired, plugin generation, final UX"
```

---

## Testing Checklist

After completing all tasks, verify these scenarios:

- [ ] Fresh install (no existing container) → completes successfully
- [ ] Update install (container already running) → detects existing, updates, restores if fails
- [ ] Wrong Ollama URL → retries prompt (does not exit)
- [ ] Wrong Groq key → retries prompt (does not exit)
- [ ] Wrong Jellyfin token → retries prompt
- [ ] Health check fails → rollback executed, previous container restored
- [ ] Port already in use by Parody Critics → warns but continues
- [ ] Plugin file generated with correct port
- [ ] fzf available → fuzzy picker shown
- [ ] fzf not available → numbered select shown

---

*SAL-9000 — Landsraad Homelab*
