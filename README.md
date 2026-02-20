# 🎭 Parody Critics for Jellyfin

A comprehensive system for adding humorous, character-driven movie and TV show reviews to your Jellyfin media server.

## 🌟 Features

- **🎭 Character-based Critics**: Multiple unique personalities review your content
  - **🏛️ Marco Aurelio**: Stoic philosopher emperor with classical wisdom
  - **🏳️‍⚧️ Rosario Costras**: Hyper-woke social justice activist finding oppression everywhere
  - *More characters coming soon!*

- **🎨 Dynamic Theming**: Each critic has their own color scheme and visual identity
- **📊 RESTful API**: Clean, scalable backend with FastAPI and SQLite
- **🔄 Automatic Sync**: Integrates with Jellyfin's library for seamless updates
- **🤖 LLM Integration**: AI-powered review generation (planned)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   Jellyfin      │    │   FastAPI    │    │  SQLite DB  │
│   Frontend      │◄───│   Server     │◄───│  critics.db │
│   (JavaScript)  │    │  (REST API)  │    │             │
└─────────────────┘    └──────────────┘    └─────────────┘
                              ▲                     ▲
                              │                     │
                       ┌──────────────┐            │
                       │   Sync       │            │
                       │   Script     │────────────┘
                       │  (Python)    │
                       └──────────────┘
                              ▲
                              │
                       ┌──────────────┐
                       │  Jellyfin    │
                       │   API        │
                       │  (Source)    │
                       └──────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Jellyfin server running
- JavaScript Injector plugin for Jellyfin

### Installation

1. **Clone and setup:**
   ```bash
   git clone https://github.com/your-username/parody-critics-jellyfin.git
   cd parody-critics-jellyfin
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Initialize database:**
   ```bash
   python run_setup.py
   ```

3. **Start the API server:**
   ```bash
   source venv/bin/activate
   cd api
   python main.py
   ```

4. **Add to Jellyfin:**
   - Install JavaScript Injector plugin
   - Add the frontend script (see `frontend/` folder)

## 📚 API Documentation

The API runs on `http://localhost:8000` with automatic documentation at `/docs`.

### Key Endpoints

- **GET** `/api/critics/{tmdb_id}` - Get critics for a specific movie/show
- **GET** `/api/stats` - Get system statistics
- **GET** `/api/characters` - List all critic characters
- **GET** `/api/health` - Health check

### Example Response

```json
{
  "tmdb_id": "338969",
  "title": "El Vengador Tóxico",
  "type": "movie",
  "critics": {
    "marco_aurelio": {
      "author": "Marco Aurelio",
      "emoji": "🏛️",
      "rating": 8,
      "content": "Como emperador y filósofo, he contemplado muchas transformaciones...",
      "color": "#8B4513"
    },
    "rosario_costras": {
      "author": "Rosario Costras",
      "emoji": "🏳️‍⚧️",
      "rating": 2,
      "content": "Esta película perpetúa múltiples violencias sistémicas...",
      "color": "#FF69B4"
    }
  }
}
```

## 🎭 Character System

Each critic is designed with a unique personality and reviewing style:

### 🏛️ Marco Aurelio (Stoic)
- **Theme Color:** Brown (`#8B4513`)
- **Style:** Philosophical, accepting, finds wisdom in adversity
- **Quotes:** References to Meditations, Stoic principles

### 🏳️‍⚧️ Rosario Costras (Woke)
- **Theme Color:** Hot Pink (`#FF69B4`)
- **Style:** Social justice focused, sees oppression everywhere
- **Language:** Progressive terminology, hashtags, triggers

## 🔧 Development

### Project Structure
```
parody-critics-api/
├── api/
│   └── main.py              # FastAPI server
├── database/
│   ├── schema.sql           # Database schema
│   ├── init_db.py          # DB initialization
│   └── critics.db          # SQLite database (generated)
├── models/
│   └── schemas.py          # Pydantic models
├── scripts/
│   └── jellyfin_sync.py    # Sync with Jellyfin (planned)
├── frontend/
│   └── parody-critics.js   # JavaScript for Jellyfin
└── run_setup.py            # Setup script
```

### Adding New Characters

1. Update `database/schema.sql` with new character data
2. Add character theme in `frontend/parody-critics.js`
3. Create personality prompts for LLM generation
4. Re-run database initialization

## 🤖 AI Integration (Planned)

The system is designed to integrate with LLM services for automatic review generation:

- **OpenAI GPT-4**: Premium, highest quality
- **Anthropic Claude**: Great reasoning and character consistency
- **Local LLMs**: Privacy-focused, cost-effective

## 📊 Database Schema

The SQLite database includes tables for:
- `media` - Movie and TV show metadata
- `characters` - Critic personality definitions
- `critics` - Generated reviews
- `sync_log` - Synchronization tracking

## 🐛 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Jellyfin team for the amazing media server
- JavaScript Injector plugin developers
- FastAPI and SQLite communities

---

*"The spice must flow... and so must the parody reviews!"* 🎭

Made with ❤️ by SAL-9000 and the Landsraad Homelab crew