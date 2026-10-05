# Evidence Index

**Date**: 2026-10-04  
**Branch**: master  
**Base Commit**: f7ac634 (with Phase 3.1/4.1 additions)

---

## Evidence Index by Blocker

### BLOCKER 3.1.3 — Duplicate Detection Persistence

| Evidence Type | Path | Criterion |
|---------------|------|-----------|
| Implementation | `ai/duplicate/service.py:189-254` | `load_from_database()`, `persist_duplicate_data()` |
| Worker Integration | `class-fund-backend-v0.1/class-fund-backend/worker/main.py:35-68` | Startup loads duplicate data |
| Vision Endpoint | `class-fund-backend-v0.1/class-fund-backend/app/api/routes/vision.py:151-153` | Persists after high-confidence extraction |
| Migration | `class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py` | Adds perceptual_hash, field_confidences, etc. |
| Tests | `ai/tests/test_duplicate_persistence.py` (9 tests) | All 9 PASS |

---

### BLOCKER 3.1.4 — Human Review API

| Evidence Type | Path | Criterion |
|---------------|------|-----------|
| Endpoints | `class-fund-backend-v0.1/class-fund-backend/app/api/routes/review.py:76-311` | 4 endpoints: list, detail, approve, reject |
| Router Registration | `class-fund-backend-v0.1/class-fund-backend/app/main.py:42` | `app.include_router(review.router)` |
| Authorization | `review.py:19` | `require_role(OWNER_TREASURER, MODERATOR)` |
| Approval Logic | `review.py:179-270` | Confirm required, gatekeeper call, state transitions |
| Rejection Logic | `review.py:273-311` | Reason required, preserves AI data |
| Tests | `ai/tests/test_review_api.py` (15 tests) | All 15 PASS |

---

### BLOCKER 4.1.4 — Recall Security

| Evidence Type | Path | Criterion |
|---------------|------|-----------|
| Eligibility Endpoint | `class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py:234-313` | `/messages/{id}/recall-eligibility` |
| Recall Endpoint | `class-fund-backend-v0.1/class-fund-backend/app/api/routes/messages.py:165-231` | Token validation, REVERT flow |
| RecallAdapter | `classfund/classfund/src/lib/recall.ts:38-70` | `checkEligibility()` calls server |
| useRecall Hook | `classfund/classfund/src/hooks/useRecall.ts` | Eligibility check + token management |
| RecallButton | `classfund/classfund/src/components/chat/RecallButton.tsx:23-31` | Eligibility modal before confirm |
| Recall Token Lifecycle | `messages.py:176-195, 221-222` | SHA-256 hash, expiry, usage, revocation |
| After-Post Recall | `messages.py:201-214` | Calls `post_revert()` for REVERT |

---

### BLOCKER 4.1.6 — Error Handling and Safe Retry

| Evidence Type | Path | Criterion |
|---------------|------|-----------|
| Error Classification | `classfund/classfund/src/lib/retry.ts:56-182` | 9 categories, retryable/reconcile flags |
| Backoff Calculation | `classfund/classfund/src/lib/retry.ts:185-197` | Exponential + jitter, bounded |
| Retry Decision | `classfund/classfund/src/lib/retry.ts:206-224` | Max retries, RECONCILE for timeout |
| useChat Integration | `classfund/classfund/src/hooks/useChat.ts:229-357` | Stable idempotency key, retry loop |
| Idempotency Key | `useChat.ts:235-236` + `worker/main.py:175-178` | Stable key: `msg_{conv}_{ts}_{rand}` + payload hash |
| Backend Idempotency | `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py:109-117` | Fingerprint mismatch → 409 |

---

## Test Evidence

### Backend Financial (20/20 PASS)
- `tests/test_financial_core.py` (4 tests)
- `tests/test_idempotency.py` (7 tests)
- `tests/test_recall.py` (9 tests)

### AI Pipeline (132/132 PASS)
- `test_contracts.py` (12)
- `test_duplicate.py` (12)
- `test_duplicate_persistence.py` (9) — **NEW**
- `test_extraction.py` (15)
- `test_integration.py` (5)
- `test_matching.py` (11)
- `test_ocr.py` (11)
- `test_review_api.py` (15) — **NEW**
- `test_verification.py` (12)

### Frontend
- TypeScript strict: PASS
- Production build: PASS

---

## Migration & Security Artifacts

| Artifact | Path |
|----------|------|
| Migration 0005 | `class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py` |
| RLS Policies | `artifacts/residual_blocker_closure/06_rls_security_changes.md` |
| Database Schema | `artifacts/residual_blocker_closure/05_database_and_migrations.md` |
| Implementation Reports | `artifacts/residual_blocker_closure/01-04_blocker_*_implementation.md` |
| Test Results | `artifacts/residual_blocker_closure/07_targeted_test_results.md` |
| External Dependencies | `artifacts/residual_blocker_closure/08_external_dependencies.md` |
| Final Report | `artifacts/residual_blocker_closure/09_final_closure_report.md` |

---

## Phase 1 Baseline Artifacts (Accepted as Recorded)

| Artifact | Path |
|----------|------|
| Execution Baseline | `artifacts/phase_3_1_4_1/00_execution_baseline.md` |
| Blocker Inventory | `artifacts/phase_3_1_4_1/01_blocker_inventory.md` |
| Phase 3.1 Implementation | `artifacts/phase_3_1_4_1/02_phase_3_1_implementation.md` |
| AI Pipeline Contract | `artifacts/phase_3_1_4_1/03_ai_pipeline_contract.md` |
| AI Evaluation Results | `artifacts/phase_3_1_4_1/04_ai_evaluation_results.md` |
| Phase 4.1 Implementation | `artifacts/phase_3_1_4_1/05_phase_4_1_implementation.md` |
| Guest Chat API Contract | `artifacts/phase_3_1_4_1/06_guest_chat_api_contract.md` |
| Supabase Security | `artifacts/phase_3_1_4_1/07_supabase_security_and_migrations.md` |
| Financial Invariant Verification | `artifacts/phase_3_1_4_1/08_financial_invariant_verification.md` |
| Test Results | `artifacts/phase_3_1_4_1/09_test_results.md` |
| External Blockers | `artifacts/phase_3_1_4_1/10_remaining_external_blockers.md` |
| Final Execution Report | `artifacts/phase_3_1_4_1/11_final_execution_report.md` |

---

## Closure Gate Artifacts

| Artifact | Path |
|----------|------|
| Closure Scope | `artifacts/phase_3_1_4_1_closure/00_closure_scope.md` |
| Phase 3.1 Source Gate | `artifacts/phase_3_1_4_1_closure/01_phase_3_1_source_gate.md` |
| Phase 4.1 Source Gate | `artifacts/phase_3_1_4_1_closure/02_phase_4_1_source_gate.md` |
| Financial Invariant Gate | `artifacts/phase_3_1_4_1_closure/03_financial_invariant_gate.md` |
| Database & Security Gate | `artifacts/phase_3_1_4_1_closure/04_database_security_gate.md` |
| External Live Dependencies | `artifacts/phase_3_1_4_1_closure/05_external_live_dependencies.md` |
| Evidence Index | `artifacts/phase_3_1_4_1_closure/06_evidence_index.md` |
| Final Closure Decision | `artifacts/phase_3_1_4_1_closure/07_final_closure_decision.md` |