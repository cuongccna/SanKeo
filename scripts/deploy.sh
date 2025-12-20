#!/bin/bash

# Deploy Script for SanKeo Project
# Usage: ./scripts/deploy.sh

echo "🚀 Starting Deployment..."

# 1. Pull latest code
echo "📥 Pulling latest code from Git..."
git pull origin main

# 2. Activate Virtual Environment
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

# 3. Install Dependencies
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

# Ensure sessions directory exists
if [ ! -d "sessions" ]; then
    echo "📂 Creating sessions directory..."
    mkdir -p sessions
fi

# 4. Run Database Migrations (if any)
# Note: Assuming you have a migration script or using alembic. 
# For now, we run the specific migration scripts we created.
echo "🗄️ Running Database Migrations..."
# Initialize DB (Create tables if not exist)
python3 init_db.py
# Run specific migrations for updates
python3 -m scripts.migrate_affiliate
python3 -m scripts.migrate_quiet_blacklist
python3 -m scripts.migrate_business_plan

# 5. Reload PM2
echo "🔄 Reloading PM2 processes..."
if command -v pm2 &> /dev/null; then
    pm2 reload ecosystem.config.js --update-env
    pm2 save
else
    echo "❌ PM2 is not installed. Please install it globally: npm install pm2 -g"
    exit 1
fi

echo "✅ Deployment Complete!"
pm2 status
