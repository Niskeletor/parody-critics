"""
🎭 Parody Critics - Configuration Management
Environment-based configuration for different deployment scenarios
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""

    # Database
    DATABASE_PATH = os.getenv('PARODY_CRITICS_DB_PATH', 'database/critics.db')

    # API Settings
    API_HOST = os.getenv('PARODY_CRITICS_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('PARODY_CRITICS_PORT', '8000'))

    # Jellyfin Settings
    JELLYFIN_URL = os.getenv('JELLYFIN_URL', 'http://localhost:8096')
    JELLYFIN_API_TOKEN = os.getenv('JELLYFIN_API_TOKEN', '')
    JELLYFIN_DB_PATH = os.getenv('JELLYFIN_DB_PATH', '')

    # Sync Settings
    SYNC_BATCH_SIZE = int(os.getenv('SYNC_BATCH_SIZE', '100'))
    SYNC_MAX_CONCURRENT = int(os.getenv('SYNC_MAX_CONCURRENT', '5'))

    # CORS Settings
    CORS_ORIGINS = [
        "http://localhost:8096",
        "http://192.168.45.181:8096",
        "http://127.0.0.1:8096",
        # Testing origins
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "null"  # For file:// protocol testing
    ]

    # Add custom origins from environment
    custom_origins = os.getenv('PARODY_CRITICS_CORS_ORIGINS', '')
    if custom_origins:
        CORS_ORIGINS.extend([origin.strip() for origin in custom_origins.split(',')])

    # Performance
    CACHE_DURATION = int(os.getenv('PARODY_CRITICS_CACHE_DURATION', '300'))  # 5 minutes

    # Logging
    LOG_LEVEL = os.getenv('PARODY_CRITICS_LOG_LEVEL', 'INFO')

    # LLM Configuration
    # Primary Ollama endpoint (local)
    LLM_OLLAMA_URL = os.getenv('LLM_OLLAMA_URL', 'http://192.168.45.104:11434')
    LLM_PRIMARY_MODEL = os.getenv('LLM_PRIMARY_MODEL', 'qwen3:8b')
    LLM_SECONDARY_MODEL = os.getenv('LLM_SECONDARY_MODEL', 'gpt-oss:20b')

    # Future cloud endpoints
    LLM_OPENAI_API_KEY = os.getenv('LLM_OPENAI_API_KEY', '')
    LLM_ANTHROPIC_API_KEY = os.getenv('LLM_ANTHROPIC_API_KEY', '')

    # Generation settings
    LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '180'))  # 3 minutes
    LLM_MAX_RETRIES = int(os.getenv('LLM_MAX_RETRIES', '2'))
    LLM_ENABLE_FALLBACK = os.getenv('LLM_ENABLE_FALLBACK', 'true').lower() == 'true'

    @classmethod
    def get_absolute_db_path(cls) -> str:
        """Get absolute path to database"""
        if os.path.isabs(cls.DATABASE_PATH):
            return cls.DATABASE_PATH
        return str(Path(__file__).parent / cls.DATABASE_PATH)

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    API_HOST = 'localhost'

class StilagarConfig(Config):
    """Configuration for Stilgar server deployment"""
    DEBUG = False
    API_HOST = '0.0.0.0'
    JELLYFIN_URL = 'http://localhost:8096'  # Local on stilgar

    # Additional CORS origins for Stilgar network
    CORS_ORIGINS = Config.CORS_ORIGINS + [
        "http://192.168.45.181:8096",
        "http://stilgar:8096",
        "https://192.168.45.181:8096",
        "https://stilgar:8096"
    ]

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'stilgar': StilagarConfig,
    'production': ProductionConfig
}

def get_config(environment: str = None) -> Config:
    """Get configuration based on environment"""
    if environment is None:
        environment = os.getenv('PARODY_CRITICS_ENV', 'development')

    config_class = config_map.get(environment, DevelopmentConfig)
    return config_class()