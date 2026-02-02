#!/bin/bash
# Monitor Analyzer Service Performance

set -e

ANALYZER_PID=$(pm2 pid sankeo-analyzer 2>/dev/null || echo "")

echo "=========================================="
echo "📊 ANALYZER SERVICE MONITOR"
echo "=========================================="
echo ""

# 1. Service Status
echo "🟢 SERVICE STATUS:"
pm2 status | grep sankeo-analyzer || echo "Service not running"
echo ""

# 2. Recent Logs (last 20 lines)
echo "📋 RECENT LOGS (last 20 lines):"
echo "---"
pm2 logs sankeo-analyzer --lines 20 --nostream 2>/dev/null || echo "No logs available"
echo "---"
echo ""

# 3. Memory & CPU Usage
echo "⚙️ RESOURCE USAGE:"
if [ ! -z "$ANALYZER_PID" ]; then
    ps aux | awk -v pid="$ANALYZER_PID" '$2 == pid {print "   PID: " $2 "\n   CPU: " $3 "%\n   MEM: " $4 "%"}'
else
    echo "   Process not found (service may be down)"
fi
echo ""

# 4. Queue Stats (from Redis)
echo "📊 QUEUE STATISTICS:"
redis-cli -h localhost -p 6379 <<EOF 2>/dev/null || echo "Redis connection failed"
INFO stats
LLEN queue:raw_messages
EOF
echo ""

# 5. Database Stats
echo "💾 DATABASE STATISTICS:"
psql -U sankeo_user -d sankeo_db -c "
    SELECT 
        'crypto_news'::text as table_name,
        COUNT(*) as record_count,
        pg_size_pretty(pg_total_relation_size('crypto_news')) as size
    FROM crypto_news
    UNION ALL
    SELECT 'news_duplicates'::text, COUNT(*), pg_size_pretty(pg_total_relation_size('news_duplicates'))
    FROM news_duplicates
    UNION ALL
    SELECT 'news_archive'::text, COUNT(*), pg_size_pretty(pg_total_relation_size('news_archive'))
    FROM news_archive;
" 2>/dev/null || echo "Database connection failed"
echo ""

echo "=========================================="
echo "✅ MONITORING COMPLETE"
echo "=========================================="
