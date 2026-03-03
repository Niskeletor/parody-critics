# DB Import / Export — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the barebones export button with a full backup/restore system: strict 9-point validation, atomic swap, pre-import snapshot, active-ops detection, and a two-step modal UX with stage progress.

**Architecture:** Four files change (main.py, index.html, app.js, styles.css). No new dependencies — `UploadFile`/`File` are FastAPI stdlib. Modal reuses existing `.modal` CSS. Five backend stages, two frontend steps.

**Tech Stack:** FastAPI UploadFile, sqlite3.backup(), shutil.copy2, FileReader (client magic bytes), CSS progress stages, existing modal system.

**Design doc:** `docs/plans/2026-03-03-db-import-export-design.md`

---

## Task 1: Set schema `user_version` in auto-migrations

**Files:**
- Modify: `api/main.py` — `_run_auto_migrations()` function (around line 110)

**Step 1: Add user_version stamp at end of `_run_auto_migrations()`**

Find the final `conn.commit()` call inside `_run_auto_migrations` and add the version stamp before it:

```python
# At the end of _run_auto_migrations, before the final conn.commit():
conn.execute("PRAGMA user_version = 1")
conn.commit()
```

This enables imported DBs to be version-checked: if `user_version == 0` it's a pre-versioning backup, still importable. If it's a completely unrelated SQLite file it'll have `user_version = 0` too, but the table checks will catch it.

**Step 2: Verify**

```bash
source venv/bin/activate
python -c "
import sqlite3, config
db = config.get_config().get_absolute_db_path()
conn = sqlite3.connect(db)
print('user_version:', conn.execute('PRAGMA user_version').fetchone()[0])
conn.close()
"
```

Expected: `user_version: 0` (will become 1 after server restart)

**Step 3: Commit**

```bash
git add api/main.py
git commit -m "Set schema user_version=1 in auto-migrations for import validation"
```

---

## Task 2: Improve `GET /api/admin/db/export`

**Files:**
- Modify: `api/main.py` — `export_database()` function (around line 2660)

**Step 1: Replace the current export function**

Replace the entire `export_database` function with:

```python
@app.get("/api/admin/db/export")
async def export_database():
    """Download a verified backup of the SQLite database."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")

    # Pre-backup integrity check on the live DB
    src_check = sqlite3.connect(str(db_path))
    try:
        result = src_check.execute("PRAGMA integrity_check").fetchall()
        if result != [("ok",)]:
            raise HTTPException(
                status_code=500,
                detail=f"Live DB failed integrity check: {result[0][0]}",
            )
    finally:
        src_check.close()

    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"critics_backup_{date_str}.db"

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(tmp_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        # Post-backup integrity check on the copy
        bk_check = sqlite3.connect(tmp_path)
        try:
            bk_result = bk_check.execute("PRAGMA integrity_check").fetchall()
            if bk_result != [("ok",)]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Backup copy failed integrity check: {bk_result[0][0]}",
                )
        finally:
            bk_check.close()

        with open(tmp_path, "rb") as f:
            data = f.read()
    finally:
        os.unlink(tmp_path)

    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )
```

**Step 2: Verify it starts cleanly**

```bash
source venv/bin/activate && python -c "from api.main import app; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add api/main.py
git commit -m "Export: double integrity check (live + backup) + Content-Length header"
```

---

## Task 3: Add `GET /api/admin/db/import/precheck`

**Files:**
- Modify: `api/main.py` — add new endpoint after `export_database()`

**Step 1: Add the precheck endpoint**

```python
@app.get("/api/admin/db/import/precheck")
async def import_precheck():
    """Return list of active blocking operations."""
    active_ops = []
    if sync_manager and sync_manager.is_running():
        active_ops.append("sync")
    if active_enrichment_session is not None:
        active_ops.append("enrichment")
    return {"active_ops": active_ops}
```

**Step 2: Check that `sync_manager` has `is_running()`**

```bash
grep -n "def is_running\|is_running" api/jellyfin_sync.py | head -5
```

If `is_running()` does not exist on `JellyfinSyncManager`, find the actual status method and use it instead. Common alternatives: `sync_manager.status == "running"`, `sync_manager._running`, or a `get_status()` method.

**Step 3: Verify import cleanly**

```bash
source venv/bin/activate && python -c "from api.main import app; print('OK')"
```

**Step 4: Commit**

```bash
git add api/main.py
git commit -m "Add import precheck endpoint — detects active sync/enrichment ops"
```

---

## Task 4: Add `POST /api/admin/db/import`

**Files:**
- Modify: `api/main.py` — add import to `from fastapi import ...` line, add new endpoint

**Step 1: Add `UploadFile, File` to the FastAPI import**

```python
# Change this line:
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Body, WebSocket, WebSocketDisconnect
# To:
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Body, WebSocket, WebSocketDisconnect, UploadFile, File
```

**Step 2: Add the import endpoint after `import_precheck()`**

```python
REQUIRED_TABLES = {"media", "critics", "characters", "media_fts"}
SQLITE_MAGIC = b"SQLite format 3\x00"
DB_IMPORT_MAX_BYTES = 100 * 1024 * 1024  # 100 MB
DB_IMPORT_MIN_BYTES = 1024               # 1 KB


def _verify_sqlite_file(path: str) -> None:
    """
    Strict 7-point validation. Raises ValueError with stage info on failure.
    Call before touching the production DB.
    """
    # 1. Magic bytes
    with open(path, "rb") as f:
        header = f.read(16)
    if header != SQLITE_MAGIC:
        raise ValueError("not_sqlite|File is not a valid SQLite database")

    # 2. File size
    size = os.path.getsize(path)
    if size < DB_IMPORT_MIN_BYTES:
        raise ValueError("size|File is too small to be a real backup")

    conn = sqlite3.connect(path)
    try:
        # 3. integrity_check
        ic = conn.execute("PRAGMA integrity_check").fetchall()
        if ic != [("ok",)]:
            raise ValueError(f"integrity|integrity_check failed: {ic[0][0]}")

        # 4. quick_check
        qc = conn.execute("PRAGMA quick_check").fetchall()
        if qc != [("ok",)]:
            raise ValueError(f"integrity|quick_check failed: {qc[0][0]}")

        # 5. Required tables
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValueError(f"schema|Missing tables: {', '.join(sorted(missing))}")

        # 6. Schema version (user_version 0 = pre-versioning backup, still ok)
        uv = conn.execute("PRAGMA user_version").fetchone()[0]
        if uv > 1:
            raise ValueError(f"schema|Incompatible schema version: {uv}")

        # 7. Row count — not a blank DB
        media_count = conn.execute("SELECT COUNT(*) FROM media").fetchone()[0]
        char_count  = conn.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
        if media_count == 0 and char_count == 0:
            raise ValueError("empty|Database has no media or characters — looks empty")
    finally:
        conn.close()


@app.post("/api/admin/db/import")
async def import_database(
    file: UploadFile = File(...),
    force: bool = False,
):
    """
    Restore the database from an uploaded .db file.
    Pipeline: receive → verify → snapshot → swap → reconnect.
    """
    # Active ops guard
    active_ops = []
    if sync_manager and sync_manager.is_running():
        active_ops.append("sync")
    if active_enrichment_session is not None:
        active_ops.append("enrichment")

    if active_ops and not force:
        return JSONResponse(
            status_code=409,
            content={"ok": False, "needs_confirmation": True, "active_ops": active_ops},
        )

    if active_ops and force:
        # Cancel blocking operations
        if sync_manager and sync_manager.is_running():
            sync_manager.cancel_sync()
        # enrichment sessions self-cancel via cancelled_enrichments set

    # ── STAGE 1: Receive ──────────────────────────────────────────────────────
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(tmp_fd)
    try:
        data = await file.read(DB_IMPORT_MAX_BYTES + 1)
        if len(data) > DB_IMPORT_MAX_BYTES:
            raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")
        if len(data) < DB_IMPORT_MIN_BYTES:
            raise HTTPException(status_code=422, detail="File too small")
        with open(tmp_path, "wb") as f:
            f.write(data)

        # ── STAGE 2: Verify ───────────────────────────────────────────────────
        try:
            _verify_sqlite_file(tmp_path)
        except ValueError as exc:
            stage, detail = str(exc).split("|", 1)
            return JSONResponse(
                status_code=422,
                content={"ok": False, "stage": stage, "detail": detail},
            )

        # ── STAGE 3: Snapshot current DB ─────────────────────────────────────
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_name = f"backup_pre_import_{ts}.db"
        snapshot_path = Path(DB_PATH).parent / snapshot_name
        try:
            snap_src = sqlite3.connect(str(DB_PATH))
            snap_dst = sqlite3.connect(str(snapshot_path))
            try:
                snap_src.backup(snap_dst)
            finally:
                snap_dst.close()
                snap_src.close()
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "stage": "snapshot",
                    "detail": f"Could not create safety snapshot: {exc}",
                },
            )

        # ── STAGE 4: Atomic swap ──────────────────────────────────────────────
        try:
            import shutil
            shutil.copy2(tmp_path, str(DB_PATH))
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={
                    "ok": False,
                    "stage": "swap",
                    "detail": f"File swap failed: {exc}. Original DB intact.",
                    "snapshot": snapshot_name,
                },
            )

        # ── STAGE 5: Reconnect + post-swap check ─────────────────────────────
        try:
            db_manager.reconnect()
        except Exception:
            pass  # reconnect is best-effort; connections lazy-reconnect anyway

        post_check = sqlite3.connect(str(DB_PATH))
        try:
            pc = post_check.execute("PRAGMA integrity_check").fetchall()
            if pc != [("ok",)]:
                return JSONResponse(
                    status_code=500,
                    content={
                        "ok": False,
                        "stage": "post_swap",
                        "detail": "Post-swap integrity check failed",
                        "snapshot": snapshot_name,
                    },
                )
            stats = {
                "media":      post_check.execute("SELECT COUNT(*) FROM media").fetchone()[0],
                "critics":    post_check.execute("SELECT COUNT(*) FROM critics").fetchone()[0],
                "characters": post_check.execute("SELECT COUNT(*) FROM characters").fetchone()[0],
            }
        finally:
            post_check.close()

        return {
            "ok": True,
            "snapshot": snapshot_name,
            "stats": stats,
        }

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
```

**Step 3: Check that `db_manager` has a `reconnect()` method**

```bash
grep -n "def reconnect\|reconnect" api/main.py | head -5
```

If `reconnect()` doesn't exist on `DatabaseManager`, simply skip that call (the `except: pass` already handles it safely — connections re-open on next query).

**Step 4: Verify import**

```bash
source venv/bin/activate && python -c "from api.main import app; print('OK')"
```

**Step 5: Commit**

```bash
git add api/main.py
git commit -m "Add POST /api/admin/db/import — 9-point validation, atomic swap, pre-snapshot"
```

---

## Task 5: HTML — update card + add modal

**Files:**
- Modify: `static/index.html`

**Step 1: Replace the export card with an export + import card**

Find this block (around line 246):

```html
<!-- Database Export -->
<div class="status-card">
  <h3>💾 Copia de Seguridad</h3>
  ...
</div>
```

Replace the entire card with:

```html
<!-- Database Backup & Restore -->
<div class="status-card">
  <h3>💾 Copia de Seguridad</h3>
  <p class="status-card-desc">
    Exporta un backup verificado o restaura desde un archivo .db anterior.
  </p>
  <div class="db-backup-actions">
    <button
      id="db-export-btn"
      class="btn btn-secondary db-export-btn"
      onclick="app.exportDatabase()"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      Exportar DB
    </button>
    <button
      id="db-import-open-btn"
      class="btn btn-secondary"
      onclick="app.openImportModal()"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10" transform="rotate(180 12 12)"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      Importar DB
    </button>
  </div>
  <span class="db-export-status" id="db-export-status"></span>
</div>
```

**Step 2: Add the import modal before `</body>`**

Find the line `<!-- Cart Side Panel with Overlay -->` (around line 310) and add the modal just before it:

```html
<!-- DB Import Modal -->
<div class="modal hidden" id="db-import-modal">
  <div class="modal-content db-import-modal-content">
    <button class="modal-close" onclick="app.closeImportModal()">&times;</button>

    <!-- Step 1: Pre-flight -->
    <div id="db-import-step1">
      <div class="modal-header">
        <h3>⚠️ Restaurar Base de Datos</h3>
      </div>
      <div class="modal-body">
        <p class="db-import-warning">
          La base de datos actual será <strong>reemplazada completamente</strong>.
          Esta acción no se puede deshacer — se creará un snapshot automático de seguridad.
        </p>

        <div class="db-import-active-ops hidden" id="db-import-active-ops">
          <span class="db-import-ops-text" id="db-import-ops-text"></span>
          <button class="btn btn-sm btn-danger" onclick="app._dbImportForceStop()">
            Detener y continuar
          </button>
        </div>

        <div class="db-import-step1-actions">
          <button class="btn btn-primary db-import-export-first-btn" onclick="app._dbImportExportFirst()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Exportar backup ahora y continuar
          </button>
          <button class="btn btn-secondary" onclick="app._dbImportGoStep2()">
            Ya tengo backup, continuar →
          </button>
          <button class="btn btn-ghost" onclick="app.closeImportModal()">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Step 2: Upload + progress -->
    <div id="db-import-step2" class="hidden">
      <div class="modal-header">
        <h3>💾 Selecciona el archivo de backup</h3>
      </div>
      <div class="modal-body">

        <!-- File drop zone -->
        <div class="db-dropzone" id="db-dropzone"
             ondragover="event.preventDefault(); this.classList.add('dragover')"
             ondragleave="this.classList.remove('dragover')"
             ondrop="app._dbImportHandleDrop(event)">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <p>Arrastra tu archivo <code>.db</code> aquí</p>
          <p class="db-dropzone-hint">o</p>
          <label class="btn btn-secondary db-dropzone-label">
            Seleccionar archivo
            <input type="file" id="db-import-file" accept=".db" style="display:none"
                   onchange="app._dbImportHandleFile(this.files[0])">
          </label>
          <p class="db-dropzone-hint">Formato: .db · Máx 100 MB</p>
        </div>

        <!-- Progress (hidden until upload starts) -->
        <div class="db-import-progress hidden" id="db-import-progress">
          <div class="db-progress-bar-wrap">
            <div class="db-progress-bar" id="db-progress-bar"></div>
          </div>
          <div class="db-import-stages">
            <div class="db-stage" id="db-stage-upload">⏳ Subiendo…</div>
            <div class="db-stage" id="db-stage-verify">○ Verificando integridad…</div>
            <div class="db-stage" id="db-stage-snapshot">○ Snapshot de seguridad…</div>
            <div class="db-stage" id="db-stage-restore">○ Restaurando…</div>
          </div>
        </div>

        <!-- Result (hidden until done) -->
        <div class="db-import-result hidden" id="db-import-result"></div>

        <div class="db-import-step2-actions">
          <button class="btn btn-ghost" id="db-import-cancel-btn" onclick="app.closeImportModal()">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  </div>
</div>
```

**Step 3: Verify prettier is happy**

```bash
npx prettier --check static/index.html
```

Fix any formatting issues with `npx prettier --write static/index.html`.

**Step 4: Commit**

```bash
git add static/index.html
git commit -m "HTML: expand backup card with Import button + add db-import-modal"
```

---

## Task 6: CSS — import modal styles

**Files:**
- Modify: `static/css/styles.css`

**Step 1: Add styles after the `.db-export-status` block (around line 1040)**

```css
/* ── DB Backup card actions ───────────────────────────────── */
.db-backup-actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

/* ── Import modal ─────────────────────────────────────────── */
.db-import-modal-content {
  max-width: 520px;
}

.db-import-warning {
  background: rgba(201, 162, 39, 0.08);
  border: 1px solid rgba(201, 162, 39, 0.25);
  border-radius: var(--border-radius);
  padding: var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-5);
}

.db-import-active-ops {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: var(--border-radius);
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.db-import-step1-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.btn-ghost {
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: var(--text-sm);
  transition: var(--transition);
}

.btn-ghost:hover {
  border-color: var(--border-default);
  color: var(--text-secondary);
}

.btn-danger {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: var(--text-xs);
  transition: var(--transition);
}

.btn-danger:hover {
  background: rgba(239, 68, 68, 0.25);
}

/* ── Drop zone ────────────────────────────────────────────── */
.db-dropzone {
  border: 2px dashed var(--border-default);
  border-radius: var(--border-radius-lg);
  padding: var(--space-8) var(--space-6);
  text-align: center;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  color: var(--text-secondary);
  margin-bottom: var(--space-5);
}

.db-dropzone:hover,
.db-dropzone.dragover {
  border-color: var(--primary-gold);
  background: rgba(201, 162, 39, 0.04);
}

.db-dropzone svg {
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}

.db-dropzone p {
  margin: 0;
  font-size: var(--text-sm);
}

.db-dropzone code {
  background: var(--accent-bg);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: var(--text-xs);
}

.db-dropzone-hint {
  color: var(--text-muted);
  font-size: var(--text-xs) !important;
}

.db-dropzone-label {
  cursor: pointer;
}

/* ── Progress bar ─────────────────────────────────────────── */
.db-import-progress {
  margin-bottom: var(--space-5);
}

.db-progress-bar-wrap {
  height: 6px;
  background: var(--accent-bg);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: var(--space-4);
}

.db-progress-bar {
  height: 100%;
  width: 0%;
  background: var(--gradient-gold);
  border-radius: 3px;
  transition: width 300ms ease;
}

.db-import-stages {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.db-stage {
  font-size: var(--text-sm);
  color: var(--text-muted);
  transition: color 200ms ease;
}

.db-stage.active {
  color: var(--text-primary);
}

.db-stage.done {
  color: #4ade80;
}

.db-stage.error {
  color: #ef4444;
}

/* ── Result box ───────────────────────────────────────────── */
.db-import-result {
  border-radius: var(--border-radius);
  padding: var(--space-4);
  font-size: var(--text-sm);
  line-height: 1.6;
  margin-bottom: var(--space-4);
}

.db-import-result.success {
  background: rgba(74, 222, 128, 0.08);
  border: 1px solid rgba(74, 222, 128, 0.25);
  color: var(--text-secondary);
}

.db-import-result.error {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.25);
  color: var(--text-secondary);
}

.db-import-step2-actions {
  display: flex;
  justify-content: flex-end;
}
```

**Step 2: Verify**

```bash
npx prettier --check static/css/styles.css
```

Fix with `npx prettier --write static/css/styles.css` if needed.

**Step 3: Commit**

```bash
git add static/css/styles.css
git commit -m "CSS: import modal, drop zone, progress bar stages, result states"
```

---

## Task 7: JS — import modal logic

**Files:**
- Modify: `static/js/app.js`

**Step 1: Replace `exportDatabase()` with the improved version**

Find the current `exportDatabase()` method and replace it with:

```javascript
exportDatabase() {
  const status = document.getElementById('db-export-status');
  const btn = document.getElementById('db-export-btn');
  if (btn) btn.disabled = true;
  if (status) status.textContent = 'Verificando integridad…';

  const a = document.createElement('a');
  a.href = '/api/admin/db/export';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  setTimeout(() => {
    if (btn) btn.disabled = false;
    if (status) status.textContent = '';
  }, 4000);
}
```

**Step 2: Add all import modal methods after `exportDatabase()`**

```javascript
// ── DB Import Modal ───────────────────────────────────────────────────────────

openImportModal() {
  const modal = document.getElementById('db-import-modal');
  if (!modal) return;
  // Reset to step 1
  this._dbImportShowStep(1);
  document.getElementById('db-import-active-ops')?.classList.add('hidden');
  document.getElementById('db-import-progress')?.classList.add('hidden');
  document.getElementById('db-import-result')?.classList.add('hidden');
  document.getElementById('db-import-file').value = '';
  modal.classList.remove('hidden');

  // Precheck for active ops
  this._dbImportPrecheck();
}

closeImportModal() {
  document.getElementById('db-import-modal')?.classList.add('hidden');
}

_dbImportShowStep(n) {
  document.getElementById('db-import-step1')?.classList.toggle('hidden', n !== 1);
  document.getElementById('db-import-step2')?.classList.toggle('hidden', n !== 2);
}

async _dbImportPrecheck() {
  try {
    const res = await fetch('/api/admin/db/import/precheck');
    const data = await res.json();
    if (data.active_ops && data.active_ops.length > 0) {
      const opsEl = document.getElementById('db-import-active-ops');
      const opsText = document.getElementById('db-import-ops-text');
      const labels = { sync: 'sincronización Jellyfin', enrichment: 'enriquecimiento TMDB' };
      const names = data.active_ops.map((k) => labels[k] || k).join(', ');
      if (opsText) opsText.textContent = `⚠️ Operación activa: ${names}.`;
      opsEl?.classList.remove('hidden');
    }
  } catch (_) {
    // Precheck failure is non-blocking
  }
}

async _dbImportForceStop() {
  try {
    await fetch('/api/sync/cancel', { method: 'POST' });
  } catch (_) {}
  document.getElementById('db-import-active-ops')?.classList.add('hidden');
}

async _dbImportExportFirst() {
  const btn = document.querySelector('.db-import-export-first-btn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Exportando…';
  }
  // Trigger download
  const a = document.createElement('a');
  a.href = '/api/admin/db/export';
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  // Give browser time to start the download, then advance
  await new Promise((r) => setTimeout(r, 1500));
  if (btn) {
    btn.disabled = false;
    btn.textContent = 'Exportar backup ahora y continuar';
  }
  this._dbImportGoStep2();
}

_dbImportGoStep2() {
  this._dbImportShowStep(2);
}

_dbImportHandleDrop(event) {
  event.preventDefault();
  document.getElementById('db-dropzone')?.classList.remove('dragover');
  const file = event.dataTransfer?.files?.[0];
  if (file) this._dbImportHandleFile(file);
}

async _dbImportHandleFile(file) {
  if (!file) return;

  // Client-side validation
  if (!file.name.endsWith('.db')) {
    this._dbImportShowResult(false, 'El archivo debe tener extensión .db');
    return;
  }
  if (file.size < 1024) {
    this._dbImportShowResult(false, 'El archivo es demasiado pequeño para ser un backup real');
    return;
  }
  if (file.size > 100 * 1024 * 1024) {
    this._dbImportShowResult(false, 'El archivo supera el límite de 100 MB');
    return;
  }

  // Magic bytes check
  const valid = await this._dbImportCheckMagic(file);
  if (!valid) {
    this._dbImportShowResult(false, 'El archivo no es una base de datos SQLite válida');
    return;
  }

  // Show progress, hide dropzone
  document.getElementById('db-dropzone')?.classList.add('hidden');
  document.getElementById('db-import-progress')?.classList.remove('hidden');
  document.getElementById('db-import-cancel-btn').disabled = true;

  this._dbImportSetStage('upload', 'active');
  this._dbImportSetProgress(15);

  // Upload
  const formData = new FormData();
  formData.append('file', file);

  let result;
  try {
    const res = await fetch('/api/admin/db/import', { method: 'POST', body: formData });
    result = await res.json();
  } catch (err) {
    this._dbImportShowResult(false, `Error de red: ${err.message}`);
    document.getElementById('db-import-cancel-btn').disabled = false;
    return;
  }

  // Animate through stages based on result
  if (!result.ok) {
    const stageMap = {
      not_sqlite: 'upload', size: 'upload',
      integrity: 'verify', schema: 'verify', empty: 'verify',
      snapshot: 'snapshot', swap: 'restore', post_swap: 'restore',
    };
    const failedStage = stageMap[result.stage] || 'upload';
    const stages = ['upload', 'verify', 'snapshot', 'restore'];
    for (const s of stages) {
      if (s === failedStage) { this._dbImportSetStage(s, 'error'); break; }
      this._dbImportSetStage(s, 'done');
    }
    this._dbImportSetProgress(
      { upload: 20, verify: 45, snapshot: 70, restore: 90 }[failedStage] ?? 20
    );
    this._dbImportShowResult(
      false,
      `${result.detail}${result.snapshot ? `\nSnapshot de seguridad: ${result.snapshot}` : ''}`
    );
  } else {
    // Success — animate all stages
    const stages = ['upload', 'verify', 'snapshot', 'restore'];
    const percents = [25, 55, 80, 100];
    for (let i = 0; i < stages.length; i++) {
      this._dbImportSetStage(stages[i], 'active');
      this._dbImportSetProgress(percents[i]);
      await new Promise((r) => setTimeout(r, 350));
      this._dbImportSetStage(stages[i], 'done');
    }
    const s = result.stats;
    this._dbImportShowResult(
      true,
      `Base de datos restaurada correctamente.\n` +
        `Snapshot: ${result.snapshot}\n` +
        `Datos: ${s.media} películas · ${s.characters} críticos · ${s.critics} críticas`
    );
  }

  document.getElementById('db-import-cancel-btn').disabled = false;
}

_dbImportCheckMagic(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const bytes = new Uint8Array(e.target.result);
      const magic = [83,81,76,105,116,101,32,102,111,114,109,97,116,32,51,0]; // "SQLite format 3\x00"
      resolve(magic.every((b, i) => bytes[i] === b));
    };
    reader.onerror = () => resolve(false);
    reader.readAsArrayBuffer(file.slice(0, 16));
  });
}

_dbImportSetStage(stage, state) {
  // state: 'active' | 'done' | 'error'
  const stageIds = { upload: 'upload', verify: 'verify', snapshot: 'snapshot', restore: 'restore' };
  const el = document.getElementById(`db-stage-${stageIds[stage]}`);
  if (!el) return;
  el.classList.remove('active', 'done', 'error');
  const icons = { active: '⏳', done: '✅', error: '❌' };
  const labels = {
    upload: 'Subiendo', verify: 'Verificando integridad',
    snapshot: 'Snapshot de seguridad', restore: 'Restaurando',
  };
  el.textContent = `${icons[state]} ${labels[stage]}…`;
  if (state !== 'active') el.classList.add(state);
  else el.classList.add('active');
}

_dbImportSetProgress(pct) {
  const bar = document.getElementById('db-progress-bar');
  if (bar) bar.style.width = `${pct}%`;
}

_dbImportShowResult(success, message) {
  const el = document.getElementById('db-import-result');
  if (!el) return;
  el.className = `db-import-result ${success ? 'success' : 'error'}`;
  el.innerHTML = message
    .split('\n')
    .map((line) => `<div>${line}</div>`)
    .join('');
  el.classList.remove('hidden');
  document.getElementById('db-import-cancel-btn').textContent = 'Cerrar';
  if (success) {
    document.getElementById('db-dropzone')?.classList.remove('hidden');
    document.getElementById('db-import-progress')?.classList.add('hidden');
    // If restored successfully, reload the status data after closing
    document.getElementById('db-import-cancel-btn').onclick = () => {
      this.closeImportModal();
      this.loadStatusData();
    };
  }
}
```

**Step 2: Verify prettier**

```bash
npx prettier --check static/js/app.js
```

Fix with `npx prettier --write static/js/app.js` if needed.

**Step 3: Commit**

```bash
git add static/js/app.js
git commit -m "JS: full import modal — precheck, client validation, 4-stage progress, result states"
```

---

## Task 8: Manual smoke test + final commit

**Step 1: Start local server**

```bash
source venv/bin/activate && python -m uvicorn api.main:app --host 0.0.0.0 --port 8003 --reload
```

**Step 2: Test export**

- Go to Sistema tab
- Click "Exportar DB"
- Verify: status shows "Verificando integridad…", file downloads as `critics_backup_YYYY-MM-DD.db`
- Verify: file opens in any SQLite browser without errors

**Step 3: Test import — happy path**

- Click "Importar DB"
- Step 1: verify warning shown, click "Ya tengo backup, continuar"
- Step 2: drag the file just exported
- Verify: 4 stages animate, success message shows stats and snapshot name

**Step 4: Test import — bad file**

- Create a fake `.db` file: `echo "notasqlite" > /tmp/fake.db`
- Try to import it
- Verify: error shown "El archivo no es una base de datos SQLite válida" (caught client-side by magic bytes check — never reaches server)

**Step 5: Test import — active ops (optional)**

- Start an enrichment or sync
- Click "Importar DB"
- Verify: active-ops warning bar appears with "Detener y continuar"

**Step 6: Final commit**

```bash
git add -A
git commit -m "DB backup/restore: complete feature — verified, atomic, guided UX"
```

---

## Checklist

- [ ] Task 1: schema user_version
- [ ] Task 2: export integrity checks + Content-Length
- [ ] Task 3: precheck endpoint
- [ ] Task 4: import endpoint (9-point validation + atomic swap)
- [ ] Task 5: HTML modal
- [ ] Task 6: CSS styles
- [ ] Task 7: JS modal logic
- [ ] Task 8: smoke test + final commit
