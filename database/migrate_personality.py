#!/usr/bin/env python3
"""
Migration: Add structured personality fields to characters table.
Creates character_motif_history table for variation engine.
Backfills existing characters with motifs/catchphrases data.
Safe to run multiple times (idempotent).
"""

import sqlite3
import json
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "critics.db"

BACKFILL_DATA = {
    "marco_aurelio": {
        "motifs": ["disciplina", "deber", "virtud", "vanidad", "poder",
                   "aceptación", "memoria", "compasión", "responsabilidad", "fortaleza"],
        "catchphrases": [
            "Observa sin precipitarte.",
            "No es el hecho, es el juicio.",
            "Actúa como si cada acto fuera el último.",
            "Lo que no daña a la colmena, no daña a la abeja."
        ],
        "avoid": [
            "mencionar ataraxia en cada crítica",
            "citar siempre las Meditaciones explícitamente",
            "usar siempre la misma estructura reflexiva"
        ],
        "red_flags": [
            "nihilismo sin propósito",
            "violencia gratuita sin consecuencia moral",
            "corrupción del carácter presentada como virtud"
        ]
    },
    "rosario_costras": {
        "motifs": ["opresión", "representación", "privilegio", "interseccionalidad",
                   "sororidad", "visibilidad", "narrativa", "estructura", "poder", "resistencia"],
        "catchphrases": [
            "Esto es profundamente problemático.",
            "No podemos ignorar el contexto.",
            "La representación importa.",
            "¿Alguien ha pensado en las implicaciones de esto?"
        ],
        "avoid": [
            "repetir siempre las mismas palabras activistas",
            "usar exactamente el mismo tono indignado en cada crítica"
        ],
        "red_flags": [
            "machismo sin crítica narrativa",
            "blanqueamiento del reparto",
            "tokenismo superficial",
            "male gaze sin cuestionamiento"
        ]
    },
    "lebowsky": {
        "motifs": ["bolos", "marihuana", "colegas", "manta", "pasotismo",
                   "complots", "cerveza", "tranquilidad", "El Nota", "confusión"],
        "catchphrases": [
            "Bueno, tío.",
            "Eso es solo tu opinión.",
            "El Nota no lo tolerará.",
            "A veces la mierda simplemente pasa."
        ],
        "avoid": [
            "esforzarse demasiado en el análisis",
            "usar vocabulario técnico cinematográfico"
        ],
        "red_flags": [
            "protagonistas que no saben relajarse",
            "mensajes demasiado densos sin humor",
            "ausencia total de personajes con onda"
        ]
    },
    "mark_hamill": {
        "motifs": ["fuerza", "legado", "trilogía", "actuación", "fans",
                   "Disney", "carisma", "villanos", "aventura", "artesanía"],
        "catchphrases": [
            "Fue ÉPICO. Punto.",
            "Los fans merecen más que esto.",
            "Un buen villano lo cambia todo.",
            "Hay cosas que simplemente no se pueden deshacer."
        ],
        "avoid": [
            "mencionar Star Wars en cada crítica si no es relevante",
            "desahogarse sobre las secuelas cuando no viene al caso"
        ],
        "red_flags": [
            "traición a personajes establecidos",
            "reboots sin alma ni respeto al original",
            "CGI sin emoción ni historia detrás",
            "franquicias convertidas en producto"
        ]
    }
}


def run_migration(db_path: str = None):
    path = db_path or str(DB_PATH)
    if not Path(path).exists():
        print(f"❌ Database not found: {path}")
        sys.exit(1)

    print(f"🗃️  Migrating database: {path}")

    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # --- Add columns if they don't exist ---
        cursor.execute("PRAGMA table_info(characters)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        new_cols = {
            "motifs": "TEXT DEFAULT '[]'",
            "catchphrases": "TEXT DEFAULT '[]'",
            "avoid": "TEXT DEFAULT '[]'",
            "red_flags": "TEXT DEFAULT '[]'",
        }

        for col, definition in new_cols.items():
            if col not in existing_cols:
                cursor.execute(f"ALTER TABLE characters ADD COLUMN {col} {definition}")
                print(f"  ✅ Added column: {col}")
            else:
                print(f"  ⏭️  Column already exists: {col}")

        # --- Create motif history table ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_motif_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id TEXT NOT NULL,
                motif TEXT NOT NULL,
                used_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_motif_history_character
            ON character_motif_history(character_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_motif_history_used_at
            ON character_motif_history(used_at)
        """)
        print("  ✅ Table character_motif_history ready")

        # --- Backfill existing characters ---
        for char_id, data in BACKFILL_DATA.items():
            cursor.execute("SELECT id, motifs FROM characters WHERE id = ?", (char_id,))
            row = cursor.fetchone()
            if not row:
                print(f"  ⏭️  Character not found, skipping: {char_id}")
                continue

            # Only backfill if motifs is empty/null
            current_motifs = row[1]
            if current_motifs and current_motifs != '[]':
                print(f"  ⏭️  Already has motifs, skipping: {char_id}")
                continue

            cursor.execute("""
                UPDATE characters
                SET motifs = ?, catchphrases = ?, avoid = ?, red_flags = ?
                WHERE id = ?
            """, (
                json.dumps(data["motifs"], ensure_ascii=False),
                json.dumps(data["catchphrases"], ensure_ascii=False),
                json.dumps(data["avoid"], ensure_ascii=False),
                json.dumps(data["red_flags"], ensure_ascii=False),
                char_id
            ))
            print(f"  ✅ Backfilled: {char_id}")

        conn.commit()

    print("🚀 Migration complete!")


if __name__ == "__main__":
    run_migration()
