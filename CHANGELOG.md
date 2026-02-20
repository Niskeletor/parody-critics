# Changelog

All notable changes to Parody Critics for Jellyfin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- LLM integration for automatic review generation
- Additional critic characters (El Cinéfilo Snob, Karen de Madrid)
- Batch review generation
- Docker deployment support
- Configuration management system

### Changed
- TBD

### Fixed
- TBD

## [1.0.0] - 2025-02-20

### Added
- Initial release of Parody Critics system
- SQLite database with full schema for media and critics
- FastAPI REST API server with comprehensive endpoints
- Two initial critic characters:
  - Marco Aurelio (Stoic philosopher)
  - Rosario Costras (Woke social activist)
- Dynamic theming system with character-specific colors
- Frontend JavaScript client for Jellyfin integration
- Jellyfin library synchronization script
- Automatic API health checking and retry logic
- Comprehensive error handling and logging
- Database migration and initialization scripts
- Cache system for improved performance
- Responsive UI design matching Jellyfin aesthetics

### Technical Features
- RESTful API with OpenAPI documentation
- SQLite database with foreign key constraints
- Async Python with httpx for Jellyfin integration
- Pydantic models for data validation
- CORS support for web client integration
- Background task support for long-running operations
- Database connection pooling and transaction management

### Endpoints
- `GET /api/critics/{tmdb_id}` - Get critics for specific media
- `GET /api/stats` - System statistics
- `GET /api/characters` - List all critic characters
- `GET /api/media` - Browse media library with pagination
- `GET /api/health` - API health check
- `GET /api/sync-logs` - View synchronization history

### Documentation
- Complete README with setup instructions
- API documentation via FastAPI Swagger UI
- Database schema documentation
- Character system documentation
- Development setup guides