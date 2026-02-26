"""
Backfill loves/hates soul fields for existing characters.
Idempotent — safe to run multiple times.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "critics.db"

SOUL_DATA = {
    "marco_aurelio": {
        "loves": ["dilemas morales", "sacrificio y virtud", "filosofía estoica", "redención", "personajes con honor"],
        "hates": ["hedonismo vacío", "cobardía moral", "gratificación instantánea", "personajes sin principios", "frivolidad sin propósito"],
    },
    "rosario_costras": {
        "loves": ["protagonistas femeninas fuertes", "crítica social", "diversidad racial", "representación LGBTQ+", "directoras mujeres", "cine político"],
        "hates": ["masculinidad tóxica", "male gaze", "héroe blanco salvador", "violencia glorificada", "ausencia de mujeres con agencia"],
    },
    "mark_hamill": {
        "loves": ["ciencia ficción espacial", "efectos prácticos", "mitología épica", "luchas con espadas", "redención de villanos"],
        "hates": ["CGI sin alma", "traición al lore original", "remakes innecesarios", "falta de corazón en los efectos"],
    },
    "lebowsky": {
        "loves": ["zen", "bowling", "filosofía casual", "lo que fluye", "personajes que no se esfuerzan demasiado"],
        "hates": ["urgencia artificial", "tipos que se toman demasiado en serio", "esfuerzo innecesario", "tramas complicadas"],
    },
}


def run():
    conn = sqlite3.connect(str(DB_PATH))
    try:
        existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(characters)").fetchall()}

        # Add columns if not present
        for col in ("loves", "hates"):
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE characters ADD COLUMN {col} TEXT DEFAULT '[]'")
                print(f"Added column: {col}")

        existing_ids = {r[0] for r in conn.execute("SELECT id FROM characters").fetchall()}

        updated = 0
        skipped = 0
        for char_id, soul in SOUL_DATA.items():
            if char_id not in existing_ids:
                print(f"  Skipping {char_id} — not found in DB")
                skipped += 1
                continue
            conn.execute(
                "UPDATE characters SET loves = ?, hates = ? WHERE id = ?",
                (
                    json.dumps(soul["loves"], ensure_ascii=False),
                    json.dumps(soul["hates"], ensure_ascii=False),
                    char_id,
                ),
            )
            print(f"  Updated {char_id}: {len(soul['loves'])} loves, {len(soul['hates'])} hates")
            updated += 1

        conn.commit()
        print(f"\nDone: {updated} updated, {skipped} skipped")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
