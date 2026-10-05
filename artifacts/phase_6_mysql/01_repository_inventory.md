# Phase 6 Repository Inventory

## 1. Backend Structure

### Root: `class-fund-backend-v0.1/class-fund-backend/`

```
class-fund-backend-v0.1/class-fund-backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial.py
│       ├── 0002_add_messages_and_message_id.py
│       ├── 0003_add_recall_tokens.py
│       ├── 0004_add_worker_id_to_messages.py
│       └── 0005_add_attachment_ids_and_ai_fields.py
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── admin.py
│   │       ├── ai_internal.py
│   │       ├── auth.py
│   │       ├── campaigns.py
│   │       ├── chat.py
│   │       ├── fund.py
│   │       ├── health.py
│   │       ├── messages.py
│   │       ├── public.py
│   │       ├── review.py
│   │       ├── uploads.py
│   │       └── vision.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── init_db.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   └── admin.py
│   └── services/
│       ├── __init__.py
│       ├── activity.py
│       ├── audit.py
│       ├── ledger.py
│       ├── ollama_client.py
│       └── supabase_client.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_admin.py
│   ├── test_financial_core.py
│   ├── test_idempotency.py
│   ├── test_recall.py
│   └── simulation/
│       ├── __init__.py
│       ├── config.py
│       ├── mock_ollama.py
│       ├── mock_supabase.py
│       ├── test_e2e.py
│       ├── test_failure_injection.py
│       └── test_supabase_auth.py
├── worker/
│   └── main.py
├── storage/
│   └── uploads/
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── openapi.json
├── pyproject.toml
└── README.md
```

## 2. Frontend Structure

### Root: `classfund/classfund/`

```
classfund/classfund/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ExtractionResultDisplay.tsx
│   │   │   ├── MessageItem.tsx
│   │   │   └── RecallButton.tsx
│   │   └── common/
│   │       └── Navbar.tsx
│   ├── context/
│   │   └── AppContext.tsx
│   ├── data/
│   ├── hooks/
│   │   ├── useChat.ts
│   │   └── useRecall.ts
│   ├── lib/
│   │   ├── liquidglass/
│   │   ├── adminApi.ts
│   │   ├── api.ts
│   │   ├── polling.ts
│   │   ├── realtime.ts
│   │   ├── recall.ts
│   │   ├── retry.ts
│   │   └── upload.ts
│   ├── pages/
│   ├── types/
│   │   ├── chat.ts
│   │   └── index.ts
│   ├── utils/
│   ├── views/
│   │   ├── AIReviewQueueView.tsx
│   │   ├── AdminDashboardView.tsx
│   │   ├── AdminLedgerView.tsx
│   │   ├── AuditLogView.tsx
│   │   └── SystemMonitoringView.tsx
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
├── dist/
├── node_modules/
├── web gay/
├── .env.example
├── .gitignore
├── bun.lock
├── index.html
├── metadata.json
├── package-lock.json
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 3. Backend API Routes Inventory

| Route Module | Prefix | Key Endpoints | Supabase Dep |
|--------------|--------|---------------|--------------|
| admin.py | /api/v1 | /admin/stats, /admin/audit-logs, /admin/workers, /admin/health, /admin/queue-status, /internal/review/* | Yes (health check) |
| ai_internal.py | /api/v1 | /internal/ai/vision, /internal/ai/uploads/*/file | No |
| auth.py | /api/v1 | /auth/login, /auth/register, /auth/me | No (local JWT) |
| campaigns.py | /api/v1 | /campaigns/*, /campaigns/*/members | No |
| chat.py | /api/v1 | /chat/messages, /chat/conversations | No |
| fund.py | /api/v1 | /fund/accounts, /fund/transactions, /fund/ledger | No |
| health.py | /api/v1 | /health | No |
| messages.py | /api/v1 | /messages/, /messages/*/recall, /messages/*/recall-eligibility | No |
| public.py | /api/v1 | /public/fund, /public/bank-accounts | No |
| review.py | /api/v1 | /internal/review/*, /internal/review/*/approve, /internal/review/*/reject | No |
| uploads.py | /api/v1 | /uploads/, /uploads/{id} | No (local storage) |
| vision.py | /api/v1 | /vision/extract | **Yes** (Supabase storage) |

## 4. Database Models Inventory (models.py)

### Enums
- `Role`: OWNER_TREASURER, MODERATOR, MEMBER, PUBLIC
- `LedgerType`: CREDIT, DEBIT, REVERT
- `LedgerSource`: IMAGE, MANUAL, REVERT
- `LedgerStatus`: VERIFIED, REVERTED
- `UploadStatus`: PENDING, PROCESSING, NEEDS_REVIEW, VERIFIED, REJECTED, DUPLICATE
- `CampaignStatus`: DRAFT, OPEN, CLOSED
- `CampaignMemberStatus`: UNPAID, PAID, EXEMPT
- `MessageStatus`: PENDING, PROCESSING, AWAITING_REVIEW, POSTED, REJECTED, FAILED, RECALLED

### Tables (17 total)

| Model | Table | PK | Financial | Key Columns |
|-------|-------|----|-----------|-------------|
| RevokedToken | revoked_tokens | jti | No | jti, user_id, expires_at, revoked_at |
| User | users | id | No | email(unique), password_hash, role, created_at |
| Account | accounts | id | **YES** | name(unique), currency, opening_balance(Numeric(18,2)), active |
| BankAccount | bank_accounts | id | **YES** | bank_name, account_name, account_number, payment_link, qr_image_url, active |
| Upload | uploads | id | **YES** | file_hash(index), perceptual_hash, original_filename, storage_path, uploaded_by(FK), uploader_name, status(index) |
| Student | students | id | No | full_name(index), aliases(JSON), student_code(index), active |
| CollectionCampaign | collection_campaigns | id | **YES** | title, description, expected_amount(Numeric(18,2)), start_at, end_at, status |
| CampaignMember | campaign_members | id | **YES** | campaign_id(FK), student_id(FK), status, uq(campaign_id,student_id) |
| ExtractedTransaction | extracted_transactions | id | **YES** | upload_id(FK,unique), transaction_code, amount(Numeric(18,2)), sender_name, bank_name, bank_account_id(FK), transaction_time, confidence(Numeric(5,4)), raw_ocr, campaign_id(FK), student_id(FK), status, field_confidences(JSON), extraction_method, source_image_id, currency, reviewed_by(FK), reviewed_at, review_notes |
| Transaction | transactions | id | **YES** | account_id(FK,index), bank_account_id(FK), transaction_code, type(LedgerType), amount(Numeric(18,2)), currency, source(LedgerSource), status(LedgerStatus), upload_id(FK), created_by(FK), effective_at, note, message_id(FK,index), uq(bank_account_id,transaction_code) |
| LedgerEntry | ledger_entries | id | **YES** | transaction_id(FK,unique), type(LedgerType), amount(Numeric(18,2)), currency, transaction_code(index), source(LedgerSource), status(LedgerStatus), upload_id(FK), created_by(FK), effective_at, original_entry_id(FK,self), note |
| IdempotencyKey | idempotency_keys | id | **YES** | key(unique,index), request_fingerprint, response_status, response_body(JSON), created_at |
| AuditLog | audit_logs | id | **YES** | actor_id(FK), action, entity_type, entity_id, before_data(JSON), after_data(JSON), ip, created_at |
| PaymentMatch | payment_matches | id | **YES** | transaction_id(FK,unique), campaign_id(FK), student_id(FK), confidence(Numeric(5,4)), matched_by, created_at |
| Message | messages | id | No | conversation_id(index), sender_id(FK), sender_name, sender_photo, sender_role, message_type, content, attachment_id, attachment_ids(JSON), status, public_code(unique,index), recall_token_hash, transaction_id(FK), error_message, retry_count, created_at, claimed_at, lease_expires_at, processed_at, worker_id(FK), indexes: ix_messages_status_created(partial), ix_messages_conversation_status_created, ix_messages_processing_lease(partial), ix_messages_worker_id |
| WorkerStatus | worker_status | worker_id | No | status, model_name, last_heartbeat, last_processed_at, current_job_id(FK), metadata(JSONB) |
| RecallToken | recall_tokens | id | **YES** | message_id(FK,unique), token_hash, created_at, expires_at, used_at, revoked_at, index on message_id |
| ChatMessage | chat_messages | id | No | sender_id(FK), sender_role, message_type, content, attachment_id, ledger_entry_id(FK), created_at |

## 5. Services Inventory

| Service | File | Purpose | Supabase Dep |
|---------|------|---------|--------------|
| ledger.py | app/services/ledger.py | Core financial operations (post_transaction, post_revert, verify_and_post_from_ai, calculate_balance, idempotency) | No |
| audit.py | app/services/audit.py | Audit logging | No |
| activity.py | app/services/activity.py | Activity feed (chat_messages) | No |
| ollama_client.py | app/services/ollama_client.py | AI vision extraction | No |
| supabase_client.py | app/services/supabase_client.py | Supabase integration (storage, realtime, auth, RLS) | **YES** - Full wrapper |

## 6. Frontend Library Modules

| Module | File | Purpose | Supabase Dep |
|--------|------|---------|--------------|
| api.ts | src/lib/api.ts | REST API client (uploads, messages, public, recall) | No |
| adminApi.ts | src/lib/adminApi.ts | Admin API client (stats, audit, workers, health, queue, review) | No |
| realtime.ts | src/lib/realtime.ts | Supabase Realtime adapter for messages | **YES** - Direct Supabase JS |
| polling.ts | src/lib/polling.ts | Polling fallback for realtime | Config only |
| recall.ts | src/lib/recall.ts | Recall token management | No |
| retry.ts | src/lib/retry.ts | Retry logic | No |
| upload.ts | src/lib/upload.ts | Upload handling | No |

## 7. Configuration Files

| File | Purpose | Database Config |
|------|---------|-----------------|
| app/core/config.py | Pydantic Settings | PostgreSQL URL, Supabase keys |
| alembic.ini | Alembic config | PostgreSQL URL |
| docker-compose.yml | Local dev stack | PostgreSQL 17 service |
| .env.example | Env template | All secrets |
| pyproject.toml | Python deps | - |
| package.json | Node deps | @supabase/supabase-js |

## 8. Test Files

| File | Type | Database |
|------|------|----------|
| test_financial_core.py | Unit | SQLite |
| test_idempotency.py | Unit | SQLite |
| test_recall.py | Unit | SQLite |
| test_admin.py | Unit | SQLite |
| simulation/test_e2e.py | E2E Simulation | SQLite + Mocks |
| simulation/test_failure_injection.py | Failure injection | SQLite + Mocks |
| simulation/test_supabase_auth.py | Auth simulation | SQLite + Mocks |
| simulation/config.py | Simulation config | - |
| simulation/mock_ollama.py | Mock Ollama | - |
| simulation/mock_supabase.py | Mock Supabase | - |
| conftest.py | Pytest fixtures | Sets SQLite |

## 9. Supabase Dependency Summary

### Active Runtime Dependencies (MUST REPLACE)

| Component | Location | Replacement Target |
|-----------|----------|-------------------|
| File Storage | supabase_client.py:upload_receipt/download_receipt/delete_receipt, vision.py | Local filesystem / S3-compatible |
| Realtime | supabase_client.py:subscribe_to_messages/subscribe_to_worker_status, realtime.ts | WebSocket / Server-Sent Events |
| Auth (JWT verify) | supabase_client.py:verify_jwt/get_user_by_id, admin.py health check | Local JWT verification (already exists) |
| RLS Policies | supabase_client.py:enable_rls/create_policy | Application-level authorization |

### Configuration Dependencies
- Backend: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`
- Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

### Package Dependencies
- Backend: `supabase`, `postgrest` (in pyproject.toml)
- Frontend: `@supabase/supabase-js` (in package.json)

## 10. PostgreSQL-Specific Schema Elements

### Requiring Migration Adaptation

| Element | Current (PG) | MySQL Equivalent | Risk |
|---------|--------------|------------------|------|
| `postgresql.JSONB` | worker_status.metadata | JSON | Low - MySQL 8.0+ supports JSON |
| `Enum(..., native_enum=False)` | All enums use native PG enums | ENUM or VARCHAR+CHECK | Medium - MySQL ENUM differs |
| Partial indexes `postgresql_where` | messages table (3 indexes) | WHERE clause in CREATE INDEX | Medium - MySQL 8.0+ supports |
| `server_default=sa.func.now()` | created_at columns | DEFAULT CURRENT_TIMESTAMP | Low |
| UUID as String(36) | All PKs/FKs | CHAR(36) or BINARY(16) | Low |
| Numeric(18,2) | Money amounts | DECIMAL(18,2) | **Critical - must preserve** |

### Data Types Mapping

| PostgreSQL | MySQL 8.4 | Notes |
|------------|-----------|-------|
| UUID (String(36)) | CHAR(36) | Keep as string for compatibility |
| TIMESTAMP WITH TIME ZONE | TIMESTAMP(6) | MySQL stores UTC, configure timezone |
| NUMERIC(18,2) | DECIMAL(18,2) | **Exact match for money** |
| NUMERIC(5,4) | DECIMAL(5,4) | Confidence scores |
| JSONB | JSON | MySQL 8.0+ native JSON |
| TEXT | LONGTEXT | |
| BOOLEAN | TINYINT(1) | |
| ENUM (native) | ENUM or VARCHAR+CHECK | Use VARCHAR+CHECK for portability |

## 11. Files Requiring Modification for MySQL Migration

### Core Database Files
1. `app/core/config.py` - Database URL
2. `alembic.ini` - SQLAlchemy URL
3. `app/db/session.py` - Engine creation (pool settings for MySQL)
4. `app/db/base.py` - May need MySQL-specific base

### Models & Migrations
5. `app/models/models.py` - Enum handling, index definitions, JSON columns
6. All 5 alembic versions - Rewrite for MySQL compatibility
7. New alembic environment for MySQL

### Supabase Replacement
8. `app/services/supabase_client.py` - Replace with local implementations
9. `app/api/routes/vision.py` - Local file serving
10. `app/api/routes/admin.py` - Local health checks
11. `worker/main.py` - Local worker (no Supabase realtime)

### Frontend
12. `src/lib/realtime.ts` - WebSocket/SSE implementation
13. `src/hooks/useChat.ts` - Remove Supabase config
14. `src/lib/polling.ts` - Remove Supabase config
15. `package.json` - Remove @supabase/supabase-js

### Configuration
16. `docker-compose.yml` - MySQL service instead of PostgreSQL
17. `.env.example` - MySQL env vars, remove Supabase vars
18. `alembic.ini` - MySQL connection

### Tests
19. `tests/conftest.py` - MySQL test database (testcontainers or external)
20. New MySQL-specific test files

## 12. Financial Invariants Checklist (Must Preserve)

| Invariant | Implementation | Test Coverage |
|-----------|---------------|---------------|
| Ledger authority | LedgerEntry immutable after VERIFIED | test_financial_core.py |
| AI proposals only | verify_and_post_from_ai() gatekeeps | test_financial_core.py, test_idempotency.py |
| Recall before post → prevent | messages.py recall logic | test_recall.py |
| Recall after post → REVERT | ledger.py post_revert() | test_financial_core.py |
| Idempotency | fingerprint + idempotency_keys table | test_idempotency.py (8 tests) |
| Concurrent balance updates | with_for_update() + retry | test_idempotency.py |
| Decimal precision | Numeric(18,2) everywhere | test_financial_core.py |
| Double reversal prevention | LedgerEntry.original_entry_id check | test_financial_core.py |

---

**Total Files to Modify: ~20+**  
**Total Tables to Migrate: 17**  
**Supabase Dependencies to Replace: 4 major components**  
**Test Database Migration: SQLite → MySQL (testcontainers recommended)**