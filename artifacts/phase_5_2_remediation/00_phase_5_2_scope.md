# Phase 5.2 — Admin Dashboard Remediation Scope

## Project Context
- **Project:** CLASS_FUND_WEB
- **Phase:** 5.2 — Remediation
- **Branch:** master
- **Execution Mode:** IMPLEMENTATION + TARGETED VERIFICATION
- **Previous Phase:** Phase 5.1 Closure Gate → `PHASE_5_CLOSED_WITH_LIMITATIONS`

## Authorization Status
Phase 5.2 explicitly authorized to implement remediation for three limitation groups identified in Phase 5.1:
1. Canonical role mapping
2. Worker and system health semantics
3. CSV export and audit integrity

## Baseline — Git Status (Before Remediation)

### Modified Files (Pre-existing from Phase 5)
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

## Key Findings from Phase 5.1 (To Be Remediated)

### 1. Role Mapping Mismatch
- **Backend canonical role:** `OWNER_TREASURER` (in `Role` enum, `models.py:21`)
- **Frontend role type:** `TREASURER` (in `UserRole` type, `types/index.ts:1`)
- **No explicit mapping** in authentication flow
- Works in mock mode; may fail with live Supabase Auth

### 2. Health Semantics Gaps
- Worker health: 4 states tested (ONLINE/DEGRADED/OFFLINE/UNKNOWN) — correct
- System health: `NOT_CONFIGURED` detection fragile (string matching on exception)
- Overall status badge conflates `NOT_CONFIGURED` with `DOWN` (red)
- `/admin/health` endpoint has no dedicated test
- Frontend preserves component-level status but loses aggregate distinction

### 3. CSV Export Limitations
- Exports only current page (50 records), not complete filtered result set
- CSV escaping incomplete (quotes, newlines not escaped)
- Formula injection not addressed (`=`, `+`, `-`, `@` prefixes)
- No error handling — silent failures possible
- No "Export All" capability

### 4. Audit Integrity
- Application-level immutability only (no delete/update endpoints)
- No database-level enforcement (triggers, REVOKE DELETE, pg_audit)
- Dashboard correctly exposes no edit/delete for audit records
- REVERT history preserves original transactions

## Remediation Scope

### A. Canonical Role Mapping
- Implement explicit frontend role normalization layer
- Map backend `OWNER_TREASURER` → frontend `TREASURER` for UI compatibility
- Unknown/nonexistent roles fail closed
- Backend authorization remains authoritative

### B. Health Semantics
- Fix `NOT_CONFIGURED` detection (explicit config checks, not exception string matching)
- Distinguish overall health states: ONLINE/DEGRADED/OFFLINE/UNKNOWN/NOT_CONFIGURED
- Add `/admin/health` endpoint tests
- Frontend overall status badge reflects exact backend semantics

### C. CSV Export
- Implement "Export All" using paginated fetch or backend export endpoint
- Complete CSV escaping (quotes, commas, newlines, Unicode)
- Formula injection protection for untrusted text fields
- Legitimate negative numeric values preserved
- Error handling with user feedback, no partial files

### D. Audit Integrity
- Document application-level immutability accurately
- No unsupported database-level guarantee claimed
- Preserve read-only dashboard, authorized read endpoints

## Non-Goals (Explicitly Excluded)
- User Management CRUD
- New `/admin/users` API
- Phase 6
- Supabase live integration
- PostgreSQL production deployment
- Live Ollama qualification
- Worker deployment
- Supabase Realtime implementation
- Changes to financial posting, recall, or reversal contracts