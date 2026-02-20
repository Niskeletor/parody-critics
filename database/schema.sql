-- Parody Critics Database Schema
-- SQLite database for storing media and critic reviews

-- Tabla de medios (películas y series)
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tmdb_id TEXT UNIQUE NOT NULL,
    jellyfin_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    original_title TEXT,
    year INTEGER,
    type TEXT CHECK(type IN ('movie', 'series')) NOT NULL,
    genres TEXT, -- JSON array de géneros
    overview TEXT,
    poster_url TEXT,
    backdrop_url TEXT,
    imdb_id TEXT,
    runtime INTEGER, -- En minutos
    vote_average REAL,
    vote_count INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de personajes críticos
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY, -- 'marco_aurelio', 'rosario_costras', etc.
    name TEXT NOT NULL,
    emoji TEXT,
    color TEXT, -- Hex color code
    border_color TEXT,
    accent_color TEXT,
    personality TEXT, -- 'stoic', 'woke', 'snob', 'karen'
    description TEXT,
    prompt_template TEXT, -- Template para el LLM
    active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de críticas generadas
CREATE TABLE IF NOT EXISTS critics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_id INTEGER NOT NULL,
    character_id TEXT NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 10),
    content TEXT NOT NULL,
    preview_length INTEGER DEFAULT 300,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    generation_model TEXT, -- 'gpt-4', 'claude-3', etc.
    generation_prompt TEXT, -- Prompt usado
    tokens_used INTEGER,
    FOREIGN KEY (media_id) REFERENCES media (id) ON DELETE CASCADE,
    FOREIGN KEY (character_id) REFERENCES characters (id),
    UNIQUE(media_id, character_id) -- Solo una crítica por personaje por media
);

-- Tabla de sincronización (para tracking)
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL, -- 'jellyfin_sync', 'critic_generation'
    total_processed INTEGER DEFAULT 0,
    total_success INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    status TEXT DEFAULT 'running', -- 'running', 'completed', 'error'
    error_message TEXT,
    metadata TEXT -- JSON con info adicional
);

-- Índices para optimización
CREATE INDEX IF NOT EXISTS idx_media_tmdb ON media(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_media_jellyfin ON media(jellyfin_id);
CREATE INDEX IF NOT EXISTS idx_media_type ON media(type);
CREATE INDEX IF NOT EXISTS idx_media_year ON media(year);
CREATE INDEX IF NOT EXISTS idx_critics_media ON critics(media_id);
CREATE INDEX IF NOT EXISTS idx_critics_character ON critics(character_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_type ON sync_log(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status);

-- Insertar personajes iniciales
INSERT OR REPLACE INTO characters (
    id, name, emoji, color, border_color, accent_color,
    personality, description, active
) VALUES
(
    'marco_aurelio',
    'Marco Aurelio',
    '🏛️',
    '#8B4513',
    '#8B4513',
    'rgba(139, 69, 19, 0.2)',
    'stoic',
    'Emperador romano y filósofo estoico. Analiza las obras desde la perspectiva de la virtud, el destino y la aceptación.',
    TRUE
),
(
    'rosario_costras',
    'Rosario Costras',
    '🏳️‍⚧️',
    '#FF69B4',
    '#FF69B4',
    'rgba(255, 105, 180, 0.2)',
    'woke',
    'Activista social hipersensible. Ve opresión y problemáticas sociales en cada elemento cinematográfico.',
    TRUE
),
(
    'el_cinefilo_snob',
    'El Cinéfilo Snob',
    '🎩',
    '#9370DB',
    '#9370DB',
    'rgba(147, 112, 219, 0.2)',
    'snob',
    'Crítico pretencioso que solo aprecia el cine de autor y desprecia todo lo comercial.',
    FALSE -- Desactivado hasta implementar
),
(
    'karen_madrid',
    'Karen de Madrid',
    '😤',
    '#FF4500',
    '#FF4500',
    'rgba(255, 69, 0, 0.2)',
    'karen',
    'La típica Karen española que se queja de todo y quiere hablar con el director.',
    FALSE -- Desactivado hasta implementar
);

-- Triggers para updated_at
CREATE TRIGGER IF NOT EXISTS update_media_timestamp
    AFTER UPDATE ON media
    BEGIN
        UPDATE media SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Vista para estadísticas rápidas
CREATE VIEW IF NOT EXISTS stats_summary AS
SELECT
    (SELECT COUNT(*) FROM media) as total_media,
    (SELECT COUNT(*) FROM media WHERE type = 'movie') as total_movies,
    (SELECT COUNT(*) FROM media WHERE type = 'series') as total_series,
    (SELECT COUNT(*) FROM critics) as total_critics,
    (SELECT COUNT(DISTINCT character_id) FROM critics) as active_characters,
    (SELECT COUNT(*) FROM media WHERE id NOT IN (SELECT DISTINCT media_id FROM critics)) as media_without_critics,
    (SELECT MAX(created_at) FROM media) as last_media_sync,
    (SELECT MAX(generated_at) FROM critics) as last_critic_generation;