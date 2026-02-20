"""
🎭 Parody Critics - Configuration Management
Environment-based configuration for different deployment scenarios
"""

import os
from pathlib import Path

class Config:
    """Base configuration class"""

    # Database
    DATABASE_PATH = os.getenv('PARODY_CRITICS_DB_PATH', 'database/critics.db')

    # API Settings
    API_HOST = os.getenv('PARODY_CRITICS_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('PARODY_CRITICS_PORT', '8000'))

    # Jellyfin Settings
    JELLYFIN_URL = os.getenv('JELLYFIN_URL', 'http://localhost:8096')
    JELLYFIN_API_KEY = os.getenv('JELLYFIN_API_KEY', '')

    # CORS Settings
    CORS_ORIGINS = [
        "http://localhost:8096",
        "http://192.168.45.181:8096",
        "http://127.0.0.1:8096"
    ]

    # Add custom origins from environment
    custom_origins = os.getenv('PARODY_CRITICS_CORS_ORIGINS', '')
    if custom_origins:
        CORS_ORIGINS.extend([origin.strip() for origin in custom_origins.split(',')])

    # Performance
    CACHE_DURATION = int(os.getenv('PARODY_CRITICS_CACHE_DURATION', '300'))  # 5 minutes

    # Logging
    LOG_LEVEL = os.getenv('PARODY_CRITICS_LOG_LEVEL', 'INFO')

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

    return config_map.get(environment, DevelopmentConfig)