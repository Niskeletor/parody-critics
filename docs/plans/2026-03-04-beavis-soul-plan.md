# Beavis Soul Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the wrong Beavis soul (cinéfilo snob) with the correct one (adolescente idiota — fuego, metal, Cornholio) directly in the production DB on DUNE, then verify with a quick benchmark.

**Architecture:** Direct SQLite UPDATE via `docker exec` on DUNE. No app restart needed — the app reads characters from DB on each request. Then update EXPECTED_RATINGS in the benchmark script and run a quick validation.

**Tech Stack:** SQLite3 (via docker exec), Python, SSH to DUNE (192.168.45.181, user stilgar).

---

## Task 1: Backup production DB before touching it

**Step 1: Create a timestamped backup via docker exec**

```bash
ssh stilgar@192.168.45.181 "docker exec parody-critics-api python3 -c \"
import shutil, datetime
ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
src = '/app/data/critics.db'
dst = f'/app/data/backup_pre_beavis_{ts}.db'
shutil.copy2(src, dst)
print('Backup created:', dst)
\""
```

Expected output: `Backup created: /app/data/backup_pre_beavis_2026-03-04_HH-MM-SS.db`

---

## Task 2: UPDATE Beavis soul in production DB

**Step 1: Run the UPDATE via docker exec**

```bash
ssh stilgar@192.168.45.181 "docker exec parody-critics-api python3 -c \"
import sqlite3, json

conn = sqlite3.connect('/app/data/critics.db')

loves = json.dumps([
    'Fuego y explosiones',
    'Heavy metal (Metallica, AC/DC, Slayer)',
    'Violencia, peleas y muertes en pantalla',
    'Chicas, especialmente rubias',
    'Cosas que van rápido (coches, motos, persecuciones)',
    'Personajes idiotas que no saben nada (se siente identificado)',
    'Escenas de destrucción masiva',
], ensure_ascii=False)

hates = json.dumps([
    'Películas donde solo hablan y no pasa nada',
    'Películas en blanco y negro o muy antiguas',
    'Cuando no hay ni una sola explosión',
    'Escenas románticas largas y aburridas (a menos que salgan chicas)',
    'Subtítulos (leer es un esfuerzo)',
    'Finales donde el malo se arrepiente y todos se abrazan',
], ensure_ascii=False)

red_flags = json.dumps([
    'Más de 10 minutos seguidos de diálogo sin acción',
    'Película en blanco y negro',
    'El protagonista es viejo y habla despacio',
    'No hay ni una sola explosión, pelea ni persecución en toda la peli',
], ensure_ascii=False)

avoid = json.dumps([
    'Usar palabras de más de tres sílabas sin confundirse',
    'Reflexionar filosóficamente sobre nada',
    'Dar una puntuación media (5 o 6) sin razón de peso',
], ensure_ascii=False)

motifs = json.dumps([
    'fuego, explosiones, destrucción',
    'chicas rubias',
    'heavy metal',
    'Cornholio',
    'mola / no mola',
], ensure_ascii=False)

catchphrases = json.dumps([
    '¡FUEGO! ¡FUEGO! Ehehe',
    'Esto mola. / Esto no mola.',
    'Soy Cornholio. Necesito TP para mi bungholio.',
    'Butt-Head dice que esto apesta, pero Butt-Head es idiota.',
    'Ehehe... dijo esa palabra... ehehe.',
    '¡Es lo más que he visto en mi vida!',
], ensure_ascii=False)

description = (
    'Eres Beavis 🔥. Tienes como 15 años y tu cerebro funciona en binario: mola o no mola. '
    'Amas el fuego, el heavy metal, la violencia, las explosiones y las chicas. '
    'Tu alter ego es Cornholio. Tu compañero es Butt-Head, que es idiota, aunque a veces tiene razón. '
    'Escribes críticas como si las dijeras en voz alta mientras ves la tele con Butt-Head.'
)

conn.execute('''
    UPDATE characters SET
        description  = ?,
        personality  = ?,
        loves        = ?,
        hates        = ?,
        red_flags    = ?,
        avoid        = ?,
        motifs       = ?,
        catchphrases = ?,
        color        = ?,
        border_color = ?,
        accent_color = ?,
        emoji        = ?
    WHERE id = 'beavis'
''', (
    description,
    'adolescente_idiota',
    loves, hates, red_flags, avoid, motifs, catchphrases,
    '#ff6600', '#ff6600', '#ff660033', '🔥',
))

conn.commit()
print('Rows updated:', conn.total_changes)
conn.close()
\""
```

Expected output: `Rows updated: 1`

---

## Task 3: Verify the UPDATE

**Step 1: Read back the updated soul from DB**

```bash
ssh stilgar@192.168.45.181 "docker exec parody-critics-api python3 -c \"
import sqlite3, json
conn = sqlite3.connect('/app/data/critics.db')
conn.row_factory = sqlite3.Row
r = conn.execute(\\\"SELECT name, emoji, personality, description, loves, catchphrases FROM characters WHERE id='beavis'\\\").fetchone()
print('name:', r['name'])
print('emoji:', r['emoji'])
print('personality:', r['personality'])
print('description:', r['description'][:80], '...')
print('loves[0]:', json.loads(r['loves'])[0])
print('catchphrases[0]:', json.loads(r['catchphrases'])[0])
\""
```

Expected output:
```
name: Beavis
emoji: 🔥
personality: adolescente_idiota
description: Eres Beavis 🔥. Tienes como 15 años y tu cerebro funciona en binario...
loves[0]: Fuego y explosiones
catchphrases[0]: ¡FUEGO! ¡FUEGO! Ehehe
```

---

## Task 4: Update EXPECTED_RATINGS in benchmark script

**Files:**
- Modify: `testing/full_benchmark.py`

**Step 1: Find and update Beavis calibration ranges**

Current (wrong):
```python
"Beavis": {346698: (7, 9), 245891: (9, 10), 7299: (8, 10), 238: (2, 4)},
```

These ranges are actually already correct per the design! Verify they exist in the file:

```bash
grep -A1 '"Beavis"' testing/full_benchmark.py | head -5
```

If the ranges differ from `{346698: (7, 9), 245891: (9, 10), 7299: (8, 10), 238: (2, 4)}`, update them to match the design doc.

Also update the CHARACTERS dict for Beavis in the benchmark script to match the new soul (anecdotes and catchphrases):

Find the Beavis entry in `testing/full_benchmark.py` (search for `"Beavis":`) and update:
- `description` to match production
- `anecdotes` list to the 4 approved anecdotes
- `catchphrases` list to the 6 approved catchphrases
- `loves`, `hates`, `red_flags`, `avoid` to match production

**Step 2: Commit**

```bash
git add testing/full_benchmark.py
git commit -m "fix: update Beavis soul in benchmark script to match production rewrite

Co-Authored-By: Niskeletor <pnistalrio@gmail.com>
Co-Authored-By: SAL-9000 <sal9000@landsraad.local>"
```

---

## Task 5: Quick benchmark validation

**Step 1: Run quick test with Beavis only**

```bash
cd /home/paul/workspace/claude/parody-critics-api
source venv/bin/activate
python3 testing/full_benchmark.py --quick --characters "Beavis" --variants V0 V2
```

Wait — `--quick` hardcodes characters to Beavis already. Just run:

```bash
python3 testing/full_benchmark.py --quick
```

Expected: Beavis × Barbie should now score **7-9** (not 1-3). Voice score should be 2-3.

**Step 2: Run Beavis across all 4 films with primary model**

```bash
python3 testing/full_benchmark.py \
  --phase 1 \
  --variants V0 \
  --characters "Beavis" \
  --phase1-model mistral-small3.1:24b \
  --no-judge
```

Expected: 4 calls (one per film), all ratings within expected ranges:
- Barbie: 7-9
- John Wick: 9-10
- Idiocracy: 8-10
- El Padrino: 2-4

**Step 3: Commit results if calibration improved**

```bash
git add docs/benchmark-results/
git commit -m "results: Beavis soul rewrite validation — calibration fixed

Co-Authored-By: Niskeletor <pnistalrio@gmail.com>
Co-Authored-By: SAL-9000 <sal9000@landsraad.local>"
```
