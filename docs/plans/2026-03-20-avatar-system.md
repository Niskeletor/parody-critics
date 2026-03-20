# Avatar System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add character avatar images to Parody Critics — generated via ComfyUI (FLUX on Omnius), uploaded manually, or via file upload — displayed in both the SPA admin and the Jellyfin plugin.

**Architecture:** New `avatar_url TEXT` column in `characters` table (auto-migrated on startup). Images stored in `data/avatars/` (Docker volume, persistent). FastAPI mounts `/static/avatars/` pointing to that directory. Three new endpoints handle generate/upload/delete. New `api/avatar_generator.py` handles ComfyUI API calls.

**Tech Stack:** FastAPI, httpx (already in requirements), ComfyUI REST API (Omnius Tailscale `100.84.103.61:8188`), SQLite auto-migration, vanilla JS (SPA + Jellyfin plugin).

---

## Task 1: Config + auto-migration

**Files:**
- Modify: `config.py`
- Modify: `api/main.py` (lines 111–165, `_run_auto_migrations`)

**Step 1: Añadir vars a config.py**

En `config.py`, dentro de la clase `Config`, añadir después del bloque `# Generation settings`:

```python
# Avatar / ComfyUI
COMFYUI_URL = os.getenv('COMFYUI_URL', 'http://100.84.103.61:8188')
AVATAR_STYLE_PROMPT = os.getenv(
    'AVATAR_STYLE_PROMPT',
    'cartoon portrait, caricature, bold colors, thick outlines, white background, high quality, 512x512'
)
AVATAR_NEGATIVE_PROMPT = os.getenv(
    'AVATAR_NEGATIVE_PROMPT',
    'realistic, photo, blurry, text, watermark, multiple people'
)
AVATAR_MAX_SIZE_MB = int(os.getenv('AVATAR_MAX_SIZE_MB', '2'))
AVATAR_DIR = os.getenv('AVATAR_DIR', '/app/data/avatars')
```

**Step 2: Añadir auto-migration de avatar_url**

En `api/main.py`, función `_run_auto_migrations()`, añadir después del bloque de columnas de personality (línea ~130):

```python
# Avatar URL column
if "avatar_url" not in existing_char_cols:
    migrations.append("ALTER TABLE characters ADD COLUMN avatar_url TEXT")
```

**Step 3: Crear directorio avatars al arrancar**

En `api/main.py`, función `lifespan()`, después de `_run_auto_migrations(str(DB_PATH))`:

```python
# Ensure avatars directory exists
avatars_dir = Path(config.AVATAR_DIR)
avatars_dir.mkdir(parents=True, exist_ok=True)
```

**Step 4: Montar /static/avatars/ en FastAPI**

En `api/main.py`, después de la línea que monta `/static` (~línea 265):

```python
# Mount avatars directory (persisted in Docker volume, separate from static/)
avatars_dir = Path(config.AVATAR_DIR)
avatars_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/avatars", StaticFiles(directory=str(avatars_dir)), name="avatars")
```

**Step 5: Verificar manualmente**

```bash
cd /home/paul/workspace/claude/parody-critics-api
python3 -c "from config import get_config; c = get_config(); print(c.COMFYUI_URL, c.AVATAR_DIR)"
```
Expected: `http://100.84.103.61:8188 /app/data/avatars`

---

## Task 2: avatar_generator.py

**Files:**
- Create: `api/avatar_generator.py`

Este módulo encapsula toda la lógica de comunicación con ComfyUI.

```python
"""
🎨 Avatar Generator — ComfyUI FLUX integration for character portrait generation.
Calls Omnius ComfyUI API (Tailscale: 100.84.103.61:8188) to generate character avatars.
"""
import asyncio
import httpx
import json
import uuid
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("avatar_generator")

# ComfyUI basic FLUX txt2img workflow template
# Uses KSampler + CLIPTextEncode + VAEDecode — minimal workflow that works with FLUX.1-dev
_FLUX_WORKFLOW = {
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["11", 0], "text": "POSITIVE_PROMPT"}
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {"clip": ["11", 0], "text": "NEGATIVE_PROMPT"}
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["13", 0], "vae": ["10", 0]}
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "avatar", "images": ["8", 0]}
    },
    "10": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
    "11": {
        "class_type": "DualCLIPLoader",
        "inputs": {
            "clip_name1": "clip_l.safetensors",
            "clip_name2": "t5xxl_fp16.safetensors",
            "type": "flux"
        }
    },
    "12": {
        "class_type": "UNETLoader",
        "inputs": {"unet_name": "flux1-dev.safetensors", "weight_dtype": "fp8_e4m3fn"}
    },
    "13": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 1,
            "denoise": 1,
            "latent_image": ["16", 0],
            "model": ["12", 0],
            "negative": ["7", 0],
            "positive": ["6", 0],
            "sampler_name": "euler",
            "scheduler": "simple",
            "seed": 42,
            "steps": 20
        }
    },
    "16": {
        "class_type": "EmptySD3LatentImage",
        "inputs": {"batch_size": 1, "height": 512, "width": 512}
    }
}


class AvatarGenerator:
    def __init__(self, comfyui_url: str, avatar_dir: str, style_prompt: str, negative_prompt: str):
        self.comfyui_url = comfyui_url.rstrip("/")
        self.avatar_dir = Path(avatar_dir)
        self.style_prompt = style_prompt
        self.negative_prompt = negative_prompt

    async def check_comfyui_available(self) -> bool:
        """Ping ComfyUI /system_stats — returns True if reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.comfyui_url}/system_stats")
                return r.status_code == 200
        except Exception:
            return False

    def _build_prompt(self, character_name: str, personality: str) -> str:
        return f"{character_name}, {personality}, {self.style_prompt}"

    async def generate_avatar(self, character_id: str, character_name: str, personality: str) -> Path:
        """
        Generate avatar via ComfyUI FLUX workflow.
        Returns path to saved PNG file.
        Raises RuntimeError on failure.
        """
        positive = self._build_prompt(character_name, personality)
        workflow = json.loads(json.dumps(_FLUX_WORKFLOW))  # deep copy
        workflow["6"]["inputs"]["text"] = positive
        workflow["7"]["inputs"]["text"] = self.negative_prompt
        # Random seed per generation
        workflow["13"]["inputs"]["seed"] = int(uuid.uuid4().int % (2**32))

        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}

        async with httpx.AsyncClient(timeout=120) as client:
            # Submit prompt
            r = await client.post(f"{self.comfyui_url}/prompt", json=payload)
            if r.status_code != 200:
                raise RuntimeError(f"ComfyUI /prompt failed: {r.status_code} {r.text[:200]}")

            prompt_id = r.json().get("prompt_id")
            if not prompt_id:
                raise RuntimeError(f"ComfyUI returned no prompt_id: {r.text[:200]}")

            logger.info(f"[avatar] prompt_id={prompt_id} character={character_id}")

            # Poll /history until done (max 120s)
            for attempt in range(60):
                await asyncio.sleep(2)
                h = await client.get(f"{self.comfyui_url}/history/{prompt_id}")
                data = h.json()
                if prompt_id not in data:
                    continue

                outputs = data[prompt_id].get("outputs", {})
                # Find SaveImage node output (node "9")
                save_node = outputs.get("9", {})
                images = save_node.get("images", [])
                if not images:
                    continue

                img_info = images[0]
                filename = img_info["filename"]
                subfolder = img_info.get("subfolder", "")

                # Download image from ComfyUI /view
                params = {"filename": filename, "type": "output"}
                if subfolder:
                    params["subfolder"] = subfolder
                img_r = await client.get(f"{self.comfyui_url}/view", params=params)
                if img_r.status_code != 200:
                    raise RuntimeError(f"Failed to download image from ComfyUI: {img_r.status_code}")

                # Save to data/avatars/
                dest = self.avatar_dir / f"{character_id}.png"
                dest.write_bytes(img_r.content)
                logger.info(f"[avatar] saved {dest} ({len(img_r.content)} bytes)")
                return dest

        raise RuntimeError(f"ComfyUI generation timed out after 120s for {character_id}")
```

**Step 1: Verificar que el módulo importa sin errores**

```bash
cd /home/paul/workspace/claude/parody-critics-api
python3 -c "from api.avatar_generator import AvatarGenerator; print('OK')"
```
Expected: `OK`

---

## Task 3: Endpoints en main.py

**Files:**
- Modify: `api/main.py`
- Modify: `models/schemas.py` (añadir `avatar_url` a `CharacterInfo`)

**Step 1: Añadir avatar_url a CharacterInfo en schemas.py**

En `models/schemas.py`, en la clase `CharacterInfo`, añadir:

```python
avatar_url: Optional[str] = None
```

**Step 2: Inicializar AvatarGenerator en lifespan**

En `api/main.py`, en la función `lifespan()`, después de la inicialización de `MediaEnricher`:

```python
from api.avatar_generator import AvatarGenerator
avatar_generator = AvatarGenerator(
    comfyui_url=config.COMFYUI_URL,
    avatar_dir=config.AVATAR_DIR,
    style_prompt=config.AVATAR_STYLE_PROMPT,
    negative_prompt=config.AVATAR_NEGATIVE_PROMPT,
)
app.state.avatar_generator = avatar_generator
```

**Step 3: Endpoint POST /api/characters/{id}/generate-avatar**

Añadir después del endpoint `@app.delete("/api/characters/{character_id}/critics")` (~línea 2152):

```python
@app.post("/api/characters/{character_id}/generate-avatar")
async def generate_character_avatar(character_id: str):
    """Generate avatar for a character via ComfyUI FLUX."""
    # Load character
    rows = db_manager.execute_query(
        "SELECT id, name, personality FROM characters WHERE id = ?",
        (character_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Character not found")
    char = dict(rows[0])

    gen = app.state.avatar_generator

    # Check ComfyUI availability
    if not await gen.check_comfyui_available():
        raise HTTPException(
            status_code=503,
            detail=f"ComfyUI not reachable at {config.COMFYUI_URL}. Check Tailscale connection."
        )

    try:
        dest = await gen.generate_avatar(character_id, char["name"], char["personality"] or "")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    avatar_url = f"/static/avatars/{character_id}.png"
    db_manager.execute_query(
        "UPDATE characters SET avatar_url = ? WHERE id = ?",
        (avatar_url, character_id),
        fetch=False
    )
    return {"avatar_url": avatar_url, "character_id": character_id}


@app.post("/api/characters/{character_id}/avatar")
async def upload_character_avatar(character_id: str, file: UploadFile = File(...)):
    """Upload a custom avatar image (PNG/JPG/WebP, max 2MB)."""
    # Validate character exists
    rows = db_manager.execute_query(
        "SELECT id FROM characters WHERE id = ?", (character_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Character not found")

    # Validate file type
    allowed = {"image/png", "image/jpeg", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed. Use PNG, JPG or WebP.")

    # Validate size
    max_bytes = config.AVATAR_MAX_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large (max {config.AVATAR_MAX_SIZE_MB}MB)")

    # Save file (always as .png regardless of input format — simplifies serving)
    dest = Path(config.AVATAR_DIR) / f"{character_id}.png"
    dest.write_bytes(content)

    avatar_url = f"/static/avatars/{character_id}.png"
    db_manager.execute_query(
        "UPDATE characters SET avatar_url = ? WHERE id = ?",
        (avatar_url, character_id),
        fetch=False
    )
    return {"avatar_url": avatar_url, "character_id": character_id}


@app.delete("/api/characters/{character_id}/avatar")
async def delete_character_avatar(character_id: str):
    """Remove character avatar — reverts to emoji display."""
    rows = db_manager.execute_query(
        "SELECT id FROM characters WHERE id = ?", (character_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Character not found")

    avatar_path = Path(config.AVATAR_DIR) / f"{character_id}.png"
    if avatar_path.exists():
        avatar_path.unlink()

    db_manager.execute_query(
        "UPDATE characters SET avatar_url = NULL WHERE id = ?",
        (character_id,),
        fetch=False
    )
    return {"avatar_url": None, "character_id": character_id}
```

**Step 4: Verificar que execute_query acepta fetch=False**

```bash
grep -n "def execute_query" /home/paul/workspace/claude/parody-critics-api/api/main.py
```

Si `execute_query` no tiene parámetro `fetch`, buscar cómo se hacen las queries de escritura en el código existente y adaptar los UPDATE/DELETE al patrón ya usado.

**Step 5: Test manual con curl**

```bash
# Desde tu máquina (contenedor test en :8004)
curl -s http://192.168.45.181:8004/api/characters | python3 -m json.tool | grep -A2 "marco_aurelio"
# Debe mostrar avatar_url: null (campo nuevo)
```

---

## Task 4: SPA Admin — character cards con avatar UI

**Files:**
- Modify: `static/js/app.js` (función que renderiza character cards ~línea 894–912)

**Step 1: Localizar la función de render de character cards**

```bash
grep -n "character-card\|character-emoji\|loadCharacters\|characterSelector" \
  /home/paul/workspace/claude/parody-critics-api/static/js/app.js | head -20
```

**Step 2: Reemplazar el render de character cards**

Encontrar este bloque (aproximadamente línea 899–910):

```js
characterSelector.innerHTML = characters
    .map(char => `
        <div class="character-card ${char.id}" onclick="app.selectCharacter('${char.id}')">
            <span class="character-emoji">${char.emoji}</span>
            <h3 class="character-name">${char.name}</h3>
            <p class="character-description">${char.description}</p>
        </div>
    `).join('');
```

Reemplazarlo con:

```js
characterSelector.innerHTML = characters
    .map(char => {
        const avatarHtml = char.avatar_url
            ? `<img class="character-avatar" src="${char.avatar_url}?t=${Date.now()}"
                    alt="${char.name}"
                    onerror="this.style.display='none';this.nextElementSibling.style.display='block'">`
            : '';
        const emojiHtml = `<span class="character-emoji" ${char.avatar_url ? 'style="display:none"' : ''}>${char.emoji}</span>`;
        return `
        <div class="character-card ${char.id}" onclick="app.selectCharacter('${char.id}')">
            <div class="character-avatar-wrap">
                ${avatarHtml}
                ${emojiHtml}
                <div class="character-avatar-actions" onclick="event.stopPropagation()">
                    <button class="btn-avatar-gen" title="Generar avatar con IA"
                        onclick="app.generateAvatar('${char.id}', this)">🎨</button>
                    <label class="btn-avatar-upload" title="Subir imagen">
                        📁<input type="file" accept="image/png,image/jpeg,image/webp"
                            onchange="app.uploadAvatar('${char.id}', this)" style="display:none">
                    </label>
                    ${char.avatar_url
                        ? `<button class="btn-avatar-del" title="Eliminar avatar"
                               onclick="app.deleteAvatar('${char.id}', this)">🗑</button>`
                        : ''}
                </div>
            </div>
            <h3 class="character-name">${char.name}</h3>
            <p class="character-description">${char.description?.substring(0, 80)}...</p>
        </div>`;
    }).join('');
```

**Step 3: Añadir métodos al objeto app**

En `static/js/app.js`, añadir los métodos `generateAvatar`, `uploadAvatar`, `deleteAvatar` al objeto principal de la app (buscar el lugar donde están `selectCharacter` u otros métodos similares):

```js
async generateAvatar(characterId, btn) {
    btn.textContent = '⏳';
    btn.disabled = true;
    try {
        const res = await fetch(`${this.apiBase}/api/characters/${characterId}/generate-avatar`, {method: 'POST'});
        if (!res.ok) {
            const err = await res.json();
            alert(`Error generando avatar: ${err.detail}`);
            return;
        }
        await this.loadCharacters(); // refresca la lista
    } catch(e) {
        alert(`Error de red: ${e.message}`);
    } finally {
        btn.textContent = '🎨';
        btn.disabled = false;
    }
},

async uploadAvatar(characterId, input) {
    const file = input.files[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
        const res = await fetch(`${this.apiBase}/api/characters/${characterId}/avatar`, {method: 'POST', body: form});
        if (!res.ok) {
            const err = await res.json();
            alert(`Error subiendo avatar: ${err.detail}`);
            return;
        }
        await this.loadCharacters();
    } catch(e) {
        alert(`Error de red: ${e.message}`);
    }
},

async deleteAvatar(characterId, btn) {
    if (!confirm('¿Eliminar avatar? Volverá al emoji.')) return;
    try {
        const res = await fetch(`${this.apiBase}/api/characters/${characterId}/avatar`, {method: 'DELETE'});
        if (!res.ok) {
            const err = await res.json();
            alert(`Error eliminando avatar: ${err.detail}`);
            return;
        }
        await this.loadCharacters();
    } catch(e) {
        alert(`Error de red: ${e.message}`);
    }
},
```

**Step 4: Añadir CSS para los avatares**

Localizar el CSS inline en `static/index.html` o en `static/css/`. Añadir:

```css
.character-avatar-wrap {
    position: relative;
    width: 80px;
    height: 80px;
    margin: 0 auto 8px;
}
.character-avatar {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--accent, #6366f1);
}
.character-emoji {
    font-size: 48px;
    display: block;
    text-align: center;
    line-height: 80px;
}
.character-avatar-actions {
    position: absolute;
    bottom: -8px;
    right: -8px;
    display: flex;
    gap: 2px;
    opacity: 0;
    transition: opacity 0.2s;
}
.character-card:hover .character-avatar-actions {
    opacity: 1;
}
.btn-avatar-gen, .btn-avatar-upload, .btn-avatar-del {
    background: rgba(0,0,0,0.7);
    border: none;
    border-radius: 4px;
    padding: 2px 4px;
    cursor: pointer;
    font-size: 14px;
    color: white;
}
.btn-avatar-upload {
    cursor: pointer;
    display: inline-block;
    line-height: 1.5;
}
```

**Step 5: Verificar en browser que los botones aparecen al hacer hover**

Abrir `http://192.168.45.181:8004` → sección Personajes → verificar cards con emoji y botones de hover.

---

## Task 5: Plugin Jellyfin — mostrar avatar junto a la crítica

**Files:**
- Modify: `/home/paul/workspace/claude/parody-critics-basic.js`

**Step 1: Localizar el render de la crítica en el plugin**

En `parody-critics-basic.js`, línea ~59–72, función `createParodyCriticCard`. Actualmente:

```js
<strong class="parody-critic-author" style="color:${color};">
    ${escapeHtml(critic.emoji || '🎭')} ${escapeHtml(critic.author)}
</strong>
```

**Step 2: Reemplazar para soportar avatar**

```js
const authorIcon = critic.avatar_url
    ? `<img src="${escapeHtml(critic.avatar_url)}" alt=""
            style="width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:6px;"
            onerror="this.style.display='none'">`
    : `${escapeHtml(critic.emoji || '🎭')} `;

// En el innerHTML del card:
<strong class="parody-critic-author" style="color:${color};">
    ${authorIcon}${escapeHtml(critic.author)}
</strong>
```

**Step 3: Verificar que la API devuelve avatar_url**

El endpoint `/api/critics/{tmdb_id}` devuelve los critics. Verificar que incluye `avatar_url` del personaje:

```bash
curl -s http://192.168.45.181:8004/api/critics/346698 | python3 -m json.tool | grep avatar
```

Si no incluye `avatar_url`, buscar el endpoint `/api/critics/{tmdb_id}` en `api/main.py` y añadir el JOIN o campo al SELECT:

```sql
SELECT c.*, ch.emoji, ch.color, ch.border_color, ch.accent_color, ch.avatar_url, ch.name as author
FROM critics c JOIN characters ch ON c.character_id = ch.id
WHERE c.media_id = ...
```

---

## Task 6: Docker — verificar persistencia de avatars volume

**Files:**
- Check: `docker-compose.yml`
- Optionally modify: `docker-compose.yml` y compose de test en stilgar

**Step 1: Verificar que data/ persiste en el volume**

El `docker-compose.yml` actual tiene:
```yaml
volumes:
  - parody_critics_data:/app/data
```

`AVATAR_DIR=/app/data/avatars` → dentro del volume ✅ No hay nada que cambiar.

**Step 2: Verificar en el compose de test en Stilgar**

```bash
ssh stilgar 'cat /home/stilgar/docker/parody-critics-test/docker-compose.yml | grep -A3 volumes'
```

Debe tener un volume mapeado a `/app/data`. Si usa bind mount, verificar que el directorio `avatars/` se crea automáticamente (lo hace el lifespan).

**Step 3: Añadir COMFYUI_URL al .env de producción y test**

En Stilgar:
```bash
ssh stilgar 'echo "COMFYUI_URL=http://100.84.103.61:8188" >> /home/stilgar/docker/parody-critics-test/.env'
```

---

## Task 7: Build + deploy al contenedor test

**Step 1: Build imagen local**

```bash
cd /home/paul/workspace/claude/parody-critics-api
docker build -t parody-critics-api:latest .
```

**Step 2: Deploy a stilgar**

```bash
docker save parody-critics-api:latest | ssh stilgar 'docker load'
ssh stilgar 'cd /home/stilgar/docker/parody-critics-test && docker compose restart'
```

**Step 3: Verificar que arranca**

```bash
ssh stilgar 'docker logs parody-critics-test --tail=30'
```

Debe mostrar la auto-migration de `avatar_url` y el mount de `/static/avatars`.

**Step 4: Test end-to-end — generar avatar de marco_aurelio**

```bash
curl -X POST http://192.168.45.181:8004/api/characters/marco_aurelio/generate-avatar
```

Si ComfyUI no está disponible → `503` con mensaje claro. Si está disponible → esperar ~20s → `{"avatar_url": "/static/avatars/marco_aurelio.png"}`.

---

## Task 8: Documentar + commit

**Files:**
- Modify: `docs/internal/03-backend.md`

**Step 1: Añadir sección de avatares en 03-backend.md**

Añadir al final:

```markdown
## Sistema de avatares (`api/avatar_generator.py`)

Genera avatares de personajes via ComfyUI FLUX (Omnius, Tailscale `100.84.103.61:8188`).

### Endpoints
- `POST /api/characters/{id}/generate-avatar` — genera con IA, guarda en `data/avatars/`
- `POST /api/characters/{id}/avatar` — upload manual (PNG/JPG/WebP, max 2MB)
- `DELETE /api/characters/{id}/avatar` — elimina fichero + pone `avatar_url=NULL`

### Storage
- `data/avatars/{character_id}.png` — dentro del Docker volume (persistente)
- FastAPI sirve `/static/avatars/` → ese directorio
- `characters.avatar_url TEXT` — columna auto-migrada al arrancar

### Config
| Variable | Default | Descripción |
|----------|---------|-------------|
| `COMFYUI_URL` | `http://100.84.103.61:8188` | URL ComfyUI en Omnius (Tailscale) |
| `AVATAR_STYLE_PROMPT` | `cartoon portrait...` | Estilo base para todos los avatares |
| `AVATAR_NEGATIVE_PROMPT` | `realistic, photo...` | Negative prompt |
| `AVATAR_MAX_SIZE_MB` | `2` | Tamaño máximo upload |
| `AVATAR_DIR` | `/app/data/avatars` | Directorio de avatares |
```

**Step 2: Commit**

```bash
cd /home/paul/workspace/claude/parody-critics-api
git add api/avatar_generator.py api/main.py config.py models/schemas.py \
        static/js/app.js static/index.html docs/internal/03-backend.md \
        docs/plans/2026-03-20-avatar-system.md
git add /home/paul/workspace/claude/parody-critics-basic.js
git commit -m "$(cat <<'EOF'
Add avatar system — ComfyUI FLUX generation + upload + Jellyfin display

- New AvatarGenerator class with ComfyUI FLUX.1-dev workflow
- Three endpoints: generate (AI), upload (manual), delete
- Auto-migration: avatar_url column in characters table
- Docker volume persistence: data/avatars/ inside existing /app/data
- SPA: character cards show avatar with hover buttons (generate/upload/delete)
- Jellyfin plugin: circular avatar 28px next to critic name, emoji fallback
- Config: COMFYUI_URL, AVATAR_STYLE_PROMPT, AVATAR_NEGATIVE_PROMPT, AVATAR_DIR

Co-Authored-By: Niskeletor <pnistalrio@gmail.com>
Co-Authored-By: SAL-9000 <sal9000@landsraad.local>
EOF
)"
```

---

## Notas importantes para la implementación

### ComfyUI workflow
El workflow `_FLUX_WORKFLOW` en `avatar_generator.py` usa los nombres de fichero por defecto de FLUX.1-dev en ComfyUI. Si los modelos en Omnius tienen nombres diferentes, ajustar:
- `"unet_name": "flux1-dev.safetensors"` — verificar con `ls /opt/ollama/models/llm/` o en la UI de ComfyUI
- `"clip_name1": "clip_l.safetensors"` — en ComfyUI → Model Manager

Para inspeccionar qué workflow JSON usa una generación real en ComfyUI, usar el botón "Save (API format)" en la UI de ComfyUI con el workflow cargado.

### execute_query con writes
En `api/main.py`, `DatabaseManager.execute_query()` puede que no tenga parámetro `fetch`. Buscar cómo se hacen UPDATEs en el código existente (ej: línea ~2116 `@app.put("/api/characters/{character_id}")`) y adaptar las queries de escritura al mismo patrón.

### Cache-busting en imágenes
Los avatares se sirven como ficheros estáticos. Al regenerar, el browser puede cachear la versión antigua. Por eso el render usa `?t=${Date.now()}` en el src. No es necesario configurar headers adicionales.
