# Phase 5.2 — Preflight and Baseline

## Git Status (Before Remediation)

### Current Branch
- `master`
- HEAD: `f7ac634` (Merge Phase 3 AI Pipeline + Phase 4 Guest Chat)

### Modified Files (Pre-existing)
```
ai/duplicate/__pycache__/service.cpython-312.pyc
ai/duplicate/service.py
class-fund-backend-v0.1/class-fund-backend/.env.example
class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py
class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py
class-fund-backend-v0.1/class-fund-backend/app/main.py
class-fund-backend-v0.1/class-fund-backend/app/models/models.py
class-fund-backend-v0.1/class-fund-backend/app/schemas/__init__.py
class-fund-backend-v0.1/class-fund-backend/app/schemas/schemas.py
class-fund-backend-v0.1/class-fund-backend/app/services/ollama_client.py
class-fund-backend-v0.1/class-fund-backend/worker/main.py
classfund/classfund/.env.example
classfund/classfund/src/App.tsx
classfund/classfund/src/components/chat/MessageItem.tsx
classfund/classfund/src/components/chat/RecallButton.tsx
classfund/classfund/src/components/common/Navbar.tsx
classfund/classfund/src/hooks/useChat.ts
classfund/classfund/src/lib/recall.ts
classfund/classfund/src/types/chat.ts
classfund/classfund/src/types/index.ts
```

### New Files (Pre-existing from Phase 5)
```
ai/tests/__pycache__/test_duplicate_persistence.cpython-312-pytest-9.1.1.pyc
ai/tests/__pycache__/test_review_api.cpython-312-pytest-9.1.1.pyc
ai/tests/test_duplicate_persistence.py
ai/tests/test_review_api.py
artifacts/master_consolidation/
artifacts/phase_2_merge_resolution/
artifacts/phase_3_1_4_1/
artifacts/phase_3_1_4_1_closure/
artifacts/phase_5_1_closure/
artifacts/phase_5_admin_dashboard/
artifacts/residual_blocker_closure/
class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py
class-fund-backend-v0.1/class-fund-backend/app/api/routes/admin.py
class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py
class-fund-backend-v0.1/class-fund-backend/app/schemas/admin.py
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

## Baseline Test Results (Phase 5.1)

### Backend: 24/24 Passing
| Test | Status |
|------|--------|
| test_admin_stats_aggregation | ✅ |
| test_audit_log_pagination_and_filters | ✅ |
| test_worker_health_computation | ✅ |
| test_queue_status_metrics | ✅ |
| Financial Core (4 tests) | ✅ |
| Idempotency (8 tests) | ✅ |
| Recall Authorization (8 tests) | ✅ |

### Frontend Checks
| Check | Status |
|-------|--------|
| TypeScript Strict (`npm run lint`) | ✅ PASS |
| Production Build (`npm run build`) | ✅ PASS |

## Key Source Files to Modify

### Backend
- `class-fund-backend-v0.1/class-fund-backend/app/api/routes/admin.py` — Health endpoint, worker health, CSV export endpoint
- `class-fund-backend-v0.1/class-fund-backend/app/schemas/admin.py` — Health schemas, CSV export schemas
- `class-fund-backend-v0.1/class-fund-backend/tests/test_admin.py` — New health tests, CSV export tests

### Frontend
- `classfund/classfund/src/context/AppContext.tsx` — Role normalization layer
- `classfund/classfund/src/types/index.ts` — Role types, health status types
- `classfund/classfund/src/components/common/Navbar.tsx` — Admin navigation guards
- `classfund/classfund/src/views/AdminDashboardView.tsx` — Health rendering
- `classfund/classfund/src/views/SystemMonitoringView.tsx` — Health rendering
- `classfund/classfund/src/views/AdminLedgerView.tsx` — CSV export
- `classfund/classfund/src/views/AuditLogView.tsx` — CSV export
- `classfund/classfund/src/lib/adminApi.ts` — New export endpoints, health types

## Existing Evidence to Reuse
- Phase 5 artifacts in `artifacts/phase_5_admin_dashboard/`
- Phase 5.1 closure artifacts in `artifacts/phase_5_1_closure/`
- All 24 backend tests passing
- TypeScript strict check passing
- Production build succeeding