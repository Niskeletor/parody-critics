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

## 🚀 Deployment

### Quick Deploy to Jellyfin Server

If your Jellyfin runs on a remote server (like `stilgar@192.168.45.181`), use the automated deployment script:

```bash
# Make sure SSH key authentication is set up first
./deploy-to-stilgar.sh
```

This script will:
- ✅ Copy all project files to the remote server
- ✅ Set up Python virtual environment
- ✅ Install dependencies and initialize database
- ✅ Create systemd service for the API
- ✅ Install JavaScript client in Jellyfin web directory
- ✅ Start the API service automatically

After deployment:
```bash
# SSH to your Jellyfin server
ssh stilgar@192.168.45.181

# Navigate to project directory
cd parody-critics

# Activate environment and sync your Jellyfin library
source venv/bin/activate
python scripts/jellyfin_sync.py --jellyfin-url http://localhost:8096 --api-key YOUR_API_KEY

# Restart Jellyfin to load the new JavaScript client
sudo systemctl restart jellyfin
```

### Manual Deployment

1. **Copy project to your Jellyfin server:**
   ```bash
   rsync -avz ./ user@your-server:/path/to/parody-critics/
   ```

2. **Set up environment:**
   ```bash
   # On the server
   cd /path/to/parody-critics
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python run_setup.py
   ```

3. **Configure for your environment:**
   ```bash
   # Copy and edit environment file
   cp .env.stilgar .env
   nano .env  # Update JELLYFIN_API_KEY and other settings
   ```

4. **Start the API:**
   ```bash
   # Development
   source venv/bin/activate
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

   # Production (with systemd)
   sudo cp parody-critics-api.service /etc/systemd/system/
   sudo systemctl enable parody-critics-api.service
   sudo systemctl start parody-critics-api.service
   ```

5. **Install JavaScript client:**
   ```bash
   # Copy to your Jellyfin web directory
   sudo cp frontend/parody-critics-api-client.js /opt/jellyfin/jellyfin-web/
   ```

### Environment Variables

The API supports environment-based configuration:

```bash
# Environment
PARODY_CRITICS_ENV=stilgar          # development, stilgar, production

# API Configuration
PARODY_CRITICS_HOST=0.0.0.0         # Bind address
PARODY_CRITICS_PORT=8000            # Port number

# Database
PARODY_CRITICS_DB_PATH=/path/to/critics.db

# Jellyfin
JELLYFIN_URL=http://localhost:8096
JELLYFIN_API_KEY=your-api-key

# CORS (comma-separated URLs)
PARODY_CRITICS_CORS_ORIGINS=http://localhost:8096,http://server:8096
```

### Network Configuration

The JavaScript client automatically detects the API URL:
- **Local development**: Uses `http://localhost:8000/api`
- **Remote deployment**: Uses `http://YOUR_SERVER_IP:8000/api`

Make sure:
- ✅ Port 8000 is open on your server firewall
- ✅ Jellyfin can access the API (same network/CORS configured)
- ✅ API service starts automatically on boot

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