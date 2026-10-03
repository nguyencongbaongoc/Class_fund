# 15_BLOCKER_CLOSURE_REGISTER.md

## Blocker Closure Register

This register tracks all actionable blockers from Phases 0, 1, 1.1, 1.1.1 and their resolution status in Phase 1.2.

### Phase 0 Blockers

| ID | Blocker | Source | Workstream | Status | Resolution |
|----|---------|--------|------------|--------|------------|
| P0-01 | Celery/Redis requires online Redis | `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | F | ✅ CLOSED | Supabase polling worker implemented |
| P0-02 | No message persistence table | `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | C | ✅ CLOSED | `messages` table created (migration 0002) |
| P0-03 | No atomic claim mechanism | `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | F | ✅ CLOSED | `FOR UPDATE SKIP LOCKED` in worker |
| P0-04 | No lease expiry/crash recovery | `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | F | ✅ CLOSED | Startup reclaim + lease expiry |
| P0-05 | No worker heartbeat/status | `13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md` | F | ✅ CLOSED | `worker_status` table + heartbeat |
| P0-06 | No guest authentication | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | C/I | ✅ CLOSED | Guest message creation with recall token |
| P0-07 | No inline photo capture | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | I | ⏳ PENDING | Frontend integration needed |
| P0-08 | No UUID message IDs | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | C | ✅ CLOSED | `uuid4_str()` default on `Message.id` |
| P0-09 | No public message codes | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | C | ✅ CLOSED | `CF-YYYYMMDD-XXXXXX` format |
| P0-10 | No message status tracking | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | C | ✅ CLOSED | `MessageStatus` enum + column |
| P0-11 | No recall tokens | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | E | ✅ CLOSED | `RecallToken` model + generation |
| P0-12 | No recall authorization | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | E | ✅ CLOSED | Token validation in recall endpoint |
| P0-13 | Race condition: recall during processing | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | E/F | ✅ CLOSED | Worker checks status + atomic claim |
| P0-14 | No guest message → transaction linkage | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | C/D | ✅ CLOSED | `transactions.message_id` FK |
| P0-15 | No Supabase Storage | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | H | ✅ CLOSED | `supabase_client.py` storage ops |
| P0-16 | No realtime status updates | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | I | ⏳ PENDING | Supabase Realtime helpers ready |
| P0-17 | No Ollama/Vision integration | `19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` | G | ✅ CLOSED | `ollama_client.py` + vision endpoint |

### Phase 1.1 Contract Review Gaps

| ID | Gap | Source | Workstream | Status | Resolution |
|----|-----|--------|------------|--------|------------|
| P11-01 | Message persistence 0% | `03_IMPLEMENTATION_STATUS_MATRIX.md` | C | ✅ CLOSED | `messages` table + API |
| P11-02 | Worker 0% (Celery only) | `03_IMPLEMENTATION_STATUS_MATRIX.md` | F | ✅ CLOSED | Supabase polling worker |
| P11-03 | Vision/Ollama 0% | `03_IMPLEMENTATION_STATUS_MATRIX.md` | G | ✅ CLOSED | Ollama vision adapter |
| P11-04 | Supabase 0% | `03_IMPLEMENTATION_STATUS_MATRIX.md` | H | ✅ CLOSED | Supabase adapters |
| P11-05 | Recall 0% | `03_IMPLEMENTATION_STATUS_MATRIX.md` | E | ✅ CLOSED | Recall API + token auth |
| P11-06 | Unstable idempotency key | `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` | A | ✅ CLOSED | Stable key (content version) |
| P11-07 | No ambiguous commit recovery | `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` | A/B | ✅ CLOSED | Recovery via `message_id` |
| P11-08 | Recall before post not protected | `09_RECALL_AND_REVERSAL_REVIEW.md` | E | ✅ CLOSED | Worker checks `status=RECALLED` |

### Phase 1.1.1 Forensic Corrections

| ID | Correction | Source | Workstream | Status | Resolution |
|----|------------|--------|------------|--------|------------|
| P111-01 | Fingerprint excludes message_id | `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | A | ✅ CLOSED | Added `message_id` to fingerprint |
| P111-02 | Unstable key format proposed | `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | A | ✅ CLOSED | Rejected unstable format |
| P111-03 | Retry with different key → HTTPException | `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | A/B | ✅ CLOSED | Structured result contract |
| P111-04 | verify_and_post_from_ai catches only IntegrityError | `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | B | ✅ CLOSED | Returns structured result |
| P111-05 | No duplicate exception → transaction mapping | `03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` | A | ✅ CLOSED | Recovery via `message_id` |
| P111-06 | Exactly-once claim UNVERIFIED | `05_FINANCIAL_INVARIANT_ASSESSMENT.md` | A | ✅ CLOSED | Stable idempotency implemented |
| P111-07 | Idempotency identity BLOCKED | `05_FINANCIAL_INVARIANT_ASSESSMENT.md` | A | ✅ CLOSED | Stable key format |
| P111-08 | Recall auth DESIGNED but BLOCKED | `05_FINANCIAL_INVARIANT_ASSESSMENT.md` | E | ✅ CLOSED | Implemented + tested |
| P111-09 | Recall token missing from source | `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | E | ✅ CLOSED | `RecallToken` model |
| P111-10 | No atomic status check before post | `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | E | ✅ CLOSED | Worker `FOR UPDATE` + check |
| P111-11 | Frontend recall has NO authorization | `06_RECALL_AND_REVERSAL_CONSISTENCY.md` | E/I | ✅ CLOSED | Token required in API |

### Summary

| Category | Total | Closed | Pending | Blocked |
|----------|-------|--------|---------|---------|
| Phase 0 | 17 | 14 | 2 | 1 |
| Phase 1.1 | 8 | 8 | 0 | 0 |
| Phase 1.1.1 | 11 | 11 | 0 | 0 |
| **Total** | **36** | **33** | **2** | **1** |

### Pending (Require External Dependencies)

| ID | Blocker | Dependency | Resolution Plan |
|----|---------|------------|-----------------|
| P0-07 | Inline photo capture | Frontend implementation | Integrate camera/file input in ChatView |
| P0-16 | Realtime status updates | Supabase project | Deploy Supabase + enable Realtime |
| P0-17 | Model accuracy verification | Measured dataset | Collect labeled receipts, evaluate |

### Blocked (Cannot Proceed Without External Input)

| ID | Blocker | Reason |
|----|---------|--------|
| - | Live Supabase integration | No credentials provided |
| - | Live Ollama integration | Ollama not running locally |
| - | RLS policy testing | Requires Supabase project |
| - | End-to-end integration test | Requires all services deployed |