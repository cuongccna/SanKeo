#!/bin/bash

# ==========================================
# 🚀 SAN KEO BOT - VPS DEPLOYMENT SCRIPT
# ==========================================
# Usage: 
#   ./scripts/deploy.sh        (Full Deploy)
#   ./scripts/deploy.sh --quick (Skip system updates)

set -e # Exit immediately if a command exits with a non-zero status.

# --- CONFIGURATION ---
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="$PROJECT_DIR/logs/deploy.log"

# Ensure logs directory exists
mkdir -p "$PROJECT_DIR/logs"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "❌ [ERROR] $1" | tee -a "$LOG_FILE"
    exit 1
}

log "🚀 Starting Deployment in $PROJECT_DIR..."

# --- 1. GIT UPDATE ---
log "📥 Pulling latest code..."
cd "$PROJECT_DIR"

# Check for local changes
if [[ -n $(git status -s) ]]; then
    log "⚠️ Local changes detected. Stashing..."
    git stash save "Auto-stash before deploy $(date)"
fi

git pull origin main || error "Git pull failed!"

# --- 2. SYSTEM DEPENDENCIES (Optional with --quick) ---
if [[ "$1" != "--quick" ]]; then
    log "🛠️ Checking system dependencies..."
    
    # Node.js & PM2
    if ! command -v npm &> /dev/null; then
        log "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi

    if ! command -v pm2 &> /dev/null; then
        log "Installing PM2..."
        sudo npm install -g pm2
    fi

    # Redis
    if ! command -v redis-server &> /dev/null; then
        log "Installing Redis..."
        sudo apt-get update
        sudo apt-get install -y redis-server
        sudo systemctl enable redis-server
        sudo systemctl start redis-server
    fi

    # Python Venv
    if ! dpkg -s python3-venv &> /dev/null; then
        log "Installing python3-venv..."
        sudo apt-get install -y python3-venv python3-full
    fi
else
    log "⏩ Skipping system updates (--quick mode)"
fi

# --- 3. PYTHON ENVIRONMENT ---
log "🔌 Setting up Python Environment..."

if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate Venv
source "$VENV_DIR/bin/activate" || error "Failed to activate venv"

# Upgrade pip
pip install --upgrade pip

# Install Requirements
log "📦 Installing Python dependencies..."
pip install -r requirements.txt || error "Failed to install requirements"

# --- 4. DIRECTORY SETUP ---
log "📂 Creating necessary directories..."
mkdir -p sessions logs temp_images

# --- 5. DATABASE & MIGRATIONS ---
log "🗄️ Database Operations..."
export PYTHONPATH=$PROJECT_DIR

# Init DB
python3 init_db.py || error "Failed to init DB"

# Run Migrations
log "🔄 Running Migrations..."
# Add any new migration scripts here
python3 -m scripts.migrate_affiliate || true
python3 -m scripts.migrate_quiet_blacklist || true
python3 -m scripts.migrate_business_plan || true
python3 -m scripts.migrate_source_config || true

# Seed Data
log "🌱 Seeding Data..."
python3 -m scripts.seed_templates || error "Failed to seed templates"
python3 -m scripts.seed_data || log "Seed data might already exist or failed non-critically"

# --- 6. PM2 PROCESS MANAGEMENT ---
log "🔄 Reloading PM2..."

# Check if ecosystem file exists
if [ ! -f "ecosystem.config.js" ]; then
    error "ecosystem.config.js not found!"
fi

# Start or Reload
pm2 startOrReload ecosystem.config.js --update-env || error "PM2 failed"
pm2 save

# --- 7. CLEANUP ---
log "🧹 Cleaning up temp files..."
# Optional: Clear old temp images > 24h
find temp_images -name "*.jpg" -type f -mtime +1 -delete
find temp_images -name "*.png" -type f -mtime +1 -delete

log "✅ DEPLOYMENT COMPLETE!"
pm2 status
