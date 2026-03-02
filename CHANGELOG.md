# Changelog — Parody Critics

All notable changes to this project are documented here.

---

## [1.2.0] — 2026-03-02

### Deployment & Operations
- **Makefile** — `make deploy` builds the image locally and transfers it to DUNE via SSH pipe. No more manual steps: `make build`, `make push`, `make restart`, `make logs`, `make db-setup`
- **Secrets out of compose** — `docker-compose.yml` now uses `env_file: .env`. The Jellyfin API token and all credentials live in a `chmod 600` `.env` file, never in YAML
- **Hardcoded IPs eliminated** — `soul_generator.py` and `config.py` now read all URLs and models from environment variables. No more `192.168.x.x` buried in Python code

### LLM & Benchmarks
- **Benchmark ronda 2 complete** — All 16 Omnius models tested. Full results in `docs/benchmark-comparison.md`
- **Final production ranking**: `mistral-small3.1:24b` (primary, best calibration), `type32/eva-qwen-2.5-14b` (secondary, best speed). `phi4` and `mis-firefly-22b` discarded
- **ModelProfile for all models** — Every model on Omnius now has an explicit profile (think mode, temperature, num_predict, system_in_user)

### Character Management
- **Import modal rewrite** — The import button now actually works. Proper `<form>`, JSON-only validation, 1MB size limit, inline error messages, multi-character support
- **Import slug generation** — Characters imported without an `id` field get one auto-generated from their name (`Werner Herzog` → `werner_herzog`)
- **Export/import round-trip** — All 16 character fields including soul lists (loves, hates, motifs, catchphrases, avoid, red_flags) survive a full export → import cycle
- **Example files** — `docs/ejemplo_importar_personaje.json` (single) and `docs/ejemplo_importar_varios.json` (3 characters) for reference

### Internal
- **Internal documentation** — `docs/internal/` (gitignored): full architecture, API reference, deploy guide, LLM model guide, testing guide — 8 documents covering the entire project

---

## [1.1.0] — 2026-02-28

### New Features
- **Soul Generator** — AI-powered character creation wizard. Enter a real person's name (e.g. "Werner Herzog"), the system searches DuckDuckGo for context and generates all soul fields via LLM: personality, description, loves, hates, motifs, catchphrases, red flags. Each field can be regenerated individually
- **Full character roster** — 8 active characters deployed: Marco Aurelio, Rosario Costras, El Gran Lebowski, Adolf Histeric, Alan Turbing, Stanley Kubrick, Elon Musaka, Po (Teletubbie Rojo)
- **Character soul fields** — `loves`, `hates`, `red_flags`, `avoid` fields added to all characters. These feed the ideological calibration engine so ratings vary correctly by personality

### Bug Fixes
- **X/10 rating parser** — Fixed regex that failed to parse ratings when the model generated them with spaces or different formatting
- **Mark Hamill character** — Scoped his Star Wars rage to actual Star Wars content, not every sci-fi film

### Quality
- **CI pipeline** — GitHub Actions runs JS (ESLint) and Python (ruff) linting on every push
- **Pre-commit hooks** — ruff for Python, ESLint for JS, Prettier for formatting

---

## [1.0.0] — 2026-02-26

### New Features
- **Media enrichment pipeline** — Fetches cast, director, keywords, tagline and web snippets (TMDB + Letterboxd/FA scraping) to give the LLM richer context per film. Progress tracked via WebSocket with real-time modal and cancel support
- **Variation engine** — Rotates character motifs and catchphrases across critiques using `character_motif_history` table. Characters don't repeat themselves
- **Structured personality system** — Each character now has archetype labels (`estoico`, `woke`, `nihilista`, `fanatico_ideologico`, etc.) used in prompt construction

### Improvements
- **Brave API 429 handling** — Graceful fallback when Brave Search quota is exceeded
- **Fresh install reliability** — Schema, auto-migration and `.env.example` all aligned so a clean install works without manual intervention

---

## [0.9.0] — 2026-02-24

### New Features
- **E-commerce batch system** — Cart-style workflow: select films, pick characters per film, process all combinations in one batch. Real-time async progress tracking
- **Character management UI** — Full CRUD for characters in the web panel: create, edit, delete, view all their critiques, delete individual critiques or wipe all at once
- **"Ver Críticas" modal** — Per-character view of all generated critiques with multi-select delete

### Bug Fixes
- **Checkout visibility** — Fixed CSS conflicts causing the checkout view to disappear after navigation
- **Cart button** — Replaced broken `onclick` handler with proper async event listener

---

## [0.8.0] — 2026-02-22

### New Features
- **Installation Wizard** — Web UI wizard for first-time setup: test Jellyfin connection, test Ollama connection, save config, initialize database — all from the browser
- **Infinite scroll + alphabet navigation** — Media list now loads progressively and can be filtered by first letter
- **Dynamic character system** — Characters and their prompt templates are database-driven, no hardcoded personalities in Python

### Architecture
- **LLM hybrid system** — Ollama primary endpoint with fallback to secondary model. Configurable timeout, retries, and fallback toggle via environment variables
- **Docker deployment** — Full containerized deployment with auto-discovery of Jellyfin library

---

## [0.1.0] — 2026-02-20 — Initial Release

- FastAPI backend with SQLite database
- Jellyfin sync (API mode + direct DB mode)
- LLM critique generation via Ollama
- Basic web panel (media list, critic generation, character list)
- Docker support with volume-based persistence
