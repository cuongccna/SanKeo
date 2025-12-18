# PROJECT CONTEXT: PERSONAL ALPHA HUNTER (COMMERCIAL NATIVE LINUX EDITION)

## 1. Project Overview & Business Logic
Xây dựng hệ thống SaaS (Software as a Service) trên Telegram.
- **Chức năng:** Tự động lắng nghe tin nhắn từ hàng ngàn nhóm Telegram (Userbot), lọc thông tin theo từ khóa cá nhân hóa (Real-time), và gửi thông báo cho người dùng trả phí.
- **Đối tượng:** Crypto traders, Freelancers, Deal hunters.
- **Mô hình doanh thu:** Freemium (Gói Free giới hạn & Gói VIP trả phí theo tháng).
- **Thanh toán:** Tự động 100% qua chuyển khoản ngân hàng (QR Code) tích hợp Webhook (SePay/Casso).

## 2. Infrastructure Constraints (Low-Spec VPS Optimization)
- **Environment:** VPS Ubuntu 20.04+, 1 CPU Core, 4GB RAM.
- **Deployment Strategy:** Native Systemd Services (No Docker).
- **Concurrency Model:** 100% Asyncio (Single-threaded cooperative multitasking) để tối ưu hóa hiệu năng trên 1 CPU.
- **Dependency Management:** Python Virtual Environment (`venv`).

## 3. Technology Stack
- **Language:** Python 3.10+.
- **Database:** PostgreSQL (lưu Users, Rules) + `SQLAlchemy` (Async ORM) + `asyncpg`.
- **Message Queue & Cache:** Redis (Localhost) + `redis-py` (Async).
- **Telegram Core:**
  - `Telethon`: Dùng cho Ingestor (Userbot listening).
  - `Aiogram 3.x`: Dùng cho Bot Interface (User interaction).
- **Web Server:** `FastAPI` + `Uvicorn` (Xử lý Webhook thanh toán).
- **Utilities:** `Loguru` (Logging), `Pydantic` (Data Validation).

## 4. System Architecture (The 4-Pillars)

Hệ thống bao gồm 4 Service chạy độc lập, giao tiếp qua Redis:

### A. Service 1: Ingestor (The Ear)
- **File:** `src/ingestor/main.py`
- **Nhiệm vụ:**
  - Chạy Client Telethon (Userbot).
  - Lắng nghe `events.NewMessage` từ các Channels/Groups mục tiêu.
  - **Không xử lý logic.** Chỉ đóng gói (Serialize) tin nhắn thành JSON.
  - Đẩy vào Redis Queue: `queue:raw_messages`.

### B. Service 2: Worker (The Brain)
- **File:** `src/worker/main.py`
- **Nhiệm vụ:**
  - Loop liên tục lấy tin từ `queue:raw_messages`.
  - **Deduplication:** Check Redis Cache để loại bỏ tin trùng lặp (trong 5-10 phút).
  - **Filtering:** Query DB lấy Rules của User -> Chạy Regex Matching.
  - Nếu Match -> Đẩy job vào Redis Queue: `queue:notifications`.

### C. Service 3: Bot Interface (The Mouth)
- **File:** `src/bot/main.py`
- **Nhiệm vụ:**
  - Xử lý lệnh `/start`, `/add`, `/pay`.
  - Hiển thị Menu Inline Buttons.
  - **Notification Task:** Chạy nền `asyncio.create_task` để lấy tin từ `queue:notifications` và gửi cho User.

### D. Service 4: Payment Gateway (The Wallet)
- **File:** `src/bot/payment_server.py`
- **Nhiệm vụ:**
  - API Endpoint: `POST /webhook/sepay`.
  - Nhận dữ liệu từ SePay -> Parse nội dung chuyển khoản -> Update hạn sử dụng trong DB.
  - Báo cho Bot để gửi tin nhắn cảm ơn User.

## 5. Database Schema (PostgreSQL)

### Table: `users`
- `id` (BigInt, PK): Telegram User ID.
- `username` (String).
- `plan_type` (Enum): 'FREE', 'VIP'.
- `expiry_date` (DateTime): Thời hạn gói VIP.
- `created_at` (DateTime).

### Table: `filter_rules`
- `id` (Serial, PK).
- `user_id` (FK -> users.id).
- `keyword` (String): Từ khóa cần lọc (VD: "ETH", "Recruit").
- `is_active` (Boolean).

### Table: `transactions`
- `id` (String, PK): Mã giao dịch ngân hàng.
- `user_id` (FK -> users.id).
- `amount` (Decimal).
- `status` (String): 'SUCCESS'.

## 6. Directory Structure
```text
/opt/alpha_hunter/
├── .env                  # Secrets (API Keys, DB URL)
├── requirements.txt
├── src/
│   ├── database/         # Models & Connection logic
│   ├── ingestor/         # Telethon Userbot logic
│   ├── worker/           # Filter Engine logic
│   ├── bot/              # Aiogram Bot & Payment logic
│   └── common/           # Shared Utils (Logger, Redis Connector)
└── scripts/
    ├── start_services.sh
    └── install.sh
	
## 7.Developer Instructions (For Copilot)
- Luôn sử dụng Async/Await: Tuyệt đối không dùng blocking code (như time.sleep, requests).
- Error Handling: Luôn bọc các tác vụ mạng (Telegram API, DB, Redis) trong try/except để tránh crash service.
- Logging: Ghi log rõ ràng (Info/Error) để debug trên VPS.