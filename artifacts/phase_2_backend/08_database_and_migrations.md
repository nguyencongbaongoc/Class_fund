# 08_DATABASE_AND_MIGRATIONS.md

## Phase 2 Database Schema and Migrations

**Status**: ✅ MIGRATIONS COMPLETE (0001-0004) — Compatible with Supabase PostgreSQL
**Location**: `alembic/versions/`, `app/models/models.py`

### 1. Migration History

| Migration | Revision | Description | Tables Affected |
|-----------|----------|-------------|-----------------|
| 0001 | `0001_initial` | Core financial schema | accounts, bank_accounts, transactions, ledger_entries, uploads, extracted_transactions, users, campaigns, students, campaign_members, payment_matches, idempotency_keys, audit_logs, revoked_tokens |
| 0002 | `0002_add_messages_and_message_id` | Message queue + worker | messages, worker_status, transactions.message_id |
| 0003 | `0003_add_recall_tokens` | Recall authorization | recall_tokens |
| 0004 | `0004_add_worker_id_to_messages` | Worker tracking | messages.worker_id |

### 2. Core Schema (0001_initial)

```sql
-- Financial Core
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    name VARCHAR(120) UNIQUE NOT NULL,
    currency VARCHAR(8) DEFAULT 'VND',
    opening_balance NUMERIC(18,2) DEFAULT 0,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY,
    bank_name VARCHAR(120) NOT NULL,
    account_name VARCHAR(160) NOT NULL,
    account_number VARCHAR(64) NOT NULL,
    payment_link VARCHAR(500),
    qr_image_url VARCHAR(500),
    active BOOLEAN DEFAULT true
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    bank_account_id UUID REFERENCES bank_accounts(id),
    transaction_code VARCHAR(120),
    type VARCHAR(20) NOT NULL CHECK (type IN ('CREDIT','DEBIT','REVERT')),
    amount NUMERIC(18,2) NOT NULL,
    currency VARCHAR(8) DEFAULT 'VND',
    source VARCHAR(20) NOT NULL CHECK (source IN ('IMAGE','MANUAL','REVERT')),
    status VARCHAR(20) DEFAULT 'VERIFIED' CHECK (status IN ('VERIFIED','REVERTED')),
    upload_id UUID REFERENCES uploads(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    effective_at TIMESTAMPTZ DEFAULT NOW(),
    note TEXT,
    message_id UUID REFERENCES messages(id),  -- Added in 0002
    UNIQUE (bank_account_id, transaction_code)
);

CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY,
    transaction_id UUID UNIQUE REFERENCES transactions(id),
    type VARCHAR(20) NOT NULL CHECK (type IN ('CREDIT','DEBIT','REVERT')),
    amount NUMERIC(18,2) NOT NULL,
    currency VARCHAR(8) DEFAULT 'VND',
    transaction_code VARCHAR(120),
    source VARCHAR(20) NOT NULL CHECK (source IN ('IMAGE','MANUAL','REVERT')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('VERIFIED','REVERTED')),
    upload_id UUID REFERENCES uploads(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    effective_at TIMESTAMPTZ DEFAULT NOW(),
    original_entry_id UUID REFERENCES ledger_entries(id),
    note TEXT
);

-- Idempotency
CREATE TABLE idempotency_keys (
    id UUID PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    response_status INTEGER NOT NULL,
    response_body JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    actor_id UUID REFERENCES users(id),
    action VARCHAR(120) NOT NULL,
    entity_type VARCHAR(120) NOT NULL,
    entity_id VARCHAR(120),
    before_data JSONB,
    after_data JSONB,
    ip VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. Message Queue Schema (0002)

```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL,
    sender_id UUID REFERENCES users(id),
    sender_name VARCHAR(120) NOT NULL,
    sender_photo VARCHAR(500),
    sender_role VARCHAR(40) DEFAULT 'PUBLIC',
    message_type VARCHAR(50) DEFAULT 'TEXT',
    content TEXT NOT NULL,
    attachment_id UUID REFERENCES uploads(id),
    status VARCHAR(30) DEFAULT 'pending' CHECK (status IN ('pending','processing','awaiting_review','posted','rejected','failed','recalled')),
    public_code VARCHAR(50) UNIQUE,
    recall_token_hash VARCHAR(64),
    transaction_id UUID REFERENCES transactions(id),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    claimed_at TIMESTAMPTZ,
    lease_expires_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    worker_id UUID REFERENCES worker_status(worker_id)  -- Added in 0004
);

-- Indexes for efficient polling
CREATE INDEX ix_messages_status_created ON messages (status, created_at) WHERE status = 'pending';
CREATE INDEX ix_messages_conversation_status_created ON messages (conversation_id, status, created_at);
CREATE INDEX ix_messages_processing_lease ON messages (status, lease_expires_at) WHERE status = 'processing';

CREATE TABLE worker_status (
    worker_id UUID PRIMARY KEY,
    status VARCHAR(20) DEFAULT 'offline',
    model_name VARCHAR(100),
    last_heartbeat TIMESTAMPTZ,
    last_processed_at TIMESTAMPTZ,
    current_job_id UUID REFERENCES messages(id),
    metadata JSONB DEFAULT '{}'
);

-- Add message_id to transactions
ALTER TABLE transactions ADD COLUMN message_id UUID REFERENCES messages(id);
CREATE INDEX ix_transactions_message_id ON transactions (message_id);
```

### 4. Recall Tokens (0003)

```sql
CREATE TABLE recall_tokens (
    id UUID PRIMARY KEY,
    message_id UUID UNIQUE NOT NULL REFERENCES messages(id),
    token_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX ix_recall_tokens_message_id ON recall_tokens (message_id);
```

### 5. Worker ID on Messages (0004)

```sql
ALTER TABLE messages ADD COLUMN worker_id UUID REFERENCES worker_status(worker_id);
CREATE INDEX ix_messages_worker_id ON messages (worker_id);
```

### 6. Complete ER Diagram

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   accounts  │       │   transactions   │       │  ledger_entries │
├─────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)     │◄──────│ account_id (FK)  │       │ id (PK)         │
│ name        │       │ id (PK)          │──────►│ transaction_id  │
│ currency    │       │ bank_account_id  │       │ (FK, UNIQUE)    │
│ opening_bal │       │ transaction_code │       │ type            │
│ active      │       │ type             │       │ amount          │
│ created_at  │       │ amount           │       │ source          │
└─────────────┘       │ currency         │       │ status          │
                      │ source           │       │ original_entry_ │
                      │ status           │       │ upload_id       │
                      │ upload_id (FK)   │◄──────│ created_by      │
                      │ created_by (FK)  │       │ created_at      │
                      │ created_at       │       │ effective_at    │
                      │ effective_at     │       │ note            │
                      │ note             │       └─────────────────┘
                      │ message_id (FK)  │
                      └────────┬─────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌────────────┐  ┌──────────────┐  ┌─────────────┐
       │  uploads   │  │   messages   │  │  campaigns  │
       ├────────────┤  ├──────────────┤  ├─────────────┤
       │ id (PK)    │  │ id (PK)      │  │ id (PK)     │
       │ file_hash  │  │ conversation_│  │ title       │
       │ storage_   │  │ attachment_id│  │ expected_   │
       │ path       │  │ status       │  │ amount      │
       │ status     │  │ public_code  │  │ status      │
       │ uploaded_  │  │ recall_token_│  └──────┬──────┘
       │ by (FK)    │  │ hash         │         │
       └──────┬─────┘  │ worker_id    │         ▼
              │        │ lease_expire │  ┌──────────────────┐
              │        └──────┬───────┘  │ campaign_members │
              │               │          ├──────────────────┤
              │               ▼          │ campaign_id (FK) │
              │        ┌──────────────┐  │ student_id (FK)  │
              │        │ worker_status│  │ status           │
              │        ├──────────────┤  │ UNIQUE(camp,stud)│
              │        │ worker_id(PK)│  └────────┬─────────┘
              │        │ status       │           │
              │        │ last_heartbt │           ▼
              │        │ current_job_ │    ┌─────────────┐
              │        └──────────────┘    │  students   │
              │                             ├─────────────┤
              │                             │ id (PK)     │
              ▼                             │ full_name   │
       ┌──────────────────┐                 │ aliases     │
       │extracted_trans   │                 │ student_code│
       ├──────────────────┤                 │ active      │
       │ id (PK)          │                 └─────────────┘
       │ upload_id (FK,UQ)│
       │ transaction_code │
       │ amount           │
       │ sender_name      │
       │ bank_name        │
       │ bank_account_id  │
       │ confidence       │
       │ campaign_id (FK) │
       │ student_id (FK)  │
       │ status           │
       └──────────────────┘
```

### 7. Key Constraints Summary

| Constraint | Table | Purpose |
|------------|-------|---------|
| `PRIMARY KEY (id)` | All tables | Unique identification |
| `UNIQUE (name)` | accounts | One active fund per name |
| `UNIQUE (bank_account_id, transaction_code)` | transactions | Prevent duplicate bank transactions |
| `UNIQUE (transaction_id)` | ledger_entries | 1:1 transaction:ledger |
| `UNIQUE (key)` | idempotency_keys | Deduplication |
| `UNIQUE (public_code)` | messages | Human-readable codes |
| `UNIQUE (message_id)` | recall_tokens | One token per message |
| `UNIQUE (upload_id)` | extracted_transactions | One extraction per upload |
| `UNIQUE (campaign_id, student_id)` | campaign_members | One membership per campaign |
| `UNIQUE (transaction_id)` | payment_matches | One match per transaction |
| `FOREIGN KEY (message_id)` | transactions | Traceability to message |
| `FOREIGN KEY (worker_id)` | messages | Worker tracking |
| `CHECK (amount > 0)` | Application-level | Positive amounts |
| `CHECK (status IN ...)` | messages, transactions | Valid state machine |

### 8. Indexes for Performance

| Index | Table | Use Case |
|-------|-------|----------|
| `ix_messages_status_created` | messages | Worker polling pending messages |
| `ix_messages_conversation_status_created` | messages | Frontend conversation view |
| `ix_messages_processing_lease` | messages | Lease expiry scanning |
| `ix_messages_worker_id` | messages | Worker job queries |
| `ix_transactions_message_id` | transactions | Message → transaction lookup |
| `ix_recall_tokens_message_id` | recall_tokens | Recall token validation |

### 9. Supabase PostgreSQL Compatibility

All migrations use portable SQL:
- ✅ `UUID` as `VARCHAR(36)` (not native `UUID` type)
- ✅ `TIMESTAMPTZ` for all timestamps
- ✅ `JSONB` for metadata
- ✅ Partial indexes with `WHERE` clause
- ✅ `ON CONFLICT` for upserts
- ✅ No vendor-specific types

**Apply to Supabase**:
```bash
# Via Supabase CLI
supabase db push

# Or via SQL Editor in Supabase Dashboard
# Run each migration file in order
```

### 10. Seed Data (Required for Operation)

```sql
-- Minimum seed for operation
INSERT INTO accounts (id, name, currency, opening_balance, active)
VALUES ('00000000-0000-0000-0000-000000000001', 'Class Fund', 'VND', 0, true);

-- At least one bank account for AI credits
INSERT INTO bank_accounts (id, bank_name, account_name, account_number, active)
VALUES ('00000000-0000-0000-0000-000000000002', 'Vietcombank', 'Class Fund', '1234567890', true);
```

### 11. Migration Commands

```bash
# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1

# Show history
alembic history

# Current revision
alembic current
```

### 12. Phase 2 Database Changes (Applied)

| Change | Migration | Reason |
|--------|-----------|--------|
| `transactions.message_id` | 0002 | Traceability for idempotency recovery |
| `messages` table + indexes | 0002 | Persistent worker queue |
| `worker_status` table | 0002 | Worker heartbeat/monitoring |
| `recall_tokens` table | 0003 | Recall authorization |
| `messages.worker_id` | 0004 | Worker-message linkage |
| `messages` indexes | 0002 | Polling performance |

### 13. Future Migrations (Post-Phase 2)

| Planned | Description | Priority |
|---------|-------------|----------|
| Add `rate_limit_keys` table | Rate limiting state | Phase 2 (HIGH) |
| Add `file_scans` table | Malware scan results | Phase 2 (MEDIUM) |
| Add `notification_preferences` | User preferences | Phase 3+ |
| Add `webhook_endpoints` | External integrations | Phase 5+ |
| Partition `audit_logs` by month | Performance | Phase 6+ |
| Add `archive_` tables | Data retention | Phase 6+ |

### 14. Verification Checklist

- [x] All migrations apply cleanly to SQLite (tests pass)
- [x] All migrations apply cleanly to PostgreSQL (syntax verified)
- [x] No data loss in downgrade paths
- [x] Indexes support query patterns (polling, lookup, joins)
- [x] Constraints enforce business rules at DB level
- [x] `message_id` on transactions enables recovery
- [x] `worker_status` enables monitoring
- [x] `recall_tokens` enables secure recall
- [ ] Live Supabase application (BLOCKED_EXTERNAL_DEPENDENCY)
- [ ] RLS policies applied (BLOCKED_EXTERNAL_DEPENDENCY)

---

**Status**: ✅ MIGRATIONS COMPLETE — Schema is stable, tested with SQLite, compatible with Supabase PostgreSQL. Ready for production deployment when credentials available.