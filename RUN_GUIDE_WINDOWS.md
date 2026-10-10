# CLASS FUND WEB — HƯỚNG DẪN VẬN HÀNH & CHẠY HỆ THỐNG NATIVE WINDOWS (PHASE 11)
> **Tài liệu Kỹ thuật Chuẩn hóa & Hướng dẫn Vận hành Native Windows (Phase 11 Production-Ready)**  
> **Môi trường Thực thi:** Native Windows 10 / 11 / Windows Server (Dịch vụ Cục bộ — Không sử dụng Docker)  
> **Bộ mã hóa:** UTF-8 (`chcp 65001`) | **Phiên bản:** v1.1.0-windows-automation | **Trạng thái:** PRODUCTION OPERATIONAL  

---

## MỤC LỤC
1. [Giới thiệu & Kiến trúc Tổng thể](#1-giới-thiệu--kiến-trúc-tổng-thể)
2. [Yêu cầu Môi trường & Cài đặt Phần mềm (Native Setup)](#2-yêu-cầu-môi-trường--cài-đặt-phần-mềm-native-setup)
3. [Thiết lập Cơ sở Dữ liệu Lần đầu (Database Setup & Migrations)](#3-thiết-lập-cơ-sở-dữ-liệu-lần-đầu-database-setup--migrations)
4. [Khởi động & Vận hành Native bằng Batch Script (Phase 11)](#4-khởi-động--vận-hành-native-bằng-batch-script-phase-11)
5. [Hướng dẫn Sử dụng Tính năng Người dùng](#5-hướng-dẫn-sử-dụng-tính-năng-người-dùng)
6. [Quy trình Chuyển đổi Máy A sang Máy B (Cross-Machine Migration)](#6-quy-trình-chuyển-đổi-máy-a-sang-máy-b-cross-machine-migration)
7. [Xử lý Sự cố Thường gặp (Troubleshooting & Diagnostic Matrix)](#7-xử-lý-sự-cố-thường-gặp-troubleshooting--diagnostic-matrix)

---

## 1. GIỚI THIỆU & KIẾN TRÚC TỔNG THỂ

### 1.1 Tên Dự án & Tầm nhìn
**CLASS FUND WEB** là nền tảng quản lý tài chính quỹ lớp thông minh, minh bạch và tự động hóa cao cấp. Hệ thống được xây dựng nhằm giải quyết triệt để các vấn đề thất thoát quỹ, nhầm lẫn số liệu và chậm trễ đối soát trong các tập thể lớp học, hội phụ huynh và câu lạc bộ.

Hệ thống kết hợp mô hình thị giác máy tính cục bộ (**Local Vision AI**) với kiến trúc tài chính ngân hàng lõi (**Core Banking Ledger Engine**), cho phép học sinh/phụ huynh nộp quỹ bằng cách gửi ảnh chuyển khoản qua Chat, AI tự động nhận diện và ghi nhận sổ cái với độ chính xác tuyệt đối.

### 1.2 Cơ chế Tài chính Cốt lõi (Financial Invariants)
Hệ thống tuân thủ nghiêm ngặt 5 bất biến tài chính được kiểm toán tự động:

1. **Sổ cái Bất biến (Append-Only Immutable Ledger):**
   - Mọi bản ghi trong bảng `ledger_entries` và `transactions` đều mang tính chất bất biến (không bao giờ thực thi câu lệnh `UPDATE` số tiền hoặc `DELETE` bản ghi đã ghi sổ).
   - Mọi điều chỉnh tài chính (nhầm lẫn, nộp thừa, thu hồi) đều phải thông qua bút toán đảo ngược đối ứng mang loại `REVERT`, bảo tồn 100% dòng tiền và lịch sử kiểm toán (`audit_logs`).
2. **Độ chính xác Tài chính Ngân hàng (`DECIMAL(18,2)`):**
   - Triệt tiêu hoàn toàn sai số dấu phẩy động (floating-point inaccuracies) thường gặp ở JavaScript/Python float. Mọi phép toán tài chính trên MySQL và Backend Python đều thực thi trên kiểu dữ liệu số thực chính xác cao `DECIMAL(18,2)`.
3. **Kiểm toán Cân đối Tuyệt đối (0.00 VND Drift Guarantee):**
   - Bất đẳng thức kế toán: $\text{Số dư hiện tại} = \text{Số dư mở đầu} + \sum(\text{CREDIT}) - \sum(\text{DEBIT}) \pm \sum(\text{REVERT})$.
   - Hệ thống liên tục kiểm tra sai số đối soát qua công cụ `reconcile_migration.py --audit`, cam kết sai số tuyệt đối bằng **0.00 VND**.
4. **Cổng Đột biến Đơn nhất (Single Mutation Gateway):**
   - Toàn bộ dòng tiền tạo ra từ quá trình đọc biên lai AI bắt buộc phải hội tụ qua một hàm kiểm soát duy nhất: `verify_and_post_from_ai()` trong module `app.services.ledger`. Không một API công khai nào có quyền ghi trực tiếp vào sổ cái mà không qua cổng kiểm định này.
5. **Định danh Bất biến & Chống Trùng lặp (Idempotency Engine):**
   - Khóa Idempotency tuân thủ cấu trúc chuẩn hóa: `msg_{message_id}_v{content_hash}`.
   - Cơ chế phòng chống gian lận nộp trùng đa lớp:
     - **Tầng 1 (File Hash):** Kiểm tra mã băm SHA-256 nhị phân của tệp ảnh.
     - **Tầng 2 (Perceptual Hash - pHash):** Sử dụng thuật toán nhận diện ảnh tương đồng chống hành vi cắt viền, nén lại hoặc thay đổi kích thước ảnh biên lai cũ.
     - **Tầng 3 (Bank Transaction Code Constraint):** Khóa duy nhất cơ sở dữ liệu `uq_bank_transaction_code` trên cặp `(bank_account_id, transaction_code)`.

### 1.3 AI Vision Pipeline — Bảo mật & Riêng tư Cục bộ 100%
- **Thị giác Máy tính Cục bộ (Local Computer Vision):** Sử dụng mô hình `qwen2.5vl:3b` vận hành qua **Ollama for Windows** (cổng `11434`).
- **Xử lý Đa tầng:** Tự động trích xuất các trường thông tin: Mã giao dịch ngân hàng (`transaction_code`), Số tiền chuyển (`amount`), Tên người chuyển (`sender_name`), Ngân hàng thụ hưởng (`bank_name`), và Thời gian giao dịch (`transaction_time`).
- **Ngôn ngữ Bổ trợ Fallback:** Sử dụng mô hình văn bản `qwen3.5:4b` kết hợp bộ tiền xử lý hình ảnh OpenCV/Pillow để phục hồi văn bản trong điều kiện ảnh mờ hoặc biên lai có độ tương phản thấp.
- **Quyền riêng tư Tuyệt đối (Zero Cloud Leakage):** Không một byte hình ảnh hay thông tin tài khoản cá nhân nào bị gửi lên dịch vụ đám mây bên thứ ba. Toàn bộ quá trình suy luận AI diễn ra trên GPU/CPU nội bộ của máy Windows.

### 1.4 Sơ đồ Luồng Hoạt động Kiến trúc Hệ thống

```mermaid
flowchart TD
    subgraph ClientLayer ["Lớp Người dùng (Browser)"]
        Guest["Khách / Học sinh / Phụ huynh<br/>(Guest Chat - Không cần đăng nhập)"]
        Admin["Thủ quỹ / Ban cán sự<br/>(Admin Dashboard & Review Queue)"]
    end

    subgraph PresentationLayer ["Giao diện Frontend (Port 3000 / 5173)"]
        ViteUI["React 19 + Vite UI<br/>- GuestChatPage (Upload & Token Recall)<br/>- AdminDashboardView & ReviewQueue"]
    end

    subgraph CoreLayer ["Lớp Backend & AI Processing (Native Windows)"]
        FastAPI["FastAPI Core API (Port 8000)<br/>- /api/v1/messages<br/>- /api/v1/health/deep<br/>- /internal/review"]
        RedisPubSub["Redis / Memurai (Port 6379)<br/>Cache, Hàng đợi & WebSocket Pub/Sub"]
        Worker["Background AI Worker (worker/main.py)<br/>Claim Jobs qua FOR UPDATE SKIP LOCKED"]
        OllamaEngine["Ollama Service (Port 11434)<br/>- qwen2.5vl:3b (Vision OCR)<br/>- qwen3.5:4b (Text Fallback)"]
    end

    subgraph DataLayer ["Lớp Dữ liệu Bất biến (MySQL 8.4/9.x - Port 3306)"]
        DB[("MySQL Database: classfund<br/>- uploads (pHash, SHA256)<br/>- messages (Lease 300s)<br/>- transactions & ledger_entries (DECIMAL 18,2)<br/>- idempotency_keys & audit_logs")]
        Storage["Thư mục lưu trữ tệp cục bộ<br/>(./uploads & ./storage/uploads)"]
    end

    Guest -->|1. Gửi ảnh biên lai + Lời nhắn| ViteUI
    Admin -->|Quản lý & Duyệt thủ công| ViteUI
    ViteUI -->|2. HTTP POST /api/v1/messages| FastAPI
    FastAPI -->|3. Lưu ảnh & Tạo tin nhắn (Pending)| DB
    FastAPI -->|Lưu tệp ảnh| Storage
    FastAPI -->|Bắn tín hiệu sự kiện| RedisPubSub
    Worker -->|4. Quét job (SKIP LOCKED)| DB
    Worker -->|5. Đọc ảnh & Suy luận bóc tách| OllamaEngine
    Worker -->|6. verify_and_post_from_ai()| DB
    Worker -->|7. Cập nhật tiến độ realtime| RedisPubSub
    RedisPubSub -->|8. WebSocket / Polling Stream| ViteUI
```

---

## 2. YÊU CẦU MÔI TRƯỜNG & CÀI ĐẶT PHẦN MỀM (NATIVE SETUP)

Hệ thống được thiết kế để chạy trực tiếp trên hệ điều hành Windows (**Native Windows**) bằng các dịch vụ hệ thống cục bộ, mang lại hiệu năng cao nhất, không bị phụ thuộc vào lớp ảo hóa Hyper-V/WSL2 của Docker.

### 2.1 Bảng Tổng hợp 5 Thành phần Phần mềm Bắt buộc

| STT | Phần mềm | Phiên bản Yêu cầu | Cổng Dịch vụ | Mục đích Sử dụng |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Python (Windows x64)** | 3.11.x hoặc 3.12.x | — | Runtime cho FastAPI Backend, Background AI Worker, Alembic Migrations |
| **2** | **Node.js & npm** | v18.x, v20.x hoặc v24.x (npm 10+) | `3000` / `5173` | Runtime và Trình đóng gói giao diện Frontend React + Vite |
| **3** | **MySQL Server** | 8.4 LTS hoặc 9.x | `3306` | Cơ sở dữ liệu quan hệ lưu trữ sổ cái quỹ, bảng băm pHash và nhật ký kiểm toán |
| **4** | **Memurai / Redis for Windows** | v4.x+ (tương thích Redis 7) | `6379` | Bộ nhớ đệm (Cache), Quản lý phiên và Redis Pub/Sub cho WebSocket realtime |
| **5** | **Ollama for Windows** | v0.3.x trở lên | `11434` | Máy chủ cục bộ chạy mô hình thị giác máy tính đọc biên lai tài chính |

---

### 2.2 Hướng dẫn Cài đặt & Cấu hình Chi tiết từng Thành phần

#### Bước 1: Cài đặt Python & Thiết lập Môi trường Ảo (`.venv`)
1. Tải Python 3.11/3.12 từ [python.org](https://www.python.org/downloads/windows/).  
   *(Khi cài đặt, bắt buộc tích chọn **"Add python.exe to PATH"**).*
2. Mở PowerShell tại thư mục gốc của dự án (`C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB`):
   ```powershell
   # 1. Tạo môi trường ảo Python cô lập
   python -m venv .venv

   # 2. Kích hoạt môi trường ảo
   .\.venv\Scripts\Activate.ps1

   # 3. Nâng cấp bộ cài đặt gói cơ sở
   python -m pip install --upgrade pip setuptools wheel

   # 4. Cài đặt các gói phụ thuộc Backend
   cd class-fund-backend-v0.1\class-fund-backend
   pip install -e .
   pip install pymysql argon2-cffi redis pydantic-settings
   cd ..\..
   ```

#### Bước 2: Cài đặt Node.js & Cài đặt Gói Phụ thuộc Frontend
1. Tải Node.js phiên bản LTS từ [nodejs.org](https://nodejs.org/).
2. Mở terminal và cài đặt dependencies cho ứng dụng web:
   ```powershell
   cd classfund\classfund
   npm install
   cd ..\..
   ```

#### Bước 3: Cài đặt & Cấu hình MySQL Server (Port 3306)
1. Tải MySQL Installer cho Windows từ [dev.mysql.com](https://dev.mysql.com/downloads/installer/).
2. Chọn cài đặt **MySQL Server 8.4 LTS** (hoặc 9.x).
3. Cấu hình dịch vụ:
   - Port: `3306`.
   - Windows Service Name: `MySQL84` (hoặc `MySQL`).
   - Khởi động dịch vụ tự động cùng Windows.
4. Kiểm tra dịch vụ trên Windows:
   ```powershell
   # Khởi động dịch vụ nếu đang dừng
   net start MySQL84

   # Kiểm tra cổng 3306 đang lắng nghe
   Test-NetConnection -ComputerName 127.0.0.1 -Port 3306
   ```

#### Bước 4: Cài đặt Redis for Windows (Memurai - Port 6379)
Vì Redis chính thức chỉ hỗ trợ Linux, trên môi trường Native Windows ta sử dụng **Memurai** (bản tương thích 100% với Redis 7 API) hoặc bản build độc lập của Redis:
1. Tải Memurai từ [memurai.com](https://www.memurai.com/).
2. Cài đặt Memurai dưới dạng Windows Service, cổng mặc định `6379`, không yêu cầu mật khẩu trong môi trường phát triển cục bộ.
3. Kiểm tra kết nối Redis qua PowerShell:
   ```powershell
   net start Memurai
   Test-NetConnection -ComputerName 127.0.0.1 -Port 6379
   ```

#### Bước 5: Cài đặt Ollama & Tải Mô hình Thị giác Máy tính
1. Tải và cài đặt Ollama từ [ollama.com/download/windows](https://ollama.com/download/windows).
2. Sau khi cài đặt, Ollama tự động chạy ở khay hệ thống (System Tray) tại địa chỉ `http://127.0.0.1:11434`.
3. Mở Command Prompt / PowerShell tải 2 mô hình bắt buộc:
   ```powershell
   # Tải mô hình Vision đọc ảnh biên lai ngân hàng (bắt buộc)
   ollama pull qwen2.5vl:3b

   # Tải mô hình Text xử lý suy luận & OCR fallback (bổ trợ)
   ollama pull qwen3.5:4b

   # Kiểm tra danh sách mô hình đã sẵn sàng
   ollama list
   ```

---

## 3. THIẾT LẬP DỮ LIỆU LẦN ĐẦU (DATABASE SETUP & MIGRATIONS)

### 3.1 Khởi tạo Cơ sở Dữ liệu & Người dùng trên MySQL
Mở MySQL Command Line Client hoặc MySQL Workbench bằng tài khoản `root`, chạy các câu lệnh SQL sau:

```sql
-- 1. Tạo cơ sở dữ liệu hỗ trợ bảng mã tiếng Việt đầy đủ (utf8mb4)
CREATE DATABASE IF NOT EXISTS classfund 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 2. Tạo tài khoản ứng dụng classfund
CREATE USER IF NOT EXISTS 'classfund'@'localhost' IDENTIFIED BY 'classfund';
CREATE USER IF NOT EXISTS 'classfund'@'127.0.0.1' IDENTIFIED BY 'classfund';

-- 3. Phân quyền đầy đủ cho tài khoản trên database classfund
GRANT ALL PRIVILEGES ON classfund.* TO 'classfund'@'localhost';
GRANT ALL PRIVILEGES ON classfund.* TO 'classfund'@'127.0.0.1';
FLUSH PRIVILEGES;
```

### 3.2 Cấu hình Tệp Biến Môi trường (`.env`)
Đảm bảo tệp `.env` tại thư mục backend (`class-fund-backend-v0.1\class-fund-backend\.env`) và thư mục gốc chứa các thông số chuẩn hóa sau:

```ini
# Application Configuration
APP_NAME=Class Fund API
ENVIRONMENT=development
LOG_LEVEL=INFO

# MySQL 8.4 Connection URL (Driver PyMySQL, Charset utf8mb4)
DATABASE_URL=mysql+pymysql://classfund:classfund@127.0.0.1:3306/classfund?charset=utf8mb4

# Redis In-Memory Cache & Pub/Sub
REDIS_URL=redis://127.0.0.1:6379/0

# Ollama Vision & Text AI Service
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=qwen2.5vl:3b
OLLAMA_TEXT_MODEL=qwen3.5:4b

# Security, Tokens & Files
JWT_SECRET=supersecret-dev-jwt-key-minimum-32-chars-long!
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=60
UPLOAD_DIR=./storage/uploads
MAX_UPLOAD_MB=10
AI_SERVICE_KEY=dev-ai-service-key-12345

# Financial Invariants & Worker Policy
AI_CONFIDENCE_THRESHOLD=0.90
DECIMAL_PRECISION=2
WORKER_ID=worker-1
LEASE_DURATION=300
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 3.3 Chạy Migrations Alembic (Khởi tạo Toàn bộ Bảng Dữ liệu)
Thực thi lệnh Alembic Migration để thiết lập toàn bộ cấu trúc cơ sở dữ liệu:

```powershell
# Di chuyển vào thư mục backend và kích hoạt venv
cd C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB\class-fund-backend-v0.1\class-fund-backend
..\..\.venv\Scripts\Activate.ps1

# Chạy migration lên phiên bản mới nhất
alembic upgrade head
```

#### Cấu trúc 19 Bảng Dữ liệu được Tạo lập:
Hệ thống tạo đầy đủ 19 bảng (18 bảng nghiệp vụ + 1 bảng theo dõi schema `alembic_version`):
1. `users`: Tài khoản người dùng, phân quyền RBAC (`OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC`).
2. `accounts`: Tài khoản quỹ lớp (Số dư mở đầu `opening_balance`, tiền tệ `VND`).
3. `bank_accounts`: Danh sách tài khoản ngân hàng nhận tiền, liên kết mã thanh toán và ảnh VietQR.
4. `uploads`: Quản lý tệp tải lên, chứa `file_hash` (SHA-256) và `perceptual_hash` (pHash) nhận diện trùng lặp ảnh.
5. `students`: Danh bạ học sinh, mã sinh viên/học sinh (`student_code`) và danh sách biệt danh (`aliases` JSON).
6. `collection_campaigns`: Chiến dịch thu quỹ lớp (Hạn nộp, số tiền kỳ vọng `expected_amount`).
7. `campaign_members`: Danh sách học sinh trong từng đợt thu (`UNPAID`, `PAID`, `EXEMPT`).
8. `extracted_transactions`: Bảng ghi nhận kết quả bóc tách từ Vision AI (`confidence`, `field_confidences` JSON).
9. `transactions`: Bảng giao dịch nghiệp vụ (`CREDIT`, `DEBIT`, `REVERT`). Khóa chống trùng `uq_bank_transaction_code`.
10. `ledger_entries`: **Sổ cái tài chính bất biến**, đối tượng kiểm toán số dư cốt lõi.
11. `idempotency_keys`: Lưu trữ khóa định danh ngăn chặn việc lặp lại thao tác thanh toán.
12. `audit_logs`: Nhật ký kiểm toán an ninh ghi nhận trạng thái trước (`before_data`) và sau (`after_data`).
13. `payment_matches`: Liên kết tự động giữa giao dịch ngân hàng với chiến dịch thu quỹ và học sinh.
14. `messages`: Hàng đợi tin nhắn trao đổi và gửi biên lai. Hỗ trợ trường `attachment_ids` (JSON), mã `public_code` (`CF-YYYYMMDD-XXXXXX`), `recall_token_hash`, và cơ chế khóa hạn giờ `lease_expires_at`.
15. `worker_status`: Theo dõi nhịp tim (`heartbeat`), trạng thái sống (`online`/`offline`) và tác vụ hiện tại của Worker.
16. `recall_tokens`: Quản lý mã thu hồi tin nhắn/biên lai của người dùng.
17. `chat_messages`: Lưu trữ trao đổi nội bộ gắn liền với từng dòng sổ cái.
18. `revoked_tokens`: Danh sách đen JWT đã bị thu hồi/đăng xuất.
19. `alembic_version`: Lưu trữ chuỗi định danh phiên bản schema (`0001_initial_mysql`).

### 3.4 Khởi tạo Dữ liệu Mẫu (Seed Admin & Default Fund Account)
Chạy script khởi tạo tài khoản quản trị viên và tài khoản quỹ mặc định:

```powershell
python scripts\seed_admin.py
```
- **Tài khoản Thủ quỹ Mặc định:** `admin@classfund.local`
- **Mật khẩu Mặc định:** `change-this`
- **Tài khoản Quỹ:** `Class Fund` (Số dư ban đầu: `0.00 VND`)

---

## 4. KHỞI ĐỘNG & VẬN HÀNH NATIVE BẰNG BATCH SCRIPT (PHASE 11)

Dự án cung cấp bộ tự động hóa chuẩn hóa chuyên biệt cho hệ điều hành Windows, loại bỏ nhu cầu gõ các lệnh phức tạp.

### 4.1 Danh mục Script Tự động hóa Gốc & Thư mục `scripts\windows`

| Script tại Thư mục Gốc | Script Thực thi Thực tế | Vai trò & Mục đích |
| :--- | :--- | :--- |
| `start.bat` | `scripts\windows\01_start_all.bat` | Khởi động 1-Click: Kiểm tra `.env`, kiểm tra dịch vụ và bật hệ thống |
| `stop.bat` | `scripts\windows\02_stop_all.bat` | Tắt an toàn 1-Click: Rút cạn worker (drain 5s), giải phóng khóa `SKIP LOCKED` |
| `backup.bat` | `scripts\windows\03_db_backup.bat` | Sao lưu cơ sở dữ liệu GTID, tính mã băm SHA-256 và giữ 7 bản sao lưu gần nhất |
| — | `scripts\windows\04_db_restore.bat` | Phục hồi dữ liệu từ bản backup và tự động đối soát số dư sai số `0.00 VND` |
| `export_to_machine_b.bat` | `scripts\windows\05_export_machine_a.bat` | Đóng gói toàn bộ hệ thống trên Máy A thành `classfund_transfer_package.zip` |
| `import_from_machine_a.bat` | `scripts\windows\06_import_machine_b.bat` | Tiếp nhận gói chuyển đổi trên Máy B, nạp dữ liệu và đối soát cân bằng sổ cái |
| — | `scripts\windows\07_health_check.bat` | Kiểm tra cổng dịch vụ MySQL 3306, Redis 6379 và probe `/api/v1/health/deep` |
| — | `scripts\windows\08_reconcile_balance.bat` | Kiểm toán tức thì toàn bộ sổ cái quỹ lớp, kiểm tra độ lệch `0.00 VND` |

---

### 4.2 Chế độ 1: Vận hành Tự động 1-Click bằng Batch Script (Production / Staging)

#### Khởi động Hệ thống:
Người dùng chỉ cần nhấp đúp chuột vào file `start.bat` tại thư mục gốc, hoặc mở PowerShell:
```cmd
start.bat
:: Hoặc chạy trực tiếp với cờ độc lập:
scripts\windows\01_start_all.bat --standalone
```
*Luồng xử lý tự động:*
1. Thiết lập bảng mã console UTF-8 chuẩn (`chcp 65001`).
2. Tự động kiểm tra file `.env`; nếu thiếu sẽ khởi tạo từ `.env.production.example`.
3. Khi phát hiện cờ `--standalone` (hoặc môi trường native không bật Docker Desktop), script tự động kiểm tra kết nối dịch vụ MySQL cục bộ và Redis.
4. Kích hoạt engine kiểm toán `reconcile_migration.py --audit` để bảo đảm sổ cái toàn vẹn trước khi cho phép lưu lượng truy cập.
5. In danh mục đường dẫn truy cập hệ thống.

#### Dừng Hệ thống An toàn (Graceful Worker Draining):
Nhấp đúp chuột vào file `stop.bat` tại thư mục gốc, hoặc chạy:
```cmd
stop.bat
:: Hoặc:
scripts\windows\02_stop_all.bat --standalone
```
> [!IMPORTANT]
> **Quy tắc An toàn Draining 5 Giây:**  
> Khác với lệnh ngắt tiến trình đột ngột (`kill` / `taskkill /F`), script `02_stop_all.bat` dành ra thời gian ân hạn **5 giây (Worker Grace Period)**. Khoảng thời gian này giúp AI Worker hoàn tất các biên lai đang bóc tách dở dang, giải phóng khóa hàng đợi `FOR UPDATE SKIP LOCKED`, ghi nhận trạng thái `offline` vào bảng `worker_status`, và thực hiện đối soát số dư cuối cùng trước khi đóng dịch vụ.

#### Kiểm tra Sức khỏe Hệ thống (Health Diagnostics):
Mở terminal và chạy:
```cmd
scripts\windows\07_health_check.bat
```
Script sẽ kiểm tra trạng thái cụm MySQL, thực hiện bắt tay TCP cổng `6379` với Redis/Memurai, và gửi truy vấn kiểm tra toàn diện tới endpoint `/api/v1/health/deep`.

---

### 4.3 Chế độ 2: Vận hành Thủ công từng Terminal (Manual Debug Mode)
Chế độ này được khuyến nghị khi phát triển tính năng, kiểm thử trực tiếp trên Kilo Code hoặc gỡ lỗi từng thành phần. Mở 3 cửa sổ PowerShell độc lập:

#### Cửa sổ 1: FastAPI Core API Backend
```powershell
cd C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB\class-fund-backend-v0.1\class-fund-backend
..\..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Địa chỉ API:** `http://127.0.0.1:8000`
- **Swagger UI Tài liệu API:** `http://127.0.0.1:8000/docs`
- **Kiểm tra Sức khỏe Hệ thống:** `http://127.0.0.1:8000/api/v1/health/deep`

#### Cửa sổ 2: Background AI Vision Worker
```powershell
cd C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB\class-fund-backend-v0.1\class-fund-backend
..\..\.venv\Scripts\Activate.ps1
python worker\main.py
```
- Worker sẽ:
  1. Tự động thu hồi các tin nhắn bị kẹt lease từ phiên trước (`reclaim_stale_leases()`).
  2. Nạp cơ sở dữ liệu pHash và SHA-256 vào bộ nhớ để chống nộp biên lai trùng.
  3. Lắng nghe và khóa tin nhắn `pending` bằng cơ chế `FOR UPDATE SKIP LOCKED`.
  4. Gửi ảnh biên lai sang Ollama `qwen2.5vl:3b` để trích xuất thông tin.
  5. Gọi cổng `verify_and_post_from_ai()` để ghi sổ cái và phát thông báo qua Redis Pub/Sub.

#### Cửa sổ 3: Vite React Frontend
```powershell
cd C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB\classfund\classfund
npm run dev
```
- **Địa chỉ Ứng dụng Web:** `http://localhost:3000` (hoặc `http://localhost:5173`)

---

## 5. HƯỚNG DẪN SỬ DỤNG TÍNH NĂNG NGƯỜI DÙNG

### 5.1 Hành trình Người nộp Quỹ (Guest Chat Experience)

```mermaid
sequenceDiagram
    actor Guest as Người Nộp Quỹ (Khách)
    participant UI as Giao Diện Web (React)
    participant API as FastAPI Backend
    participant Worker as AI Worker & Ollama
    participant Ledger as Sổ Cái Bất Biến (MySQL)

    Guest->>UI: Nhập họ tên, lời nhắn & Đính kèm ảnh biên lai
    UI->>API: POST /api/v1/messages (Kèm File)
    API-->>UI: Trả về Public Code (CF-YYYYMMDD-XXXXXX) & Recall Token (64 hex)
    Note over UI: Lưu Recall Token vào sessionStorage trình duyệt
    API->>Ledger: Lưu tin nhắn (Status: pending) & Lưu ảnh (uploads)
    Worker->>Ledger: Quét job qua FOR UPDATE SKIP LOCKED
    Worker->>Worker: Gọi Ollama qwen2.5vl:3b bóc tách dữ liệu
    alt AI Tin cậy >= 90% & Không trùng lặp
        Worker->>Ledger: verify_and_post_from_ai() -> Tạo Transaction & LedgerEntry
        Worker-->>UI: Cập nhật trạng thái "Đã ghi sổ" (VERIFIED)
    else AI Nghi ngờ / Dưới 90% / Sai thông tin
        Worker->>Ledger: Cập nhật Status: NEEDS_REVIEW
        Worker-->>UI: Cập nhật trạng thái "Chờ thủ quỹ duyệt"
    end

    opt Người nộp muốn Thu hồi (Nút Thu hồi)
        Guest->>UI: Bấm nút "Thu hồi"
        UI->>API: POST /api/v1/messages/recall (Gửi kèm Recall Token)
        alt Nếu chưa ghi sổ (Pending / Processing)
            API->>Ledger: Đổi trạng thái sang RECALLED, hủy tác vụ worker
        else Nếu đã ghi sổ (Verified)
            API->>Ledger: Tạo bút toán REVERT bù trừ số tiền, ghi log kiểm toán
        end
        API-->>UI: Xác nhận thu hồi thành công
    end
```

1. **Gửi Biên lai Đóng quỹ:**
   - Người nộp quỹ mở ứng dụng web, không cần đăng nhập tài khoản.
   - Nhập **Họ và tên** (ví dụ: `Nguyễn Văn An`) và **Nội dung chuyển khoản**.
   - Bấm biểu tượng kẹp tệp để tải lên ảnh chụp màn hình chuyển khoản ngân hàng (hỗ trợ định dạng `.png`, `.jpg`, `.jpeg`).
   - Bấm **Gửi tin nhắn**.
2. **Theo dõi Mã Giao dịch Công khai:**
   - Ngay khi gửi, hệ thống cấp một mã tra cứu duy nhất định dạng: `CF-YYYYMMDD-XXXXXX` (Ví dụ: `CF-20261010-3FA8B1`).
   - Giao diện hiển thị trạng thái xử lý theo thời gian thực: `Đang xử lý (Processing)` ➔ `Đã ghi sổ (Verified)` hoặc `Chờ thủ quỹ xem xét (Needs Review)`.
3. **Cơ chế Thu hồi Biên lai (Recall Action):**
   - Người dùng có thể nhấn nút **"Thu hồi"** ngay trên bong bóng tin nhắn của mình:
   - **Trường hợp 1 — Thu hồi khi chưa ghi sổ (`Pending` hoặc `Processing`):** Tin nhắn được chuyển ngay sang trạng thái `RECALLED`. Tác vụ AI bị hủy lập tức, không có bất kỳ dòng tiền nào ghi vào sổ quỹ.
   - **Trường hợp 2 — Thu hồi sau khi đã ghi sổ (`Verified`):** Hệ thống sử dụng token bí mật kích hoạt hàm `post_revert()`. Một bút toán đảo ngược đối ứng (`REVERT`) được ghi vào bảng `ledger_entries`, số dư quỹ tự động giảm trừ tương ứng, trạng thái giao dịch cũ chuyển sang `REVERTED`. Mọi lịch sử đều được lưu vết trong `audit_logs`, và hệ thống tự động ngăn chặn hoàn toàn việc thu hồi 2 lần.

---

### 5.2 Hành trình Thủ quỹ & Ban Cán sự (Admin Dashboard & Review Queue)
1. **Đăng nhập Quản trị:**
   - Truy cập giao diện quản trị với email `admin@classfund.local` và mật khẩu tương ứng.
2. **Theo dõi Bảng Điều khiển (Dashboard):**
   - Xem tổng số dư quỹ lớp hiện tại theo thời gian thực (độ chính xác đến từng xu).
   - Biểu đồ biến động thu/chi, danh sách các đợt thu quỹ (`collection_campaigns`) và tỷ lệ hoàn thành nộp quỹ của các thành viên.
3. **Hàng đợi Phê duyệt Thủ công (Human Review Queue — `/internal/review`):**
   - Khi AI phát hiện:
     - Độ tin cậy nhận diện dưới 90% (`confidence < 0.90`).
     - Tên người chuyển khoản không khớp danh bạ học sinh.
     - Số tiền chuyển khác biệt so với số tiền yêu cầu của chiến dịch.
     - Ảnh có dấu hiệu tương đồng pHash với biên lai cũ.
   - Giao diện Review Queue sẽ hiển thị chi tiết: Ảnh gốc biên lai, bảng so sánh từng trường dữ liệu bóc tách kèm độ tin cậy (`field_confidences`).
   - Thủ quỹ có thể đối chiếu, sửa lại số tiền hoặc mã giao dịch chuẩn xác, sau đó bấm **"Phê duyệt (Approve)"** hoặc **"Từ chối (Reject)"**.
4. **Kiểm toán Đối soát Số dư Nhanh:**
   - Bất kỳ lúc nào cần lập báo cáo quyết toán tài chính, thủ quỹ mở terminal chạy:
     ```cmd
     scripts\windows\08_reconcile_balance.bat
     ```
   - Màn hình sẽ hiển thị xác nhận đối soát: Khớp 100% số lượng tài khoản, khớp 100% dòng sổ cái, và sai lệch số dư cam kết là **0.00 VND**.

---

## 6. QUY TRÌNH CHUYỂN ĐỔI MÁY A SANG MÁY B (CROSS-MACHINE MIGRATION)

Quy trình chuyển giao toàn bộ dữ liệu dự án từ máy đang vận hành (**Máy A**) sang một máy tính mới (**Máy B**) hoàn toàn bằng Native Windows, không dùng Docker:

```mermaid
flowchart LR
    subgraph MachineA ["MÁY A (Nguồn - Đóng gói)"]
        direction TB
        A1["Chạy export_to_machine_b.bat"] --> A2["Rút cạn Worker & Đóng băng Sổ cái"]
        A2 --> A3["Chụp Baseline tài chính<br/>(migration_baseline.json)"]
        A3 --> A4["Xuất MySQL Dump chuẩn<br/>(--single-transaction --hex-blob)"]
        A4 --> A5["Đóng gói uploads/, .env, dump & baseline<br/>➔ classfund_transfer_package.zip"]
    end

    subgraph TransferChannel ["VẬN CHUYỂN VẬT LÝ / MẠNG"]
        T["Sao chép classfund_transfer_package.zip<br/>(Qua USB / Mạng LAN / Google Drive)"]
    end

    subgraph MachineB ["MÁY B (Đích - Tiếp nhận & Khởi tạo)"]
        direction TB
        B1["Đặt classfund_transfer_package.zip vào thư mục gốc"] --> B2["Chạy import_from_machine_a.bat"]
        B2 --> B3["Tự động giải nén & Phục hồi uploads/, .env"]
        B3 --> B4["Nạp SQL Dump vào MySQL cục bộ"]
        B4 --> B5{"Đối soát Tài chính Nghiêm ngặt<br/>Sai số == 0.00 VND?"}
        B5 -- "ĐÚNG (0.00 VND)" --> B6["Khởi động Hệ thống Máy B Sẵn sàng!"]
        B5 -- "SAI (Có Drift)" --> B7["BÁO ĐỘNG ĐỎ & HỦY KHỞI ĐỘNG"]
    end

    MachineA --> TransferChannel --> MachineB
```

---

### 6.1 Các bước Thực hiện tại Máy A (Đóng gói Dữ liệu)
1. Mở thư mục dự án `CLASS_FUND_WEB` trên Máy A.
2. Nhấp đúp chuột vào file `export_to_machine_b.bat` (hoặc mở Command Prompt chạy `scripts\windows\05_export_machine_a.bat`).
3. Script sẽ tự động thực hiện tuần tự:
   - **Bước 1/6:** Dừng tiến trình ghi sổ và rút cạn worker 5 giây để đóng băng dữ liệu.
   - **Bước 2/6:** Chạy `python scripts/reconcile_migration.py --create-baseline` để ghi nhận tệp kiểm toán chuẩn `migration_baseline.json`.
   - **Bước 3/6:** Chạy `mysqldump` với các tham số giao dịch an toàn cao:
     ```cmd
     mysqldump -h 127.0.0.1 -P 3306 -u root -p000000 --single-transaction --quick --set-gtid-purged=ON --hex-blob --routines --triggers classfund > migration_dump.sql
     ```
   - **Bước 4/6:** Thu thập tệp cấu hình `.env`, toàn bộ ảnh biên lai trong `uploads/` (hoặc `storage/uploads/`), file `migration_dump.sql` và `migration_baseline.json`.
   - **Bước 5/6:** Nén nguyên khối thành file **`classfund_transfer_package.zip`**.
   - **Bước 6/6:** Dọn dẹp thư mục trung gian.
4. Khi màn hình thông báo `[SUCCESS] MACHINE A EXPORT COMPLETED SUCCESSFULLY`, sao chép file `classfund_transfer_package.zip` sang thiết bị lưu trữ (USB, ổ cứng di động, mạng LAN).

---

### 6.2 Các bước Thực hiện tại Máy B (Tiếp nhận & Vận hành)
1. Cài đặt đầy đủ 5 phần mềm bắt buộc trên Máy B theo [Phần 2](#2-yêu-cầu-môi-trường--cài-đặt-phần-mềm-native-setup) (Python, Node.js, MySQL Server, Memurai/Redis, Ollama).
2. Tạo cơ sở dữ liệu `classfund` trên MySQL Máy B theo [Mục 3.1](#31-khởi-tạo-cơ-sở-dữ-liệu--người-dùng-trên-mysql).
3. Đặt file **`classfund_transfer_package.zip`** vào thư mục gốc của dự án trên Máy B (`C:\Users\...\CLASS_FUND_WEB\`).
4. Nhấp đúp chuột vào file `import_from_machine_a.bat` (hoặc chạy `scripts\windows\06_import_machine_b.bat`).
5. Script sẽ tự động thực hiện tuần tự:
   - **Bước 1-3:** Giải nén gói chuyển đổi, khôi phục tệp cấu hình `.env` và thư mục ảnh biên lai `uploads/`.
   - **Bước 4-5:** Kiểm tra kết nối dịch vụ MySQL 3306 trên Máy B.
   - **Bước 6:** Nạp dữ liệu từ `migration_dump.sql` vào cơ sở dữ liệu `classfund`. Công cụ `restore_helper.py` tự động loại bỏ các câu lệnh GTID purged xung đột để đảm bảo việc nạp diễn ra thông suốt.
   - **Bước 7 (Cực kỳ Quan trọng):** Thực thi đối soát tài chính đối chiếu với `migration_baseline.json`:
     - So khớp 100% số lượng tài khoản quỹ (`accounts_count`).
     - So khớp 100% số lượng bút toán sổ cái (`ledger_count`).
     - So khớp tổng số dư tiền quỹ: **Sai lệch bắt buộc phải bằng chính xác 0.00 VND**.
     - *Nếu phát hiện sai số tài chính bất kỳ, script sẽ lập tức báo động đỏ và chặn toàn bộ việc khởi động.*
   - **Bước 8:** Khi kiểm toán thành công đạt `0.00 VND Discrepancy`, script xác nhận hoàn tất.
6. Máy B đã sẵn sàng! Người dùng chạy `start.bat` để bắt đầu phục vụ người dùng trên máy mới.

---

## 7. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING & DIAGNOSTIC MATRIX)

| Mã Lỗi / Hiện Tượng | Nguyên Nhân Cốt Lõi | Các Bước Khắc Phục Chuẩn Hóa |
| :--- | :--- | :--- |
| **MySQL Port 3306 Connection Refused**<br>`Can't connect to MySQL server on '127.0.0.1:3306'` | Dịch vụ Windows MySQL Service (`MySQL84` hoặc `MySQL`) chưa được khởi chạy. | 1. Mở PowerShell với quyền Administrator.<br>2. Chạy: `net start MySQL84` (hoặc `net start MySQL`).<br>3. Kiểm tra cổng: `Test-NetConnection -Port 3306 127.0.0.1`. |
| **Redis / Memurai Connection Refused**<br>`Error 10061 connecting to 127.0.0.1:6379` | Dịch vụ Memurai hoặc Redis cho Windows chưa được bật. | 1. Mở PowerShell: `net start Memurai`.<br>2. Nếu chạy bản portable: Chạy file `memurai.exe` hoặc `redis-server.exe`.<br>3. Kiểm tra cổng 6379 phản hồi `TCP handshake success`. |
| **Ollama Model Not Found**<br>`model 'qwen2.5vl:3b' not found` | Chưa tải mô hình thị giác máy tính vào máy chủ Ollama Windows. | 1. Kiểm tra Ollama đang chạy ở khay hệ thống.<br>2. Mở Command Prompt chạy: `ollama pull qwen2.5vl:3b`.<br>3. Tải thêm model text: `ollama pull qwen3.5:4b`.<br>4. Kiểm tra lại bằng lệnh: `ollama list`. |
| **Lỗi Kẹt Worker Lease (`SKIP LOCKED`)**<br>Tin nhắn ở trạng thái `processing` mãi không kết thúc. | Worker bị tắt đột ngột khi đang xử lý tin nhắn, khiến khóa hạn giờ chưa hết hạn. | 1. Khởi động lại Worker bằng `python worker\main.py`. Worker có cơ chế `reclaim_stale_leases()` tự động giải phóng tin nhắn quá 300s.<br>2. Hoặc mở MySQL chạy query giải phóng cưỡng bức:<br>`UPDATE messages SET status='pending', worker_id=NULL, claimed_at=NULL, lease_expires_at=NULL WHERE status='processing';` |
| **Lỗi Hiển thị Tiếng Việt trên CMD / PowerShell**<br>Ký tự tiếng Việt bị lỗi font (mojibake). | Bảng mã mặc định của Windows Console là CP437 hoặc CP1252. | 1. Chạy lệnh đổi bảng mã sang UTF-8 trước khi thực thi:<br>`chcp 65001`<br>2. Toàn bộ các script `.bat` trong `scripts\windows\` đã được cấu hình sẵn dòng `chcp 65001 > nul`. |
| **Lỗi MySQL Restore GTID (Error 3546)**<br>`@@GLOBAL.GTID_PURGED cannot be changed` | Tệp SQL dump chứa lệnh gán lại GTID khi restore vào một máy chủ đang có GTID. | Không sử dụng lệnh `mysql < dump.sql` thủ công trực tiếp. Luôn sử dụng `04_db_restore.bat` hoặc `06_import_machine_b.bat`; script đã tích hợp `restore_helper.py` tự động vô hiệu hóa dòng này an toàn. |
| **Lỗi CORS khi gọi API từ Frontend**<br>`Access-Control-Allow-Origin missing` | Cổng của Vite Frontend (`3000` hoặc `5173`) chưa được khai báo trong biến `CORS_ORIGINS`. | Mở tệp `.env` tại thư mục backend, cập nhật cấu hình:<br>`CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000`<br>Khởi động lại tiến trình backend. |

---

## 8. BẢN QUYỀN & CHỨNG NHẬN KIỂM TOÁN TÀI CHÍNH

- **Tổ chức Phát triển:** Đội ngũ Kỹ thuật Hệ thống Quỹ Lớp (Class Fund Engineering Team).
- **Chứng nhận Kiểm toán Phase 11:** 100% các ca kiểm thử sao lưu, phục hồi và chuyển dịch máy tính (Machine A ➔ Machine B) đạt mức sai số **0.00 VND (Zero Financial Drift)**.
- **Tiêu chuẩn Tài liệu:** Tuân thủ chuẩn vận hành hệ thống Native Windows theo hồ sơ kỹ thuật `artifacts/phase_11_windows_automation/phase_11_results.json`.

