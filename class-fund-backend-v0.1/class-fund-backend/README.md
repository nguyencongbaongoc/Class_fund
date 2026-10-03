# CLASS FUND WEB — Backend / Financial Core

Backend starter bám theo `CLASS_FUND_MINH_BACKEND.md` và `CLASS_FUND_WEB_PHASE_PLAN.md`.

## Kiến trúc

- **FastAPI**: REST API + OpenAPI/Swagger.
- **PostgreSQL**: dữ liệu production.
- **SQLAlchemy 2**: ORM/database access.
- **Alembic**: migration.
- **JWT + Argon2**: authentication.
- **Ledger bất biến**: balance chỉ được tính từ opening balance + ledger entries.
- **AI callback**: AI chỉ trả candidate/result; backend validate rồi mới post.
- **Idempotency + unique constraint + DB transaction**: chống post trùng/race condition.

## Chạy local

```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_admin.py
uvicorn app.main:app --reload
```

Swagger: `http://localhost:8000/docs`

## Default local admin

Script seed dùng biến môi trường:

```text
SEED_ADMIN_EMAIL=admin@classfund.local
SEED_ADMIN_PASSWORD=change-this
SEED_ADMIN_NAME=Class Fund Owner
```

## Frontend integration

Frontend không tự tính số dư. Gọi:

- `GET /api/v1/public/fund`
- `GET /api/v1/fund/balance`
- `GET /api/v1/fund/transactions`
- `POST /api/v1/uploads`
- `GET /api/v1/uploads/{upload_id}`
- `GET /api/v1/campaigns`
- `GET /api/v1/chat/messages`

Response upload luôn có `status`, `upload_id` để frontend hiển thị processing/review/duplicate/verified.

## AI integration

AI service nhận ảnh từ storage/URL ngoài, xử lý OCR/extraction, sau đó gọi:

`POST /api/v1/internal/ai/uploads/{upload_id}/result`

Header:

```text
X-AI-Service-Key: <AI_SERVICE_KEY>
```

Payload mẫu nằm ở `docs/api-contract.md`.

**Không gửi `new_balance` từ frontend/AI.** AI không được tạo ledger trực tiếp.

## Các giới hạn có chủ ý

Đây là backend foundation có thể mở rộng. Virus scanning thật, object storage S3, background queue (Celery/RQ), email/OTP, WebSocket realtime và monitoring production chưa được bật sẵn; nhưng API boundary và trạng thái xử lý đã được thiết kế để cắm vào sau mà không đổi financial core.
