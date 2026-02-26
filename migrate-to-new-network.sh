#!/bin/bash
# 🌐 Network Migration Script - SAL-9000 & niskeletor
# Automatically updates network configuration for new location

echo "🌐 Parody Critics Network Migration Tool"
echo "======================================="

# Detect current network
echo "🔍 Detecting current network..."
CURRENT_IP=$(hostname -I | awk '{print $1}')
CURRENT_NETWORK=$(echo $CURRENT_IP | cut -d. -f1-3)
echo "📍 Current network: $CURRENT_NETWORK.x"

# Check if we're on a different network than .45
if [[ $CURRENT_NETWORK == "192.168.45" ]]; then
    echo "✅ Already on homelab network (192.168.45.x)"
    echo "🎯 No changes needed!"
    exit 0
fi

echo "🔄 Detected network change!"
echo "📍 New network: $CURRENT_NETWORK.x"

# Backup current .env
if [ -f .env ]; then
    echo "💾 Backing up current .env to .env.backup-$(date +%Y%m%d-%H%M%S)"
    cp .env .env.backup-$(date +%Y%m%d-%H%M%S)
fi

# Ask for new network configuration
echo ""
echo "🔧 Please provide new network configuration:"
echo "-------------------------------------------"

# Jellyfin URL
echo -n "📺 Jellyfin URL (or press Enter for localhost:8096): "
read JELLYFIN_URL
if [ -z "$JELLYFIN_URL" ]; then
    JELLYFIN_URL="http://localhost:8096"
fi

# Ollama URL
echo -n "🤖 Ollama URL (or press Enter for localhost:11434): "
read OLLAMA_URL
if [ -z "$OLLAMA_URL" ]; then
    OLLAMA_URL="http://localhost:11434"
fi

# API Token
echo -n "🔑 Jellyfin API Token (or press Enter to keep current): "
read API_TOKEN
if [ -z "$API_TOKEN" ]; then
    # Extract current token if exists
    if [ -f .env ]; then
        API_TOKEN=$(grep "JELLYFIN_API_TOKEN=" .env | cut -d= -f2)
    fi
    if [ -z "$API_TOKEN" ]; then
        API_TOKEN="YOUR_API_TOKEN_HERE"
    fi
fi

# Generate new .env file
echo ""
echo "🔄 Generating new configuration..."

cat > .env << EOF
# Parody Critics Configuration
# Network migration on $(date)

# Jellyfin Configuration
JELLYFIN_URL=$JELLYFIN_URL
JELLYFIN_API_TOKEN=$API_TOKEN

# LLM Configuration
LLM_OLLAMA_URL=$OLLAMA_URL
LLM_PRIMARY_MODEL=qwen3:8b
LLM_SECONDARY_MODEL=gpt-oss:20b
LLM_TIMEOUT=180
LLM_MAX_RETRIES=2
LLM_ENABLE_FALLBACK=true
EOF

echo "✅ New configuration created!"
echo ""
echo "📋 Configuration Summary:"
echo "------------------------"
echo "📺 Jellyfin: $JELLYFIN_URL"
echo "🤖 Ollama:   $OLLAMA_URL"
echo "🔑 Token:    ${API_TOKEN:0:10}..."
echo ""

# Test if we can start the server
echo "🚀 Testing server startup..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 available"
    echo "💡 Ready to start with: uvicorn api.main:app --reload --host 0.0.0.0 --port 8877"
    echo "🌐 Access via: http://localhost:8877"
else
    echo "⚠️  Python3 not found - make sure virtual environment is activated"
fi

echo ""
echo "🎯 Migration complete! The app is now configured for the new network."
echo "📝 Run 'source venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8877'"