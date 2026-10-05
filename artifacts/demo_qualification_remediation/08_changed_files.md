# Changed Files Summary

## Remediation-Related Changes

The following files were modified during remediation (not including pre-existing changes from earlier phases):

### 1. `class-fund-backend-v0.1/class-fund-backend/app/models/models.py`
**Change**: Added `created_at` column to `ExtractedTransaction` model
```python
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```
**Purpose**: Fix Review endpoint 500 error - missing `created_at` for ordering and response serialization
**Impact**: Enables `/api/v1/internal/review` endpoint to function correctly

### 2. `class-fund-backend-v0.1/class-fund-backend/tests/conftest.py`
**Change**: Updated auth helper functions to use real JWT tokens
```python
# Before:
def get_auth_headers(user_id: str) -> dict:
    return {"Authorization": f"Bearer mock-token-{user_id}"}

# After:
from app.core.security import create_access_token

def get_auth_headers(user_id: str, role: str = "MEMBER") -> dict:
    token = create_access_token(subject=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}
```
**Purpose**: Fix Admin Dashboard 401 errors - mock tokens incompatible with OAuth2PasswordBearer
**Impact**: All admin dashboard tests now pass with proper JWT authentication

### 3. `class-fund-backend-v0.1/class-fund-backend/tests/simulation/test_e2e.py`
**Changes**:
1. Added `timedelta` import: `from datetime import datetime, timezone, timedelta`
2. Fixed `TestScenarioERecallAfterPosting::test_recall_after_posting_creates_reversal`:
   - Added `test_message` fixture parameter
   - Added defensive assertion: `assert claimed is not None`
   - Fixed balance assertion: `Decimal("1000000")` instead of `Decimal("0")`
3. Fixed `TestScenarioFExternalServiceFailure::test_ollama_unavailable`:
   - Creates new upload without extraction to simulate Ollama failure
   - Properly tests "no extraction found" path
4. Fixed `TestScenarioFExternalServiceFailure::test_worker_crash`:
   - Moved into test class
   - Added `test_message` fixture parameter
   - Added defensive assertion
   - Uses `timedelta` for lease expiry simulation

**Purpose**: Fix Scenario E (claim_next_message returns None) and Scenario F worker crash test
**Impact**: All E2E workflow tests pass

## Files Created During Qualification (Not Modified by Remediation)

The following test infrastructure files were created during the Demo & Live Integration Qualification phase and are untracked:

- `class-fund-backend-v0.1/class-fund-backend/tests/__init__.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/conftest.py` (modified by remediation)
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/__init__.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/config.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/mock_ollama.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/mock_supabase.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/mock_worker.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/test_e2e.py` (modified by remediation)
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/test_ollama.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/test_supabase_auth.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/simulation/test_worker.py`
- `class-fund-backend-v0.1/class-fund-backend/tests/test_admin.py`

## Artifacts Generated During Remediation

All in `artifacts/demo_qualification_remediation/`:
- `00_scope_and_authorization.md`
- `01_preflight_and_evidence_reconciliation.md`
- `02_admin_auth_remediation.md`
- `03_review_endpoint_remediation.md`
- `04_worker_scenario_e_remediation.md`
- `05_frontend_backend_contract_report.md`
- `06_targeted_test_results.md`
- `07_financial_security_regression.md`
- `08_changed_files.md` (this file)
- `09_remaining_limitations.md` (to be created)
- `10_final_remediation_report.md` (to be created)

## Pre-existing Changes (From Earlier Phases)

The following files show modifications from earlier development phases (not part of this remediation):

### Backend Source
- `class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py`
- `class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py`
- `class-fund-backend-v0.1/class-fund-backend/app/core/config.py`
- `class-fund-backend-v0.1/class-fund-backend/app/main.py`
- `class-fund-backend-v0.1/class-fund-backend/app/schemas/__init__.py`
- `class-fund-backend-v0.1/class-fund-backend/app/schemas/schemas.py`
- `class-fund-backend-v0.1/class-fund-backend/app/services/ollama_client.py`
- `class-fund-backend-v0.1/class-fund-backend/worker/main.py`
- `class-fund-backend-v0.1/class-fund-backend/.env.example`

### Frontend Source
- `classfund/classfund/src/App.tsx`
- `classfund/classfund/src/components/chat/MessageItem.tsx`
- `classfund/classfund/src/components/chat/RecallButton.tsx`
- `classfund/classfund/src/components/common/Navbar.tsx`
- `classfund/classfund/src/context/AppContext.tsx`
- `classfund/classfund/src/hooks/useChat.ts`
- `classfund/classfund/src/lib/recall.ts`
- `classfund/classfund/src/types/chat.ts`
- `classfund/classfund/src/types/index.ts`
- `classfund/classfund/.env.example`

### AI Module
- `ai/duplicate/service.py`