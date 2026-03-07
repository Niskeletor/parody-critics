#!/usr/bin/env bash
# Parody Critics — Interactive Installer
# Run this script on the server where Docker will run.
set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

ok()      { echo -e "${GREEN}  ✓${NC} $*"; }
err()     { echo -e "${RED}  ✗${NC} $*" >&2; }
warn()    { echo -e "${YELLOW}  !${NC} $*"; }
info()    { echo -e "${BLUE}  →${NC} $*"; }
section() { echo -e "\n${BOLD}=== $* ===${NC}\n"; }

# ── State ─────────────────────────────────────────────────────────────────────
USE_FZF=0
PREV_CONTAINER_ID=""
PREV_IMAGE_ID=""
LLM_PROVIDER=""
LLM_OLLAMA_URL=""
LLM_API_KEY=""
LLM_PRIMARY_MODEL=""
LLM_SECONDARY_MODEL=""
JELLYFIN_URL=""
JELLYFIN_API_TOKEN=""
JELLYFIN_DB_PATH=""
PARODY_CRITICS_PORT=""
TMDB_ACCESS_TOKEN=""
BRAVE_API_KEY=""

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

# ── Helpers ───────────────────────────────────────────────────────────────────

# ask_input VAR_NAME "prompt" "default" [secret]
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
ask_optional() {
    local var="$1" prompt="$2"
    printf "  %s (Enter para omitir): " "$prompt"
    local value=""
    read -r value
    printf -v "$var" '%s' "$value"
}

# mask "string" — shows first 4 and last 4 chars
mask() {
    local s="$1"
    if [ ${#s} -le 8 ]; then echo "****"; return; fi
    echo "${s:0:4}****${s: -4}"
}

# pick_model VAR_NAME "title" "newline-separated list"
pick_model() {
    local var="$1" title="$2" models_str="$3"
    local chosen=""

    if [ "$USE_FZF" = "1" ]; then
        chosen=$(echo "$models_str" | fzf \
            --prompt="  $title > " \
            --height=14 \
            --border=rounded \
            --header="Flechas para navegar · Enter para seleccionar · Ctrl-C para cancelar" \
            --no-info 2>/dev/null) || true
    fi

    # Fallback to select if fzf not used or returned empty
    if [ -z "$chosen" ]; then
        local arr=()
        while IFS= read -r line; do
            [ -n "$line" ] && arr+=("$line")
        done <<< "$models_str"
        echo ""
        PS3="  $title (número): "
        select chosen in "${arr[@]}"; do
            [ -n "$chosen" ] && break
            warn "Selección inválida. Elige un número de la lista."
        done
    fi

    if [ -z "$chosen" ]; then
        err "No se seleccionó ningún modelo. Abortando."
        exit 1
    fi
    ok "Modelo seleccionado: $chosen"
    printf -v "$var" '%s' "$chosen"
}

# ── Phase 0: Prerequisites ────────────────────────────────────────────────────

check_prerequisites() {
    section "FASE 0: Prerequisitos"

    if ! docker info > /dev/null 2>&1; then
        err "Docker no está instalado o el daemon no está corriendo."
        err "Instala Docker: https://docs.docker.com/engine/install/"
        exit 1
    fi
    ok "Docker corriendo"

    if ! docker compose version > /dev/null 2>&1; then
        err "docker compose v2 no disponible."
        err "Actualiza Docker o instala el plugin: https://docs.docker.com/compose/install/"
        exit 1
    fi
    ok "docker compose v2 disponible"

    if ! command -v curl > /dev/null 2>&1; then
        err "curl no está instalado. Instálalo: apt install curl"
        exit 1
    fi
    ok "curl disponible"

    if ! command -v python3 > /dev/null 2>&1; then
        err "python3 no está instalado. Instálalo: apt install python3"
        exit 1
    fi
    ok "python3 disponible"

    if command -v fzf > /dev/null 2>&1; then
        USE_FZF=1
        ok "fzf disponible — model picker interactivo activado"
    else
        warn "fzf no encontrado — usando menú numerado (recomendado: apt install fzf)"
    fi

    PREV_CONTAINER_ID=$(docker ps -q -f name=parody-critics-api 2>/dev/null || true)
    if [ -n "$PREV_CONTAINER_ID" ]; then
        PREV_IMAGE_ID=$(docker inspect parody-critics-api --format '{{.Image}}' 2>/dev/null || true)
        warn "Instalación existente detectada (container: ${PREV_CONTAINER_ID:0:12})"
        warn "Esta instalación la actualizará. El servicio se reiniciará brevemente."
    fi
}

# ── Phase 1: LLM ──────────────────────────────────────────────────────────────

fetch_ollama_models() {
    local url="$1"
    curl -sf "$url/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print('\n'.join(models))
"
}

configure_llm_ollama() {
    LLM_PROVIDER="ollama"
    LLM_API_KEY=""
    LLM_SECONDARY_MODEL=""

    ask_input LLM_OLLAMA_URL "URL de Ollama" "http://localhost:11434"

    local attempt=0
    local models_str=""
    while true; do
        info "Conectando con Ollama en $LLM_OLLAMA_URL ..."
        if models_str=$(fetch_ollama_models "$LLM_OLLAMA_URL" 2>/dev/null) && [ -n "$models_str" ]; then
            ok "Conectado. $(echo "$models_str" | wc -l | tr -d ' ') modelos disponibles."
            break
        fi
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 3 ]; then
            err "No se pudo conectar con Ollama tras 3 intentos."
            err "Verifica que Ollama esté corriendo: curl $LLM_OLLAMA_URL/api/tags"
            exit 1
        fi
        warn "Fallo de conexión. Corrige la URL e inténtalo de nuevo."
        ask_input LLM_OLLAMA_URL "URL de Ollama" "$LLM_OLLAMA_URL"
    done

    echo ""
    info "Selecciona el modelo PRIMARIO:"
    pick_model LLM_PRIMARY_MODEL "Modelo primario" "$models_str"

    echo ""
    info "Selecciona el modelo SECUNDARIO (fallback — puede ser el mismo):"
    pick_model LLM_SECONDARY_MODEL "Modelo secundario" "$models_str"
}

# Curated lists for providers without a useful models API
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
        -H "Authorization: Bearer $key" 2>/dev/null) || return 1
    echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
exclude = ['whisper','guard','safeguard','arabic','orpheus','compound']
models = [m['id'] for m in data.get('data',[]) if not any(x in m['id'].lower() for x in exclude)]
print('\n'.join(sorted(models)))
"
}

validate_openai_key() {
    curl -sf "https://api.openai.com/v1/models" \
        -H "Authorization: Bearer $1" > /dev/null 2>&1
}

validate_anthropic_key() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        "https://api.anthropic.com/v1/messages" \
        -H "x-api-key: $1" \
        -H "anthropic-version: 2023-06-01" \
        -H "content-type: application/json" \
        -d '{"model":"claude-haiku-4-5-20251001","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}')
    [ "$http_code" != "401" ] && [ "$http_code" != "403" ]
}

configure_llm_cloud() {
    local provider="$1"
    LLM_PROVIDER="$provider"
    LLM_OLLAMA_URL=""
    LLM_SECONDARY_MODEL=""

    ask_input LLM_API_KEY "API Key de $provider" "" "secret"

    local models_str="" valid attempt=0
    while true; do
        info "Validando API key con $provider ..."
        case "$provider" in
            groq)
                models_str=$(validate_groq_key "$LLM_API_KEY" 2>/dev/null) && valid=0 || valid=1
                ;;
            openai)
                if validate_openai_key "$LLM_API_KEY"; then
                    models_str="$OPENAI_MODELS"; valid=0
                else
                    valid=1
                fi
                ;;
            anthropic)
                if validate_anthropic_key "$LLM_API_KEY"; then
                    models_str="$ANTHROPIC_MODELS"; valid=0
                else
                    valid=1
                fi
                ;;
        esac

        if [ "$valid" -eq 0 ] && [ -n "$models_str" ]; then
            ok "API key válida. $(echo "$models_str" | wc -l | tr -d ' ') modelos disponibles."
            break
        fi

        attempt=$((attempt + 1))
        if [ "$attempt" -ge 3 ]; then
            err "API key inválida tras 3 intentos. Abortando."
            exit 1
        fi
        warn "API key inválida o error de conexión."
        ask_input LLM_API_KEY "API Key de $provider" "" "secret"
    done

    echo ""
    info "Selecciona el modelo PRIMARIO:"
    pick_model LLM_PRIMARY_MODEL "Modelo primario ($provider)" "$models_str"
}

configure_llm() {
    section "FASE 1: Proveedor LLM"

    echo "  ¿Qué proveedor LLM quieres usar?"
    echo ""
    echo "  1) Ollama    — local, requiere GPU"
    echo "  2) Groq      — cloud, tier gratuito disponible"
    echo "  3) OpenAI    — cloud, de pago"
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
            *) warn "Opción inválida. Elige 1, 2, 3 o 4." ;;
        esac
    done
}

# ── Phase 2: Jellyfin ─────────────────────────────────────────────────────────

configure_jellyfin() {
    section "FASE 2: Jellyfin"

    ask_input JELLYFIN_URL "URL de Jellyfin" "http://localhost:8096"

    local attempt=0
    while true; do
        info "Verificando conectividad con Jellyfin ..."
        if curl -sf "$JELLYFIN_URL/System/Info/Public" > /dev/null 2>&1; then
            ok "Jellyfin accesible en $JELLYFIN_URL"
            break
        fi
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 3 ]; then
            err "No se pudo conectar con Jellyfin tras 3 intentos. Abortando."
            exit 1
        fi
        warn "No hay respuesta en $JELLYFIN_URL. Verifica la URL."
        ask_input JELLYFIN_URL "URL de Jellyfin" "$JELLYFIN_URL"
    done

    ask_input JELLYFIN_API_TOKEN "Jellyfin API Token" "" "secret"

    attempt=0
    while true; do
        info "Validando API token ..."
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            "$JELLYFIN_URL/System/Info" \
            -H "X-Emby-Token: $JELLYFIN_API_TOKEN")
        if [ "$http_code" = "200" ]; then
            ok "API token válido."
            break
        fi
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 3 ]; then
            err "Token inválido tras 3 intentos. Abortando."
            exit 1
        fi
        warn "Token inválido (HTTP $http_code). Genera uno en Jellyfin → Dashboard → API Keys."
        ask_input JELLYFIN_API_TOKEN "Jellyfin API Token" "" "secret"
    done

    ask_input JELLYFIN_DB_PATH "Ruta completa a library.db de Jellyfin" ""
    if [ ! -f "$JELLYFIN_DB_PATH" ]; then
        warn "El archivo no existe en '$JELLYFIN_DB_PATH'."
        warn "Puedes continuar pero el sync de biblioteca no funcionará hasta configurarlo."
    else
        ok "Archivo DB encontrado."
    fi
}

# ── Phase 3: API config ───────────────────────────────────────────────────────

configure_api() {
    section "FASE 3: Configuración API"

    ask_input PARODY_CRITICS_PORT "Puerto de la API" "8003"

    if ss -tlnp 2>/dev/null | grep -q ":${PARODY_CRITICS_PORT} "; then
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q parody-critics; then
            ok "Puerto $PARODY_CRITICS_PORT en uso por Parody Critics — se reemplazará."
        else
            warn "El puerto $PARODY_CRITICS_PORT está en uso por otro proceso."
            ask_input PARODY_CRITICS_PORT "Puerto alternativo" "$PARODY_CRITICS_PORT"
        fi
    else
        ok "Puerto $PARODY_CRITICS_PORT disponible."
    fi

    echo ""
    info "TMDB enriquece las sinopsis con más contexto (opcional)."
    info "Obtén tu token gratuito en: https://www.themoviedb.org/settings/api"
    ask_optional TMDB_ACCESS_TOKEN "TMDB Access Token"
    [ -n "$TMDB_ACCESS_TOKEN" ] && ok "TMDB configurado." || info "TMDB omitido."

    echo ""
    info "Brave Search añade contexto de críticas sociales (opcional, 2000 req/mes gratis)."
    ask_optional BRAVE_API_KEY "Brave Search API Key"
    [ -n "$BRAVE_API_KEY" ] && ok "Brave configurado." || info "Brave omitido."
}

# ── Summary ───────────────────────────────────────────────────────────────────

show_summary() {
    section "RESUMEN — Revisa antes de continuar"

    echo -e "  ${BOLD}LLM:${NC}"
    echo "    Provider:   $LLM_PROVIDER"
    [ -n "$LLM_OLLAMA_URL"      ] && echo "    Ollama URL: $LLM_OLLAMA_URL"
    [ -n "$LLM_API_KEY"         ] && echo "    API Key:    $(mask "$LLM_API_KEY")"
    echo "    Modelo 1:   $LLM_PRIMARY_MODEL"
    [ -n "$LLM_SECONDARY_MODEL" ] && echo "    Modelo 2:   $LLM_SECONDARY_MODEL"

    echo -e "\n  ${BOLD}Jellyfin:${NC}"
    echo "    URL:        $JELLYFIN_URL"
    echo "    Token:      $(mask "$JELLYFIN_API_TOKEN")"
    echo "    DB path:    $JELLYFIN_DB_PATH"

    echo -e "\n  ${BOLD}API:${NC}"
    echo "    Puerto:     $PARODY_CRITICS_PORT"
    [ -n "$TMDB_ACCESS_TOKEN" ] \
        && echo "    TMDB:       $(mask "$TMDB_ACCESS_TOKEN")" \
        || echo "    TMDB:       (no configurado)"
    [ -n "$BRAVE_API_KEY" ] \
        && echo "    Brave:      $(mask "$BRAVE_API_KEY")" \
        || echo "    Brave:      (no configurado)"

    echo ""
    local confirm
    read -rp "  ¿Continuar con el deploy? [S/n]: " confirm
    case "${confirm,,}" in
        n|no) echo "Instalación cancelada."; exit 0 ;;
        *)    info "Iniciando deploy..." ;;
    esac
}

# ── Phase 4: Deploy ───────────────────────────────────────────────────────────

write_env() {
    [ -f .env ] && cp .env .env.bak && info "Backup de .env guardado en .env.bak"

    cat > .env.new << EOF
# Generated by install.sh on $(date)
PARODY_CRITICS_ENV=production
PARODY_CRITICS_HOST=0.0.0.0
PARODY_CRITICS_PORT=${PARODY_CRITICS_PORT}
PARODY_CRITICS_DB_PATH=/app/data/critics.db

LLM_PROVIDER=${LLM_PROVIDER}
LLM_OLLAMA_URL=${LLM_OLLAMA_URL}
LLM_API_KEY=${LLM_API_KEY}
LLM_PRIMARY_MODEL=${LLM_PRIMARY_MODEL}
LLM_SECONDARY_MODEL=${LLM_SECONDARY_MODEL}
LLM_TIMEOUT=180
LLM_MAX_RETRIES=2
LLM_ENABLE_FALLBACK=true

JELLYFIN_URL=${JELLYFIN_URL}
JELLYFIN_API_TOKEN=${JELLYFIN_API_TOKEN}
JELLYFIN_DB_PATH=${JELLYFIN_DB_PATH}

TMDB_ACCESS_TOKEN=${TMDB_ACCESS_TOKEN}
BRAVE_API_KEY=${BRAVE_API_KEY}

SYNC_BATCH_SIZE=100
SYNC_MAX_CONCURRENT=5
PARODY_CRITICS_CACHE_DURATION=300
PARODY_CRITICS_LOG_LEVEL=INFO
EOF
    mv .env.new .env
    ok ".env escrito."
}

deploy_container() {
    section "FASE 4: Deploy"

    write_env

    info "Descargando imagen..."
    if ! docker compose pull 2>/dev/null; then
        info "No hay imagen en registry. Construyendo localmente..."
        docker compose build
    fi

    info "Iniciando container..."
    docker compose up -d --force-recreate

    info "Esperando health check (máx 30s)..."
    local healthy=0
    for i in $(seq 1 10); do
        sleep 3
        if curl -sf "http://localhost:${PARODY_CRITICS_PORT}/api/health" > /dev/null 2>&1; then
            healthy=1
            break
        fi
        printf "    Intento %d/10...\r" "$i"
    done
    echo ""

    if [ "$healthy" = "1" ]; then
        ok "Container saludable en http://localhost:${PARODY_CRITICS_PORT}"
        return 0
    fi

    err "Health check fallido. Haciendo rollback..."
    docker compose down 2>/dev/null || true
    if [ -f .env.bak ]; then
        mv .env.bak .env
        warn ".env anterior restaurado."
    fi
    if [ -n "$PREV_CONTAINER_ID" ]; then
        docker start "$PREV_CONTAINER_ID" 2>/dev/null \
            && ok "Container anterior restaurado." \
            || warn "No se pudo restaurar el container anterior."
    fi
    err "Deploy fallido. Revisa los logs: docker logs parody-critics-api"
    err "Tu servicio anterior (si existía) sigue activo."
    exit 1
}

# ── Phase 5: JS Plugin ────────────────────────────────────────────────────────

generate_plugin() {
    section "FASE 5: Plugin para Jellyfin"

    local src="frontend/parody-critics-api-client.js"
    local out="parody-critics-plugin.js"

    if [ ! -f "$src" ]; then
        warn "No se encontró $src."
        warn "Ejecuta install.sh desde el directorio raíz del proyecto."
        return
    fi

    cp "$src" "$out"
    sed -i "s/:8000\/api/:${PARODY_CRITICS_PORT}\/api/g" "$out"
    ok "Plugin generado: $(pwd)/$out"

    echo ""
    echo -e "  ${BOLD}Cómo instalarlo en Jellyfin:${NC}"
    echo ""
    echo "  1. Copia el archivo al directorio de plugins de Jellyfin:"
    echo "       cp $out /ruta/a/jellyfin-web/plugins/"
    echo ""
    echo "  2. El plugin detecta la API automáticamente desde el host de Jellyfin:"
    echo "       http://<ip-del-servidor>:${PARODY_CRITICS_PORT}/api"
    echo ""
    echo "  3. Reinicia Jellyfin y navega a cualquier película para ver las críticas."
    echo ""
}

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
    ok "Parody Critics corriendo en http://localhost:${PARODY_CRITICS_PORT}"
    ok "UI de administración:    http://localhost:${PARODY_CRITICS_PORT}/static/index.html"
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
