# News Analyzer Service 📊

## Overview

The News Analyzer is a standalone service that processes cryptocurrency news messages through a 3-layer filtering system and saves qualified news to the database.

**Luồng xử lý:**
```
Ingestor (push messages)
    ↓
queue:raw_messages (Redis)
    ↓
Analyzer Service
    ├─ Layer 1: Keyword Matching (relevance score)
    ├─ Layer 2: Content Analysis (quality, sentiment, urgency)
    ├─ Layer 3: Gemini AI Scoring (final weight)
    └─ Save to crypto_news table (with dedup)
```

## Features

✅ **3-Layer Filtering:**
- Layer 1: Keyword matching across 9 crypto categories
- Layer 2: Content quality, sentiment, urgency analysis
- Layer 3: Gemini AI final scoring (relevance, credibility, market impact)

✅ **Deduplication:**
- Content hash (SHA256) prevents duplicates
- Tracks occurrences of same news from multiple sources
- Separate `news_duplicates` table for analytics

✅ **Compression:**
- Full text stored only for important news (weight >= 70)
- Archive old news (>7 days) to reduce DB size
- 90% space saving with compression strategy

✅ **Rate Limiting:**
- Batch processing (10 messages/batch)
- Configurable sleep between batches
- Memory efficient with streaming queue processing

## Database Schema

### crypto_news
Main table storing analyzed news messages
```
Columns:
- id: BigInteger (primary key)
- content_hash: String(64) (unique index for dedup)
- source_id, source_name: Chat/Channel info
- text_summary, text_full: Content
- layer1/2/3_*: Filter results
- final_weight: 0-100 score
- tags, created_at, occurrences: Metadata
```

### news_duplicates
Tracks duplicate messages
```
Columns:
- content_hash: Reference to original
- first_news_id: Points to canonical record
- source_id, message_id: Duplicate source
- cosine_similarity: How similar (0-1)
```

### news_archive
Archived old news (>7 days)
```
Columns:
- summary: Compressed text
- total_occurrences: Aggregated count
- archived_at, original_created_at: Timing
```

## Deployment

### Local Testing
```bash
# Test with sample messages
python scripts/test_filter.py

# Check health
python -m src.worker.analyzer_health

# Run analyzer (blocking)
python -m src.worker.news_analyzer
```

### VPS Deployment

#### 1. Initial Setup
```bash
cd /root/sankeo
bash scripts/deploy_analyzer.sh
```

#### 2. Check Status
```bash
pm2 status
pm2 logs sankeo-analyzer
```

#### 3. Monitor Performance
```bash
bash scripts/monitor_analyzer.sh
```

## Configuration

### ecosystem.config.js
```javascript
{
  name: "sankeo-analyzer",
  script: "src/worker/news_analyzer.py",
  interpreter: "./venv/bin/python3",
  instances: 1,
  autorestart: true,
  max_memory_restart: "800M",
  env: {
    PYTHONPATH: ".",
    NODE_ENV: "production"
  }
}
```

### Environment Variables
```
# In .env file
GEMINI_API_KEY=xxx  # For Layer 3 AI scoring
DATABASE_URL=xxx    # PostgreSQL connection
REDIS_URL=xxx       # Redis connection
```

## Queue Format

**Input (queue:raw_messages):**
```json
{
  "user_id": 123,
  "text": "BTC reached $100k! Bullish breakout...",
  "chat_id": -1001234567,
  "message_id": 12345,
  "source_title": "CryptoChanNews",
  "message_link": "https://t.me/...",
  "image_path": "/path/to/image.png",
  "tags": ["SIGNAL", "ONCHAIN"]
}
```

**Output (crypto_news table):**
- Message stored with filter results
- final_weight (0-100)
- Sentiment, urgency, relevance scores
- Dedup via content_hash

## Monitoring & Maintenance

### Daily Checks
```bash
# Check service status
pm2 status | grep sankeo-analyzer

# View recent logs
pm2 logs sankeo-analyzer --lines 50

# Health check
python -m src.worker.analyzer_health
```

### Database Maintenance
```sql
-- Count messages by day
SELECT DATE(created_at), COUNT(*) 
FROM crypto_news 
GROUP BY DATE(created_at);

-- Find duplicates
SELECT content_hash, COUNT(*) as occurrences 
FROM crypto_news 
GROUP BY content_hash 
HAVING COUNT(*) > 1;

-- Archive old messages (>7 days)
-- See scripts/archive_old_news.sh
```

### Troubleshooting

#### Analyzer not processing messages
```bash
# Check queue size
redis-cli LLEN queue:raw_messages

# Check logs
pm2 logs sankeo-analyzer

# Restart service
pm2 restart sankeo-analyzer
```

#### Memory usage high
```bash
# Increase max_memory_restart in ecosystem.config.js
# Or reduce batch_size in news_analyzer.py
```

#### Database disk space
```bash
# Archive old messages
python scripts/archive_old_news.py

# Check table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables WHERE tablename LIKE 'news%' OR tablename LIKE 'crypto%';
```

## Performance Tuning

### Queue Processing
- Default batch size: 10 messages
- Sleep between batches: 5 seconds
- Memory limit: 800MB

### Adjust in news_analyzer.py:
```python
async def process_queue(self, batch_size: int = 10):  # Change batch_size
    ...
    await asyncio.sleep(5)  # Change sleep time
```

### Database Indices
All important columns are indexed for fast querying:
- idx_content_hash: Fast dedup check
- idx_source_id: Find messages by source
- idx_created_at: Time-based queries
- idx_final_weight: Sort by importance

## API Integration

### Store news in database
```python
from src.worker.news_analyzer import NewsAnalyzer

analyzer = NewsAnalyzer()
filtered = await analyzer.process_message(message_data)
if filtered:
    await analyzer.save_to_database(filtered)
```

### Query news
```python
from src.database.models import CryptoNews
from sqlalchemy import select

async with AsyncSessionLocal() as session:
    # High weight news (>70)
    result = await session.execute(
        select(CryptoNews)
        .where(CryptoNews.final_weight >= 70)
        .order_by(CryptoNews.created_at.desc())
        .limit(10)
    )
    news = result.scalars().all()
```

## Future Enhancements

- [ ] Schedule archiving job (move >7 day news to archive)
- [ ] Analytics dashboard (filter accuracy, processing speed)
- [ ] Custom scoring thresholds per tag
- [ ] Integration with user notification system
- [ ] Export news to external APIs

---

**Questions?** Check logs: `pm2 logs sankeo-analyzer`
