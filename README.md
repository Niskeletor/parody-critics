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
- **Python 3.11+** (Required for modern FastAPI features)
- **Jellyfin server** running and accessible
- **Ollama** (Optional, for AI-powered reviews)
- **JavaScript Injector plugin** for Jellyfin (for frontend integration)

**Recommended System Requirements:**
- 8GB+ RAM (for LLM processing)
- 10GB+ free disk space (for models and database)
- Network access to Jellyfin and Ollama servers

### Installation

#### 🧙‍♂️ Option 1: Setup Wizard (Recommended)

Use our interactive setup wizard for the easiest installation:

```bash
# Clone and navigate
git clone https://github.com/your-username/parody-critics-jellyfin.git
cd parody-critics-jellyfin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the setup wizard
python simple_wizard.py
```

The wizard will:
- ✅ Check all system dependencies
- ✅ Test connections to Jellyfin and Ollama servers
- ✅ Create optimized `.env` configuration
- ✅ Provide next steps for deployment

**Wizard Options:**
```bash
python simple_wizard.py --help           # Show all options
python simple_wizard.py --demo           # Run with pre-filled demo values
python simple_wizard.py --skip-deps      # Skip dependency checks
python simple_wizard.py --config-only    # Only create configuration
```

#### 📋 Option 2: Manual Installation

1. **Clone and setup:**
   ```bash
   git clone https://github.com/your-username/parody-critics-jellyfin.git
   cd parody-critics-jellyfin
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   # Copy and edit configuration
   cp .env.example .env
   nano .env  # Update JELLYFIN_URL, LLM settings, etc.
   ```

3. **Initialize database:**
   ```bash
   python run_setup.py
   ```

4. **Start the API server:**
   ```bash
   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
   ```

5. **Add to Jellyfin:**
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

## 🤖 AI Integration

### LLM Integration with Ollama

The system integrates with **Ollama** for local AI-powered review generation:

#### Supported Models
- **QWen3:8B**: Primary model for fast, coherent reviews
- **GPT-OSS:20B**: Secondary/fallback model for complex analysis
- **Custom Models**: Any Ollama-compatible model

#### Setup Ollama Integration

1. **Install Ollama** (if not already installed):
   ```bash
   # Linux/macOS
   curl -fsSL https://ollama.com/install.sh | sh

   # Or visit https://ollama.com for other installation methods
   ```

2. **Pull recommended models:**
   ```bash
   ollama pull qwen3:8b        # Primary model (~5GB)
   ollama pull gpt-oss:20b     # Secondary model (~12GB)
   ```

3. **Configure in the setup wizard:**
   ```bash
   python simple_wizard.py
   # The wizard will auto-detect your Ollama models and configure them
   ```

4. **Manual configuration (optional):**
   ```bash
   # .env file
   LLM_OLLAMA_URL=http://localhost:11434        # Ollama server URL
   LLM_PRIMARY_MODEL=qwen3:8b                   # Default model
   LLM_SECONDARY_MODEL=gpt-oss:20b              # Fallback model
   LLM_TIMEOUT=180                              # Request timeout (seconds)
   LLM_MAX_RETRIES=2                            # Retry attempts
   LLM_ENABLE_FALLBACK=true                     # Use fallback model on failure
   ```

#### LLM Features
- **🎭 Character Consistency**: Each critic maintains their unique voice
- **🔄 Automatic Fallback**: Switches to secondary model if primary fails
- **⚡ Caching**: Reviews are cached to avoid regeneration
- **🛡️ Privacy**: All processing done locally with Ollama
- **⚖️ Load Balancing**: Distributes requests across available models

### Cloud LLM Support (Future)
- **OpenAI GPT-4**: Premium, highest quality
- **Anthropic Claude**: Great reasoning and character consistency
- **Google Gemini**: Multimodal capabilities

## 📊 Database Schema

The SQLite database includes tables for:
- `media` - Movie and TV show metadata
- `characters` - Critic personality definitions
- `critics` - Generated reviews
- `sync_log` - Synchronization tracking

## 🛠️ Troubleshooting

### Setup Wizard Issues

**Wizard fails with "module not found" errors:**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate
pip install -r requirements.txt
```

**Connection test failures:**
- **Jellyfin**: Check URL format (include `http://`) and port
- **Ollama**: Ensure Ollama is running (`ollama serve`)
- **Models**: Pull required models (`ollama pull qwen3:8b`)

**Port 8000 already in use:**
```bash
# Check what's using the port
lsof -i :8000
# Kill the process or use a different port
```

**EOF errors during interactive setup:**
- Use `--demo` mode for non-interactive testing
- Ensure terminal supports input (not running in background)

### LLM Integration Issues

**Models not detected:**
```bash
# Check Ollama status
ollama list
ollama serve  # If not running

# Test connection manually
curl http://localhost:11434/api/tags
```

**Generation timeouts:**
- Increase `LLM_TIMEOUT` in `.env`
- Use smaller models (qwen3:8b instead of larger models)
- Check system resources (RAM/CPU)

**Character inconsistency:**
- Update character prompts in database
- Clear review cache
- Tune model temperature settings

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