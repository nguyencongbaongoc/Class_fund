# Phase 6 Preflight Report

## 1. Git Repository State

**Branch:** `master`  
**HEAD:** Latest commit on master branch  
**Working Tree Status:** Uncommitted changes present (see below)

### Uncommitted Changes (Preserved)

```
modified:   ai/duplicate/__pycache__/service.cpython-312.pyc
modified:   ai/duplicate/service.py
modified:   class-fund-backend-v0.1/class-fund-backend/.env.example
modified:   class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py
modified:   class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py
modified:   class-fund-backend-v0.1/class-fund-backend/app/core/config.py
modified:   class-fund-backend-v0.1/class-fund-backend/app/main.py
modified:   class-fund-backend-v0.1/class-fund-backend/app/models/models.py
modified:   class-fund-backend-v0.1/class-fund-backend/app/schemas/__init__.py
modified:   class-fund-backend-v0.1/class-fund-backend/app/schemas/schemas.py
modified:   class-fund-backend-v0.1/class-fund-backend/app/services/ollama_client.py
modified:   class-fund-backend-v0.1/class-fund-backend/worker/main.py
modified:   classfund/classfund/.env.example
modified:   classfund/classfund/src/App.tsx
modified:   classfund/classfund/src/components/chat/MessageItem.tsx
modified:   classfund/classfund/src/components/chat/RecallButton.tsx
modified:   classfund/classfund/src/components/common/Navbar.tsx
modified:   classfund/classfund/src/context/AppContext.tsx
modified:   classfund/classfund/src/hooks/useChat.ts
modified:   classfund/classfund/src/lib/recall.ts
modified:   classfund/classfund/src/types/chat.ts
modified:   classfund/classfund/src/types/index.ts
```

### Untracked Files (Noted)
- `artifacts/demo_live_qualification/`
- `artifacts/demo_qualification_remediation/`
- `artifacts/demo_qualification_requalification_v2/`
- `artifacts/master_consolidation/`
- `artifacts/phase_2_merge_resolution/`
- `artifacts/phase_3_1_4_1/`
- `artifacts/phase_3_1_4_1_closure/`
- `artifacts/phase_5_1_closure/`
- `artifacts/phase_5_2_remediation/`
- `artifacts/phase_5_admin_dashboard/`
- `artifacts/residual_blocker_closure/`
- `class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py`
- `class-fund-backend-v0.1/class-fund-backend/app/api/routes/admin.py`
- `class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py`
- `class-fund-backend-v0.1/class-fund-backend/app/schemas/admin.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/__init__.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/conftest.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/`
- `class-fund-backend-v0.1/class-fund-backend/tests/test_admin.py`
- `classfund/classfund/src/components/chat/ExtractionResultDisplay.tsx`
- `classfund/classfund/src/hooks/useRecall.ts`
- `classfund/classfund/src/lib/adminApi.ts`
- `classfund/classfund/src/lib/retry.ts`
- `classfund/classfund/src/views/AIReviewQueueView.tsx`
- `classfund/classfund/src/views/AdminDashboardView.tsx`
- `classfund/classfund/src/views/AdminLedgerView.tsx`
- `classfund/classfund/src/views/AuditLogView.tsx`
- `classfund/classfund/src/views/SystemMonitoringView.tsx`
- `pgdata_phase6/`
- `pgpassword.txt`
- `postgresql-18.6-5-windows-x64-binaries/`

## 2. Repository Structure

### Backend Root
```
class-fund-backend-v0.1/class-fund-backend/
├── alembic/           # Database migrations (5 versions)
├── app/
│   ├── api/routes/    # 12 route modules
│   ├── core/          # Config, security
│   ├── db/            # Session, base, init_db
│   ├── models/        # SQLAlchemy models (models.py)
│   ├── schemas/       # Pydantic schemas
│   └── services/      # ledger.py, supabase_client.py, ollama_client.py, etc.
├── tests/             # Unit and simulation tests
├── worker/            # Background worker
├── storage/           # Local file storage
├── docker-compose.yml # PostgreSQL only
├── alembic.ini        # PostgreSQL connection
└── pyproject.toml
```

### Frontend Root
```
classfund/classfund/
├── src/
│   ├── components/
│   ├── context/
│   ├── hooks/
│   ├── lib/           # api.ts, realtime.ts, polling.ts, adminApi.ts, etc.
│   ├── pages/
│   ├── types/
│   ├── views/
│   ├── App.tsx
│   └── main.tsx
├── package.json       # @supabase/supabase-js dependency
└── vite.config.ts
```

## 3. Database Configuration (Current)

### `app/core/config.py`
```python
database_url: str = "postgresql+psycopg://classfund:classfund@localhost:5432/classfund"
```

### `alembic.ini`
```ini
sqlalchemy.url = postgresql+psycopg://classfund:classfund@localhost:5432/classfund
```

### `docker-compose.yml`
- PostgreSQL 17-alpine
- Port 5432 exposed
- Volume: `classfund_pgdata`

## 4. Supabase Dependencies Identified

### Backend
1. **`app/services/supabase_client.py`** - Full Supabase client wrapper
   - Storage operations (upload/download/delete receipts)
   - Realtime subscriptions (messages, worker_status)
   - Auth operations (JWT verification, user lookup)
   - RLS policy helpers

2. **`app/api/routes/vision.py`** - Uses Supabase for image retrieval
3. **`app/api/routes/admin.py`** - Health check includes Supabase storage
4. **`worker/main.py`** - Supabase-backed persistent worker
5. **`app/core/config.py`** - Supabase URL, service key, anon key, JWT secret settings

### Frontend
1. **`src/lib/realtime.ts`** - RealtimeAdapter using `@supabase/supabase-js`
2. **`src/hooks/useChat.ts`** - Uses Supabase URL/keys
3. **`src/lib/polling.ts`** - Supabase config for fallback
4. **`package.json`** - `@supabase/supabase-js: ^2.39.0` dependency

### Environment Variables
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

## 5. PostgreSQL-Specific Features in Use

### Alembic Migrations (PostgreSQL-specific)
1. **0002_add_messages_and_message_id.py**
   - `postgresql.JSONB` for worker_status.metadata
   - `postgresql_where` partial indexes on messages table

2. **0003_add_recall_tokens.py** - Standard SQL

3. **0004_add_worker_id_to_messages.py** - Standard SQL

4. **0005_add_attachment_ids_and_ai_fields.py** - Standard SQL (uses sa.JSON)

### SQLAlchemy Models (PostgreSQL-specific)
- `Enum(..., native_enum=False)` - Uses native PostgreSQL enums
- `JSON` type columns (uses PostgreSQL JSONB)
- Partial indexes with `postgresql_where`

### Raw SQL / Database Functions
- None found in migrations (all SQLAlchemy ORM)
- Supabase RPC calls for RLS: `enable_rls`, `create_policy`

## 6. ORM Models Inventory (14 Tables)

| Table | Primary Key | Key Constraints | Financial |
|-------|-------------|-----------------|-----------|
| users | id (UUID) | email unique | No |
| accounts | id (UUID) | name unique | **YES** |
| bank_accounts | id (UUID) | - | **YES** |
| uploads | id (UUID) | file_hash index | **YES** |
| students | id (UUID) | - | No |
| collection_campaigns | id (UUID) | - | **YES** |
| campaign_members | id (UUID) | (campaign_id, student_id) unique | **YES** |
| extracted_transactions | id (UUID) | upload_id unique | **YES** |
| transactions | id (UUID) | (bank_account_id, transaction_code) unique | **YES** |
| ledger_entries | id (UUID) | transaction_id unique | **YES** |
| idempotency_keys | id (UUID) | key unique | **YES** |
| audit_logs | id (UUID) | - | **YES** |
| payment_matches | id (UUID) | transaction_id unique | **YES** |
| messages | id (UUID) | public_code unique, partial indexes | No |
| worker_status | worker_id (UUID) | - | No |
| recall_tokens | id (UUID) | message_id unique | **YES** |
| chat_messages | id (UUID) | - | No |

## 7. Financial Tables and Constraints

### Critical Financial Invariants (from ledger.py)

1. **Ledger Authority** - LedgerEntry is authoritative; posted records immutable
2. **AI Proposals Only** - AI creates proposals via `verify_and_post_from_ai()`; never posts directly
3. **Recall Behavior** - Before posting: prevents posting; After posting: creates REVERT entry
4. **Idempotency** - Fingerprint-based; same key + same payload = duplicate; different payload = VALIDATION error
5. **Concurrency** - `with_for_update()` row locking; IntegrityError recovery via message_id

### Decimal Precision
- All monetary amounts: `Numeric(18, 2)` (18 digits, 2 decimal places)
- Confidence: `Numeric(5, 4)`
- **NEVER use FLOAT/DOUBLE for money**

## 8. Authentication, Storage, Realtime

### Authentication
- JWT tokens (HS256) with role claims
- Roles: OWNER_TREASURER, MODERATOR, MEMBER, PUBLIC
- Supabase Auth currently used for JWT verification
- Local password hashing (bcrypt via `app.core.security`)

### Storage
- Local filesystem: `./storage/uploads/`
- Supabase Storage: receipts bucket (public URLs)
- File validation: JPEG, PNG, WebP; max 10MB

### Realtime
- Supabase Realtime: postgres_changes on messages, worker_status
- Frontend: RealtimeAdapter with reconnection logic
- Fallback: polling mechanism in `polling.ts`

## 9. Existing Tests Baseline

### Test Files
- `tests/test_financial_core.py` - 4 tests (balance, revert, AI low confidence, AI retry)
- `tests/test_idempotency.py` - 8 tests (various idempotency scenarios)
- `tests/test_recall.py` - Recall functionality
- `tests/test_admin.py` - Admin endpoints
- `tests/simulation/` - E2E simulation tests with mock Ollama/Supabase

### Test Database
- All tests use **SQLite in-memory** (`sqlite+pysqlite:///:memory:`)
- `conftest.py` sets `DATABASE_URL` to SQLite before imports
- **No MySQL tests exist**

## 10. Summary

| Aspect | Status |
|--------|--------|
| Git clean | No - uncommitted changes preserved |
| Backend root | `class-fund-backend-v0.1/class-fund-backend/` |
| Frontend root | `classfund/classfund/` |
| Database | PostgreSQL (Supabase-compatible) |
| ORM | SQLAlchemy 2.0 with DeclarativeBase |
| Migrations | Alembic (5 versions, PostgreSQL-specific) |
| Supabase deps | Backend: storage, realtime, auth, RLS; Frontend: realtime, auth |
| Financial invariants | Implemented in `ledger.py` with strict rules |
| Test baseline | SQLite-only, comprehensive financial tests |

**Ready to proceed with Phase 6 implementation.**