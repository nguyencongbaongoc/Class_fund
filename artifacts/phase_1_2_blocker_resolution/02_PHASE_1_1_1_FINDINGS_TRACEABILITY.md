# 02_PHASE_1_1_1_FINDINGS_TRACEABILITY.md

## Source-to-Artifact Traceability Matrix

This document maps every actionable finding from Phase 0, Phase 1, Phase 1.1, and Phase 1.1.1 to the specific source code locations and the Phase 1.2 workstream responsible for resolution.

## Phase 0 Findings

| Phase 0 Artifact | Finding | Source Location | Workstream | Status |
|------------------|---------|-----------------|------------|--------|
| `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | Celery/Redis requires Redis running; incompatible with PC offline | `ai/worker/queue.py` lines 27-46, 85-105 | F - Persistent Worker | BLOCKED |
| `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | No message persistence table for guest chat | Missing `messages` table | C - Database Integrity, F - Persistent Worker | BLOCKED |
| `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | No atomic claim mechanism for Supabase | Design only in audit | F - Persistent Worker | BLOCKED |
| `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | No lease expiry / crash recovery | Design only in audit | F - Persistent Worker | BLOCKED |
| `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | No worker heartbeat / status table | Design only in audit | F - Persistent Worker | BLOCKED |
| `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | No dead letter / human review state | Design only in audit | F - Persistent Worker | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No guest authentication (photo + name) | `ChatView.tsx`, `AppContext.tsx` | C - Database, I - Frontend | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No inline photo capture in chat | `ChatView.tsx` lines 190-197 | I - Frontend | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No UUID message IDs (timestamp-based) | `AppContext.tsx` line 452 | C - Database, I - Frontend | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No public message codes | Missing | C - Database | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No message status tracking | `src/types/index.ts` - ChatMessage lacks status | C - Database, I - Frontend | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No recall tokens | Missing | E - Recall Auth | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No recall authorization (anyone can revert) | `AppContext.tsx` line 310-315 | E - Recall Auth | CRITICAL |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | Race condition: recall during processing | No lease mechanism | E - Recall Auth | CRITICAL |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No guest message → transaction linkage | `models.py` - ChatMessage.ledger_entry_id indirect | C - Database, D - Gatekeeper | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No Supabase Storage for photos | `uploads.py` uses local filesystem | H - Supabase | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No realtime status updates | Missing Supabase Realtime | I - Frontend | BLOCKED |
| `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | No Ollama/Vision integration | `ai/worker/queue.py` uses Tesseract only | G - Vision Adapter | BLOCKED |

## Phase 1 Contracts (Design Only - Not Implemented)

| Phase 1 Artifact | Contract | Implementation Status | Workstream |
|------------------|----------|----------------------|------------|
| `02_SUPABASE_SCHEMA.md` | Messages table with status, lease, recall_token | Not implemented | C - Database |
| `03_MESSAGE_CONTRACT.md` | Message lifecycle states | Not implemented | C - Database, F - Worker |
| `05_RLS_SECURITY.md` | RLS policies for messages, transactions | Not implemented | H - Supabase |
| `08_LOCAL_WORKER.md` | Supabase polling worker design | Not implemented | F - Persistent Worker |
| `09_OLLAMA_ADAPTER.md` | Vision adapter interface | Not implemented | G - Vision Adapter |
| `11_FINANCIAL_GATEKEEPER.md` | Idempotency key format `msg_{message.id}_attempt_{retry_count}` | **UNSTABLE DESIGN** | A - Idempotency |
| `12_RECALL_SAFETY.md` | Recall token + atomic check before posting | Not implemented | E - Recall Auth |

## Phase 1.1 Contract Review Gaps

| Phase 1.1 Artifact | Gap | Source Evidence | Workstream |
|---------------------|-----|-----------------|------------|
| `03_IMPLEMENTATION_STATUS_MATRIX.md` | Message persistence: 0% implemented | `models.py` - no messages table | C - Database |
| `03_IMPLEMENTATION_STATUS_MATRIX.md` | Worker: 0% implemented (Celery only) | `ai/worker/queue.py` - Celery/Redis | F - Persistent Worker |
| `03_IMPLEMENTATION_STATUS_MATRIX.md` | Vision/Ollama: 0% implemented | `ai/` - Tesseract only | G - Vision Adapter |
| `03_IMPLEMENTATION_STATUS_MATRIX.md` | Supabase: 0% implemented | No Supabase client | H - Supabase |
| `03_IMPLEMENTATION_STATUS_MATRIX.md` | Recall: 0% implemented | `ledger.py` - only post_revert for authenticated users | E - Recall Auth |
| `04_DATABASE_CONTRACT_REVIEW.md` | Missing unique constraints for idempotency | `models.py` IdempotencyKey.key unique ✅ | A - Idempotency |
| `04_DATABASE_CONTRACT_REVIEW.md` | Missing message table constraints | Not in schema | C - Database |
| `07_WORKER_RELIABILITY_REVIEW.md` | Worker crash recovery not implemented | Celery relies on Redis | F - Persistent Worker |
| `07_WORKER_RELIABILITY_REVIEW.md` | Lease expiration not implemented | Design only | F - Persistent Worker |
| `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` | Retry count in key breaks idempotency | `11_FINANCIAL_GATEKEEPER.md` line 32 | A - Idempotency |
| `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` | No recovery from ambiguous commit | `ledger.py` - HTTPException not caught | A - Idempotency, B - Exception Contract |
| `09_RECALL_AND_REVERSAL_REVIEW.md` | Recall before post not protected | `verify_and_post_from_ai()` no message status check | E - Recall Auth |
| `10_AI_CONTRACT_REVIEW.md` | No vision model integration | `ai/extraction/service.py` - regex only | G - Vision Adapter |
| `11_FRONTEND_REALTIME_CONTRACT_REVIEW.md` | Frontend uses mock data only | `AppContext.tsx` - all mock | I - Frontend |

## Phase 1.1.1 Forensic Corrections (Verified from Source)

| Artifact | Corrected Finding | Source Location | Workstream | Resolution Required |
|----------|-------------------|-----------------|------------|---------------------|
| `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | Fingerprint does NOT include message.id or retry_count | `ledger.py` lines 39-40, 70-73 | A - Idempotency | Stable key format needed |
| `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | Design proposes unstable key `msg_{message.id}_attempt_{retry_count}` | `11_FINANCIAL_GATEKEEPER.md` line 32 | A - Idempotency | Reject unstable format |
| `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | Retry with different key → HTTPException(409) not recovered | `ledger.py` lines 80-86, 172-242 | A - Idempotency, B - Exception Contract | Deterministic result enum |
| `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | verify_and_post_from_ai() catches only IntegrityError | `ledger.py` line 236 | B - Exception Contract | Catch HTTPException |
| `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | No mapping from duplicate exception to existing tx | `ledger.py` - no recovery mechanism | A - Idempotency | Recovery mechanism |
| `05_FINANCIAL_INVARIANT_ASSESSMENT.md` | Exactly-once claim UNVERIFIED / BLOCKED | `ledger.py` - unstable key breaks it | A - Idempotency | Stable idempotency |
| `05_FINANCIAL_INVARIANT_ASSESSMENT.md` | Idempotency identity BLOCKED (unstable key) | `ledger.py` + design | A - Idempotency | Fix key format |
| `05_FINANCIAL_INVARIANT_ASSESSMENT.md` | Recall/reversal auth: DESIGNED but BLOCKED | `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | E - Recall Auth | Implement tokens + auth |
| `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | Recall token design missing from source | Not in `models.py` or `ledger.py` | E - Recall Auth | Add recall_token_hash |
| `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | Race condition: no atomic status check before post | `verify_and_post_from_ai()` line 177-179 | E - Recall Auth | SELECT FOR UPDATE |
| `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | Double-revert protected in backend | `ledger.py` lines 134-138 ✅ | E - Recall Auth | Verified |
| `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | Frontend recall has NO authorization | `AppContext.tsx` line 310-315 | E - Recall Auth, I - Frontend | Add token validation |
| `07_PHASE_1_1_CORRECTION_REGISTER.md` | 12 corrections to Phase 1.1 claims | Various | All | Apply corrections |

## Workstream Mapping Summary

| Workstream | Phase 0 Findings | Phase 1 Contracts | Phase 1.1 Gaps | Phase 1.1.1 Corrections | Total Items |
|------------|------------------|-------------------|----------------|-------------------------|-------------|
| A - Idempotency | 0 | 1 | 1 | 3 | 5 |
| B - Exception Contract | 0 | 0 | 0 | 2 | 2 |
| C - Database Integrity | 6 | 2 | 2 | 0 | 10 |
| D - Financial Gatekeeper | 1 | 0 | 0 | 1 | 2 |
| E - Recall Auth | 4 | 1 | 1 | 4 | 10 |
| F - Persistent Worker | 6 | 1 | 2 | 0 | 9 |
| G - Vision Adapter | 1 | 1 | 1 | 0 | 3 |
| H - Supabase | 1 | 1 | 0 | 0 | 2 |
| I - Frontend | 5 | 0 | 1 | 1 | 7 |
| J - Testing | 0 | 0 | 0 | 0 | N/A |

## Resolution Priority Order

1. **CRITICAL - Financial Integrity**: A (Idempotency), B (Exception Contract), D (Gatekeeper)
2. **CRITICAL - Security**: E (Recall Auth) - anyone can revert
3. **CRITICAL - Offline Operation**: F (Persistent Worker) - PC offline survival
4. **HIGH - Data Persistence**: C (Database), H (Supabase)
5. **HIGH - AI Integration**: G (Vision Adapter)
6. **HIGH - User Experience**: I (Frontend)
7. **COMPREHENSIVE**: J (Testing) - spans all

## Key Source Files to Modify

### Backend (`class-fund-backend-v0.1/class-fund-backend/app/`)
| File | Workstreams | Changes Needed |
|------|-------------|----------------|
| `models.py` | C, E | Add `Message`, `RecallToken`, `WorkerStatus` tables; add `message_id` to `Transaction` |
| `ledger.py` | A, B, D, E | Fix idempotency key, add result enum, add recall check before post |
| `api/routes/ai_internal.py` | A, B, E | Pass message_id, handle new result contract |
| `api/routes/public.py` | I | Add message status endpoints |
| `api/routes/uploads.py` | H | Supabase Storage integration |
| `api/routes/chat.py` | I, E | Guest message + recall endpoints |
| `db/session.py` | F | Support Supabase pool |
| `core/config.py` | G, H | Ollama + Supabase settings |

### Frontend (`classfund/classfund/src/`)
| File | Workstreams | Changes Needed |
|------|-------------|----------------|
| `views/ChatView.tsx` | I, E | Inline photo, name input, status badges, recall button |
| `context/AppContext.tsx` | I | Replace mock with API calls |
| `types/index.ts` | C, I | Add status, recall_token to ChatMessage |
| `views/UploadReceiptView.tsx` | I, H | Integrate with chat message flow |

### AI (`ai/`)
| File | Workstreams | Changes Needed |
|------|-------------|----------------|
| `worker/queue.py` | F | Replace Celery with Supabase polling worker |
| `contracts.py` | B, G | Add ProcessingResult enum, Vision result types |
| `extraction/service.py` | G | Add Ollama vision fallback |
| `verification/service.py` | B, G | Return deterministic result |

### New Files Needed
| File | Workstream | Purpose |
|------|------------|---------|
| `worker/main.py` | F | Supabase polling worker entry |
| `worker/claim.py` | F | Atomic claim with FOR UPDATE SKIP LOCKED |
| `worker/heartbeat.py` | F | Worker status updates |
| `services/supabase_client.py` | H | Supabase admin client |
| `services/ollama_client.py` | G | Vision model client |
| `alembic/versions/xxxx_add_messages.py` | C | Messages table migration |
| `alembic/versions/xxxx_add_worker_status.py` | C, F | Worker status table migration |
| `alembic/versions/xxxx_add_recall_tokens.py` | C, E | Recall token table migration |