# 🎯 SanKeo - Personal Alpha Hunter

> Hệ thống SaaS trên Telegram: Tự động lắng nghe tin nhắn từ hàng ngàn nhóm, lọc theo từ khóa cá nhân hóa, gửi thông báo real-time cho người dùng trả phí.

---

## 📊 Tiến độ dự án

### Phase 1: Khung dự án (Framework Setup)
| Task | Mô tả | Trạng thái |
|------|-------|------------|
| Cấu trúc thư mục | Tạo src/, scripts/, common/ | ✅ Done |
| Database Models | User, FilterRule, Transaction | ✅ Done |
| Config & Environment | .env, config.py, requirements.txt | ✅ Done |
| Logger & Redis Client | Common utilities | ✅ Done |
| Scripts | install.sh, install_windows.ps1 | ✅ Done |

### Phase 2: Core Services (4-Pillars)
| Service | File | Mô tả | Trạng thái |
|---------|------|-------|------------|
| Ingestor | `src/ingestor/main.py` | Telethon Userbot lắng nghe tin nhắn | ✅ Done |
| Worker | `src/worker/main.py` | Filter Engine + Regex Matching + Dedup | ✅ Done |
| Bot Interface | `src/bot/main.py` | Aiogram Bot + FSM + Inline Buttons | ✅ Done |
| Payment Gateway | `src/bot/payment_server.py` | FastAPI Webhook SePay/Casso | ✅ Done |

### Phase 3: Business Logic
| Task | Mô tả | Trạng thái |
|------|-------|------------|
| User Registration | /start tạo user mới trong DB | ✅ Done |
| Add Keywords | /add thêm filter rules + FSM | ✅ Done |
| Deduplication | Redis cache chống tin trùng (5 phút) | ✅ Done |
| Regex Matching | Worker filter tin nhắn | ✅ Done |
| Notification | Bot gửi tin cho user | ✅ Done |
| Payment Flow | Webhook SePay/Casso + Auto VIP upgrade | ✅ Done |
| VIP/Free Logic | Phân quyền theo plan_type + daily limit | ✅ Done |

### Phase 4: Production Ready
| Task | Mô tả | Trạng thái |
|------|-------|------------|
| Systemd Services | Tạo .service files cho VPS | ⬜ Pending |
| Error Handling | Try/except toàn bộ services | ✅ Done |
| Rate Limiting | Giới hạn request/user (FREE: 10/ngày) | ✅ Done |
| Monitoring | Health check endpoints | ✅ Done |

---

## 🛠️ Cài đặt

### Windows (Local Development)
```powershell
# 1. Chạy script setup
.\scripts\install_windows.ps1

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Cấu hình .env (copy từ .env.example)

# 4. Khởi tạo database tables
python init_db.py

# 5. Chạy services (mỗi terminal riêng)
python -m src.bot.main
python -m src.worker.main
python -m src.ingestor.main
```

### VPS Ubuntu
```bash
# 1. Clone repo
git clone <repo_url> /opt/alpha_hunter
cd /opt/alpha_hunter

# 2. Chạy install script
chmod +x scripts/install.sh
./scripts/install.sh

# 3. Cấu hình .env

# 4. Chạy services
./scripts/start_services.sh
```

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │     │   Redis     │     │ PostgreSQL  │
│  Channels   │     │   Queues    │     │   Database  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  INGESTOR   │────▶│   WORKER    │────▶│     BOT     │
│  (Telethon) │     │  (Filter)   │     │  (Aiogram)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                    queue:raw_messages
                    queue:notifications
```

---

## 📁 Cấu trúc thư mục

```
SanKeo/
├── .env                      # Secrets (Git ignored)
├── .env.example              # Template
├── .gitignore
├── requirements.txt
├── init_db.py                # DB initialization
├── PROJECT_CONTEXT.md        # Architecture docs
├── README.md                 # This file
├── src/
│   ├── common/
│   │   ├── config.py         # Pydantic Settings
│   │   ├── logger.py         # Loguru
│   │   └── redis_client.py   # Async Redis
│   ├── database/
│   │   ├── db.py             # SQLAlchemy Async
│   │   └── models.py         # ORM Models
│   ├── ingestor/
│   │   └── main.py           # Userbot Service
│   ├── worker/
│   │   └── main.py           # Filter Service
│   └── bot/
│       ├── main.py           # Bot Service
│       └── payment_server.py # Webhook Service
└── scripts/
    ├── install.sh            # VPS setup
    ├── install_windows.ps1   # Windows setup
    └── start_services.sh     # VPS startup
```

---

## 📋 Chú thích trạng thái

| Icon | Ý nghĩa |
|------|---------|
| ✅ | Hoàn thành |
| 🔲 | Skeleton (có code nhưng chưa logic) |
| ⬜ | Chưa bắt đầu |
| 🚧 | Đang làm |

---

## 📞 Tech Stack

- **Python 3.10+**
- **PostgreSQL** + SQLAlchemy (Async)
- **Redis** + redis-py (Async)
- **Telethon** (Userbot)
- **Aiogram 3.x** (Bot)
- **FastAPI** + Uvicorn (Webhook)
- **Loguru** (Logging)
