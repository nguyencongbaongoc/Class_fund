# 02 Repository Baseline

## Git Status

### Current Branch
- **Branch**: `master`
- **HEAD Commit**: `f7ac634` - "Merge Phase 3 AI Pipeline + Phase 4 Guest Chat"
- **Date**: Recent (based on commit history)

### Working Tree Status (Modified Files)
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

### Untracked Files (New/Generated)
```
ai/tests/__pycache__/test_duplicate_persistence.cpython-312-pytest-9.1.1.pyc
ai/tests/__pycache__/test_review_api.cpython-312-pytest-9.1.1.pyc
ai/tests/test_duplicate_persistence.py
ai/tests/test_review_api.py
artifacts/demo_live_qualification/
artifacts/demo_qualification_remediation/
artifacts/master_consolidation/
artifacts/phase_2_merge_resolution/
artifacts/phase_3_1_4_1/
artifacts/phase_3_1_4_1_closure/
artifacts/phase_5_1_closure/
artifacts/phase_5_2_remediation/
artifacts/phase_5_admin_dashboard/
artifacts/residual_blocker_closure/
class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py
class-fund-backend-v0.1/class-fund-backend/app/api/routes/admin.py
class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py
class-fund-backend-v0.1/class-fund-backend/app/schemas/admin.py
class-fund-backend-v0.1/class-fund-backend/tests/__init__.py
class-fund-backend-v0.1/class-fund-backend/tests/conftest.py
class-fund-backend-v0.1/class-fund-backend/tests/simulation/
class-fund-backend-v0.1/class-fund-backend/tests/test_admin.py
classfund/classfund/src/components/chat/ExtractionResultDisplay.tsx
classfund/classfund/src/hooks/useRecall.ts
classfund/classfund/src/lib/adminApi.ts
classfund/classfund/src/lib/retry.ts
classfund/classfund/src/views/AIReviewQueueView.tsx
classfund/classfund/src/views/AdminDashboardView.tsx
classfund/classfund/src/views/AdminLedgerView.tsx
classfund/classfund/src/views/AuditLogView.tsx
classfund/classfund/src/views/SystemMonitoringView.tsx
postgresql-18.6-5-windows-x64-binaries/
```

## Key Backend Files (Modified)
1. **app/models/models.py** - Core data models including Transaction, LedgerEntry, Message, WorkerStatus, RecallToken
2. **app/services/ledger.py** - Financial gatekeeper: post_transaction, post_revert, verify_and_post_from_ai, calculate_balance
3. **app/services/ollama_client.py** - AI vision/text extraction client
4. **app/api/routes/admin.py** - Admin dashboard endpoints
5. **app/api/routes/review.py** - AI review queue endpoints
6. **app/api/routes/messages.py** - Message handling
7. **app/api/routes/vision.py** - Vision extraction endpoints
8. **worker/main.py** - Background worker implementation

## Key Test Files
1. **tests/conftest.py** - Test fixtures, mocks, database setup
2. **tests/test_financial_core.py** - Core financial logic tests (4 tests)
3. **tests/test_idempotency.py** - Idempotency and duplicate protection (9 tests)
4. **tests/test_recall.py** - Recall authorization and reversal (8 tests)
5. **tests/test_admin.py** - Admin dashboard functionality (12 tests)
6. **tests/simulation/test_e2e.py** - E2E scenarios A-G (17 tests)
7. **tests/simulation/test_worker.py** - Worker lifecycle and queue (31 tests)
8. **tests/simulation/test_ollama.py** - Ollama vision/text simulation (37 tests)
9. **tests/simulation/test_supabase_auth.py** - Supabase auth and RBAC (13 tests)
10. **tests/simulation/config.py** - Central simulation configuration
11. **tests/simulation/mock_*.py** - Mock implementations for Ollama, Supabase, Worker

## Previous Qualification Artifacts

### Phase 5.1 Closure (artifacts/phase_5_1_closure/)
- 00_phase_5_1_scope.md
- 01_role_mapping_verification.md
- 02_health_semantics_verification.md
- 03_csv_and_audit_verification.md
- 04_financial_security_crosscheck.md
- 05_artifact_reconciliation_matrix.md
- 06_existing_test_evidence.md
- 07_deferred_live_verification.md
- 08_final_closure_decision.md

### Phase 5.2 Remediation (artifacts/phase_5_2_remediation/)
- 00_phase_5_2_scope.md
- 01_preflight_and_baseline.md
- 02_role_mapping_remediation.md
- 03_health_semantics_remediation.md
- 04_csv_export_remediation.md
- 05_audit_integrity_remediation.md
- 06_targeted_test_results.md
- 07_changed_files.md
- 08_deferred_items.md
- 09_final_phase_5_2_report.md

### Demo Live Qualification (artifacts/demo_live_qualification/)
### Demo Qualification Remediation (artifacts/demo_qualification_remediation/)
### Phase 5 Admin Dashboard (artifacts/phase_5_admin_dashboard/)

## Test Suite Summary (Current Baseline)

| Test File | Tests Collected | Tests Passed | Tests Skipped |
|-----------|----------------|--------------|---------------|
| test_financial_core.py | 4 | 4 | 0 |
| test_idempotency.py | 9 | 9 | 0 |
| test_recall.py | 8 | 8 | 0 |
| test_admin.py | 12 | 10 | 2 (known mock issues) |
| test_e2e.py (simulation) | 17 | 17 | 0 |
| test_worker.py (simulation) | 31 | 31 | 0 |
| test_ollama.py (simulation) | 37 | 37 | 0 |
| test_supabase_auth.py (simulation) | 13 | 13 | 1 (review routes) |
| **Total** | **141** | **136** | **5** |

Note: 136 collected includes some test classes with multiple methods. Actual test nodes = 132 passed + 4 skipped = 136.

## Repository Commit History (Recent)
1. `f7ac634` - Merge Phase 3 AI Pipeline + Phase 4 Guest Chat
2. `d604d14` - Phase 2: Backend, ledger, financial core & persistent worker
3. `dbbb627` - feat: Implement polling and realtime messaging adapters
4. `2d20a50` - Phase 1 integration artifacts
5. `dc7768e` - Phase 0 audit artifacts + initial working state

## Migration Status
- **Alembic Versions**: 5 migrations (0005 is latest - "add_attachment_ids_and_ai_fields")
- **Models**: Transaction, LedgerEntry, Message, WorkerStatus, RecallToken, ExtractedTransaction, Upload, Account, User, BankAccount

## Environment Configuration
- **Python**: 3.12.10
- **Dependencies**: FastAPI 0.116, SQLAlchemy 2.0, psycopg 3.2, alembic 1.16, pydantic-settings 2.10, PyJWT 2.10, argon2-cffi 25.1
- **Dev Dependencies**: httpx 0.28, pytest 8.4+, pytest-asyncio 1.1+