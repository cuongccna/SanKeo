#!/bin/bash

# Deploy Script for SanKeo Project
# Usage: ./scripts/deploy.sh

echo "🚀 Starting Deployment..."

# 1. Pull latest code
echo "📥 Pulling latest code from Git..."
git pull origin main

# 2. Activate Virtual Environment
echo "🔌 Activating Virtual Environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️ venv not found! Creating one..."
    python3 -m venv venv
    source venv/bin/activate
fi

# 3. Install Dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# 4. Run Database Migrations (if any)
# Note: Assuming you have a migration script or using alembic. 
# For now, we run the specific migration scripts we created.
echo "🗄️ Running Database Migrations..."
python -m scripts.migrate_affiliate
python -m scripts.migrate_quiet_blacklist

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
