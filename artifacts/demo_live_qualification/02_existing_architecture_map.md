# Existing Architecture Map

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLASS_FUND_WEB SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌─────────────────────┐     ┌────────────────────┐   │
│  │   FRONTEND   │────▶│    BACKEND API      │────▶│   DATABASE         │   │
│  │  (React)     │     │   (FastAPI)         │     │   (PostgreSQL)     │   │
│  └──────────────┘     └──────────┬──────────┘     └────────────────────┘   │
│                                 │                                          │
│                    ┌────────────┼────────────┐                             │
│                    ▼            ▼            ▼                             │
│           ┌──────────────┐ ┌──────────┐ ┌───────────┐                     │
│           │   OLLAMA     │ │ SUPABASE │ │  WORKER   │                     │
│           │  (Vision/Text)│ │ (Auth/   │ │ (Queue/   │                     │
│           │              │ │ Storage/ │ │  Process) │                     │
│           │              │ │ Realtime)│ │           │                     │
│           └──────────────┘ └──────────┘ └───────────┘                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Frontend (React + TypeScript + Vite)
**Location**: `classfund/classfund/src/`

**Key Views**:
- `DashboardView` - Main user dashboard
- `LedgerView` - Transaction ledger
- `UploadReceiptView` - Receipt upload
- `CampaignView` - Collection campaigns
- `ChatView` - Chat messaging
- `BankQRView` - Bank QR codes
- `DonateView` - Donations
- `PublicFundView` - Public fund display
- `GuestChatPage` - Guest chat
- **Admin Views**:
  - `AdminDashboardView` - Admin metrics
  - `AdminLedgerView` - Admin ledger
  - `AIReviewQueueView` - AI review queue
  - `AuditLogView` - Audit logs
  - `SystemMonitoringView` - System health

**State Management**: React Context (`AppContext.tsx`)
**API Layer**: `src/lib/` - API clients, retry logic, recall utilities

### 2. Backend API (FastAPI)
**Location**: `class-fund-backend-v0.1/class-fund-backend/app/`

**Routes**:
| Route | Purpose | Auth |
|-------|---------|------|
| `/auth` | Login, registration | Public |
| `/uploads` | File upload | Member+ |
| `/vision` | AI vision extraction | Member+ |
| `/fund` | Fund operations | Member+ |
| `/campaigns` | Collection campaigns | Member+ |
| `/chat` | Chat messaging | Member+ |
| `/messages` | Message processing | Member+ |
| `/review` | Human review queue | Owner/Moderator |
| `/admin` | Admin dashboard | Owner/Moderator |
| `/public` | Public fund view | Public |
| `/health` | Health checks | Public |

**Core Services**:
- `ledger.py` - **CRITICAL**: Financial transaction posting, reversal, idempotency
- `ollama_client.py` - Vision/text extraction with circuit breaker
- `supabase_client.py` - Supabase auth, storage, realtime
- `audit.py` - Audit logging
- `activity.py` - Activity feed

**Authentication**: JWT-based with role hierarchy
- `OWNER_TREASURER` - Full access
- `MODERATOR` - Admin access
- `MEMBER` - Standard user
- `PUBLIC` - Read-only

### 3. Database Schema (PostgreSQL/SQLAlchemy)
**Location**: `app/models/models.py`

**Core Tables**:
| Table | Purpose |
|-------|---------|
| `users` | User accounts with roles |
| `accounts` | Fund accounts |
| `bank_accounts` | Bank account details |
| `uploads` | File uploads |
| `extracted_transactions` | AI extraction results |
| `transactions` | Financial transactions |
| `ledger_entries` | Ledger entries (immutable) |
| `idempotency_keys` | Idempotency tracking |
| `audit_logs` | Audit trail |
| `messages` | Chat messages with processing state |
| `worker_status` | Worker heartbeat/status |
| `recall_tokens` | Recall authorization tokens |
| `campaigns` | Collection campaigns |
| `students` | Student roster |
| `payment_matches` | Campaign payment matching |

**Key Enums**:
- `Role`: OWNER_TREASURER, MODERATOR, MEMBER, PUBLIC
- `LedgerType`: CREDIT, DEBIT, REVERT
- `LedgerSource`: IMAGE, MANUAL, REVERT
- `LedgerStatus`: VERIFIED, REVERTED
- `UploadStatus`: PENDING, PROCESSING, NEEDS_REVIEW, VERIFIED, REJECTED, DUPLICATE
- `MessageStatus`: PENDING, PROCESSING, AWAITING_REVIEW, POSTED, REJECTED, FAILED, RECALLED

### 4. Worker (Persistent Queue Processor)
**Location**: `worker/main.py`

**Lifecycle**:
1. `STARTING` - Initialize, reclaim stale leases
2. `ONLINE` - Processing messages
3. `DEGRADED` - Duplicate data load failed
4. `OFFLINE` - Shutdown
5. `RECOVERING` - Restart after crash
6. `STOPPED` - Terminated

**Processing Flow**:
```
Claim Message (FOR UPDATE SKIP LOCKED)
    ▼
Load Upload & Extraction
    ▼
Verify via verify_and_post_from_ai()
    ▼
SUCCESS/DUPLICATE → Mark POSTED
NEEDS_HUMAN_REVIEW → Mark AWAITING_REVIEW
FAILED → Retry with backoff (max 3)
RECALLED → Mark RECALLED
```

**Lease Duration**: 300 seconds (configurable)
**Retry Backoff**: 60s, 120s, 240s (exponential)

### 5. AI Pipeline (Ollama)
**Models**:
- Vision: `qwen2.5vl:3b` - Receipt image extraction
- Text: `qwen3.5:4b` - OCR text fallback

**Endpoint**: `http://127.0.0.1:11434`

**Extraction Schema** (from `ai/contracts.py`):
```python
class VisionExtractionSchema(BaseModel):
    transaction_code: Optional[str]
    amount: Optional[int]  # VND
    sender_name: Optional[str]
    bank_name: Optional[str]
    transaction_time: Optional[str]  # ISO 8601
    confidence: float  # 0.0-1.0
    raw_text: Optional[str]
```

**Circuit Breaker**: 5 failures → OPEN, 60s recovery timeout

**Text Fallback**: Triggered when vision fails or confidence < 0.7

### 6. Supabase Integration
**Services**:
- **Auth**: JWT verification, user management
- **Storage**: Receipt uploads (bucket: `receipts`)
- **Realtime**: Message subscriptions, worker status

### 7. Financial Core Invariants (CRITICAL)

**From `ledger.py`**:
1. **AI Never Posts Directly** - All AI output → `verify_and_post_from_ai()` gatekeeper
2. **Idempotency** - `message_id` + content hash = stable key
3. **Duplicate Prevention** - DB unique constraint on `(bank_account_id, transaction_code)`
4. **Reversal Pattern** - `post_revert()` creates compensating REVERT entry
5. **Original Preserved** - Reverted transaction stays, marked `REVERTED`
6. **Double Reversal Blocked** - Check `original_entry_id` before revert
7. **Recall Before Post** - Message status check blocks posting
8. **Recall After Post** - Creates REVERT via `post_revert()`
9. **Backend Authorization** - All admin routes require `OWNER_TREASURER` or `MODERATOR`
10. **Unknown Roles Fail Closed** - Default deny

### 8. Message Flow

```
Member Uploads Receipt
        ▼
   Create Upload + Message (PENDING)
        ▼
Worker Claims Message (PROCESSING)
        ▼
AI Vision Extraction
        ▼
verify_and_post_from_ai() Gatekeeper
        ▼
├── CONFIDENT ≥ 0.9 + Complete Fields → POSTED
├── Low Confidence / Missing Fields → NEEDS_REVIEW
├── Duplicate → DUPLICATE
└── Error → RETRY (max 3) → FAILED
        ▼
Human Review (Owner/Moderator)
        ▼
├── Approve → verify_and_post_from_ai() → POSTED
└── Reject → REJECTED
```

### 9. Integration Points for Simulation

| Component | Interface | Simulation Strategy |
|-----------|-----------|---------------------|
| PostgreSQL | SQLAlchemy ORM | In-memory SQLite or test DB |
| Supabase Auth | `supabase_client.py` | Mock JWT verification |
| Supabase Storage | `upload_receipt()` | In-memory file store |
| Supabase Realtime | Channels | Event emitter mock |
| Ollama Vision | `ollama_client.py` | Deterministic response fixtures |
| Ollama Text | `extract_with_text_fallback()` | Deterministic response fixtures |
| Worker | `worker/main.py` | Direct instantiation with test DB |

### 10. Test Coverage Gaps for Simulation

**Need to Implement**:
1. Supabase mock adapters (auth, storage, realtime)
2. Ollama mock client with deterministic responses
3. Worker simulator with controlled lifecycle
4. End-to-end scenario runner
5. Failure injection framework
6. Frontend API contract tests
7. Financial invariant regression tests