# PHASE 0 — BACKEND FORENSIC INVENTORY

## Repository: `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB\class-fund-backend-v0.1\class-fund-backend`

### Git Status
- Not a git repository (no `.git` directory found)
- No commit history available for inspection
- All files appear to be initial implementation

### Directory Structure
```
class-fund-backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── ai_internal.py
│   │   │   ├── auth.py
│   │   │   ├── campaigns.py
│   │   │   ├── chat.py
│   │   │   ├── fund.py
│   │   │   ├── health.py
│   │   │   ├── public.py
│   │   │   └── uploads.py
│   │   ├── deps.py
│   │   └── __init__.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── __init__.py
│   ├── db/
│   │   ├── base.py
│   │   ├── init_db.py
│   │   ├── session.py
│   │   └── __init__.py
│   ├── models/
│   │   ├── models.py
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── schemas.py
│   │   └── __init__.py
│   ├── services/
│   │   ├── activity.py
│   │   ├── audit.py
│   │   ├── ledger.py
│   │   └── __init__.py
│   └── main.py
├── docs/
├── scripts/
├── storage/
├── tests/
│   └── test_financial_core.py
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── openapi.json
├── pyproject.toml
└── README.md
```

### Entry Points
- **Main Application**: `app/main.py:24` — FastAPI app with lifespan, CORS, router mounting at `/api/v1`
- **Database Init**: `app/db/init_db.py` (referenced in lifespan, not read)
- **Alembic**: `alembic/env.py` — migration environment

### Runtime Versions
- Python: `>=3.11` (from pyproject.toml)
- FastAPI: `>=0.116,<1.0`
- SQLAlchemy: `>=2.0,<3.0`
- PostgreSQL driver: `psycopg[binary]>=3.2,<4.0`
- Alembic: `>=1.16,<2.0`
- Pydantic Settings: `>=2.10,<3.0`
- PyJWT: `>=2.10,<3.0`
- argon2-cffi: `>=25.1,<26.0`

### Dependency Manifest (pyproject.toml)
```toml
dependencies = [
  "fastapi>=0.116,<1.0",
  "uvicorn[standard]>=0.35,<1.0",
  "sqlalchemy>=2.0,<3.0",
  "psycopg[binary]>=3.2,<4.0",
  "alembic>=1.16,<2.0",
  "pydantic-settings>=2.10,<3.0",
  "PyJWT>=2.10,<3.0",
  "argon2-cffi>=25.1,<26.0",
  "python-multipart>=0.0.20,<1.0",
  "email-validator>=2.2,3.0",
]
dev = [
  "httpx>=0.28,<1.0",
  "pytest>=8.4,<9.0",
  "pytest-asyncio>=1.1,<2.0",
]
```

### Environment Variables (.env.example)
| Variable | Default | Description |
|----------|---------|-------------|
| APP_NAME | "Class Fund API" | Application name |
| ENVIRONMENT | "development" | Runtime environment |
| DATABASE_URL | "postgresql+psycopg://classfund:classfund@localhost:5432/classfund" | PostgreSQL connection |
| JWT_SECRET | "change-me-in-production" | **REDACTED** - JWT signing secret |
| JWT_ALGORITHM | "HS256" | JWT algorithm |
| ACCESS_TOKEN_MINUTES | 60 | Token expiry |
| UPLOAD_DIR | "./storage/uploads" | File upload directory |
| MAX_UPLOAD_MB | 10 | Max upload size |
| AI_SERVICE_KEY | "change-me-ai-service-key" | **REDACTED** - Internal AI service auth |
| CORS_ORIGINS | "http://localhost:5173,http://localhost:3000" | CORS allowed origins |
| AI_CONFIDENCE_THRESHOLD | 0.90 | Minimum confidence for auto-post |

### Database Technology & Schema
- **Database**: PostgreSQL (configured via DATABASE_URL)
- **ORM**: SQLAlchemy 2.x with declarative base
- **Migrations**: Alembic with single initial migration (`0001_initial.py`)
- **Tables** (from `app/models/models.py`):
  1. `revoked_tokens` — JWT token revocation
  2. `users` — Authentication & RBAC
  3. `accounts` — Fund accounts with opening_balance
  4. `bank_accounts` — Bank account details for QR/VietQR
  5. `uploads` — Receipt uploads with file_hash, perceptual_hash, status
  6. `students` — Student roster with aliases
  7. `collection_campaigns` — Fundraising campaigns
  8. `campaign_members` — Campaign-Student many-to-many with payment status
  9. `extracted_transactions` — AI extraction results linked to uploads
  10. `transactions` — Core financial transactions (immutable once posted)
  11. `ledger_entries` — Immutable ledger entries (1:1 with transactions, supports reversal linkage)
  12. `idempotency_keys` — Request deduplication
  13. `audit_logs` — Comprehensive audit trail
  14. `payment_matches` — Links transactions to campaign students
  15. `chat_messages` — Activity feed

### API Routes & Request/Response Schemas

#### `/api/v1/health` (health.py)
- `GET /` — Health check

#### `/api/v1/auth` (auth.py)
- `POST /login` — `LoginRequest` → `TokenResponse` (access_token, token_type)
- `POST /logout` — Revokes current token
- `GET /me` — Returns `UserOut` (current user)

#### `/api/v1/fund` (fund.py)
- `GET /balance` — Returns `AccountOut` (id, name, currency, opening_balance, balance)
- `GET /transactions` — Query params: account_id, limit, offset → `list[TransactionOut]`
- `PUT /accounts/{account_id}/opening-balance` — `OpeningBalanceIn` → `AccountOut` (OWNER_TREASURER)
- `POST /bank-accounts` — `BankAccountIn` → BankAccount (OWNER_TREASURER)
- `GET /bank-accounts` — `list[BankAccount]`
- `POST /credit` — `ManualTransactionIn` + `Idempotency-Key` header → `TransactionOut` (OWNER_TREASURER)
- `POST /debit` — `ManualTransactionIn` + `Idempotency-Key` header → `TransactionOut` (OWNER_TREASURER)
- `POST /transactions/{transaction_id}/revert` — `RevertIn` + `Idempotency-Key` header → `TransactionOut` (OWNER_TREASURER)

#### `/api/v1/uploads` (uploads.py)
- `POST /` — multipart/form-data (file, uploader_name) → `UploadOut`
- `GET /{upload_id}` → `UploadStatusOut` (includes extracted data, transaction_id, rejection_reason)

#### `/api/v1/internal/ai` (ai_internal.py) — **Protected by `AI_SERVICE_KEY` header**
- `GET /uploads/{upload_id}/file` — Returns receipt image file
- `POST /uploads/{upload_id}/result` — `AIResultIn` + `Idempotency-Key` header → `{upload_id, status, transaction_id, posted}`

#### `/api/v1/campaigns` (campaigns.py)
- `POST /students` — `StudentIn` → `StudentOut` (OWNER_TREASURER, MODERATOR)
- `POST /students/import` — `StudentImportIn` → `{created_count, students[]}` (OWNER_TREASURER, MODERATOR)
- `POST /` — `CampaignIn` → `CampaignOut` (OWNER_TREASURER, MODERATOR)
- `GET /` → `list[CampaignOut]`
- `PATCH /{campaign_id}` — `CampaignIn` → `CampaignOut` (OWNER_TREASURER, MODERATOR)
- `POST /{campaign_id}/students/{student_id}` — Add student to campaign (OWNER_TREASURER, MODERATOR)
- `DELETE /{campaign_id}/students/{student_id}` — Remove student (OWNER_TREASURER, MODERATOR)
- `GET /{campaign_id}/members` — Campaign members with student details

#### `/api/v1/public` (public.py) — **No auth required**
- `GET /fund` — Public fund summary (balance, total_income, total_expense)
- `GET /bank-accounts` — Active bank accounts for donations
- `GET /campaigns` — Public campaign list with progress

#### `/api/v1/chat` (chat.py)
- `GET /messages` — Paginated chat messages
- `POST /messages` — `ChatMessageIn` → `ChatMessageOut`

### Authentication & Authorization
- **Auth**: JWT Bearer tokens (HS256), 60-min expiry, argon2 password hashing
- **Token Revocation**: `revoked_tokens` table with JTI tracking
- **Roles** (enum `Role`): `OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC`
- **Dependencies**:
  - `get_current_user` — validates token, checks revocation, returns User
  - `require_roles(*roles)` — enforces role membership
  - `require_ai_service` — validates `X-AI-Service-Key` header against `AI_SERVICE_KEY`

### Background Workers & Queue Systems
- **No background worker implementation in backend**
- AI processing expected to be external service calling `/internal/ai` endpoint
- Celery/Redis configuration exists in `ai/worker/queue.py` but not integrated with backend

### File Upload & Storage
- **Endpoint**: `POST /api/v1/uploads` (multipart/form-data)
- **Allowed MIME**: `image/jpeg`, `image/png`, `image/webp`
- **Max Size**: `MAX_UPLOAD_MB` (default 10MB)
- **Storage**: Local filesystem at `UPLOAD_DIR` (default `./storage/uploads`)
- **Naming**: UUID + extension
- **Deduplication**: SHA-256 file hash check on upload (returns existing if duplicate)

### Error Handling & Logging
- **HTTP Exceptions**: Standard FastAPI `HTTPException` with status codes
- **Audit Logging**: `write_audit()` called on all mutations (ledger, users, campaigns, etc.)
- **Activity Feed**: `emit_activity()` creates `ChatMessage` entries for UI
- **Idempotency**: `IdempotencyKey` table with request fingerprint (SHA-256 of key params)
- **Database Errors**: `IntegrityError` caught and converted to 409 Conflict

### Existing Tests
- **File**: `tests/test_financial_core.py`
- **Tests** (4 total):
  1. `test_credit_debit_and_balance` — Verifies balance calculation from ledger
  2. `test_revert_restores_balance_without_deleting_original` — Verifies reversal preserves original + creates REVERT entry
  3. `test_ai_low_confidence_does_not_post` — Verifies confidence threshold enforcement
  4. `test_ai_retry_same_upload_does_not_double_post` — Verifies idempotency on AI retry
- **Test DB**: SQLite in-memory (not PostgreSQL)

### Missing, Duplicated, Obsolete, Conflicting Modules
- **Missing**: 
  - No database initialization script (`init_db.py` referenced but not found)
  - No AI worker integration (external service expected)
  - No webhook/callback for AI completion
  - No rate limiting
  - No API versioning strategy beyond `/v1`
- **Duplicated**: None found
- **Obsolete**: None found
- **Conflicting**: None found

### Key Implementation Details (Verified by Code Inspection)

#### Financial Integrity (`app/services/ledger.py`)
- **Balance Calculation** (`calculate_balance:19-36`): Sums `LedgerEntry` where `status=VERIFIED`, adds credits, subtracts debits, handles REVERT by checking note prefix
- **Idempotency** (`check_idempotency:43-51`, `save_idempotency:54-56`): SHA-256 fingerprint of request params, stores response body
- **Transaction Posting** (`post_transaction:59-118`): 
  - Validates amount > 0
  - AI credits require transaction_code + bank_account_id
  - Duplicate check: `UNIQUE(bank_account_id, transaction_code)` with `SELECT ... FOR UPDATE`
  - Creates `Transaction` + `LedgerEntry` atomically
  - Audit log + activity emission
- **Reversal** (`post_revert:121-169`):
  - Locks original transaction + ledger entry with `FOR UPDATE`
  - Prevents reverting REVERT transactions
  - Prevents double-revert (checks `original_entry_id`)
  - Creates REVERT transaction + ledger entry linking to original
  - Marks original status = `REVERTED`
- **AI Verification & Post** (`verify_and_post_from_ai:172-242`):
  - Checks confidence ≥ threshold (0.90 default)
  - Validates required fields (transaction_code, amount, bank_account_id)
  - Duplicate transaction_code check with `FOR UPDATE`
  - Campaign matching: amount must equal expected_amount, student must be UNPAID
  - Posts CREDIT with `source=IMAGE`, `note="AI_VERIFIED confidence=X"`
  - Updates campaign member status to PAID, creates `PaymentMatch`

#### AI Internal Endpoint (`app/api/routes/ai_internal.py:24-52`)
- Receives `AIResultIn` (matches AI `VerificationResult` fields)
- Idempotency key required
- Calls `verify_and_post_from_ai()` with `commit=False` then commits
- Returns `{posted: boolean, transaction_id}`

#### Database Constraints (Critical for Integrity)
- `transactions`: `UNIQUE(bank_account_id, transaction_code)` — prevents duplicate bank transactions
- `ledger_entries`: `UNIQUE(transaction_id)` — 1:1 with transactions
- `extracted_transactions`: `UNIQUE(upload_id)` — 1:1 with uploads
- `campaign_members`: `UNIQUE(campaign_id, student_id)` — one entry per student per campaign
- `idempotency_keys`: `UNIQUE(key)` — deduplication

### Confidence Assessment
- **High Confidence**: All code read directly, logic verified against financial integrity requirements
- **Medium Confidence**: Database initialization script not found, Alembic migration not executed
- **Low Confidence**: Production deployment configuration (docker-compose, env vars) not tested