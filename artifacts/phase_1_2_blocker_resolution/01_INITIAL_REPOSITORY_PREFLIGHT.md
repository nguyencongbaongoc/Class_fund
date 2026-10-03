# 01_INITIAL_REPOSITORY_PREFLIGHT.md

## 1. Repository Root Verification

**Repository Root**: `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB`

**Structure**:
```
CLASS_FUND_WEB/
├── .mypy_cache/
├── .pytest_cache/
├── .ruff_cache/
├── ai/
│   ├── __pycache__/
│   ├── duplicate/
│   ├── extraction/
│   ├── matching/
│   ├── ocr/
│   ├── tests/
│   ├── verification/
│   ├── worker/
│   ├── __init__.py
│   └── contracts.py
├── artifacts/
│   ├── phase_0_compatibility_audit/
│   ├── phase_1_1_1_audit_correction/
│   ├── phase_1_1_contract_review/
│   ├── phase_1_2_blocker_resolution/
│   └── phase_1_integration/
├── build/
├── class_fund_ai.egg-info/
├── class-fund-backend-v0.1/
│   └── class-fund-backend/
├── classfund/
│   └── classfund/
├── dist/
├── docs/
├── .coverage
├── pyproject.toml
└── README.md
```

## 2. Git Status

**Current Branch**: `master`

**HEAD Commit**: `2d20a50` - "Phase 1 integration artifacts — all 14 files (00-14) created; contracts, contracts, contracts only; no existing source modified; STOP before Phase 2"

**Previous Commit**: `dc7768e` - "Phase 0 audit artifacts + initial working state preserved"

**Working Tree Status**:
- Untracked files:
  - `artifacts/phase_1_1_1_audit_correction/`
  - `artifacts/phase_1_1_contract_review/`
- No staged changes
- No tracked file modifications

## 3. Source Code Inventory

### Backend (`class-fund-backend-v0.1/class-fund-backend/`)
- **App Entry**: `app/main.py` (1347 bytes)
- **API Routes**:
  - `app/api/routes/ai_internal.py` - AI result endpoint with idempotency
  - `app/api/routes/auth.py` - Authentication
  - `app/api/routes/campaigns.py` - Campaign management
  - `app/api/routes/chat.py` - Chat messages
  - `app/api/routes/fund.py` - Fund transactions
  - `app/api/routes/health.py` - Health check
  - `app/api/routes/public.py` - Public fund info
  - `app/api/routes/uploads.py` - Receipt upload
- **Core**:
  - `app/core/config.py` - Settings (AI confidence threshold, etc.)
  - `app/core/security.py` - Password hashing, JWT
- **Database**:
  - `app/db/base.py` - SQLAlchemy Base
  - `app/db/init_db.py` - Database initialization
  - `app/db/session.py` - Session management
- **Models**: `app/models/models.py` (245 lines) - All SQLAlchemy models
- **Schemas**: `app/schemas/schemas.py` (153 lines) - Pydantic models
- **Services**:
  - `app/services/activity.py` - Activity emission
  - `app/services/audit.py` - Audit logging
  - `app/services/ledger.py` (242 lines) - **CORE FINANCIAL GATEKEEPER**
- **Tests**: `tests/test_financial_core.py` (90 lines) - 4 financial tests
- **Migrations**: `alembic/versions/0001_initial.py`
- **Config**: `pyproject.toml`, `alembic.ini`, `docker-compose.yml`

### Frontend (`classfund/classfund/`)
- **Entry**: `src/main.tsx`, `src/App.tsx`, `index.html`
- **Components**: 
  - `src/components/common/` - Navbar, Toast, LiquidGlass, etc.
  - `src/components/modals/` - TransactionDetail, UploadReceipt, etc.
- **Views**:
  - `src/views/ChatView.tsx` - Guest chat with photo button
  - `src/views/UploadReceiptView.tsx` - Receipt upload with simulated AI
  - `src/views/LedgerView.tsx` - Transaction ledger
  - `src/views/DashboardView.tsx` - Dashboard
  - `src/views/CampaignView.tsx` - Campaign management
  - `src/views/DonateView.tsx` - Donation flow
  - `src/views/BankQRView.tsx` - QR code display
  - `src/views/PublicFundView.tsx` - Public fund view
- **Context**: `src/context/AppContext.tsx` - Global state (mock data)
- **Types**: `src/types/index.ts` - TypeScript types
- **Config**: `package.json`, `vite.config.ts`, `tsconfig.json`

### AI (`ai/`)
- **Contracts**: `contracts.py` (168 lines) - Pydantic models for AI pipeline
- **Services**:
  - `extraction/service.py` - Receipt field extraction
  - `ocr/service.py` - Tesseract OCR
  - `matching/service.py` - Student/campaign matching
  - `duplicate/service.py` - Duplicate detection
  - `verification/service.py` - Verification orchestration
- **Worker**: `worker/queue.py` (250 lines) - **Celery/Redis (INCOMPATIBLE with offline PC)**
- **Tests**: Comprehensive test suite in `ai/tests/`

## 4. Phase Artifacts Inventory

### Phase 0 (`artifacts/phase_0_compatibility_audit/`)
- 19 reports (00-18) covering backend, frontend, API, database, AI, security, etc.
- Key: `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` - Celery/Redis incompatible
- Key: `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` - Guest flow gaps

### Phase 1 (`artifacts/phase_1_integration/`)
- 14 contracts (00-14) - Design contracts only, no source modifications

### Phase 1.1 (`artifacts/phase_1_1_contract_review/`)
- 16 reviews (00-15) - Contract vs implementation gap analysis

### Phase 1.1.1 (`artifacts/phase_1_1_1_audit_correction/`)
- 10 corrections (00-09) - Forensic evidence correcting Phase 1.1 claims
- Key: `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` - Unstable idempotency design
- Key: `05_FINANCIAL_INVARIANT_ASSESSMENT.md` - Financial gatekeeper preserved, exactly-once UNVERIFIED

## 5. Financial Functions & Callers

### Core Functions (`app/services/ledger.py`)

| Function | Lines | Purpose | Callers |
|----------|-------|---------|---------|
| `calculate_balance()` | 19-36 | Derive balance from ledger entries | `public.py`, tests |
| `_make_request_fingerprint()` | 39-40 | SHA256 of transaction params | `post_transaction()`, `post_revert()` |
| `check_idempotency()` | 43-51 | Check idempotency key | `post_transaction()`, `post_revert()` |
| `save_idempotency()` | 54-57 | Save idempotency result | `post_transaction()`, `post_revert()` |
| `post_transaction()` | 59-118 | **Main posting function** | `verify_and_post_from_ai()`, `fund.py` |
| `post_revert()` | 121-169 | Create reversal transaction | `fund.py` (revert endpoint) |
| `verify_and_post_from_ai()` | 172-242 | **AI gatekeeper** | `ai_internal.py` (receive_ai_result) |

### Call Chain for AI Processing
```
ai/worker/queue.py: process_verification_task()
  → VerificationService.verify()
    → ai_internal.py: receive_ai_result() (POST /internal/ai/uploads/{id}/result)
      → ledger.py: verify_and_post_from_ai()
        → ledger.py: post_transaction()
          → DB: Transaction + LedgerEntry + IdempotencyKey
```

## 6. Test Coverage & Baseline

### Backend Tests (`tests/test_financial_core.py`)
- `test_credit_debit_and_balance` - Basic balance calculation
- `test_revert_restores_balance_without_deleting_original` - Reversal integrity
- `test_ai_low_confidence_does_not_post` - AI threshold enforcement
- `test_ai_retry_same_upload_does_not_double_post` - Idempotency (uses different keys!)

### AI Tests (`ai/tests/`)
- `test_contracts.py` - Schema validation
- `test_duplicate.py` - Duplicate detection
- `test_extraction.py` - Field extraction
- `test_integration.py` - Full pipeline
- `test_matching.py` - Student matching
- `test_ocr.py` - OCR accuracy
- `test_verification.py` - Verification logic

## 7. Backup/Recovery Strategy

### Before Any Modification:
1. **Git stash** current working tree (no tracked changes, but untracked artifacts exist)
2. **Copy** entire `class-fund-backend-v0.1` directory to backup location
3. **Copy** entire `classfund` directory to backup location
4. **Copy** `ai` directory to backup location
5. **Record** current HEAD commit hash: `2d20a50`

### For Database Migrations:
- Use isolated test databases (sqlite in-memory for unit tests)
- Never run destructive migrations against production
- Create new alembic revisions for any schema changes
- Test migrations forward and backward

### For Financial Functions:
- Run existing tests before and after each change
- Add regression tests for any defect fixed
- Verify balance calculation consistency
- Verify no double-posting under concurrent/retried scenarios

## 8. Critical Gaps Identified (Pre-Workstream)

| Workstream | Gap | Severity |
|------------|-----|----------|
| A - Idempotency | `retry_count` in key makes retries unstable; HTTPException not recovered | CRITICAL |
| B - Exception Contract | No deterministic result enum; None return used for success/failure | CRITICAL |
| C - Database Integrity | No message table; no recall tokens; worker lease schema missing | HIGH |
| D - Financial Gatekeeper | Preserved but idempotency unstable | HIGH |
| E - Recall Auth | No tokens; no authorization; race condition during processing | CRITICAL |
| F - Persistent Worker | Celery/Redis requires online Redis; no Supabase polling worker | CRITICAL |
| G - Vision Adapter | No Ollama client; no vision model integration | HIGH |
| H - Supabase | No Supabase client; no RLS; local filesystem storage | HIGH |
| I - Frontend | Mock only; no API integration; no status polling | HIGH |
| J - Testing | Missing concurrent, crash recovery, recall race tests | HIGH |

## 9. Phase 1.2 Artifacts To Create

00. `PHASE_1_2_AUTHORIZATION_AND_SCOPE.md`
01. `INITIAL_REPOSITORY_PREFLIGHT.md` (this file)
02. `PHASE_1_1_1_FINDINGS_TRACEABILITY.md`
03. `IDEMPOTENCY_IMPLEMENTATION.md`
04. `EXCEPTION_AND_RESULT_CONTRACT.md`
05. `DATABASE_INTEGRITY_AND_MIGRATIONS.md`
06. `FINANCIAL_GATEKEEPER_REMEDIATION.md`
07. `RECALL_AUTHORIZATION_AND_REVERSAL.md`
08. `PERSISTENT_WORKER_IMPLEMENTATION.md`
09. `VISION_OLLAMA_ADAPTER.md`
10. `SUPABASE_ADAPTER_IMPLEMENTATION.md`
11. `FRONTEND_INTEGRATION.md`
12. `SECURITY_AND_RLS_AUDIT.md`
13. `TEST_PLAN_AND_RESULTS.md`
14. `REGRESSION_REPORT.md`
15. `BLOCKER_CLOSURE_REGISTER.md`
16. `REMAINING_GAPS_AND_EXTERNAL_DEPENDENCIES.md`
17. `PHASE_1_2_FINAL_REPORT.md`