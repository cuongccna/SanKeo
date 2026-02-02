#!/bin/bash
# Deploy Analyzer Service on VPS

set -e

echo "=========================================="
echo "📊 DEPLOYING NEWS ANALYZER SERVICE"
echo "=========================================="

# Navigate to project root
cd /root/sankeo

# 1. Update code
echo "📥 Pulling latest code..."
git pull origin main

# 2. Apply database migrations
echo "🗄️ Applying database migrations..."
python -m alembic upgrade head

# 3. Check if analyzer is already running
if pm2 list | grep -q "sankeo-analyzer"; then
    echo "♻️ Restarting existing analyzer service..."
    pm2 restart sankeo-analyzer
else
    echo "🚀 Starting new analyzer service..."
    pm2 start ecosystem.config.js --only sankeo-analyzer
fi

# 4. Save PM2 configuration
pm2 save

# 5. Show status
echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
pm2 status | grep sankeo-analyzer

echo ""
echo "📋 Monitor logs:"
echo "   pm2 logs sankeo-analyzer"
echo ""
echo "🛑 Stop analyzer:"
echo "   pm2 stop sankeo-analyzer"
echo ""
echo "🔄 Restart analyzer:"
echo "   pm2 restart sankeo-analyzer"
