# Design: install.sh — Interactive Installer

**Date:** 2026-03-07
**Status:** Approved

## Goal

Single bash script that gets any Linux user from zero to running Parody Critics in under 5 minutes. No hardcoded values. Safe deploy (does not touch existing container if health check fails).

## Validated Technical Decisions

Tested against live Ollama (192.168.2.69:11434) and Groq API before design:

- **Ollama model discovery**: `GET /api/tags` → `models[].name` — 16 models, clean list
- **Groq model discovery**: `GET /openai/v1/models` → filter out whisper/guard/audio → 10 text models
- **OpenAI/Anthropic**: no useful discovery endpoint → curated list hardcoded in script
- **Model picker**: `fzf` (fuzzy, arrow keys) with fallback to bash `select` (numbered)
- **JSON parsing**: `python3` (always available alongside docker installs)
- **JS plugin**: `frontend/parody-critics-api-client.js` — auto-detects host, only port needs replacement

## Phase Flow

```
PHASE 0 — Prerequisites
PHASE 1 — LLM Configuration
PHASE 2 — Jellyfin Configuration
PHASE 3 — API & Optionals
PHASE 4 — Deploy (safe)
PHASE 5 — JS Plugin generation
```

---

## Phase 0: Prerequisites

Check before asking anything:

- `docker` installed and daemon running (`docker info`)
- `docker compose` v2 available (`docker compose version`)
- `curl` available
- `python3` available
- Detect `fzf` → set `USE_FZF=1` or `USE_FZF=0`
- Detect existing install: `docker ps -q -f name=parody-critics-api`
  - If found → warn: "Existing deployment detected. This will update it."
  - Snapshot: `PREV_CONTAINER_ID` + `PREV_IMAGE_ID`

Fail fast with clear message if Docker is not available.

---

## Phase 1: LLM Configuration

### Provider selection (numbered menu, always)

```
Which LLM provider?
  1) Ollama (local — requires GPU)
  2) Groq   (cloud free tier — no GPU needed)
  3) OpenAI
  4) Anthropic
```

### Ollama flow

1. Ask Ollama URL (default: `http://localhost:11434`)
2. Validate: `curl -sf $URL/api/tags` → success = connected
3. If fail → retry prompt
4. **After validation**: fetch model list from same response
5. Show model picker (fzf or select) for PRIMARY model
6. Show model picker for SECONDARY model (same list, can be same or different)

### Cloud flow (Groq / OpenAI / Anthropic)

1. Ask API key (input hidden: `read -rs`)
2. Validate:
   - Groq/OpenAI: `GET /models` with Bearer token → HTTP 200 = valid key
   - Anthropic: `POST /v1/messages` with minimal payload → not 401 = valid key
3. If fail → retry prompt
4. **After validation**: fetch/build model list
   - Groq: `GET /openai/v1/models` → filter out whisper/guard/audio/safeguard models
   - OpenAI: curated list `[gpt-4o-mini, gpt-4o, gpt-3.5-turbo]`
   - Anthropic: curated list `[claude-haiku-4-5-20251001, claude-sonnet-4-6, claude-opus-4-6]`
5. Show model picker for PRIMARY model
6. No secondary for cloud (leave `LLM_SECONDARY_MODEL=`)

### Model picker function

```bash
pick_model() {
    local title="$1"
    local models_list="$2"   # newline-separated string

    if [ "$USE_FZF" = "1" ]; then
        echo "$models_list" | fzf --prompt="$title > " --height=12 --border
    else
        local arr=()
        while IFS= read -r line; do arr+=("$line"); done <<< "$models_list"
        PS3="$title (#): "
        select choice in "${arr[@]}"; do
            [ -n "$choice" ] && echo "$choice" && break
        done
    fi
}
```

---

## Phase 2: Jellyfin Configuration

All fields required:

1. Ask Jellyfin URL (default: `http://localhost:8096`)
2. Validate connectivity: `curl -sf $URL/System/Info/Public` → HTTP 200
3. If fail → warn + retry
4. Ask Jellyfin API token (hidden input)
5. Validate token: `curl -sf $URL/System/Info -H "X-Emby-Token: $TOKEN"` → HTTP 200
6. If fail → retry
7. Ask Jellyfin DB path (full path, no default — must exist)
8. Validate: `test -f "$JELLYFIN_DB_PATH"` or warn if not accessible

---

## Phase 3: API & Optionals

1. Ask port (default: `8003`) — validate it's a free port (`ss -tlnp | grep :$PORT`)
2. TMDB Access Token (optional — press Enter to skip)
3. Brave API key (optional — press Enter to skip)

---

## Phase 4: Deploy (safe)

### Write config

Write to `.env.new` (not `.env` yet):

```bash
cat > .env.new << EOF
PARODY_CRITICS_ENV=production
PARODY_CRITICS_PORT=$PORT
LLM_PROVIDER=$LLM_PROVIDER
LLM_OLLAMA_URL=$LLM_OLLAMA_URL
LLM_API_KEY=$LLM_API_KEY
LLM_PRIMARY_MODEL=$PRIMARY_MODEL
LLM_SECONDARY_MODEL=$SECONDARY_MODEL
JELLYFIN_URL=$JELLYFIN_URL
JELLYFIN_API_TOKEN=$JELLYFIN_API_TOKEN
JELLYFIN_DB_PATH=$JELLYFIN_DB_PATH
TMDB_ACCESS_TOKEN=$TMDB_TOKEN
BRAVE_API_KEY=$BRAVE_KEY
LLM_TIMEOUT=180
LLM_MAX_RETRIES=2
LLM_ENABLE_FALLBACK=true
SYNC_BATCH_SIZE=100
SYNC_MAX_CONCURRENT=5
PARODY_CRITICS_CACHE_DURATION=300
PARODY_CRITICS_LOG_LEVEL=INFO
EOF
```

### Deploy sequence

```bash
# 1. Move new config into place
mv .env.new .env

# 2. Pull/build image
docker compose pull 2>/dev/null || docker compose build

# 3. Start container
docker compose up -d --force-recreate

# 4. Health check with retry (10 attempts × 3s)
for i in $(seq 1 10); do
    sleep 3
    if curl -sf "http://localhost:$PORT/api/health" > /dev/null; then
        HEALTH_OK=1; break
    fi
done
```

### Rollback on failure

```bash
if [ "$HEALTH_OK" != "1" ]; then
    echo "ERROR: Health check failed. Rolling back..."
    docker compose down
    # Restore previous .env if it existed
    [ -f .env.bak ] && mv .env.bak .env
    # Restart previous container if it was running
    [ -n "$PREV_CONTAINER_ID" ] && docker start "$PREV_CONTAINER_ID"
    echo "Previous service restored. Check logs: docker logs parody-critics-api"
    exit 1
fi
```

Before step 1: `cp .env .env.bak` (if `.env` exists).

---

## Phase 5: JS Plugin

Source: `frontend/parody-critics-api-client.js`
Transform: replace port 8000 → configured port (sed in-place on copy)

```bash
# Detect best API URL to embed
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Copy and patch port
cp frontend/parody-critics-api-client.js parody-critics-plugin.js
sed -i "s/:8000\/api/:$PORT\/api/g" parody-critics-plugin.js

echo ""
echo "Plugin generated: parody-critics-plugin.js"
echo ""
echo "Copy it to your Jellyfin web directory:"
echo "  cp parody-critics-plugin.js /path/to/jellyfin-web/plugins/"
echo ""
echo "The plugin auto-detects the API at: http://<jellyfin-host>:$PORT"
```

---

## Variables Written to .env

| Variable | Source |
|----------|--------|
| `LLM_PROVIDER` | Phase 1 menu |
| `LLM_OLLAMA_URL` | Phase 1 input + validated |
| `LLM_API_KEY` | Phase 1 input + validated |
| `LLM_PRIMARY_MODEL` | Phase 1 picker (post-validation) |
| `LLM_SECONDARY_MODEL` | Phase 1 picker (Ollama only) |
| `JELLYFIN_URL` | Phase 2 input + validated |
| `JELLYFIN_API_TOKEN` | Phase 2 input + validated |
| `JELLYFIN_DB_PATH` | Phase 2 input + validated |
| `PARODY_CRITICS_PORT` | Phase 3 input |
| `TMDB_ACCESS_TOKEN` | Phase 3 optional |
| `BRAVE_API_KEY` | Phase 3 optional |

---

## UX Principles

- Colors: green = success, red = error, yellow = warning, blue = info, bold = section headers
- Each phase prints a clear header: `=== FASE 1: LLM ===`
- Validation always happens before model picker appears
- Retry on validation failure (not exit — give user chance to correct)
- Final summary screen before deploy: show all values (mask API keys)
- Total lines target: ~350 lines

---

*SAL-9000 — Landsraad Homelab*
