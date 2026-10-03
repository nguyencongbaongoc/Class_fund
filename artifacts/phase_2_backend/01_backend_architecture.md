# 01_BACKEND_ARCHITECTURE.md

## Phase 2 Backend Architecture

**Scope**: Financial core, ledger integrity, persistent worker, Supabase integration, API contracts

### 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLASS FUND BACKEND (Phase 2)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   Frontend   │    │   AI/OCR     │    │  Persistent  │    │  Admin   │  │
│  │   (Phase 3)  │    │  (Phase 3)   │    │    Worker    │    │  Tools   │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └────┬─────┘  │
│         │                   │                   │                   │        │
│         ▼                   ▼                   ▼                   ▼        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        API GATEWAY (FastAPI)                          │   │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │   │
│  │  │ Messages│ │  Fund   │ │ Campaigns│ │ Uploads │ │ Internal/AI  │  │   │
│  │  │  Router │ │  Router │ │  Router  │ │ Router  │ │   Router     │  │   │
│  │  └─────────┘ └─────────┘ └──────────┘ └─────────┘ └──────────────┘  │   │
│  └────────────────────────────────┬─────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         SERVICE LAYER                                 │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────────┐  │   │
│  │  │  Ledger     │ │  Supabase   │ │  Ollama    │ │  Audit/Activity│  │   │
│  │  │  Service    │ │  Client     │ │  Client    │ │  Service       │  │   │
│  │  └──────┬──────┘ └──────┬──────┘ └─────┬──────┘ └──────┬─────────┘  │   │
│  └─────────┼────────────────┼──────────────┼─────────────┼────────────┘   │
│            │                │              │             │                │
│            ▼                ▼              ▼             ▼                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      DATABASE (PostgreSQL/Supabase)                  │   │
│  │  ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │ Messages │ │Transactions│ │Ledger   │ │ Idempotency│ │ Workers  │  │   │
│  │  │ + Recalls│ │ + Match │ │ Entries │ │   Keys   │ │  Status  │  │   │
│  │  └──────────┘ └─────────┘ └─────────┘ └──────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Core Components

#### 2.1 Financial Gatekeeper (`verify_and_post_from_ai()`)
**Location**: `app/services/ledger.py:378`
**Role**: Single entry point for all AI-derived financial postings
**Responsibilities**:
- Validates extraction confidence threshold
- Checks required fields (transaction_code, amount, bank_account_id)
- Enforces campaign rules (amount match, student membership, duplicate payment)
- Prevents duplicate bank transactions (unique constraint + check)
- Delegates to `post_transaction()` with idempotency
- Returns structured `VerifyAndPostResult` (never throws on business logic)

**Invariants**:
- No transaction created without passing through this function
- No direct ledger writes from worker, AI, or frontend
- All financial mutations are audited

#### 2.2 Ledger Core (`post_transaction()`, `post_revert()`)
**Location**: `app/services/ledger.py:147, 300`
**Role**: Low-level financial mutation primitives
**Responsibilities**:
- Creates Transaction + LedgerEntry atomically
- Enforces balance constraints (no negative balance on debit)
- Handles idempotency via `IdempotencyKey` table
- Recovers from ambiguous commits via `message_id` lookup
- Handles concurrent commits with `FOR UPDATE` locking
- Writes audit trail on every mutation

**Idempotency Key Format**: `msg_{message_id}_v{content_version}`
- `content_version` = SHA256(payload)[:8] where payload = `transaction_code|amount|bank_account_id`
- Stable across retries (retry_count NOT in key)
- Different payload → fingerprint mismatch → VALIDATION error

#### 2.3 Persistent Worker
**Location**: `worker/main.py`
**Role**: Offline-capable message processor
**Lifecycle**:
```
STARTUP
  ├─ Reclaim stale leases (lease_expires_at < NOW)
  └─ Register worker_status = "online"
LOOP (while running)
  ├─ claim_next_message() → FOR UPDATE SKIP LOCKED
  │   ├─ Sets status=processing, worker_id, claimed_at, lease_expires_at
  │   └─ Returns Message or None
  ├─ If message:
  │   ├─ Update worker_status current_job_id
  │   ├─ Check message.status != RECALLED
  │   ├─ Get upload + extraction
  │   ├─ Generate stable idempotency_key
  │   ├─ verify_and_post_from_ai()
  │   ├─ Handle result:
  │   │   ├─ SUCCESS/DUPLICATE → complete_message (POSTED)
  │   │   ├─ NEEDS_HUMAN_REVIEW → await_review
  │   │   ├─ RECALLED → recall_message
  │   │   └─ FAILED/RETRYABLE → fail_message (retry with backoff)
  │   └─ Clear worker_id, claimed_at, lease_expires_at
  └─ Else: sleep 5s
SHUTDOWN (SIGINT/SIGTERM)
  └─ worker_status = "offline"
```

**Recovery Mechanisms**:
- Startup: `reclaim_stale_leases()` resets expired processing messages to pending
- Lease expiry: Other workers can claim after lease_expires_at
- Crash mid-processing: Message stays processing until lease expires, then reclaimed
- Duplicate protection: Idempotency key ensures exactly-once financial effect

#### 2.4 Supabase Integration
**Location**: `app/services/supabase_client.py`
**Components**:
- **Admin Client** (service role): Storage, RLS management, realtime, auth admin
- **Anon Client** (public): Frontend operations, public reads
- **User Client** (JWT): Per-request authenticated operations

**Storage**: `receipts` bucket, public URLs
**Realtime**: Channels for `messages:{conversation_id}`, `worker_status`
**Auth**: JWT verification, user lookup

#### 2.5 API Layer
**Routes**:
- `/messages` — Guest message creation, recall, status (public)
- `/fund` — Balance, transactions, manual credit/debit/revert (admin)
- `/campaigns` — Campaign CRUD, member management (admin)
- `/uploads` — File upload, status (public create, admin manage)
- `/internal/ai` — AI result webhook (service auth)
- `/vision` — Vision inference (service auth)
- `/health` — Health checks

### 3. Data Flow: Receipt → Ledger

```
Guest Uploads Receipt
        │
        ▼
POST /uploads → Upload record (PENDING) + file to Supabase Storage
        │
        ▼
POST /messages (type=RECEIPT, attachment_id) → Message (PENDING) + RecallToken
        │                         │
        │                         └─ Returns recall_token ONCE to user
        │
        ▼
Worker polls → claim_next_message() → Message (PROCESSING, lease)
        │
        ▼
Worker calls /internal/ai/uploads/{id}/result (AI adapter)
        │
        ▼
AI returns extraction → verify_and_post_from_ai()
        │
        ├── Confidence < threshold → NEEDS_HUMAN_REVIEW
        ├── Missing fields → NEEDS_HUMAN_REVIEW
        ├── Duplicate bank transaction → DUPLICATE
        ├── Campaign rules fail → NEEDS_HUMAN_REVIEW/DUPLICATE
        └── All valid → post_transaction()
                │
                ├── Idempotency hit → DUPLICATE (returns existing)
                ├── Concurrent commit → Recovery via message_id → SUCCESS
                └── New → SUCCESS (Transaction + LedgerEntry created)
        │
        ▼
Worker marks Message:
  - SUCCESS/DUPLICATE → POSTED, transaction_id set
  - NEEDS_HUMAN_REVIEW → AWAITING_REVIEW
  - FAILED (retries exhausted) → FAILED
  - RECALLED during processing → RECALLED
```

### 4. Security Boundaries

| Boundary | Enforcement |
|----------|-------------|
| Guest → Message Create | Public endpoint, rate limit (TODO) |
| Guest → Recall | Requires `recall_token` (SHA-256 hash stored) |
| Guest → Financial Post | **IMPOSSIBLE** — no endpoint, gatekeeper internal |
| AI → Financial Post | `/internal/ai` requires service auth, calls gatekeeper |
| Worker → Financial Post | Calls `verify_and_post_from_ai()` internally |
| Admin → Manual Post | `/fund/credit|debit` requires OWNER_TREASURER role + Idempotency-Key |
| Admin → Revert | `/fund/revert` requires OWNER_TREASURER role + Idempotency-Key |
| Storage → Receipts | Service role only, public URLs for access |

### 5. Database Schema Summary

**Core Tables**:
- `accounts` — Fund accounts with opening balance
- `transactions` — Financial mutations (CREDIT/DEBIT/REVERT)
- `ledger_entries` — Immutable ledger lines (1:1 with transactions)
- `bank_accounts` — External bank accounts for matching
- `uploads` — Receipt uploads with status
- `extracted_transactions` — AI extraction results
- `messages` — Chat messages with status, lease, worker_id
- `recall_tokens` — SHA-256 hash of recall tokens
- `worker_status` — Worker heartbeat, current job
- `idempotency_keys` — Deduplication records
- `audit_logs` — Immutable audit trail
- `campaigns/campaign_members/students` — Collection campaigns
- `payment_matches` — Transaction ↔ campaign member links

**Key Constraints**:
- `transactions(bank_account_id, transaction_code)` UNIQUE
- `ledger_entries(transaction_id)` UNIQUE
- `idempotency_keys(key)` UNIQUE
- `messages.public_code` UNIQUE
- `recall_tokens(message_id)` UNIQUE
- `extracted_transactions(upload_id)` UNIQUE

### 6. Concurrency Model

| Scenario | Protection |
|----------|------------|
| Duplicate AI result for same upload | `verify_and_post_from_ai` checks existing tx by upload_id |
| Concurrent worker claim | `FOR UPDATE SKIP LOCKED` — only one worker gets message |
| Concurrent financial post same idempotency key | `IdempotencyKey` table + fingerprint check |
| Concurrent commit same bank transaction | DB unique constraint + `FOR UPDATE` in `post_transaction` |
| Recall during worker processing | Worker checks `message.status` before gatekeeper call |
| Worker crash mid-transaction | Lease expiry → reclaim on startup |

### 7. Error Classification

```
ProcessingResult:
  SUCCESS           — Transaction created/confirmed
  DUPLICATE         — Idempotency hit or existing bank transaction
  FAILED            — Validation/business rule violation (permanent)
  RETRYABLE         — Transient error (DB deadlock, timeout)
  AMBIGUOUS         — Idempotency record exists but tx not recoverable
  RECALLED          — Message recalled before/during processing
  NEEDS_HUMAN_REVIEW — Confidence low, missing fields, campaign mismatch

ErrorClassification:
  VALIDATION        — Request malformed (fingerprint mismatch, bad amount)
  BUSINESS_RULE     — Domain rule violated (duplicate tx, insufficient balance)
  TRANSIENT         — Temporary failure (retry may succeed)
  PERMANENT         — Will not succeed on retry
  AMBIGUOUS         — Cannot determine outcome
```

### 8. Deployment Configuration

**Environment Variables**:
```bash
# Required
DATABASE_URL=postgresql://...
WORKER_ID=worker-1
LEASE_DURATION=300
AI_CONFIDENCE_THRESHOLD=0.9

# Supabase (BLOCKED - not provided)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_ANON_KEY=...
SUPABASE_JWT_SECRET=...

# Ollama (BLOCKED - not provided)
OLLAMA_BASE_URL=http://127.0.0.1:11434

# Auth
JWT_SECRET=...
```

**Worker Startup**:
```bash
python -m worker.main
# Runs until SIGINT/SIGTERM
# Windows: Can run as scheduled task or service
```

### 9. Integration Points for Phase 3/4/5

| Phase | Contract | Status |
|-------|----------|--------|
| 3 (AI/OCR) | `/internal/ai/uploads/{id}/result` + idempotency | Defined in `ai_internal.py` |
| 4 (Frontend) | `/messages`, `/fund`, `/uploads`, `/campaigns` | Defined in route files |
| 5 (Admin) | `/fund` manual ops, campaign mgmt | Defined in route files |

---

**Architecture Status**: Core components implemented and unit-tested (SQLite). Supabase/Ollama integration code complete but unverified (BLOCKED_EXTERNAL_DEPENDENCY). Security hardening (rate limiting, file validation, CSP) not yet implemented — Phase 2 scope.