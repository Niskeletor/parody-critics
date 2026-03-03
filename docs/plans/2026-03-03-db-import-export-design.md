# DB Import / Export — Design Document

**Date**: 2026-03-03
**Status**: Approved — ready for implementation

---

## Context

The existing export endpoint (`GET /api/admin/db/export`) works but has no integrity verification
and no feedback beyond the browser's download indicator. There is no import endpoint at all.

This design adds a production-grade backup/restore system: strict validation, atomic swap,
pre-import snapshot, and a guided two-step modal UX with progress feedback.

---

## Architecture

```
Card "Copia de Seguridad" (Sistema tab)
  ├── [⬇ Exportar DB]  →  GET  /api/admin/db/export   (improved)
  └── [⬆ Importar DB]  →  POST /api/admin/db/import   (new)

Modal #db-import-modal
  ├── Step 1 — Pre-flight warning
  └── Step 2 — Upload + 4-stage pipeline
```

---

## Backend

### `GET /api/admin/db/export` — improvements

1. `PRAGMA integrity_check` on the live DB before backup
2. `sqlite3.backup()` to tempfile (unchanged)
3. `PRAGMA integrity_check` on the backup file before serving
4. Add `Content-Length` header so browsers show download progress
5. Return structured JSON error (not generic HTTPException) if integrity fails

### `POST /api/admin/db/import` — new endpoint

Accepts `multipart/form-data` with `UploadFile` + optional `force: bool` field.

**Pipeline (4 stages):**

```
1. RECEIVE
   - Read UploadFile up to 100MB hard limit (counted in bytes, not trusting Content-Length)
   - Save to tempfile

2. VERIFY (strict)
   - Magic bytes: first 16 bytes == b"SQLite format 3\x00"
   - File size: 1KB minimum (reject empty/stub DBs), 100MB maximum
   - PRAGMA integrity_check  → must return ["ok"]
   - PRAGMA quick_check      → second pass
   - Required tables present: media, critics, characters, media_fts
   - PRAGMA user_version     → must be compatible with current schema version
   - Row count: at least 1 row in media OR characters (not a blank DB)
   - If any check fails → delete tempfile, return 422 with stage + detail

3. SNAPSHOT
   - sqlite3.backup() of current DB → data/backup_pre_import_YYYY-MM-DD_HH-MM-SS.db
   - If snapshot fails → abort, return 500, production DB untouched

4. ATOMIC SWAP
   - shutil.copy2(tempfile → DB_PATH)  [atomic on same filesystem]
   - Close and reinitialise DatabaseManager connections
   - PRAGMA integrity_check post-swap to confirm
   - Return JSON: { ok, snapshot_path, stats: { media, critics, characters } }
```

**Active operations handling:**

- On request, check `llm_manager.is_generating()`
- If active and `force=false` → return `{ needs_confirmation: true, active_ops: [...] }`
- Frontend shows warning with [Detener y continuar] button
- Re-submit with `force=true` → cancel active LLM jobs, then proceed

**Error responses (structured JSON, never bare HTTPException):**

```json
{ "ok": false, "stage": "verify", "detail": "integrity_check failed at page 142" }
{ "ok": false, "stage": "snapshot", "detail": "Could not write snapshot to data/" }
{ "ok": false, "stage": "swap", "detail": "Copy failed: disk full" }
```

---

## Frontend

### Card changes

Replace current single-button export card with two buttons side by side:

```html
[⬇ Exportar DB]   [⬆ Importar DB]
```

Export button keeps its current behaviour, plus inline status text during verification.

### Modal — Step 1: Pre-flight

Shown when user clicks "Importar DB":

- Warning: "La base de datos actual será reemplazada completamente. Esta acción no se puede deshacer."
- If active ops detected (via pre-check call): "🔄 Hay una generación en curso — [Detener y continuar]"
- Three actions:
  - **[⬇ Exportar backup ahora]** — triggers export download, then auto-advances to step 2
  - **[Ya tengo backup, continuar →]** — advances to step 2 directly
  - **[Cancelar]** — closes modal

### Modal — Step 2: Upload & Restore

- Drag-and-drop zone + click-to-select, accepts `.db` only, max 100MB
- Client-side pre-validation: extension check, `file.size` bounds, magic bytes via `FileReader`
- On submit: 4-stage progress bar with individual stage indicators:

```
████████░░░░░░░░  50%
✅ Subiendo
⏳ Verificando integridad
○  Snapshot de seguridad
○  Restaurando
```

- Stages animate sequentially as backend progresses (optimistic stepping based on response)

### Result states

**Success:**
```
✅ Base de datos restaurada correctamente
   Snapshot guardado: backup_pre_import_2026-03-03_14-32.db
   Datos: 847 películas · 23 críticos · 4.201 críticas
   [Cerrar]
```

**Verification failure:**
```
❌ El archivo no es válido
   → integrity_check falló en página 142
   La base de datos actual no ha sido modificada.
   [Intentar con otro archivo]
```

**Swap failure:**
```
❌ Error al restaurar
   La base de datos original está intacta.
   Snapshot disponible en: backup_pre_import_...db
   [Cerrar]
```

---

## Security

| Check | Where | Detail |
|-------|-------|--------|
| `.db` extension | Frontend | Reject before upload |
| File size 1KB–100MB | Both | Frontend: `file.size`. Backend: bytes read counter |
| Magic bytes `SQLite format 3\x00` | Both | Frontend: FileReader first 16 bytes. Backend: re-check |
| `PRAGMA integrity_check` | Backend | Must return `["ok"]` |
| Required tables | Backend | media, critics, characters, media_fts |
| Schema `user_version` | Backend | Must be compatible |
| Row count minimum | Backend | ≥1 row in media or characters |
| Pre-swap snapshot | Backend | Abort if snapshot fails |
| Post-swap integrity check | Backend | Confirm swap succeeded |

**Atomicity:** `shutil.copy2` is atomic on same-filesystem writes. The original DB file is
not modified until the copy completes successfully.

---

## Files to modify / create

| File | Change |
|------|--------|
| `api/main.py` | Improve export endpoint; add import endpoint with full pipeline |
| `static/index.html` | Expand backup card; add `#db-import-modal` HTML |
| `static/js/app.js` | `exportDatabase()` improved; `importDatabase()` new; modal step logic |
| `static/css/styles.css` | Progress bar stages; import modal styles; drag-drop zone |

No new dependencies required. `UploadFile` and `File` are in FastAPI stdlib.

---

## Out of scope

- Scheduled automatic backups (future)
- Backup history browser (future)
- Authentication layer (homelab — local network only)
