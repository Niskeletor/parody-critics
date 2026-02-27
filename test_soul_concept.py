"""
Soul Concept Validation Test
Tests whether loves/hates fields produce measurably different LLM critiques.

Character: Rosario Costras — progressive activist
Films: Rambo II (1985) vs Everything Everywhere All at Once (2022)
Variants: WITH soul (loves/hates) vs WITHOUT soul (base description only)
"""

import httpx
import re
import time

OLLAMA_URL = "http://192.168.45.104:11434/api/generate"
MODEL = "qwen3:8b"
TIMEOUT = 180

# --- Character definition ---

CHARACTER_NAME = "Rosario Costras"
CHARACTER_DESCRIPTION = (
    "Activista progresista del siglo XXI, crítica feroz de estructuras de poder. "
    "Analiza todo desde una perspectiva de justicia social."
)
CHARACTER_LOVES = [
    "protagonistas femeninas fuertes",
    "crítica social",
    "diversidad racial",
    "representación LGBTQ+",
    "directoras mujeres",
]
CHARACTER_HATES = [
    "masculinidad tóxica",
    "male gaze",
    "héroe blanco salvador",
    "violencia glorificada",
    "ausencia de mujeres",
]

# --- Film definitions ---

FILMS = {
    "rambo": {
        "title": "Rambo: First Blood Part II",
        "year": 1985,
        "genres": "Acción, Guerra",
        "synopsis": (
            "John Rambo, veterano de Vietnam, es liberado de prisión para una misión "
            "encubierta: rescatar prisioneros de guerra americanos en Vietnam. "
            "Armado hasta los dientes, Rambo destruye todo lo que se interpone en su camino "
            "en un festival de explosiones, músculos y heroísmo solitario masculino."
        ),
        "social_snippets": [
            "Sylvester Stallone en su máxima expresión de macho invencible y héroe blanco salvador.",
            "La película glorifica la violencia como solución y presenta a Rambo como el hombre perfecto.",
            "Ausencia total de personajes femeninos con agencia. Las mujeres son ornamento o víctima.",
            "Símbolo de la cultura Reagan: el hombre blanco heterosexual resolviendo los problemas del mundo a tiros.",
        ],
    },
    "eeaao": {
        "title": "Everything Everywhere All at Once",
        "year": 2022,
        "genres": "Ciencia Ficción, Comedia, Drama, Acción",
        "synopsis": (
            "Evelyn Wang, inmigrante china propietaria de una lavandería, descubre que puede "
            "acceder a las habilidades de sus versiones en universos paralelos. "
            "Dirigida por el dúo The Daniels, la película explora el multiverso, "
            "la identidad, las expectativas familiares, y la relación madre-hija con Joy, "
            "personaje queer. Ganó 7 Oscars incluyendo Mejor Película y Mejor Directores."
        ),
        "social_snippets": [
            "Michelle Yeoh da vida a una protagonista femenina asiática de mediana edad — rarísimo en Hollywood.",
            "Stephanie Hsu interpreta a Joy, personaje LGBTQ+ cuya historia es el corazón emocional del film.",
            "Dirigida por The Daniels (Daniel Kwan y Daniel Scheinert), voz fresca y diversa en el cine mainstream.",
            "Celebrada por su representación de la experiencia inmigrante asiático-americana y las relaciones intergeneracionales.",
        ],
    },
}

# --- Prompt builders ---

def build_prompt_with_soul(film: dict) -> str:
    loves_str = ", ".join(CHARACTER_LOVES)
    hates_str = ", ".join(CHARACTER_HATES)
    snippets = "\n".join(f"- {s}" for s in film["social_snippets"])

    return f"""Eres {CHARACTER_NAME}.
{CHARACTER_DESCRIPTION}

ALMA DEL PERSONAJE:
Amas: {loves_str}.
Detestas: {hates_str}.
Cuando algo de lo que detestas aparece en una obra, lo mencionas explícitamente con indignación.
Cuando algo de lo que amas aparece, lo celebras con entusiasmo genuino.

CONTEXTO CRÍTICO Y SOCIAL:
{snippets}

OBRA A CRITICAR:
Título: "{film['title']}" ({film['year']})
Géneros: {film['genres']}
Sinopsis: {film['synopsis']}

INSTRUCCIONES:
Escribe una crítica de máximo 150 palabras como {CHARACTER_NAME}.
Empieza con la puntuación: X/10
Escribe en primera persona con tu tono auténtico de activista.
Sé directa y personal."""


def build_prompt_without_soul(film: dict) -> str:
    snippets = "\n".join(f"- {s}" for s in film["social_snippets"])

    return f"""Eres {CHARACTER_NAME}.
{CHARACTER_DESCRIPTION}

CONTEXTO CRÍTICO Y SOCIAL:
{snippets}

OBRA A CRITICAR:
Título: "{film['title']}" ({film['year']})
Géneros: {film['genres']}
Sinopsis: {film['synopsis']}

INSTRUCCIONES:
Escribe una crítica de máximo 150 palabras como {CHARACTER_NAME}.
Empieza con la puntuación: X/10
Escribe en primera persona con tu tono auténtico de activista.
Sé directa y personal."""


# --- Ollama caller ---

def call_ollama(prompt: str) -> tuple[str, float]:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
        },
    }
    t0 = time.time()
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
    elapsed = time.time() - t0
    return resp.json()["response"], elapsed


def extract_rating(text: str) -> str:
    m = re.search(r"(\d+)/10", text)
    return f"{m.group(1)}/10" if m else "?"


# --- Display helpers ---

SEPARATOR = "=" * 72
THIN_SEP = "-" * 72


def print_result(label: str, film_key: str, response: str, elapsed: float):
    film = FILMS[film_key]
    rating = extract_rating(response)
    print(f"\n{THIN_SEP}")
    print(f"  {label}")
    print(f"  Film   : {film['title']} ({film['year']})")
    print(f"  Rating : {rating}   [{elapsed:.1f}s]")
    print(THIN_SEP)
    # Strip think-blocks (qwen3 reasoning tokens)
    clean = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    print(clean)


# --- Main ---

def main():
    print(SEPARATOR)
    print("  SOUL CONCEPT VALIDATION — Parody Critics API")
    print(f"  Character : {CHARACTER_NAME}")
    print(f"  Model     : {MODEL}")
    print(f"  Endpoint  : {OLLAMA_URL}")
    print(SEPARATOR)

    results = {}

    test_cases = [
        ("rambo",  "WITH soul",    build_prompt_with_soul),
        ("rambo",  "WITHOUT soul", build_prompt_without_soul),
        ("eeaao",  "WITH soul",    build_prompt_with_soul),
        ("eeaao",  "WITHOUT soul", build_prompt_without_soul),
    ]

    for film_key, variant, prompt_fn in test_cases:
        film = FILMS[film_key]
        label = f"[{variant.upper()}] {film['title']}"
        print(f"\nGenerating: {label} ...")
        prompt = prompt_fn(film)
        response, elapsed = call_ollama(prompt)
        results[(film_key, variant)] = {
            "response": response,
            "rating": extract_rating(response),
            "elapsed": elapsed,
        }
        print(f"  Done in {elapsed:.1f}s — rating: {results[(film_key, variant)]['rating']}")

    # --- Full output ---
    print(f"\n\n{SEPARATOR}")
    print("  FULL CRITIQUES")
    print(SEPARATOR)

    for film_key, variant, _ in test_cases:
        r = results[(film_key, variant)]
        print_result(f"[{variant.upper()}] {FILMS[film_key]['title']}", film_key, r["response"], r["elapsed"])

    # --- Side-by-side comparison summary ---
    print(f"\n\n{SEPARATOR}")
    print("  COMPARISON SUMMARY")
    print(SEPARATOR)

    for film_key in ("rambo", "eeaao"):
        film = FILMS[film_key]
        with_soul    = results[(film_key, "WITH soul")]
        without_soul = results[(film_key, "WITHOUT soul")]
        print(f"\n  {film['title']} ({film['year']})")
        print(f"    WITH soul    : {with_soul['rating']:>5}   ({with_soul['elapsed']:.1f}s)")
        print(f"    WITHOUT soul : {without_soul['rating']:>5}   ({without_soul['elapsed']:.1f}s)")

    print(f"\n\n{SEPARATOR}")
    print("  ANALYSIS QUESTIONS")
    print(SEPARATOR)
    rambo_with    = results[("rambo",  "WITH soul")]["rating"]
    rambo_without = results[("rambo",  "WITHOUT soul")]["rating"]
    eeaao_with    = results[("eeaao",  "WITH soul")]["rating"]
    eeaao_without = results[("eeaao",  "WITHOUT soul")]["rating"]

    def yn(cond): return "YES" if cond else "NO"

    rambo_low_with = rambo_with in ("1/10", "2/10", "3/10", "4/10")
    eeaao_high_with = eeaao_with in ("8/10", "9/10", "10/10")
    soul_changes_rambo = rambo_with != rambo_without
    soul_changes_eeaao = eeaao_with != eeaao_without

    print("\n  Q1. Does Rosario rate Rambo low WITH soul?")
    print(f"      {yn(rambo_low_with)} — Rambo WITH soul rated {rambo_with}")

    print("\n  Q2. Does Rosario rate EEAAO high WITH soul?")
    print(f"      {yn(eeaao_high_with)} — EEAAO WITH soul rated {eeaao_with}")

    print("\n  Q3. Does the soul field change Rambo's rating?")
    print(f"      {yn(soul_changes_rambo)} — WITH: {rambo_with}  WITHOUT: {rambo_without}")

    print("\n  Q4. Does the soul field change EEAAO's rating?")
    print(f"      {yn(soul_changes_eeaao)} — WITH: {eeaao_with}  WITHOUT: {eeaao_without}")

    print(f"\n{SEPARATOR}\n")


if __name__ == "__main__":
    main()
