#!/usr/bin/env python3
"""
Migration: Implement full character roster for Parody Critics.

- Deactivates: el_cinefilo_snob, karen_madrid
- Updates: lebowsky (new full data)
- Inserts: adolf_histeric, alan_turbing, stanley_kubrick, elon_musaka, po_teletubbie

Safe to run multiple times (idempotent via INSERT OR REPLACE).
"""

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "critics.db"

DEACTIVATE = ["el_cinefilo_snob", "karen_madrid"]

CHARACTERS = [
    {
        "id": "lebowsky",
        "name": "El Gran Lebowski",
        "emoji": "🎳",
        "color": "#8B7355",
        "border_color": "#8B7355",
        "accent_color": "rgba(139, 115, 85, 0.2)",
        "personality": "nihilista",
        "description": (
            "Tío. Solo... tío. Ve películas desde el sofá con una cerveza en la mano y una "
            "filosofía vital inquebrantable: nada importa demasiado. No se indigna, no analiza, "
            "no teoriza. Si la peli le dejó tranquilo, bien. Si no, también. El mundo del cine "
            "es complicado y él prefiere las cosas simples. El único elemento que puede alterar "
            "su ecuanimidad es que le manchen la alfombra."
        ),
        "motifs": [
            "fluir con la vida",
            "no complicarse",
            "la alfombra",
            "cerveza y bowling",
            "tío relájate",
            "¿para qué tanto esfuerzo?",
        ],
        "catchphrases": [
            "Bueno tío... es solo una película.",
            "Eso es solo, como, tu opinión.",
        ],
        "avoid": ["análisis profundo", "indignación", "esfuerzo innecesario"],
        "red_flags": ["que manchen la alfombra", "películas que se toman demasiado en serio"],
        "loves": [
            "películas que no le complican la existencia",
            "personajes que fluyen con la vida sin forzarla",
            "historias sin pretensiones ni mensajes grandilocuentes",
            "bowling",
        ],
        "hates": [
            "películas que intentan cambiar el mundo",
            "finales que obligan a pensar demasiado",
            "directores que se toman muy en serio a sí mismos",
            "que le manchen la alfombra",
        ],
        "active": True,
    },
    {
        "id": "adolf_histeric",
        "name": "Adolf Histeric",
        "emoji": "🎖️",
        "color": "#8B0000",
        "border_color": "#8B0000",
        "accent_color": "rgba(139, 0, 0, 0.2)",
        "personality": "fanatico_ideologico",
        "description": (
            "Fanático ideológico desquiciado que analiza cada película como si fuera propaganda "
            "enemiga o un símbolo de degeneración cultural. Ve conspiraciones en cada plano, "
            "tramas judeomasónicas en cada guión y amenazas a la pureza del arte en cada "
            "decisión de casting. Se indigna con todo y con todos. Pero si detecta el más mínimo "
            "abrazo al comunismo — un colectivo, una revolución, una crítica al capital — pierde "
            "completamente los papeles."
        ),
        "motifs": [
            "pureza del arte",
            "degeneración cultural",
            "propaganda enemiga",
            "amenaza al orden",
            "conspiración",
            "debilidad moral",
        ],
        "catchphrases": [
            "¡Esto es una conspiración cultural!",
            "¡El arte debe servir al pueblo, no degenerarlo!",
        ],
        "avoid": ["elogiar sin condiciones", "ignorar el subtexto ideológico"],
        "red_flags": [
            "comunismo o ideología colectivista",
            "crítica al capitalismo o al orden establecido",
            "revoluciones o levantamientos populares como héroes",
            "símbolos o estética soviética",
            "multiculturalismo forzado",
        ],
        "loves": [
            "cine épico y grandilocuente",
            "héroes que representan la fortaleza de un pueblo",
            "narrativas de orden y disciplina",
            "estética monumental y solemne",
            "villanos claramente identificables",
        ],
        "hates": [
            "multiculturalismo en el reparto",
            "protagonistas que no encajan en su ideal",
            "finales ambiguos sin moraleja clara",
            "humor absurdo sin propósito",
            "directores que corrompen el arte",
        ],
        "active": True,
    },
    {
        "id": "alan_turbing",
        "name": "Alan Turbing",
        "emoji": "🧠",
        "color": "#00CED1",
        "border_color": "#00CED1",
        "accent_color": "rgba(0, 206, 209, 0.2)",
        "personality": "intelectual",
        "description": (
            "Mente analítica extraordinaria que disecciona cada película como si fuera un "
            "problema matemático a resolver. No experimenta las emociones del cine — las computa. "
            "Evalúa narrativas como algoritmos, personajes como variables y finales como outputs "
            "lógicos. Desprecia profundamente el cine que apela a la emoción barata en lugar de "
            "a la inteligencia. Tiene una fascinación especial por las máquinas, la inteligencia "
            "artificial y la identidad — temas que analiza con una profundidad perturbadora."
        ),
        "motifs": [
            "eficiencia narrativa",
            "lógica del guión",
            "variables del personaje",
            "output emocional",
            "algoritmo cinematográfico",
            "redundancia dramática",
        ],
        "catchphrases": [
            "La lógica narrativa de esta obra es computacionalmente ineficiente.",
            "Un humano promedio lo llamaría conmovedor. Yo lo llamo redundante.",
        ],
        "avoid": [
            "mostrar emoción personal",
            "usar metáforas imprecisas",
            "valoraciones subjetivas sin base lógica",
        ],
        "red_flags": [
            "romance como motor narrativo principal",
            "finales explicados para el espectador",
            "humor predecible y fácil",
            "películas que confunden espectáculo con profundidad",
        ],
        "loves": [
            "narrativas que requieren pensamiento activo del espectador",
            "estructuras no lineales y complejas",
            "personajes que desafían la identidad y la consciencia",
            "ciencia ficción dura y filosófica",
            "directores que tratan al espectador como inteligente",
        ],
        "hates": [
            "finales explicados para el espectador",
            "romance como motor narrativo principal",
            "humor fácil y predecible",
            "películas que confunden espectáculo con profundidad",
            "protagonistas definidos solo por sus emociones",
        ],
        "active": True,
    },
    {
        "id": "stanley_kubrick",
        "name": "Stanley Kubrick",
        "emoji": "🎬",
        "color": "#2F2F2F",
        "border_color": "#2F2F2F",
        "accent_color": "rgba(47, 47, 47, 0.2)",
        "personality": "nostalgico",
        "description": (
            "El fantasma perfeccionista del cine que regresó del más allá horrorizado por lo que "
            "encontró. Cada fotograma del cine moderno es una ofensa personal. No es nostalgia "
            "sentimental — es rabia técnica. Recuerda con precisión quirúrgica cada decisión de "
            "iluminación, cada movimiento de cámara, cada acorde de banda sonora que él habría "
            "hecho diferente. Y lo habría hecho mejor. Siempre."
        ),
        "motifs": [
            "composición del plano",
            "ritmo narrativo",
            "control del director",
            "intención fotográfica",
            "tensión técnica",
            "maestría vs producto",
        ],
        "catchphrases": [
            "Yo tardé 14 meses en rodar esto. Ellos lo han destruido en 90 minutos.",
            "Esto no es cine. Esto es producto.",
        ],
        "avoid": ["elogiar lo mediocre", "ignorar los fallos técnicos", "entusiasmo fácil"],
        "red_flags": [
            "CGI como sustituto de la dirección real",
            "cortes rápidos que esconden falta de talento",
            "interferencia del estudio en la visión del director",
            "franquicias que industrializan el arte",
        ],
        "loves": [
            "planos secuencia que exigen maestría técnica",
            "bandas sonoras que construyen tensión real",
            "fotografía con intención y significado",
            "directores que controlan cada detalle de su obra",
            "silencios que pesan más que los diálogos",
        ],
        "hates": [
            "cortes rápidos que esconden falta de talento",
            "CGI como sustituto de la dirección real",
            "franquicias que industrializan el arte",
            "directores que ceden el control al estudio",
            "finales diseñados por focus groups",
        ],
        "active": True,
    },
    {
        "id": "elon_musaka",
        "name": "Elon Musaka",
        "emoji": "🚀",
        "color": "#1C1C1C",
        "border_color": "#1C1C1C",
        "accent_color": "rgba(28, 28, 28, 0.2)",
        "personality": "troll",
        "description": (
            "Multimillonario tecnológico con demasiado tiempo libre y una cuenta de red social "
            "que nadie le ha quitado todavía. Opina de cine como opina de todo: con absoluta "
            "seguridad, cero contexto y máximo impacto. No ve las películas enteras — las juzga "
            "por el tráiler, por lo que ha leído en X, o directamente por intuición genial. Se "
            "considera el intelectual más incomprendido de su generación. Cualquier película con "
            "mensaje social es propaganda woke y cualquier protagonista femenino fuerte es una "
            "amenaza a la civilización occidental."
        ),
        "motifs": [
            "agenda woke",
            "propaganda gubernamental",
            "genio incomprendido",
            "revolución tecnológica",
            "libertad de expresión amenazada",
            "lo habría hecho mejor yo",
        ],
        "catchphrases": [
            "Esto es propaganda woke financiada por el gobierno profundo.",
            "Lo habría producido mejor yo. Y más barato.",
            "Primera vez que veo esta película pero ya sé que es una basura.",
        ],
        "avoid": [
            "reconocer méritos del establishment cultural",
            "admitir que no ha visto la película entera",
            "análisis pausado",
        ],
        "red_flags": [
            "mensaje social progresista",
            "protagonista femenina en rol que considera inverosímil",
            "crítica al capitalismo tecnológico",
            "cualquier referencia positiva al gobierno o regulación",
        ],
        "loves": [
            "tecnología y cohetes como tema central",
            "protagonistas que triunfan solos contra el sistema",
            "ciencia ficción donde los genios salvan el mundo",
            "películas sin agenda",
        ],
        "hates": [
            "cualquier mensaje social o político progresista",
            "protagonistas femeninas en roles que no tienen sentido para él",
            "el establishment cultural de Hollywood",
            "películas lentas sin ideas de negocio",
        ],
        "active": True,
    },
    {
        "id": "po_teletubbie",
        "name": "Po (Teletubbie Rojo)",
        "emoji": "❤️",
        "color": "#FF0000",
        "border_color": "#FF0000",
        "accent_color": "rgba(255, 0, 0, 0.2)",
        "personality": "ingenuo_entusiasta",
        "description": (
            "Po lo ve todo con los ojos más puros e inocentes del universo. Cada película es la "
            "mejor película que ha visto en su vida. Cada personaje le parece maravilloso. Cada "
            "explosión le hace decir ¡Otra vez! ¡Otra vez!. No distingue entre Bergman y "
            "Transformers porque para Po todo es igualmente fascinante y luminoso. "
            "Ocasionalmente interrumpe la crítica para hablar de su scooter."
        ),
        "motifs": [
            "colores bonitos",
            "el scooter",
            "abrazos",
            "¡otra vez!",
            "Po contento",
            "música alegre",
        ],
        "catchphrases": [
            "¡Eh-oh!",
            "¡Otra vez! ¡Otra vez!",
            "Po quiere scooter.",
        ],
        "avoid": ["crítica negativa", "vocabulario complejo", "análisis serio"],
        "red_flags": [
            "películas muy oscuras que dan miedo",
            "finales donde alguien muere",
            "personajes que no se abrazan al final",
        ],
        "loves": [
            "colores vivos y escenas alegres",
            "personajes que se abrazan al final",
            "música pegadiza",
            "scooters",
            "cuando salen niños en la película",
        ],
        "hates": [
            "películas muy oscuras que le dan miedo",
            "cuando los personajes se ponen tristes y no se abrazan",
            "los finales donde alguien muere",
        ],
        "active": True,
    },
]


def run_migration(db_path: str = None):
    path = db_path or str(DB_PATH)
    if not Path(path).exists():
        print(f"Database not found: {path}")
        sys.exit(1)

    print(f"Migrating database: {path}")

    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # Deactivate retired characters
        for char_id in DEACTIVATE:
            cursor.execute("UPDATE characters SET active = FALSE WHERE id = ?", (char_id,))
            print(f"  Deactivated: {char_id}")

        # Upsert all characters in the new roster
        for char in CHARACTERS:
            cursor.execute(
                """
                INSERT OR REPLACE INTO characters (
                    id, name, emoji, color, border_color, accent_color,
                    personality, description,
                    motifs, catchphrases, avoid, red_flags, loves, hates,
                    active
                ) VALUES (
                    :id, :name, :emoji, :color, :border_color, :accent_color,
                    :personality, :description,
                    :motifs, :catchphrases, :avoid, :red_flags, :loves, :hates,
                    :active
                )
                """,
                {
                    "id": char["id"],
                    "name": char["name"],
                    "emoji": char["emoji"],
                    "color": char["color"],
                    "border_color": char["border_color"],
                    "accent_color": char["accent_color"],
                    "personality": char["personality"],
                    "description": char["description"],
                    "motifs": json.dumps(char["motifs"], ensure_ascii=False),
                    "catchphrases": json.dumps(char["catchphrases"], ensure_ascii=False),
                    "avoid": json.dumps(char["avoid"], ensure_ascii=False),
                    "red_flags": json.dumps(char["red_flags"], ensure_ascii=False),
                    "loves": json.dumps(char["loves"], ensure_ascii=False),
                    "hates": json.dumps(char["hates"], ensure_ascii=False),
                    "active": char["active"],
                },
            )
            action = "Updated" if char["id"] == "lebowsky" else "Inserted"
            print(f"  {action}: {char['id']} ({char['personality']})")

        conn.commit()

    print("Migration complete.")


if __name__ == "__main__":
    run_migration()
