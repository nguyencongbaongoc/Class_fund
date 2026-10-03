# PHASE 0 ADDENDUM — SUPABASE SCHEMA AND DATABASE COMPATIBILITY AUDIT

## Executive Summary
**Status: COMPATIBLE_WITH_ADAPTERS** — The existing PostgreSQL schema can work with Supabase but requires significant adapters for RLS, Realtime, Auth integration, and Storage.

---

## 1. EXISTING SCHEMA vs. PROPOSED LOGICAL ENTITIES

### Mapping Analysis

| Proposed Entity | Existing Table | Reusable? | Gaps |
|-----------------|----------------|-----------|------|
| **messages** | `chat_messages` | ✅ Yes (with extensions) | Missing: `conversation_id`, `ai_intent`, `ai_result`, `ai_confidence`, `transaction_id`, `error_message`, `processed_at`, `status` enum alignment |
| **quy_lop / fund_accounts** | `accounts` | ✅ Yes | Missing: `current_balance` (computed), `updated_at` |
| **financial_ledger** | `transactions` + `ledger_entries` | ✅ Yes | Missing: `balance_before`, `balance_after`, `idempotency_key` on ledger, `reversed_transaction_id` (exists as `original_entry_id`) |
| **worker_status** | ❌ None | ❌ Missing | New table required |

### Existing Tables Suitable for Direct Supabase Use

| Table | Supabase Ready? | Notes |
|-------|-----------------|-------|
| `users` | ⚠️ Adapter needed | Conflicts with Supabase Auth `auth.users`; must map or replace |
| `accounts` | ✅ Yes | Core fund account; add `updated_at` trigger |
| `bank_accounts` | ✅ Yes | VietQR display data |
| `uploads` | ⚠️ Storage adapter | `storage_path` local → Supabase Storage URL |
| `extracted_transactions` | ✅ Yes | AI extraction results |
| `transactions` | ✅ Yes | Immutable financial transactions |
| `ledger_entries` | ✅ Yes | Immutable ledger with reversal linkage |
| `idempotency_keys` | ✅ Yes | Critical for duplicate prevention |
| `audit_logs` | ✅ Yes | Comprehensive audit trail |
| `collection_campaigns` | ✅ Yes | Fundraising campaigns |
| `campaign_members` | ✅ Yes | Student-campaign payment tracking |
| `students` | ✅ Yes | Student roster with aliases |
| `payment_matches` | ✅ Yes | Links transactions to campaign students |
| `chat_messages` | ⚠️ Extension needed | Add AI processing fields |
| `revoked_tokens` | ❌ Replace | Supabase Auth handles token revocation |

---

## 2. POSTGRESQL COMPATIBILITY VERIFICATION

### Verified Compatible

| Feature | Evidence | Supabase Support |
|---------|----------|------------------|
| **UUID primary keys** | `String(36)` with `uuid4_str()` default | ✅ Native `uuid` type; string UUID works |
| **Numeric(18,2) money** | `opening_balance`, `amount`, `expected_amount` | ✅ Native `numeric` |
| **Timezone-aware timestamps** | `DateTime(timezone=True)` + `utcnow()` | ✅ `timestamptz` |
| **Foreign keys** | All FKs defined with `ForeignKey()` | ✅ Full support |
| **Unique constraints** | `UniqueConstraint` on multiple tables | ✅ Full support |
| **Indexes** | `index=True` on status, FK columns | ✅ Full support |
| **JSON/JSONB columns** | `JSON` type for `aliases`, `before_data`, `after_data`, `response_body` | ✅ `jsonb` preferred; `JSON` works |
| **Enum columns** | `Enum(Role, native_enum=False)` → VARCHAR | ✅ Works; Supabase prefers CHECK constraints or native enums |
| **Check constraints** | None explicit in models | ⚠️ Add for `amount > 0`, status values |
| **Triggers** | None in current schema | ⚠️ Needed for `updated_at`, `current_balance` materialized view |

### Migration Portability

```python
# alembic/versions/0001_initial.py
def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
```

**Assessment**: Uses `create_all()` — **not a true migration**. For Supabase:
- Must generate proper Alembic migration with `op.create_table()` statements
- Current approach works for dev but not production schema management
- **Action**: Run `alembic revision --autogenerate` against target DB to produce proper migration

---

## 3. ORM COMPATIBILITY WITH SUPABASE

### SQLAlchemy 2.x + psycopg3

| Aspect | Current Config | Supabase Requirement | Status |
|--------|----------------|---------------------|--------|
| **Driver** | `psycopg[binary]` | `psycopg` (v3) | ✅ Compatible |
| **Connection pooling** | `pool_pre_ping=True` | PgBouncer transaction pooling | ⚠️ Must set `pool_size=5`, `max_overflow=0` |
| **Prepared statements** | Default SQLAlchemy behavior | Disable for PgBouncer transaction mode | ⚠️ Add `connect_args={"prepare_threshold": 0}` |
| **Async support** | Sync only (`create_engine`) | Supabase supports async | ⚠️ Consider `create_async_engine` for worker |

### Required Engine Config for Supabase
```python
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=0,
    connect_args={"prepare_threshold": 0},  # Critical for PgBouncer
    future=True,
)
```

---

## 4. ROW LEVEL SECURITY (RLS) REQUIREMENTS

### Current State: **NO RLS POLICIES**

Supabase **requires RLS** for all tables exposed to anon/authenticated roles.

### Required Policies by Table

| Table | Policy | SQL Example |
|-------|--------|-------------|
| `messages` (chat_messages) | Members read own conversation; Admins read all | `CREATE POLICY "read_own_conversation" ON messages FOR SELECT USING (auth.uid() = sender_id OR EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin'));` |
| `fund_accounts` (accounts) | Public read balance; Admin write | `CREATE POLICY "public_read_balance" ON accounts FOR SELECT USING (true);` |
| `financial_ledger` (transactions/ledger_entries) | Public read verified; Admin write | `CREATE POLICY "public_read_verified" ON ledger_entries FOR SELECT USING (status = 'VERIFIED');` |
| `uploads` | Uploader read own; Admin read all | `CREATE POLICY "read_own_uploads" ON uploads FOR SELECT USING (uploaded_by = auth.uid());` |
| `students` | Public read; Admin write | `CREATE POLICY "public_read_students" ON students FOR SELECT USING (true);` |
| `campaigns` | Public read; Admin write | `CREATE POLICY "public_read_campaigns" ON collection_campaigns FOR SELECT USING (true);` |
| `audit_logs` | Admin only | `CREATE POLICY "admin_only" ON audit_logs FOR ALL USING (EXISTS (SELECT 1 FROM user_roles WHERE user_id = auth.uid() AND role = 'admin'));` |
| `worker_status` | Worker write own; Admin read all | `CREATE POLICY "worker_self" ON worker_status FOR ALL USING (worker_id = current_setting('app.current_worker_id')::uuid);` |

### Critical: Service Role for Worker
- Worker must use **service_role key** (bypasses RLS) for:
  - Claiming messages
  - Writing transactions/ledger entries
  - Updating message status
- **Never expose service_role key to frontend**

---

## 5. REALTIME PUBLICATION COMPATIBILITY

### Current Tables Needing Realtime

| Table | Publication Needed? | Reason |
|-------|---------------------|--------|
| `chat_messages` | ✅ Yes | Live chat updates |
| `transactions` | ✅ Yes | Live ledger updates |
| `ledger_entries` | ✅ Yes | Live balance computation |
| `campaign_members` | ✅ Yes | Live campaign progress |
| `uploads` | ✅ Yes | Upload status changes |
| `messages` (new) | ✅ Yes | AI processing status |

### Supabase Realtime Setup
```sql
-- Enable replication for required tables
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;
ALTER PUBLICATION supabase_realtime ADD TABLE ledger_entries;
ALTER PUBLICATION supabase_realtime ADD TABLE campaign_members;
ALTER PUBLICATION supabase_realtime ADD TABLE uploads;
ALTER PUBLICATION supabase_realtime ADD TABLE messages;  -- new table
```

### Frontend Subscription Pattern
```typescript
// src/hooks/useRealtime.ts
supabase
  .channel('ledger_changes')
  .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'ledger_entries' }, payload => {
    // Update local ledger state
  })
  .subscribe()
```

---

## 6. TRANSACTION AND LOCKING REQUIREMENTS

### Current Backend Locking (Verified in `ledger.py`)

| Operation | Locking Strategy | Supabase Compatible? |
|-----------|------------------|---------------------|
| **Duplicate check** | `SELECT ... FOR UPDATE` on `transactions` | ✅ Yes |
| **Reversal** | `SELECT ... FOR UPDATE` on `transactions` + `ledger_entries` | ✅ Yes |
| **Campaign member update** | `SELECT ... FOR UPDATE` on `campaign_members` | ✅ Yes |
| **Idempotency check** | `SELECT` on `idempotency_keys` (unique constraint) | ✅ Yes |

### Worker Atomic Claim (NEW)
```sql
-- Atomic claim with lease
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
RETURNING *;
```

**Requirement**: Supabase supports `FOR UPDATE SKIP LOCKED` ✅

---

## 7. SUPABASE AUTH INTEGRATION

### Current Auth System
- Custom `users` table with `password_hash` (argon2)
- JWT tokens (HS256) with `OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC` roles
- Token revocation via `revoked_tokens` table

### Supabase Auth Migration Options

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A: Replace entirely** | Use Supabase Auth `auth.users`; map roles to `user_metadata` or custom `user_roles` table | Standard, managed, MFA, OAuth | Lose custom argon2 hashes; migration needed |
| **B: Hybrid** | Keep `users` table; sync with Supabase Auth via webhooks | Preserve existing passwords | Complex sync; dual auth sources |
| **C: Custom JWT + Supabase** | Issue Supabase-compatible JWTs from custom backend | Full control | Manual token management |

### Recommended: Option A with Migration
1. Enable Supabase Auth (email/password)
2. Create `user_roles` table: `user_id` (FK to `auth.users`), `role` enum
3. Migrate existing users: `INSERT INTO auth.users ...` (requires Supabase admin API)
4. RLS policies reference `auth.uid()` and `user_roles`

### Frontend Auth Flow with Supabase
```typescript
// Login
const { data, error } = await supabase.auth.signInWithPassword({ email, password })
// Returns session with access_token (JWT) + refresh_token

// Frontend uses access_token as Bearer token for Supabase client
// RLS policies enforce authorization automatically
```

---

## 8. STORAGE MIGRATION

### Current: Local Filesystem
```python
# config.py
upload_dir: str = "./storage/uploads"

# uploads.py:42-44
path = Path(settings.upload_dir) / f"{uuid4()}{ext}"
path.write_bytes(data)
```

### Supabase Storage
```sql
-- Create bucket
INSERT INTO storage.buckets (id, name, public) VALUES ('receipts', 'receipts', false);

-- RLS policies
CREATE POLICY "authenticated_upload" ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id = 'receipts');
CREATE POLICY "owner_read" ON storage.objects FOR SELECT TO authenticated USING (bucket_id = 'receipts' AND owner = auth.uid());
CREATE POLICY "public_read_verified" ON storage.objects FOR SELECT TO anon USING (bucket_id = 'receipts' AND EXISTS (SELECT 1 FROM uploads WHERE uploads.storage_path = storage.objects.name AND uploads.status = 'VERIFIED'));
```

### Worker Integration
```python
# Download from Supabase Storage
response = supabase.storage.from_('receipts').download(upload.storage_path)
image_bytes = response.data
# Run AI pipeline
```

---

## 9. DECIMAL/NUMERIC MONEY HANDLING

### Current: Python `Decimal` ↔ PostgreSQL `Numeric(18,2)`

| Layer | Type | Precision |
|-------|------|-----------|
| Python | `decimal.Decimal` | Arbitrary |
| SQLAlchemy | `Numeric(18,2)` | 18 digits, 2 decimal |
| PostgreSQL | `numeric(18,2)` | Exact |
| TypeScript | `number` | IEEE 754 (53-bit mantissa) |

### Risk: JavaScript Number Precision
- `number` can safely represent integers up to `2^53 - 1` ≈ 9×10^15
- VND amounts: max ~1 billion (10^9) → **SAFE for integer VND**
- **But**: Division, percentage calculations lose precision

### Mitigation
- Store amounts as **integer VND (minor units)** in DB: `Numeric(18,0)` or `BIGINT`
- Frontend: Use `bigint` or `decimal.js` for calculations
- Display: Divide by 100 only for formatting

### Current Schema Uses `Numeric(18,2)` — **Acceptable for VND** (no sub-VND units)

---

## 10. UUID COMPATIBILITY

### Current: String(36) UUID v4
```python
def uuid4_str() -> str:
    return str(uuid.uuid4())  # "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Supabase: Native `uuid` type
- **Compatible**: String UUID inserts work into `uuid` column
- **Better**: Change models to `UUID(as_uuid=False)` for native type
- **Index performance**: Native `uuid` slightly faster

---

## 11. MISSING TABLES FOR HYBRID ARCHITECTURE

### Required New Tables

#### `messages` (Extended Chat)
```sql
CREATE TABLE messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL,
    sender_id uuid NOT NULL REFERENCES auth.users(id),
    content text NOT NULL,
    message_type varchar(50) NOT NULL DEFAULT 'TEXT',  -- TEXT, RECEIPT, ANNOUNCEMENT, SYSTEM, AI_INTENT
    status varchar(30) NOT NULL DEFAULT 'pending',     -- pending, processing, awaiting_admin, processed, failed
    ai_intent varchar(50),                             -- CONTRIBUTION, WITHDRAWAL, BALANCE_INQUIRY, UNKNOWN
    ai_result jsonb,                                   -- Structured AI extraction
    ai_confidence numeric(5,4),
    transaction_id uuid REFERENCES transactions(id),
    error_message text,
    created_at timestamptz DEFAULT now(),
    processed_at timestamptz
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_status ON messages(status);
CREATE INDEX idx_messages_sender ON messages(sender_id);
```

#### `worker_status`
```sql
CREATE TABLE worker_status (
    worker_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status varchar(20) NOT NULL DEFAULT 'offline',  -- online, offline, processing
    model_name varchar(100),
    last_heartbeat timestamptz,
    last_processed_at timestamptz,
    current_job_id uuid,
    metadata jsonb DEFAULT '{}'
);

-- Single row per worker instance; upsert on heartbeat
```

---

## 12. CONNECTION POOLING ASSUMPTIONS

### Current Backend
- Single `SessionLocal` per request (FastAPI dependency)
- `pool_pre_ping=True` only
- No explicit pool sizing

### Supabase (PgBouncer Transaction Mode)
- Max connections limited by plan
- Transaction pooling: connections released after each transaction
- **Implications**:
  - No long-running transactions across multiple requests
  - `SELECT ... FOR UPDATE` must complete in single transaction
  - Worker must use short transactions

### Worker Pool Config
```python
# Worker uses own engine with minimal pool
worker_engine = create_engine(
    settings.database_url,
    pool_size=2,
    max_overflow=0,
    connect_args={"prepare_threshold": 0},
)
```

---

## 13. VERIFICATION STATUS SUMMARY

| Check | Status | Evidence |
|-------|--------|----------|
| PostgreSQL dialect | ✅ Verified | `postgresql+psycopg` in DATABASE_URL |
| SQLAlchemy 2.x | ✅ Verified | `pyproject.toml` |
| Alembic migrations | ⚠️ Partial | `create_all()` not true migrations |
| UUID PKs | ✅ Verified | `String(36)` with uuid4 |
| Decimal money | ✅ Verified | `Numeric(18,2)` |
| FK constraints | ✅ Verified | All models |
| Unique constraints | ✅ Verified | Multiple tables |
| Indexes | ✅ Verified | `index=True` on key columns |
| JSON columns | ✅ Verified | `JSON` type used |
| Timezone timestamps | ✅ Verified | `DateTime(timezone=True)` |
| RLS policies | ❌ Missing | None defined |
| Realtime publication | ❌ Missing | Not configured |
| Supabase Auth | ❌ Missing | Custom auth only |
| Storage integration | ❌ Missing | Local filesystem only |
| Connection pooling | ⚠️ Needs config | Default pool only |

---

## 14. RECOMMENDED ADAPTERS

1. **Database Adapter** (`src/lib/db/supabase.ts`) — Supabase client for frontend
2. **Auth Adapter** — Supabase Auth integration replacing custom JWT
3. **Storage Adapter** — Upload/download receipts to Supabase Storage
4. **Realtime Adapter** — Subscription hooks for live updates
5. **Worker DB Config** — SQLAlchemy engine tuned for PgBouncer
6. **RLS Policy Migration** — SQL file for Supabase dashboard
7. **Realtime Publication Migration** — SQL for enabling Realtime
8. **Message Table Migration** — New `messages` table with AI fields

---

## 15. CONFIDENCE ASSESSMENT

- **Verified**: Schema inspection, SQLAlchemy config, locking patterns
- **Partially Verified**: Supabase-specific behaviors (RLS, Realtime, PgBouncer) from docs
- **Assumed**: Migration tooling works seamlessly; Supabase Auth migration feasible
- **Not Verified**: Actual deployment, connection limits, Realtime scalability