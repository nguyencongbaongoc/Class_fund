# 08_PERSISTENT_WORKER_IMPLEMENTATION.md

## Workstream F: Persistent Worker (Supabase-backed, Offline-capable)

### Current State Analysis

**Problem**: Existing Celery/Redis worker (`ai/worker/queue.py`) requires Redis server running - incompatible with "PC may be OFF" requirement.

**Solution**: Supabase-polling worker using PostgreSQL directly:
- Atomic message claiming with `FOR UPDATE SKIP LOCKED`
- Lease-based processing with expiry
- Worker status tracking in database
- Crash recovery on startup
- No external dependencies (no Redis)

### Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Worker entry point | ✅ IMPLEMENTED | `worker/main.py` |
| Atomic message claim | ✅ IMPLEMENTED | `worker/main.py:65-85` |
| Lease management | ✅ IMPLEMENTED | `worker/main.py:65-85` |
| Stale lease recovery | ✅ IMPLEMENTED | `worker/main.py:55-62` |
| Worker status tracking | ✅ IMPLEMENTED | `worker/main.py:87-100` |
| Recall check before posting | ✅ IMPLEMENTED | `worker/main.py:105-110` |
| Exponential backoff retry | ✅ IMPLEMENTED | `worker/main.py:170-180` |
| Graceful shutdown | ✅ IMPLEMENTED | `worker/main.py:200-210` |
| Heartbeat | ✅ IMPLEMENTED | `worker/main.py:87-100` |

### Key Features

1. **Atomic Claim**: Single SQL statement claims next pending message
2. **Lease Expiry**: 5-minute lease, auto-reclaimed on worker death
3. **Recall Check**: Worker verifies `message.status != RECALLED` before processing
3. **Crash Recovery**: Startup reclaims all stale leases
4. **No Redis**: Pure PostgreSQL/Supabase
5. **Offline Survival**: Messages persist in DB, processed when worker restarts

### Database Schema (migrations 0002, 0004)

- `messages` table: `status`, `worker_id`, `claimed_at`, `lease_expires_at`, `retry_count`
- `worker_status` table: `worker_id`, `status`, `last_heartbeat`, `current_job_id`
- `transactions.message_id`: Links transaction to originating message

### Running the Worker

```bash
export WORKER_ID="worker-1"
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export LEASE_DURATION="300"
python -m worker.main
```

### Testing

- All existing financial tests pass (20/20)
- Worker logic unit tested in `test_idempotency.py` and `test_recall.py`
- Integration test needed for full worker lifecycle

### Status

| Task | Status | Evidence |
|------|--------|----------|
| Worker main loop | ✅ IMPLEMENTED | `worker/main.py` |
| Atomic claim (FOR UPDATE SKIP LOCKED) | ✅ IMPLEMENTED | `worker/main.py:65-85` |
| Lease expiry & recovery | ✅ IMPLEMENTED | `worker/main.py:55-62` |
| Worker status table | ✅ IMPLEMENTED | Migration 0002, 0004 |
| Recall check before post | ✅ IMPLEMENTED | `worker/main.py:105-110` |
| Exponential backoff | ✅ IMPLEMENTED | `worker/main.py:170-180` |
| Graceful shutdown | ✅ IMPLEMENTED | `worker/main.py:200-210` |
| Unit tests | ✅ PASSED | `tests/test_idempotency.py`, `test_recall.py` |
| Integration test | ⏳ PENDING | Requires Supabase |