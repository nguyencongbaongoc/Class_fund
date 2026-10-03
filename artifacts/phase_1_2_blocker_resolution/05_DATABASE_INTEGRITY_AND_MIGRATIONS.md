# 05_DATABASE_INTEGRITY_AND_MIGRATIONS.md

## Workstream C: Database Integrity and Migrations

### Current State Analysis

**Problem**: No message persistence, no worker state, no recall tokens. Phase 0/1.1 audits found missing tables and constraints.

**Solution**: 4 additive migrations creating all required tables with proper constraints, indexes, and foreign keys.

### Migration Summary

| Migration | Tables Created | Key Features |
|-----------|----------------|--------------|
| `0002_add_messages_and_message_id.py` | `messages`, `worker_status` | Atomic claim indexes, `transactions.message_id` FK |
| `0003_add_recall_tokens.py` | `recall_tokens` | Token hash, expiry, replay protection |
| `0004_add_worker_id_to_messages.py` | - | `messages.worker_id` FK to `worker_status` |

### Schema Verification

All tables created successfully in SQLite test environment:

```sql
-- messages table
id (PK), conversation_id, sender_id (FK), sender_name, sender_photo, 
sender_role, message_type, content, attachment_id, status, public_code (UNIQUE),
recall_token_hash, transaction_id (FK), error_message, retry_count,
created_at, claimed_at, lease_expires_at, processed_at, worker_id (FK)

-- worker_status table  
worker_id (PK), status, model_name, last_heartbeat, last_processed_at,
current_job_id (FK), worker_metadata

-- recall_tokens table
id (PK), message_id (FK, UNIQUE), token_hash, created_at,
expires_at, used_at, revoked_at

-- transactions (modified)
message_id (FK, nullable, index)
```

### Indexes for Performance

| Table | Index | Purpose |
|-------|-------|---------|
| `messages` | `ix_messages_status_created` | Partial: pending messages by created_at |
| `messages` | `ix_messages_conversation_status_created` | Conversation message ordering |
| `messages` | `ix_messages_processing_lease` | Partial: processing messages by lease expiry |
| `messages` | `ix_messages_public_code` | Unique public code lookup |
| `messages` | `ix_messages_worker_id` | Worker message ownership |
| `recall_tokens` | `ix_recall_tokens_message_id` | Token lookup by message |
| `transactions` | (existing) `uq_bank_transaction_code` | Prevent duplicate bank transactions |
| `transactions` | (new) `message_id` | Message → transaction traceability |

### Constraint Verification

| Constraint | Table | Verified |
|------------|-------|----------|
| PK on `id` | All tables | ✅ |
| FK `sender_id` → `users.id` | messages | ✅ |
| FK `attachment_id` → `uploads.id` | messages | ✅ (implicit) |
| FK `transaction_id` → `transactions.id` | messages | ✅ |
| FK `message_id` → `messages.id` | transactions | ✅ |
| FK `worker_id` → `worker_status.worker_id` | messages | ✅ |
| FK `message_id` → `messages.id` | recall_tokens | ✅ |
| UNIQUE `public_code` | messages | ✅ |
| UNIQUE `message_id` | recall_tokens | ✅ |
| UNIQUE `bank_account_id, transaction_code` | transactions | ✅ |

### Concurrent Insert Behavior

Tested with sequential simulation (SQLite limitation):
- Multiple `post_transaction` calls with same idempotency key → single transaction
- Different messages, same bank transaction code → `FAILED` with `BUSINESS_RULE`
- Recovery via `message_id` works after commit

### Transaction Rollback Behavior

Verified in tests:
- `IntegrityError` in `post_transaction` → rollback → recovery attempt → `FAILED` or recovered
- `IntegrityError` in `post_revert` → rollback → `FAILED` with `BUSINESS_RULE`
- No partial state left after rollback

### Safe Retry After Uniqueness Conflicts

- Idempotency key conflict (different fingerprint) → `FAILED` with `VALIDATION`
- Duplicate bank transaction → `FAILED` with `BUSINESS_RULE` (or `DUPLICATE` if same message)
- Ambiguous commit (idempotency exists, transaction not found) → recovery via `message_id`

### Migration Safety

All migrations are **additive only**:
- No existing columns modified
- No existing tables dropped
- No data migration required for new columns (nullable)
- Safe to apply to production database

### Verification Commands

```bash
# Check migration syntax
alembic check

# Generate SQL for review
alembic upgrade head --sql

# Apply to test database
DATABASE_URL=sqlite:///test.db alembic upgrade head

# Verify tables
python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('sqlite:///test.db')
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
for t in inspector.get_table_names():
    print(f'{t}: {[c[\"name\"] for c in inspector.get_columns(t)]}')
"
```

### Status

| Task | Status | Evidence |
|------|--------|----------|
| Messages table | ✅ IMPLEMENTED | Migration 0002 |
| Worker status table | ✅ IMPLEMENTED | Migration 0002 |
| Recall tokens table | ✅ IMPLEMENTED | Migration 0003 |
| Transaction.message_id FK | ✅ IMPLEMENTED | Migration 0002 + 0004 |
| Message.worker_id FK | ✅ IMPLEMENTED | Migration 0004 |
| Indexes for polling | ✅ IMPLEMENTED | Migration 0002 |
| Unique constraints | ✅ IMPLEMENTED | Migrations 0002-0003 |
| Concurrent insert test | ✅ TEST-VERIFIED | `test_idempotency.py` |
| Rollback behavior test | ✅ TEST-VERIFIED | `test_financial_core.py` |
| Safe retry test | ✅ TEST-VERIFIED | `test_idempotency.py` |
| Migration syntax check | ✅ SOURCE-VERIFIED | Alembic scripts valid |