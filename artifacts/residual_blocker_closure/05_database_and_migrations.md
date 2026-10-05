# Database and Migrations

**Date**: 2026-10-04  
**Status**: MIGRATION READY / LIVE-BLOCKED (PostgreSQL required)

## Migration Status

### Existing Migrations (0001-0004)
| Migration | Description | Status |
|-----------|-------------|--------|
| 0001_initial | Initial schema | ✅ Applied |
| 0002_add_messages_and_message_id | Messages table | ✅ Applied |
| 0003_add_recall_tokens | Recall tokens | ✅ Applied |
| 0004_add_worker_id_to_messages | Worker tracking | ✅ Applied |

### New Migration (0005)
**File**: `class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py`

**Changes:**
```sql
-- Messages: multiple attachments support
ALTER TABLE messages ADD COLUMN attachment_ids JSON;

-- Uploads: perceptual hash for duplicate detection
ALTER TABLE uploads ADD COLUMN perceptual_hash VARCHAR(128);
CREATE INDEX ix_uploads_perceptual_hash ON uploads(perceptual_hash);

-- Extracted Transactions: AI pipeline fields
ALTER TABLE extracted_transactions ADD COLUMN field_confidences JSON;
ALTER TABLE extracted_transactions ADD COLUMN extraction_method VARCHAR(50);
ALTER TABLE extracted_transactions ADD COLUMN source_image_id VARCHAR(36);
ALTER TABLE extracted_transactions ADD COLUMN currency VARCHAR(8);

-- Extracted Transactions: Review audit fields
ALTER TABLE extracted_transactions ADD COLUMN reviewed_by VARCHAR(36) REFERENCES users(id);
ALTER TABLE extracted_transactions ADD COLUMN reviewed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE extracted_transactions ADD COLUMN review_notes TEXT;

-- Add indexes for duplicate detection
CREATE INDEX ix_extracted_transactions_field_confidences ON extracted_transactions(field_confidences);
```

**Rollback:** All columns and indexes dropped in reverse order.

## Schema Verification

### Key Tables for Blockers

**`uploads` table:**
- `perceptual_hash` - For duplicate detection persistence ✅ (migration 0005)
- `file_hash` - SHA-256 already exists ✅

**`extracted_transactions` table:**
- `field_confidences` JSON - Field-level confidence storage ✅ (migration 0005)
- `extraction_method` - vision/ocr/hybrid tracking ✅ (migration 0005)
- `source_image_id` - Reference to upload ✅ (migration 0005)
- `currency` - VND tracking ✅ (migration 0005)
- `reviewed_by`, `reviewed_at`, `review_notes` - Review audit ✅ (migration 0005)

**`messages` table:**
- `attachment_ids` JSON - Multiple attachments ✅ (migration 0005)
- `attachment_id` - Legacy single attachment ✅ (existing)
- `recall_token_hash` - SHA-256 hashed token ✅ (existing)

**`recall_tokens` table:**
- `token_hash` - SHA-256 stored ✅ (existing)
- `used_at`, `revoked_at`, `expires_at` - Lifecycle tracking ✅ (existing)

**`idempotency_keys` table:**
- `key` - Unique idempotency key ✅ (existing)
- `request_fingerprint` - SHA-256 of request ✅ (existing)
- `response_status`, `response_body` - Cached response ✅ (existing)

## Migration Application

### Required for Live Verification
```bash
cd class-fund-backend-v0.1/class-fund-backend
alembic upgrade head
```

### SQLite Compatibility
All migrations are compatible with SQLite for testing:
- JSON columns work in SQLite
- Foreign keys enforced
- Indexes created

## RLS Policy Requirements

### Tables Requiring Policies
| Table | Policy Needed | Role |
|-------|---------------|------|
| messages | Guest insert (PUBLIC), owner read | PUBLIC, authenticated |
| uploads | Guest insert, public read | PUBLIC, authenticated |
| extracted_transactions | Service role write, public read | service_role, PUBLIC |
| recall_tokens | Service role only | service_role |
| idempotency_keys | Service role only | service_role |

### Storage Bucket: `receipts`
- Path pattern: `uploads/{upload_id}.{ext}`
- Guest INSERT to uploads/ folder
- Public SELECT
- Service role ALL

## Database Constraints

### Unique Constraints (Enforced)
| Table | Constraint | Columns |
|-------|------------|---------|
| uploads | File hash uniqueness | file_hash |
| extracted_transactions | One per upload | upload_id (unique FK) |
| transactions | Bank transaction identity | bank_account_id + transaction_code |
| messages | Public code uniqueness | public_code |
| recall_tokens | One per message | message_id (unique FK) |
| idempotency_keys | Key uniqueness | key |

### Indexes for Performance
| Index | Table | Columns |
|-------|-------|---------|
| ix_uploads_perceptual_hash | uploads | perceptual_hash |
| ix_messages_conversation_status_created | messages | conversation_id, status, created_at |
| ix_messages_status_created | messages | status, created_at (where status='pending') |
| ix_extracted_transactions_field_confidences | extracted_transactions | field_confidences (GIN) |

## Test Database Configuration

### SQLite (Tests)
```python
engine = create_engine("sqlite:///test.db", future=True)
```

### PostgreSQL (Production)
```python
engine = create_engine(
    "postgresql+psycopg://user:pass@host:5432/db",
    pool_pre_ping=True,
    future=True,
    pool_size=5,
    max_overflow=10
)
```

## Migration Commands

```bash
# Check current revision
alembic current

# Show history
alembic history

# Generate new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1
```

## Live Blocker

**PostgreSQL required** for:
- Migration 0005 application
- Production RLS policies
- Concurrent worker testing
- Supabase realtime integration

SQLite tests validate schema and logic but cannot verify:
- PostgreSQL-specific features (FOR UPDATE SKIP LOCKED)
- Supabase realtime publications
- Production RLS policies
- Concurrent duplicate detection