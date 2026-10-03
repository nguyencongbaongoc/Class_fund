# Handoff nhanh cho team 3 người

## Minh / Backend

Điểm bắt đầu:
- `app/models/models.py` — database schema
- `app/services/ledger.py` — financial core
- `app/api/routes/fund.py` — credit/debit/revert
- `app/api/routes/ai_internal.py` — AI boundary
- `app/api/routes/uploads.py` — receipt upload/status
- `app/api/deps.py` — auth/RBAC

Không sửa balance từ frontend/AI.

## Bạn AI

Chỉ cần 2 API backend:
- `GET /api/v1/internal/ai/uploads/{upload_id}/file`
- `POST /api/v1/internal/ai/uploads/{upload_id}/result`

Xem `docs/ai-integration.md`.

## Bạn Frontend

Ưu tiên:
- `GET /api/v1/public/fund`
- `POST /api/v1/uploads`
- `GET /api/v1/uploads/{upload_id}`
- `GET /api/v1/fund/transactions`
- `GET /api/v1/campaigns`
- `GET /api/v1/chat/messages`

Xem `docs/frontend-integration.md` và import `openapi.json`.

## Cách chạy

```bash
cp .env.example .env
docker compose up -d db
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed_admin.py
uvicorn app.main:app --reload
```
