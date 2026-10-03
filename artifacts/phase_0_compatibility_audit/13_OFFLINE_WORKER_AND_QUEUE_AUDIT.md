# PHASE 0 ADDENDUM — OFFLINE WORKER AND QUEUE AUDIT

## Executive Summary
**Status: NOT_IMPLEMENTED** — No worker exists that can operate offline and resume. The current Celery/Redis queue in `ai/worker/queue.py` requires Redis server and cannot run on a Windows PC that may be OFF. A Supabase-polling worker must be built.

---

## 1. MESSAGE LIFECYCLE SUPPORT

### Required Lifecycle
```
pending
   |
   v
processing
   |
   +----> awaiting_admin
   |
   +----> processed
   |
   +----> failed
```

### Current Implementation: **NONE**

| State | Current Support | Evidence |
|-------|-----------------|----------|
| `pending` | ❌ No message queue table | Frontend only has mock `chatMessages` |
| `processing` | ❌ No worker | `ai/worker/queue.py` has Celery task but no deployment |
| `awaiting_admin` | ❌ No status | `UploadStatus.NEEDS_REVIEW` exists but only for uploads |
| `processed` | ❌ No completion tracking | Frontend simulates; no persistence |
| `failed` | ❌ No error handling | Celery has retry but no dead letter |

---

## 2. EXISTING QUEUE MECHANISMS

### Celery + Redis (`ai/worker/queue.py`)

```python
# QueueConfig
redis_url: str = "redis://localhost:6379/0"
queue_name: str = "verification_jobs"
max_retries: int = 3
retry_delay: int = 60
task_timeout: int = 300

# Celery app with Redis broker/result backend
celery_app = Celery("verification_worker")
celery_app.conf.update(broker_url=redis_url, result_backend=redis_url, ...)

# VerificationTask with auto-retry
class VerificationTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 3

@celery_app.task(bind=True, base=VerificationTask)
def process_verification_task(self, upload_id, image_data_hex, metadata):
    # Runs VerificationService.verify()
```

### Assessment for Hybrid

| Requirement | Celery/Redis | Verdict |
|-------------|--------------|---------|
| **Runs on Windows PC** | ✅ Yes (Celery runs on Windows) | Compatible |
| **Works when PC OFF** | ❌ No — Redis must be running | **BLOCKER** |
| **No cloud Redis** | ❌ Requires Redis server | **BLOCKER** |
| **Persists jobs** | ✅ Redis persists queue | But Redis unavailable when PC off |
| **Atomic claim** | ✅ Celery reserves tasks | Workers compete fairly |
| **Retry/backoff** | ✅ Built-in | Good |
| **Timeout** | ✅ 300s task timeout | Good |
| **Worker heartbeat** | ⚠️ Celery events only | No persistent status table |
| **Multiple workers** | ✅ Supported | Good |
| **Job recovery** | ✅ Redis retains queue | But only if Redis running |

**Conclusion**: Celery/Redis is **architecturally incompatible** with "PC may be OFF" requirement because Redis must be continuously available.

---

## 3. SUPABASE POLLING WORKER DESIGN

### Why Supabase Polling?

| Factor | Celery/Redis | Supabase Polling |
|--------|--------------|------------------|
| **Persistence when PC off** | ❌ Redis down = queue down | ✅ Supabase always up |
| **No external deps** | ❌ Requires Redis | ✅ Only PostgreSQL |
| **Atomic claim** | ✅ Celery internal | ✅ `UPDATE ... FOR UPDATE SKIP LOCKED` |
| **Worker status** | ⚠️ Celery inspect | ✅ `worker_status` table |
| **Lease expiration** | ⚠️ Task timeout | ✅ DB-level `lease_expires_at` |
| **Dead letter** | ⚠️ Manual | ✅ `status='failed'` + retry count |

### Required Supabase Tables

```sql
-- Messages table (extends chat_messages with AI fields)
CREATE TABLE messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL,
    sender_id uuid NOT NULL REFERENCES auth.users(id),
    content text NOT NULL,
    message_type varchar(50) NOT NULL DEFAULT 'TEXT',
    status varchar(30) NOT NULL DEFAULT 'pending',  -- pending, processing, awaiting_admin, processed, failed
    ai_intent varchar(50),
    ai_result jsonb,
    ai_confidence numeric(5,4),
    transaction_id uuid REFERENCES transactions(id),
    error_message text,
    retry_count int DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    claimed_at timestamptz,
    lease_expires_at timestamptz,
    processed_at timestamptz
);

CREATE INDEX idx_messages_status_created ON messages(status, created_at) WHERE status = 'pending';
CREATE INDEX idx_messages_conversation ON messages(conversation_id);

-- Worker status table
CREATE TABLE worker_status (
    worker_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status varchar(20) NOT NULL DEFAULT 'offline',
    model_name varchar(100),
    last_heartbeat timestamptz,
    last_processed_at timestamptz,
    current_job_id uuid REFERENCES messages(id),
    metadata jsonb DEFAULT '{}'
);
```

---

## 4. ATOMIC MESSAGE CLAIMING

### Critical: Must Be Atomic

```sql
-- Single atomic claim with lease
WITH claimed AS (
    UPDATE messages
    SET status = 'processing',
        worker_id = $1,
        claimed_at = now(),
        lease_expires_at = now() + interval '5 minutes'
    WHERE id = (
        SELECT id FROM messages
        WHERE status = 'pending'
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    RETURNING *
)
SELECT * FROM claimed;
```

### Why `FOR UPDATE SKIP LOCKED`?

| Scenario | Without SKIP LOCKED | With SKIP LOCKED |
|----------|---------------------|------------------|
| 2 workers race | One blocks, waits for lock | Both proceed, each gets different row |
| Deadlock risk | High | None |
| Throughput | Serialized | Parallel |

**Supabase Support**: ✅ PostgreSQL 15+ supports `FOR UPDATE SKIP LOCKED`

---

## 5. CONCURRENT WORKER PROTECTION

### Current: Celery Prefetch
```python
worker_prefetch_multiplier=1  # One task per worker at a time
task_acks_late=True           # Acknowledge after completion
task_reject_on_worker_lost=True  # Requeue if worker dies
```

### Supabase Equivalent
- `worker_prefetch_multiplier=1` → Worker claims ONE message at a time
- `task_acks_late` → Update status to `processed`/`failed` ONLY after successful completion
- `task_reject_on_worker_lost` → Lease expiration re-claims message

### Lease Expiration Recovery
```sql
-- Reclaim stale processing messages (run periodically or on worker startup)
UPDATE messages
SET status = 'pending',
    worker_id = NULL,
    claimed_at = NULL,
    lease_expires_at = NULL
WHERE status = 'processing'
  AND lease_expires_at < now();
```

**Run on**: Worker startup + periodic cron (every 30s)

---

## 6. DUPLICATE PROCESSING PREVENTION

### Current Backend: Idempotency Keys
```python
# ledger.py:70-73
fingerprint = _make_request_fingerprint([
    account.id, type_.value, str(amount), currency, source.value,
    transaction_code or "", bank_account_id or "", upload_id or "",
])
existing_response = check_idempotency(db, idempotency_key, fingerprint)
```

### Worker Must Pass Idempotency Key
```python
# When claiming message, generate deterministic idempotency key
idempotency_key = f"msg_{message.id}_attempt_{message.retry_count}"

# Pass to verify_and_post_from_ai()
tx = verify_and_post_from_ai(db, upload, extraction, account=account,
                             actor_id=worker_id, idempotency_key=idempotency_key)
```

### Duplicate Message Detection
```sql
-- Prevent duplicate messages from frontend
CREATE UNIQUE INDEX idx_messages_idempotency 
ON messages (sender_id, conversation_id, content, created_at)
WHERE status IN ('pending', 'processing');
-- Or use client-generated idempotency key column
```

---

## 7. WORKER CRASH RECOVERY

### Current Celery: Automatic Retry
```python
autoretry_for = (Exception,)
retry_backoff = True
retry_backoff_max = 600
max_retries = 3
```

### Supabase Worker Recovery Logic

```python
class SupabaseWorker:
    def __init__(self, worker_id: str, supabase_url: str, service_key: str):
        self.worker_id = worker_id
        self.supabase = create_client(supabase_url, service_key)
        self.db_engine = create_engine(database_url, pool_size=2, ...)
    
    def startup(self):
        # 1. Reclaim stale leases from previous runs
        self.reclaim_stale_leases()
        
        # 2. Register worker status
        self.upsert_worker_status(status='online')
        
        # 3. Start heartbeat
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
    
    def reclaim_stale_leases(self):
        with Session(self.db_engine) as db:
            db.execute(text("""
                UPDATE messages
                SET status = 'pending', worker_id = NULL, claimed_at = NULL, lease_expires_at = NULL
                WHERE status = 'processing' AND lease_expires_at < now()
            """))
            db.commit()
    
    async def heartbeat_loop(self):
        while self.running:
            self.upsert_worker_status(status='online', last_heartbeat=now())
            await asyncio.sleep(10)
    
    def poll_and_process(self):
        while self.running:
            msg = self.claim_next_message()
            if msg:
                self.process_message(msg)
            else:
                time.sleep(5)  # Backoff when empty
    
    def claim_next_message(self) -> Message | None:
        with Session(self.db_engine) as db:
            result = db.execute(text("""
                UPDATE messages
                SET status = 'processing', worker_id = :wid, claimed_at = now(),
                    lease_expires_at = now() + interval '5 minutes'
                WHERE id = (
                    SELECT id FROM messages
                    WHERE status = 'pending'
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
            """), {"wid": self.worker_id}).mappings().first()
            return result
    
    def process_message(self, msg: Message):
        try:
            # Download receipt if present
            if msg.message_type == 'RECEIPT':
                image_bytes = self.download_receipt(msg.ai_result.get('storage_path'))
                result = self.verification_service.verify(msg.id, image_bytes)
                
                if result.status == VerificationStatus.NEEDS_REVIEW:
                    self.update_message_status(msg.id, 'awaiting_admin', result)
                elif result.status == VerificationStatus.VERIFIED:
                    self.post_to_ledger(msg, result)
                    self.update_message_status(msg.id, 'processed', result)
                else:
                    self.update_message_status(msg.id, 'failed', result)
            else:
                # Handle chat intents (balance, withdrawal, etc.)
                self.handle_chat_intent(msg)
        except Exception as e:
            self.handle_failure(msg, e)
    
    def handle_failure(self, msg: Message, error: Exception):
        retry_count = msg.retry_count + 1
        if retry_count >= 3:
            self.update_message_status(msg.id, 'failed', error_message=str(error))
        else:
            # Reset to pending for retry
            self.reset_to_pending(msg.id, retry_count, str(error))
```

---

## 8. RETRY BEHAVIOR

### Current: Celery Exponential Backoff
```python
retry_backoff = True      # 2^retry * base_delay
retry_backoff_max = 600   # Max 10 minutes
retry_jitter = True       # Add randomness
```

### Supabase Equivalent
```python
def reset_to_pending(self, msg_id: str, retry_count: int, error: str):
    delay = min(2 ** retry_count * 60, 600)  # Exponential backoff, max 10 min
    delay += random.randint(0, 30)  # Jitter
    
    with Session(self.db_engine) as db:
        db.execute(text("""
            UPDATE messages
            SET status = 'pending', worker_id = NULL, claimed_at = NULL,
                lease_expires_at = NULL, retry_count = :rc, error_message = :err
            WHERE id = :id
        """), {"id": msg_id, "rc": retry_count, "err": error})
        db.commit()
    
    # Schedule re-poll after delay (or rely on next poll cycle)
```

---

## 9. MESSAGE ORDERING

### Requirement
- Messages in same conversation processed FIFO
- Cross-conversation can be parallel

### Implementation
```sql
-- Index for ordering
CREATE INDEX idx_messages_conversation_status_created 
ON messages(conversation_id, status, created_at);

-- Claim logic per conversation (simplified: global FIFO)
-- For strict per-conversation ordering:
WITH next_per_conversation AS (
    SELECT DISTINCT ON (conversation_id) id
    FROM messages
    WHERE status = 'pending'
    ORDER BY conversation_id, created_at
)
UPDATE messages
SET ...
WHERE id IN (SELECT id FROM next_per_conversation LIMIT 1);
```

---

## 10. DEAD LETTER HANDLING

### Current: None

### Required
```python
def update_message_status(self, msg_id: str, status: str, result: VerificationResult | None = None, error: str | None = None):
    with Session(self.db_engine) as db:
        updates = {"status": status, "processed_at": datetime.now(timezone.utc)}
        if result:
            updates["ai_result"] = result.model_dump()
            updates["ai_confidence"] = result.confidence
            updates["ai_intent"] = result.ai_intent
            if result.transaction_id:
                updates["transaction_id"] = result.transaction_id
        if error:
            updates["error_message"] = error
        
        db.execute(
            update(Messages)
            .where(Messages.id == msg_id)
            .values(**updates)
        )
        db.commit()
    
    # Emit realtime event
    self.supabase.table('messages').update(updates).eq('id', msg_id).execute()
```

### Dead Letter Query
```sql
-- Admin review queue
SELECT * FROM messages 
WHERE status = 'awaiting_admin' 
ORDER BY created_at;

-- Failed messages for debugging
SELECT * FROM messages 
WHERE status = 'failed' 
ORDER BY processed_at DESC;
```

---

## 11. IDEMPOTENCY ACROSS RESTARTS

### Critical: Same Message Must Not Process Twice

| Layer | Mechanism |
|-------|-----------|
| **Message claim** | Atomic `UPDATE ... FOR UPDATE SKIP LOCKED` — only one worker gets it |
| **Processing** | `lease_expires_at` — if worker dies, lease expires, another claims |
| **Ledger posting** | Backend `IdempotencyKey` table with fingerprint — prevents duplicate transactions |
| **Message status** | `status` transitions: `pending` → `processing` → `processed/failed/awaiting_admin` — never back to `pending` without incrementing `retry_count` |

### Idempotency Key Format
```python
# Deterministic per message + attempt
idempotency_key = f"worker_{self.worker_id}_msg_{msg.id}_attempt_{msg.retry_count}"
# Passed to verify_and_post_from_ai()
```

---

## 12. BACKLOG PROCESSING ON STARTUP

### Current: Celery Replays Queue
- Redis retains messages
- Workers consume on startup

### Supabase: Poll Pending on Startup
```python
def startup(self):
    self.reclaim_stale_leases()
    self.upsert_worker_status('online')
    
    # Process all pending immediately (with concurrency limit)
    while self.running:
        msg = self.claim_next_message()
        if not msg:
            break
        self.process_message(msg)
    
    # Then enter normal polling loop
    self.poll_loop()
```

---

## 13. MULTIPLE WORKER INSTANCES

### Current: Celery Supports Multiple Workers
```bash
celery -A ai.worker.queue worker -Q verification -c 1  # Run multiple
```

### Supabase: Multiple Workers Supported
- Each worker has unique `worker_id` (UUID)
- Atomic claim ensures no double-processing
- `worker_status` table tracks each worker
- Heartbeat detects dead workers

### Coordination
```sql
-- View active workers
SELECT * FROM worker_status 
WHERE status = 'online' 
  AND last_heartbeat > now() - interval '30 seconds';
```

---

## 14. WORKER HEARTBEAT

### Current: Celery Events
- `worker_ready`, `task_success`, `task_failure` signals
- No persistent status

### Supabase: Persistent Heartbeat
```python
async def heartbeat_loop(self):
    while self.running:
        try:
            self.supabase.table('worker_status').upsert({
                'worker_id': self.worker_id,
                'status': 'online',
                'last_heartbeat': datetime.now(timezone.utc).isoformat(),
                'model_name': self.model_name,
            }).execute()
        except Exception:
            pass  # Don't crash on heartbeat failure
        await asyncio.sleep(10)

# Stale worker detection (admin or cron)
UPDATE worker_status 
SET status = 'offline' 
WHERE last_heartbeat < now() - interval '60 seconds';
```

---

## 15. COMPATIBILITY MATRIX

| Requirement | Current (Celery) | Supabase Polling | Verdict |
|-------------|------------------|------------------|---------|
| Atomic claim | ✅ | ✅ (FOR UPDATE SKIP LOCKED) | Both work |
| Persistent queue | ✅ (Redis) | ✅ (PostgreSQL) | Supabase better for offline PC |
| Lease expiration | ⚠️ Task timeout | ✅ DB timestamp | Supabase more visible |
| Retry/backoff | ✅ Built-in | ✅ Manual implementation | Both work |
| Dead letter | ⚠️ Manual | ✅ Status column | Supabase better |
| Worker status | ⚠️ Events only | ✅ Persistent table | Supabase better |
| Multiple workers | ✅ | ✅ | Both work |
| Crash recovery | ✅ Redis requeue | ✅ Lease expiration | Both work |
| Ordering | ⚠️ Per-queue | ✅ Per-conversation index | Supabase more flexible |
| Idempotency | ✅ Backend keys | ✅ Backend keys + message status | Both work |
| **PC OFF survival** | ❌ **FAILS** | ✅ **WORKS** | **SUPABASE REQUIRED** |

---

## 16. RECOMMENDATION

**Abandon Celery/Redis for hybrid architecture.** Build a lightweight Supabase-polling worker in Python that:
1. Uses `FOR UPDATE SKIP LOCKED` for atomic claims
2. Leverages existing `VerificationService` (zero changes)
3. Uses backend `verify_and_post_from_ai()` with idempotency keys
4. Maintains `worker_status` table for observability
5. Handles lease expiration on startup
6. Runs as a single Python process (no Redis, no Celery)

### Reusable Code
- `ai/verification/service.py` — **100% reusable**
- `ai/extraction/service.py` — **100% reusable**
- `ai/ocr/service.py` — **100% reusable**
- `ai/matching/service.py` — **100% reusable**
- `ai/duplicate/service.py` — **Adapter needed** (persist hashes to Supabase)
- `app/services/ledger.py` — **100% reusable** (with Supabase DB URL)

### New Code Required
- `worker/main.py` — Supabase polling loop
- `worker/db.py` — SQLAlchemy engine for Supabase
- `worker/claim.py` — Atomic claim logic
- `worker/heartbeat.py` — Status updates
- `worker/receipt_downloader.py` — Supabase Storage integration

---

## 17. CONFIDENCE ASSESSMENT

- **Verified**: Celery code analysis, PostgreSQL locking syntax, Supabase capabilities
- **Partially Verified**: Worker implementation patterns (standard patterns)
- **Assumed**: Supabase `FOR UPDATE SKIP LOCKED` performance at scale
- **Not Verified**: Actual worker deployment, long-running stability