#!/bin/bash
# 🎭 Parody Critics - Deployment Script for Stilgar (192.168.45.181)
# Deploys the complete Parody Critics system to the Jellyfin server

set -e  # Exit on any error

echo "🎭 Deploying Parody Critics to Stilgar (stilgar@192.168.45.181)..."
echo

# Configuration
STILGAR_HOST="192.168.45.181"
STILGAR_USER="stilgar"
REMOTE_PATH="/home/stilgar/parody-critics"
JELLYFIN_WEB_PATH="/opt/jellyfin/jellyfin-web"
SYSTEMD_SERVICE_PATH="/etc/systemd/system"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we can SSH to Stilgar
log_info "Testing SSH connection to ${STILGAR_USER}@${STILGAR_HOST}..."
if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "${STILGAR_USER}@${STILGAR_HOST}" exit; then
    log_error "Cannot SSH to ${STILGAR_USER}@${STILGAR_HOST}"
    log_info "Please ensure:"
    log_info "  1. SSH key authentication is set up"
    log_info "  2. Host is reachable: ping ${STILGAR_HOST}"
    log_info "  3. SSH service is running on stilgar"
    exit 1
fi
log_success "SSH connection successful!"

# Create remote directory
log_info "Creating remote directory structure..."
ssh "${STILGAR_USER}@${STILGAR_HOST}" "mkdir -p ${REMOTE_PATH}"

# Copy project files (excluding venv and __pycache__)
log_info "Copying project files to stilgar..."
rsync -avz --exclude='venv/' --exclude='__pycache__/' --exclude='*.pyc' --exclude='.git/' \
    ./ "${STILGAR_USER}@${STILGAR_HOST}:${REMOTE_PATH}/"
log_success "Project files copied successfully!"

# Setup Python environment on remote server
log_info "Setting up Python environment on stilgar..."
ssh "${STILGAR_USER}@${STILGAR_HOST}" << 'EOF'
cd /home/stilgar/parody-critics

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate and install requirements
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python run_setup.py

echo "Python environment setup complete!"
EOF

log_success "Python environment configured on stilgar!"

# Create systemd service for the API
log_info "Creating systemd service for Parody Critics API..."
ssh "${STILGAR_USER}@${STILGAR_HOST}" << EOF
sudo tee ${SYSTEMD_SERVICE_PATH}/parody-critics-api.service > /dev/null << 'SERVICE_EOF'
[Unit]
Description=Parody Critics API for Jellyfin
After=network.target

[Service]
Type=simple
User=${STILGAR_USER}
WorkingDirectory=${REMOTE_PATH}
Environment=PATH=${REMOTE_PATH}/venv/bin
ExecStart=${REMOTE_PATH}/venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable parody-critics-api.service
sudo systemctl restart parody-critics-api.service

echo "Systemd service configured and started!"
EOF

log_success "Systemd service for Parody Critics API created!"

# Install JavaScript client in Jellyfin
log_info "Installing JavaScript client in Jellyfin web interface..."
ssh "${STILGAR_USER}@${STILGAR_HOST}" << EOF
# Check if Jellyfin web directory exists
if [ -d "${JELLYFIN_WEB_PATH}" ]; then
    echo "Found Jellyfin web directory at ${JELLYFIN_WEB_PATH}"

    # Backup original if exists
    if [ -f "${JELLYFIN_WEB_PATH}/parody-critics-api-client.js" ]; then
        echo "Backing up existing parody critics client..."
        sudo cp "${JELLYFIN_WEB_PATH}/parody-critics-api-client.js" \
               "${JELLYFIN_WEB_PATH}/parody-critics-api-client.js.backup"
    fi

    # Copy our JavaScript client
    sudo cp "${REMOTE_PATH}/frontend/parody-critics-api-client.js" \
           "${JELLYFIN_WEB_PATH}/"

    echo "JavaScript client installed in Jellyfin!"
else
    echo "WARNING: Jellyfin web directory not found at ${JELLYFIN_WEB_PATH}"
    echo "Please manually copy frontend/parody-critics-api-client.js to your Jellyfin web directory"
fi
EOF

log_success "JavaScript client installation attempted!"

# Check service status
log_info "Checking Parody Critics API service status..."
ssh "${STILGAR_USER}@${STILGAR_HOST}" << 'EOF'
echo "Service status:"
sudo systemctl status parody-critics-api.service --no-pager -l

echo
echo "Testing API health:"
sleep 2  # Give service time to start
curl -s http://localhost:8000/api/health | python3 -c "import sys,json; print('✅ API Status:', json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "❌ API not responding yet (may need a moment to start)"
EOF

echo
log_success "🎉 Deployment to Stilgar completed!"
echo
log_info "Next steps:"
echo "  1. 🔗 API should be accessible at: http://${STILGAR_HOST}:8000/api"
echo "  2. 📖 API docs available at: http://${STILGAR_HOST}:8000/docs"
echo "  3. 🔄 Restart Jellyfin to load the new JavaScript client"
echo "  4. 📊 Run Jellyfin sync to populate database:"
echo "     ssh ${STILGAR_USER}@${STILGAR_HOST}"
echo "     cd ${REMOTE_PATH}"
echo "     source venv/bin/activate"
echo "     python scripts/jellyfin_sync.py --jellyfin-url http://localhost:8096 --api-key YOUR_API_KEY"
echo
log_warning "Remember to:"
echo "  • Configure your Jellyfin API key for sync"
echo "  • Restart Jellyfin service to load the JavaScript client"
echo "  • Check firewall settings if API is not accessible from other machines"
echo
echo "🎭 The spice must flow... from Stilgar! 🌶️"