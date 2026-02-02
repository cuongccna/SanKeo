# Hướng Dẫn Migration Database - Script Trực Tiếp (Không Dùng Alembic)

## 📋 Mục Đích
Script `migrate_crypto_news_direct.py` tạo các tables cho crypto news storage **trực tiếp** bằng SQLAlchemy, không cần alembic.

## 🎯 Các Tables Được Tạo

### 1. **crypto_news** - Bảng chính lưu tin tức
- `id`: ID tin tức (BigInteger, auto-increment)
- `content_hash`: SHA256 hash nội dung (unique index)
- `source_id`: Chat ID nguồn (Telegram)
- `source_name`: Tên nguồn
- `message_id`: ID tin nhắn
- `text_summary`: 500 ký tự đầu
- `text_full`: Nội dung đầy đủ (nếu weight >= 70)
- **Filter results**:
  - `layer1_matched_keywords`: JSON danh sách từ khóa
  - `layer2_quality_score`: Điểm chất lượng (0-100)
  - `layer2_sentiment`: bullish|neutral|bearish
  - `layer2_urgency`: breaking|important|regular
  - `layer2_credibility`: Độ tin cậy (0-100)
  - `layer3_relevance`: Liên quan (AI, 0-100)
  - `layer3_credibility`: Tin cậy (AI, 0-100)
  - `layer3_market_impact`: Tác động thị trường (0-100)
  - `final_weight`: Điểm cuối cùng (0-100)
- `created_at`, `last_seen_at`: Timestamps
- `occurrences`: Số lần xuất hiện (dedup counter)

### 2. **news_duplicates** - Theo dõi tin trùng lặp
- `id`: ID bản ghi
- `content_hash`: Hash nội dung
- `first_news_id`: FK tới crypto_news (tin gốc)
- `source_id`, `message_id`: Thông tin bản sao
- `cosine_similarity`: Độ giống nhau (0-1)
- Dùng để tránh hiển thị cùng tin nhiều lần

### 3. **news_archive** - Lưu trữ tin cũ (> 7 ngày)
- `id`: ID ban đầu
- `content_hash`: Hash nội dung
- `summary`: Tóm tắt (200 ký tự)
- `total_occurrences`: Tổng số lần xuất hiện
- `final_weight`: Điểm cuối cùng
- `sentiment`: Cảm xúc (bullish/neutral/bearish)
- **Mục đích**: Giảm dung lượng DB (tiết kiệm ~90%)

## 🚀 Cách Sử Dụng

### Local (Windows)
```powershell
# Từ thư mục workspace
cd D:\projects\Telegrams\SanKeo

# Chạy migration script
.\.venv\Scripts\python scripts/migrate_crypto_news_direct.py
```

### VPS (Linux)
```bash
# Từ thư mục workspace
cd /root/sankeo

# Chạy migration script
./venv/bin/python scripts/migrate_crypto_news_direct.py
```

## 📝 Output Mong Đợi

```
============================================================
CRYPTO NEWS MIGRATION - DIRECT SCRIPT
============================================================
Timestamp: 2026-02-03T15:30:45.123456

📝 Creating tables from models...
  - crypto_news
  - news_duplicates
  - news_archive
✅ Tables created successfully

📊 Verification:
  ✓ crypto_news: True
  ✓ news_duplicates: True
  ✓ news_archive: True

✅ Indices created:
  - idx_content_hash: ['content_hash']
  - idx_source_id: ['source_id']
  - idx_created_at: ['created_at']
  - idx_final_weight: ['final_weight']
  - idx_first_news_id: ['first_news_id']
  - idx_archived_at: ['archived_at']

============================================================
🎉 MIGRATION COMPLETED SUCCESSFULLY!
============================================================
```

## ⚠️ Nếu Tables Đã Tồn Tại

Script sẽ hỏi:
```
⚠️  Found existing tables: crypto_news, news_duplicates, news_archive

Do you want to DROP and recreate these tables? (yes/no): 
```

- Nhập `yes` để xóa và tạo lại (sẽ mất dữ liệu cũ)
- Nhập `no` để hủy migration

## 🔄 So Sánh: Alembic vs Script Trực Tiếp

| Tính Năng | Alembic | Script Trực Tiếp |
|-----------|---------|-----------------|
| **Cơ chế** | Quản lý version, up/down | Tạo từ models trực tiếp |
| **Phức tạp** | Cao (2 files: env.py, migration) | Thấp (1 file) |
| **Rollback** | Hỗ trợ (`alembic downgrade`) | Manual (phải xóa tay) |
| **Lần đầu** | ✅ Tốt cho version control | ✅ Nhanh hơn |
| **Cập nhật schema** | ✅ Theo dõi từng bước | ❌ Cần viết lại script |
| **Sử dụng khi** | Dự án lớn, nhiều migrations | Dự án nhỏ, setup nhanh |

## 📌 Các Bước Triển Khai Trên VPS

### 1. SSH vào VPS
```bash
ssh root@your-vps-ip
cd /root/sankeo
```

### 2. Kích hoạt virtual environment
```bash
source ./venv/bin/activate
```

### 3. Chạy migration
```bash
python scripts/migrate_crypto_news_direct.py
```

### 4. Kiểm tra database
```bash
# Kết nối PostgreSQL
psql -U postgres -d sankeo -c "\dt crypto_news*"

# Hoặc xem từ script:
psql -U postgres -d sankeo -c "SELECT count(*) FROM crypto_news;"
```

## 🐛 Troubleshooting

### Lỗi: "ModuleNotFoundError: No module named 'src'"
```bash
# Chắc chắn bạn đang ở thư mục workspace
cd /root/sankeo  # VPS
# hoặc
cd D:\projects\Telegrams\SanKeo  # Windows
```

### Lỗi: "could not translate host name \"localhost\" to address"
Database không chạy. Kiểm tra:
```bash
# VPS
sudo systemctl status postgresql

# Hoặc Windows
# Kiểm tra Docker Desktop/PostgreSQL service
```

### Lỗi: "relation \"crypto_news\" already exists"
Bảng đã tồn tại. Script sẽ hỏi `yes/no` - nhập `yes` để xóa và tạo lại.

## 📊 Xác Minh Sau Migration

### Kiểm tra tables
```sql
-- Via psql
psql -U postgres -d sankeo

-- Liệt kê tables
\dt crypto_news*

-- Xem cấu trúc
\d crypto_news
\d news_duplicates
\d news_archive

-- Đếm rows
SELECT COUNT(*) FROM crypto_news;
SELECT COUNT(*) FROM news_duplicates;
SELECT COUNT(*) FROM news_archive;
```

### Script kiểm tra (tương tự test_ingestor.py)
```bash
python scripts/analyzer_health.py
```

Sẽ show:
- ✅ Database connection OK
- ✅ crypto_news table exists
- ✅ Queue size: X messages
- ✅ Recent records: X (last 24h)

## 🎯 Sử Dụng Migration Trong Deployment

### `scripts/deploy_analyzer.sh` sẽ bao gồm:
```bash
#!/bin/bash
cd /root/sankeo

# Pull code
git pull origin main

# Run migration
./venv/bin/python scripts/migrate_crypto_news_direct.py

# Start analyzer
pm2 start ecosystem.config.js --only sankeo-analyzer
```

## ✅ Checklist Triển Khai

- [ ] Chạy migration script trên VPS
- [ ] Xác minh tables được tạo (`\dt crypto_news*`)
- [ ] Kiểm tra indices (`\di`)
- [ ] Kiểm tra kết nối từ analyzer (`python scripts/analyzer_health.py`)
- [ ] Start analyzer service (`pm2 start ecosystem.config.js --only sankeo-analyzer`)
- [ ] Monitor logs (`pm2 logs sankeo-analyzer`)

## 💡 Tips

1. **Chạy lần đầu?** Cứ chạy script, nó tự tạo tables
2. **Muốn reset data?** Script sẽ hỏi `yes/no` để xóa
3. **Muốn keepu data cũ?** Tạo backup trước:
   ```sql
   CREATE TABLE crypto_news_backup AS SELECT * FROM crypto_news;
   ```
4. **Chạy trên VPS?** SSH trước, sau đó chạy script

---

**Tạo ngày**: 2026-02-03  
**Script**: `scripts/migrate_crypto_news_direct.py`  
**Tên DB**: `sankeo`  
**Tables**: 3 (crypto_news, news_duplicates, news_archive)
