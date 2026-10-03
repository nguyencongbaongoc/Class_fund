# PHASE 0 — THREE-PART RESPONSIBILITY MAP

## Executive Summary
The existing implementation cleanly separates into three ownership areas with well-defined boundaries. Cross-boundary dependencies are minimal and documented.

---

## 1. MINH — BACKEND, DATABASE, AUTH, AUTHORIZATION, FINANCIAL INTEGRITY

### Owned Components

| Component | Location | Description |
|-----------|----------|-------------|
| **FastAPI Application** | `app/main.py` | App lifecycle, CORS, router mounting |
| **Configuration** | `app/core/config.py` | Pydantic Settings, env vars |
| **Security** | `app/core/security.py` | JWT (HS256), argon2, token revocation |
| **Dependencies** | `app/api/deps.py` | `get_current_user`, `require_roles`, `require_ai_service` |
| **Database Models** | `app/models/models.py` | 15 SQLAlchemy tables |
| **Pydantic Schemas** | `app/schemas/schemas.py` | Request/response contracts |
| **Database Session** | `app/db/session.py` | SQLAlchemy engine, session factory |
| **Alembic Migrations** | `alembic/` | Schema versioning |
| **Ledger Service** | `app/services/ledger.py` | **Core financial logic** |
| **Audit Service** | `app/services/audit.py` | Audit logging |
| **Activity Service** | `app/services/activity.py` | Chat message emission |
| **Auth Routes** | `app/api/routes/auth.py` | Login, logout, me |
| **Fund Routes** | `app/api/routes/fund.py` | Balance, transactions, credit, debit, revert, bank accounts |
| **Upload Routes** | `app/api/routes/uploads.py` | Receipt upload, status |
| **AI Internal Routes** | `app/api/routes/ai_internal.py` | **Gateway for AI service** |
| **Campaign Routes** | `app/api/routes/campaigns.py` | Campaigns, students, roster |
| **Public Routes** | `app/api/routes/public.py` | Public fund, bank accounts, campaigns |
| **Chat Routes** | `app/api/routes/chat.py` | Messages CRUD |
| **Health Routes** | `app/api/routes/health.py` | Health check |
| **Tests** | `tests/test_financial_core.py` | 4 financial integrity tests |

### Key Responsibilities

| Area | Details |
|------|---------|
| **Authentication** | JWT tokens, argon2 password hashing, token revocation |
| **Authorization** | 4 roles (OWNER_TREASURER, MODERATOR, MEMBER, PUBLIC), endpoint-level enforcement |
| **Financial Integrity** | Immutable ledger, balance from ledger, idempotency, duplicate prevention, reversal |
| **Database** | PostgreSQL schema, migrations, constraints, indexes |
| **AI Gateway** | `/internal/ai` endpoint protected by `AI_SERVICE_KEY`, validates & posts AI results |
| **Audit Trail** | Every mutation logged with before/after, actor, IP |
| **Deployment** | Docker Compose (PostgreSQL), uvicorn |

### Interfaces Exposed to Others

| Consumer | Interface | Contract |
|----------|-----------|----------|
| **Ngọc (AI)** | `POST /api/v1/internal/ai/uploads/{id}/result` | `AIResultIn` schema, requires `AI_SERVICE_KEY` header, idempotency key |
| **Ngọc (AI)** | `GET /api/v1/internal/ai/uploads/{id}/file` | Returns receipt image for processing |
| **Hải (Frontend)** | All `/api/v1/*` endpoints | OpenAPI 3.1 spec (`openapi.json`), JWT Bearer auth |
| **Hải (Frontend)** | CORS | Allows `http://localhost:3000,5173` |

---

## 2. NGỌC — AI/OCR, RECEIPT EXTRACTION, VERIFICATION, DUPLICATE DETECTION

### Owned Components

| Component | Location | Description |
|-----------|----------|-------------|
| **OCR Service** | `ai/ocr/service.py` | Tesseract engine, 6 preprocessing strategies |
| **Extraction Service** | `ai/extraction/service.py` | 5 regex extractors (amount, tx_code, sender, bank, datetime) |
| **Verification Service** | `ai/verification/service.py` | Orchestrates OCR→Extraction→Matching→Duplicates→Policy |
| **Duplicate Detector** | `ai/duplicate/service.py` | 3-layer (file hash, perceptual hash, transaction identity) |
| **Student Matcher** | `ai/matching/service.py` | Name normalization, fuzzy matching, aliases |
| **Worker Queue** | `ai/worker/queue.py` | Celery + Redis, retry/backoff, task timeout |
| **Contracts** | `ai/contracts.py` | All Pydantic models for AI pipeline |

### Key Responsibilities

| Area | Details |
|------|---------|
| **Receipt OCR** | Tesseract (vie+eng) with multi-strategy preprocessing |
| **Data Extraction** | Regex-based structured extraction with confidence |
| **Verification Policy** | Configurable thresholds, risk flags, status determination |
| **Duplicate Detection** | File hash, perceptual hash, transaction identity |
| **Student Matching** | Vietnamese name normalization, fuzzy matching, aliases |
| **Worker Infrastructure** | Celery tasks, Redis queue, retry logic |
| **Ollama Integration** | **NOT YET IMPLEMENTED** — `qwen2.5vl:3b` available locally |

### Interfaces Exposed to Others

| Consumer | Interface | Contract |
|----------|-----------|----------|
| **Minh (Backend)** | `VerificationService.verify(upload_id, image_bytes)` | Returns `VerificationResult` (matches `AIResultIn`) |
| **Minh (Backend)** | `ExtractionService`, `OCRService` | Reusable as library |
| **Worker (Self)** | `process_verification_task` Celery task | Consumes from Redis queue |

### Dependencies on Others

| Dependency | Provider | Nature |
|------------|----------|--------|
| **Receipt Images** | Minh (Backend) | `GET /internal/ai/uploads/{id}/file` |
| **Student Roster** | Minh (Backend) | `GET /campaigns/{id}/members` or direct DB |
| **Bank Accounts** | Minh (Backend) | `GET /fund/bank-accounts` for bank_name → bank_account_id mapping |
| **Post Results** | Minh (Backend) | `POST /internal/ai/uploads/{id}/result` with `AIResultIn` |
| **Ollama** | Local | `http://127.0.0.1:11434` (vision model) |

---

## 3. HẢI — FRONTEND, UI/UX, PUBLIC PAGES, USER INTERACTIONS

### Owned Components

| Component | Location | Description |
|-----------|----------|-------------|
| **React App** | `src/App.tsx` | Root, providers, routing via tabs |
| **App Context** | `src/context/AppContext.tsx` | **Global state management** (mock data + actions) |
| **Types** | `src/types/index.ts` | TypeScript interfaces (LedgerEntry, Campaign, etc.) |
| **Mock Database** | `src/data/mockDatabase.ts` | Complete mock data + helpers |
| **Views (8)** | `src/views/*.tsx` | Dashboard, Ledger, Upload, Campaign, Chat, BankQR, Donate, PublicFund |
| **Components** | `src/components/` | LiquidCard, Navbar, Modals, Toast, ContextMenu |
| **Liquid Glass** | `src/lib/liquidglass/` | Custom design system |
| **Utils** | `src/utils/soundEffects.ts` | Audio feedback |
| **Config** | `vite.config.ts`, `tsconfig.json`, `package.json` | Vite, TypeScript, Bun |

### Key Responsibilities

| Area | Details |
|------|---------|
| **UI/UX Design** | Liquid Glass morphism, Apple-style animations, responsive |
| **State Management** | React Context with mock data (NO API integration yet) |
| **Financial Views** | Dashboard (balance, stats), Ledger (filterable table), Campaign (roster) |
| **Receipt Upload** | Drag-drop, preview, 4-step AI pipeline simulation |
| **Chat** | Messages, receipts, announcements, pinned, MOD toggle |
| **Public Pages** | Fund transparency, VietQR, donation link |
| **Admin Features** | Revert modal, manual expense, campaign creation, student management |
| **Role Simulation** | 4-user switcher (TREASURER, MODERATOR, MEMBER, PUBLIC) |

### Current Data Flow (Mock Only)

```
User Action → AppContext Action → Local State Update → UI Re-render
```
**No network calls anywhere.**

### Interfaces Required from Others

| Need | Provider | Current Status |
|------|----------|----------------|
| **Auth API** | Minh | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` — NOT INTEGRATED |
| **Fund Balance** | Minh | `GET /fund/balance` — MOCK |
| **Transactions** | Minh | `GET /fund/transactions` — MOCK |
| **Credit/Debit/Revert** | Minh | `POST /fund/credit|debit|revert` — MOCK |
| **Upload Receipt** | Minh | `POST /uploads` — SIMULATED |
| **Upload Status** | Minh | `GET /uploads/{id}` — MOCK |
| **Campaigns** | Minh | `GET/POST/PATCH /campaigns/*` — MOCK |
| **Chat Messages** | Minh | `GET/POST /chat/messages` — MOCK |
| **Public Fund** | Minh | `GET /public/fund` — MOCK |
| **Bank Accounts** | Minh | `GET /public/bank-accounts` — MOCK |
| **Realtime Updates** | Minh + Ngọc | Supabase Realtime — NOT IMPLEMENTED |

---

## 4. CROSS-BOUNDARY DEPENDENCIES

### Dependency Graph

```
┌─────────────┐     POST /internal/ai/...     ┌─────────────┐
│   NGỌC      │ ◄──────────────────────────── │    MINH     │
│   (AI)      │   AIResultIn + Idempotency    │  (Backend)  │
│             │   GET /internal/ai/uploads/   │             │
│             │   Receipt image for processing│             │
└──────┬──────┘                                └──────┬──────┘
       │                                               │
       │ Supabase Realtime / Direct DB                 │
       ▼                                               ▼
┌─────────────┐     REST API + Realtime         ┌─────────────┐
│   HẢI       │ ◄────────────────────────────── │   SUPABASE  │
│  (Frontend) │   Auth, DB, Storage, Realtime   │  (Cloud)    │
└─────────────┘                                └─────────────┘
```

### Critical Shared Contracts

| Contract | Owners | Location |
|----------|--------|----------|
| `VerificationResult` ↔ `AIResultIn` | Minh + Ngọc | `ai/contracts.py` + `app/schemas/schemas.py` |
| `LedgerEntry` (DB) ↔ `LedgerEntry` (TS) | Minh + Hải | `app/models/models.py` + `src/types/index.ts` |
| `Campaign` / `Student` | Minh + Hải | Same |
| `ChatMessage` | Minh + Hải | Same |
| `UploadStatus` | Minh + Ngọc + Hải | Same enum values |

---

## 5. OWNERSHIP CONFLICTS & RESOLUTIONS

| Conflict | Description | Resolution |
|----------|-------------|------------|
| **Student Roster Source** | Both backend (campaigns) and frontend (mock) have student data | **Minh owns** — Frontend reads from Supabase |
| **Campaign State** | Frontend mock has campaign; backend has campaigns table | **Minh owns** — Frontend syncs via API |
| **Chat Messages** | Backend has `chat_messages` table; frontend has mock + realtime plan | **Minh owns persistence**, Hải owns UI, Supabase Realtime syncs |
| **Receipt Processing** | AI processes, backend posts, frontend uploads | **Clear pipeline**: Hải uploads → Minh stores → Ngọc processes → Minh posts |
| **Financial Authority** | AI extracts, backend validates & posts | **Minh owns** — AI only proposes, backend decides |

---

## 6. RESPONSIBILITY MATRIX (RACI)

| Feature | Minh (Backend) | Ngọc (AI) | Hải (Frontend) |
|---------|----------------|-----------|----------------|
| User Authentication | **R/A** | I | C |
| Role-Based Access | **R/A** | I | C |
| Fund Balance Calculation | **R/A** | I | C |
| Transaction Posting | **R/A** | I | C |
| Transaction Reversal | **R/A** | I | C |
| Idempotency | **R/A** | C | I |
| Duplicate Detection | C | **R/A** | I |
| Receipt OCR | I | **R/A** | I |
| Data Extraction | I | **R/A** | I |
| Verification Policy | C | **R/A** | I |
| Student Matching | C | **R/A** | I |
| Receipt Upload UI | I | I | **R/A** |
| Dashboard/UI | I | I | **R/A** |
| Chat UI | I | I | **R/A** |
| Realtime Sync | C (Supabase config) | I | **R/A** |
| Admin Review UI | C | C | **R/A** |
| Deployment (Vercel) | I | I | **R/A** |
| Worker Deployment | C | **R/A** | I |
| Database Schema | **R/A** | C | C |
| Migrations | **R/A** | I | I |

**R** = Responsible, **A** = Accountable, **C** = Consulted, **I** = Informed

---

## 7. INTEGRATION HANDOFF POINTS

### Handoff 1: Receipt Upload (Hải → Minh)
- **Frontend**: `POST /uploads` with multipart (file, uploader_name)
- **Backend**: Returns `UploadOut` with `id`, `status=PENDING`
- **Contract**: `UploadOut` schema

### Handoff 2: AI Processing Trigger (Minh → Ngọc)
- **Option A (Polling)**: Worker polls `uploads` where `status=PENDING`
- **Option B (Webhook)**: Backend calls AI service after upload (not implemented)
- **Current**: Neither implemented — **gap**

### Handoff 3: AI Result Submission (Ngọc → Minh)
- **Worker**: `POST /internal/ai/uploads/{id}/result` with `AIResultIn`
- **Headers**: `X-AI-Service-Key`, `Idempotency-Key`
- **Backend**: Validates, posts to ledger, returns `{posted, transaction_id}`

### Handoff 4: Realtime Updates (Supabase → Hải)
- **Tables**: `messages`, `ledger_entries`, `campaign_members`, `uploads`
- **Frontend**: Supabase Realtime subscriptions
- **Events**: `INSERT`, `UPDATE` on relevant tables

---

## 8. CONFIDENCE ASSESSMENT

- **Verified**: All code ownership boundaries from source inspection
- **Partially Verified**: Handoff contracts (designed but not all implemented)
- **Assumed**: Supabase as integration layer for realtime
- **Not Verified**: Actual handoff execution, error handling across boundaries