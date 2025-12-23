#!/bin/bash

# Deploy Script for SanKeo Project
# Usage: ./scripts/deploy.sh

set -e

echo "🚀 Starting Deployment..."

# 1. Pull latest code
echo "📥 Pulling latest code from Git..."
# Stash any local changes (like config files) to avoid conflicts
git stash
git pull origin main
# Restore local changes
git stash pop || echo "⚠️ No local changes to restore or conflict occurred."

# 2. System Dependencies
echo "🛠️ Checking system dependencies..."
if ! command -v npm &> /dev/null; then
    echo "⚠️ Node.js/npm not found! Installing..."
    sudo apt update
    sudo apt install -y nodejs npm
fi

# 3. Activate Virtual Environment
echo "🔌 Activating Virtual Environment..."
# Ensure we are in the project root
cd "$(dirname "$0")/.."

if [ ! -f "venv/bin/activate" ]; then
    echo "⚠️ venv missing or broken! Creating one..."
    rm -rf venv
    # Try standard creation
    if ! python3 -m venv venv; then
        echo "⚠️ Failed to create venv. Installing python3-venv..."
        sudo apt update
        sudo apt install -y python3-venv python3-full
        # Retry
        python3 -m venv venv
    fi
fi

# Activate venv
source ./venv/bin/activate || { echo "❌ Failed to activate venv"; exit 1; }

# Load environment variables
if [ -f .env ]; then
    echo "🌍 Loading environment variables..."
    set -a
    source .env
    set +a
fi

# 4. Install Dependencies
echo "📦 Installing dependencies..."

# Check and install Redis if missing
if ! command -v redis-server &> /dev/null; then
    echo "⚠️ Redis not found! Installing..."
    sudo apt update
    sudo apt install -y redis-server
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
fi

# Upgrade pip first
pip install --upgrade pip
pip install -r requirements.txt
# Explicitly install uvicorn to ensure it's available for PM2
pip install uvicorn[standard]

# 6. Directory Setup
echo "📂 Ensuring directories exist..."
mkdir -p sessions logs temp_images

# 7. Database Setup & Migrations
echo "🗄️ Setting up Database..."

# Initialize DB (Create tables if not exist)
python3 init_db.py

# Run Migrations (CRITICAL: Run BEFORE seeding to ensure schema is correct)
echo "🔄 Running Migrations..."
python3 -m scripts.migrate_affiliate || true
python3 -m scripts.migrate_quiet_blacklist || true
python3 -m scripts.migrate_business_plan || true
python3 -m scripts.migrate_source_config || true

# Run Seeds (Idempotent)
echo "🌱 Seeding Data..."
python3 -m scripts.seed_templates
python3 -m scripts.seed_data

# 8. PM2 Reload
echo "🔄 Reloading PM2 processes..."
if ! command -v pm2 &> /dev/null; then
    echo "⚠️ PM2 not found! Installing globally..."
    sudo npm install -g pm2
fi

# Start/Reload ecosystem
pm2 startOrReload ecosystem.config.js --update-env
pm2 save

echo "✅ Deployment Complete!"
pm2 status
