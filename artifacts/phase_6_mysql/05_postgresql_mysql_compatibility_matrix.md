# Phase 6 PostgreSQL to MySQL Compatibility Matrix

## Overview
Complete compatibility analysis for every table, column, index, constraint, and PostgreSQL-specific feature. This matrix guides the migration implementation and identifies risks.

---

## 1. Table-by-Table Compatibility

### 1.1 revoked_tokens
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `revoked_tokens` | `revoked_tokens` | Compatible |
| PK: jti | String(36) | CHAR(36) | Keep String(36) |
| FK: user_id → users.id | String(36) | String(36) | Compatible |
| expires_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| revoked_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| Indexes | None | None | - |
| **Risk** | **LOW** | | |

### 1.2 users
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `users` | `users` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| email | String(255), unique, index | VARCHAR(255), unique, index | Compatible |
| password_hash | String(255) | VARCHAR(255) | Compatible |
| role | Enum(Role, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| **Risk** | **LOW** | | |

### 1.3 accounts
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `accounts` | `accounts` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| name | String(120), unique | VARCHAR(120), unique | Compatible |
| currency | String(8) | VARCHAR(8) | Compatible |
| opening_balance | Numeric(18,2) | DECIMAL(18,2) | **CRITICAL - Verify precision** |
| active | Boolean | TINYINT(1) | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| **Risk** | **MEDIUM** (financial precision) | | |

### 1.4 bank_accounts
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `bank_accounts` | `bank_accounts` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| bank_name | String(120) | VARCHAR(120) | Compatible |
| account_name | String(160) | VARCHAR(160) | Compatible |
| account_number | String(64) | VARCHAR(64) | Compatible |
| payment_link | String(500), nullable | VARCHAR(500), nullable | Compatible |
| qr_image_url | String(500), nullable | VARCHAR(500), nullable | Compatible |
| active | Boolean | TINYINT(1) | Compatible |
| **Risk** | **LOW** | | |

### 1.5 uploads
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `uploads` | `uploads` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| file_hash | String(64), index | VARCHAR(64), index | Compatible |
| perceptual_hash | String(128), nullable | VARCHAR(128), nullable | Compatible |
| original_filename | String(255) | VARCHAR(255) | Compatible |
| storage_path | String(500) | VARCHAR(500) | Compatible |
| uploaded_by → users.id | String(36), nullable | String(36), nullable | Compatible |
| uploader_name | String(120) | VARCHAR(120) | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| status | Enum(UploadStatus, native_enum=False), index | VARCHAR(20) + CHECK + index | Keep native_enum=False |
| **Risk** | **LOW** | | |

### 1.6 students
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `students` | `students` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| full_name | String(160), index | VARCHAR(160), index | Compatible |
| aliases | JSON | JSON | Compatible |
| student_code | String(64), nullable, index | VARCHAR(64), nullable, index | Compatible |
| active | Boolean | TINYINT(1) | Compatible |
| **Risk** | **LOW** | | |

### 1.7 collection_campaigns
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `collection_campaigns` | `collection_campaigns` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| title | String(200) | VARCHAR(200) | Compatible |
| description | Text, nullable | LONGTEXT, nullable | Compatible |
| expected_amount | Numeric(18,2) | DECIMAL(18,2) | **CRITICAL - Verify precision** |
| start_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| end_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| status | Enum(CampaignStatus, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| **Risk** | **MEDIUM** (financial precision) | | |

### 1.8 campaign_members
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `campaign_members` | `campaign_members` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: campaign_id → collection_campaigns.id | String(36) | String(36) | Compatible |
| FK: student_id → students.id | String(36) | String(36) | Compatible |
| status | Enum(CampaignMemberStatus, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| Unique: (campaign_id, student_id) | UniqueConstraint | UniqueConstraint | Compatible |
| **Risk** | **LOW** | | |

### 1.9 extracted_transactions
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `extracted_transactions` | `extracted_transactions` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: upload_id → uploads.id (unique) | String(36), unique | String(36), unique | Compatible |
| transaction_code | String(120), nullable | VARCHAR(120), nullable | Compatible |
| amount | Numeric(18,2), nullable | DECIMAL(18,2), nullable | **CRITICAL - Verify precision** |
| sender_name | String(160), nullable | VARCHAR(160), nullable | Compatible |
| bank_name | String(120), nullable | VARCHAR(120), nullable | Compatible |
| FK: bank_account_id → bank_accounts.id | String(36), nullable | String(36), nullable | Compatible |
| transaction_time | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| confidence | Numeric(5,4), nullable | DECIMAL(5,4), nullable | **Verify precision** |
| raw_ocr | Text, nullable | LONGTEXT, nullable | Compatible |
| FK: campaign_id → collection_campaigns.id | String(36), nullable | String(36), nullable | Compatible |
| FK: student_id → students.id | String(36), nullable | String(36), nullable | Compatible |
| status | Enum(UploadStatus, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| field_confidences | JSON, nullable | JSON, nullable | Compatible |
| extraction_method | String(50), nullable | VARCHAR(50), nullable | Compatible |
| source_image_id | String(36), nullable | VARCHAR(36), nullable | Compatible |
| currency | String(8), nullable | VARCHAR(8), nullable | Compatible |
| FK: reviewed_by → users.id | String(36), nullable | String(36), nullable | Compatible |
| reviewed_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| review_notes | Text, nullable | LONGTEXT, nullable | Compatible |
| **Risk** | **MEDIUM** (financial precision) | | |

### 1.10 transactions
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `transactions` | `transactions` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: account_id → accounts.id | String(36), index | String(36), index | Compatible |
| FK: bank_account_id → bank_accounts.id | String(36), nullable | String(36), nullable | Compatible |
| transaction_code | String(120), nullable | VARCHAR(120), nullable | Compatible |
| type | Enum(LedgerType, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| amount | Numeric(18,2) | DECIMAL(18,2) | **CRITICAL - Verify precision** |
| currency | String(8) | VARCHAR(8) | Compatible |
| source | Enum(LedgerSource, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| status | Enum(LedgerStatus, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| FK: upload_id → uploads.id | String(36), nullable | String(36), nullable | Compatible |
| FK: created_by → users.id | String(36), nullable | String(36), nullable | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| effective_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| note | Text, nullable | LONGTEXT, nullable | Compatible |
| FK: message_id → messages.id | String(36), nullable, index | String(36), nullable, index | Compatible |
| Unique: (bank_account_id, transaction_code) | UniqueConstraint | UniqueConstraint | Compatible |
| **Risk** | **HIGH** (financial core table) | | |

### 1.11 ledger_entries
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `ledger_entries` | `ledger_entries` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: transaction_id → transactions.id (unique) | String(36), unique | String(36), unique | Compatible |
| type | Enum(LedgerType, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| amount | Numeric(18,2) | DECIMAL(18,2) | **CRITICAL - Verify precision** |
| currency | String(8) | VARCHAR(8) | Compatible |
| transaction_code | String(120), nullable, index | VARCHAR(120), nullable, index | Compatible |
| source | Enum(LedgerSource, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| status | Enum(LedgerStatus, native_enum=False) | VARCHAR(20) + CHECK | Keep native_enum=False |
| FK: upload_id → uploads.id | String(36), nullable | String(36), nullable | Compatible |
| FK: created_by → users.id | String(36), nullable | String(36), nullable | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| effective_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| FK: original_entry_id → ledger_entries.id | String(36), nullable | String(36), nullable | Compatible |
| note | Text, nullable | LONGTEXT, nullable | Compatible |
| **Risk** | **HIGH** (financial core table) | | |

### 1.12 idempotency_keys
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `idempotency_keys` | `idempotency_keys` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| key | String(255), unique, index | VARCHAR(255), unique, index | Compatible |
| request_fingerprint | String(64) | VARCHAR(64) | Compatible |
| response_status | Integer | INT | Compatible |
| response_body | JSON | JSON | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| **Risk** | **LOW** | | |

### 1.13 audit_logs
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `audit_logs` | `audit_logs` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: actor_id → users.id | String(36), nullable | String(36), nullable | Compatible |
| action | String(120) | VARCHAR(120) | Compatible |
| entity_type | String(120) | VARCHAR(120) | Compatible |
| entity_id | String(120), nullable | VARCHAR(120), nullable | Compatible |
| before_data | JSON, nullable | JSON, nullable | Compatible |
| after_data | JSON, nullable | JSON, nullable | Compatible |
| ip | String(64), nullable | VARCHAR(64), nullable | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| **Risk** | **LOW** | | |

### 1.14 payment_matches
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `payment_matches` | `payment_matches` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: transaction_id → transactions.id (unique) | String(36), unique | String(36), unique | Compatible |
| FK: campaign_id → collection_campaigns.id | String(36) | String(36) | Compatible |
| FK: student_id → students.id | String(36) | String(36) | Compatible |
| confidence | Numeric(5,4) | DECIMAL(5,4) | **Verify precision** |
| matched_by | String(32) | VARCHAR(32) | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| **Risk** | **LOW** | | |

### 1.15 messages
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `messages` | `messages` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| conversation_id | String(36), index | VARCHAR(36), index | Compatible |
| FK: sender_id → users.id | String(36), nullable | String(36), nullable | Compatible |
| sender_name | String(120) | VARCHAR(120) | Compatible |
| sender_photo | String(500), nullable | VARCHAR(500), nullable | Compatible |
| sender_role | String(40) | VARCHAR(40) | Compatible |
| message_type | String(50) | VARCHAR(50) | Compatible |
| content | Text | LONGTEXT | Compatible |
| attachment_id | String(36), nullable | VARCHAR(36), nullable | Compatible |
| attachment_ids | JSON, nullable | JSON, nullable | Compatible |
| status | String(30) | VARCHAR(30) | Compatible |
| public_code | String(50), nullable, unique, index | VARCHAR(50), nullable, unique, index | Compatible |
| recall_token_hash | String(64), nullable | VARCHAR(64), nullable | Compatible |
| FK: transaction_id → transactions.id | String(36), nullable | String(36), nullable | Compatible |
| error_message | Text, nullable | LONGTEXT, nullable | Compatible |
| retry_count | Integer | INT | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| claimed_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| lease_expires_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| processed_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| FK: worker_id → worker_status.worker_id | String(36), nullable | String(36), nullable | Compatible |
| **Partial Indexes** | postgresql_where | mysql_where | **Rewrite required** |
| **Risk** | **MEDIUM** (partial indexes) | | |

### 1.16 worker_status
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `worker_status` | `worker_status` | Compatible |
| PK: worker_id | String(36) | CHAR(36) | Keep String(36) |
| status | String(20) | VARCHAR(20) | Compatible |
| model_name | String(100), nullable | VARCHAR(100), nullable | Compatible |
| last_heartbeat | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| last_processed_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| FK: current_job_id → messages.id | String(36), nullable | String(36), nullable | Compatible |
| metadata | postgresql.JSONB | JSON | **Change JSONB → JSON** |
| **Risk** | **LOW** | | |

### 1.17 recall_tokens
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `recall_tokens` | `recall_tokens` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: message_id → messages.id (unique) | String(36), unique | String(36), unique | Compatible |
| token_hash | String(64) | VARCHAR(64) | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| expires_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| used_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| revoked_at | TIMESTAMP WITH TIME ZONE, nullable | DATETIME(6), nullable | Use variant |
| Index: message_id | Index | Index | Compatible |
| **Risk** | **LOW** | | |

### 1.18 chat_messages
| Aspect | PostgreSQL | MySQL 8.4 | Action |
|--------|------------|-----------|--------|
| Table | `chat_messages` | `chat_messages` | Compatible |
| PK: id | String(36) | CHAR(36) | Keep String(36) |
| FK: sender_id → users.id | String(36), nullable | String(36), nullable | Compatible |
| sender_role | String(40) | VARCHAR(40) | Compatible |
| message_type | String(50) | VARCHAR(50) | Compatible |
| content | Text | LONGTEXT | Compatible |
| attachment_id | String(36), nullable | VARCHAR(36), nullable | Compatible |
| FK: ledger_entry_id → ledger_entries.id | String(36), nullable | String(36), nullable | Compatible |
| created_at | TIMESTAMP WITH TIME ZONE | DATETIME(6) | Use variant |
| **Risk** | **LOW** | | |

---

## 2. Data Type Compatibility Summary

| PostgreSQL Type | MySQL 8.4 Type | SQLAlchemy Mapping | Precision Risk |
|-----------------|----------------|-------------------|----------------|
| `UUID` (native) | `CHAR(36)` | `String(36)` | None |
| `VARCHAR(n)` | `VARCHAR(n)` | `String(n)` | None |
| `TEXT` | `LONGTEXT` | `Text` | None |
| `TIMESTAMP WITH TIME ZONE` | `DATETIME(6)` | `DateTime(timezone=True).with_variant(DATETIME(6), "mysql")` | **App-layer TZ** |
| `NUMERIC(p,s)` | `DECIMAL(p,s)` | `Numeric(p, s)` | **CRITICAL - Test** |
| `JSONB` | `JSON` | `JSON` | None |
| `BOOLEAN` | `TINYINT(1)` | `Boolean` | None |
| `INTEGER` | `INT` | `Integer` | None |
| `ENUM` (native) | `VARCHAR + CHECK` | `Enum(..., native_enum=False)` | None |
| `BIGSERIAL` | `BIGINT AUTO_INCREMENT` | Not used | N/A |

---

## 3. Index Compatibility

| Index Type | PostgreSQL | MySQL 8.4 | Migration |
|------------|------------|-----------|-----------|
| B-Tree (standard) | ✅ | ✅ | Direct |
| Unique | ✅ | ✅ | Direct |
| Partial (WHERE) | `postgresql_where` | `mysql_where` (8.0.13+) | **Rewrite** |
| Expression | ✅ | ✅ (8.0.13+) | Verify |
| Full-text | ✅ | ✅ | Not used |
| JSON (GIN) | ✅ | ✅ (virtual columns) | Not used |
| Composite | ✅ | ✅ | Direct |

### Partial Indexes to Rewrite
```sql
-- PostgreSQL (alembic 0002)
CREATE INDEX ix_messages_status_created ON messages (status, created_at) 
WHERE status = 'pending';

CREATE INDEX ix_messages_processing_lease ON messages (status, lease_expires_at) 
WHERE status = 'processing';

-- MySQL 8.4 Equivalent
CREATE INDEX ix_messages_status_created ON messages (status, created_at) 
WHERE status = 'pending';

CREATE INDEX ix_messages_processing_lease ON messages (status, lease_expires_at) 
WHERE status = 'processing';
```

---

## 4. Constraint Compatibility

| Constraint | PostgreSQL | MySQL 8.4 | Notes |
|------------|------------|-----------|-------|
| PRIMARY KEY | ✅ | ✅ | Direct |
| FOREIGN KEY | ✅ | ✅ | Direct (InnoDB) |
| UNIQUE | ✅ | ✅ | Direct |
| CHECK | ✅ (9.0+) | ✅ (8.0.16+) | **Use native_enum=False** |
| NOT NULL | ✅ | ✅ | Direct |
| DEFAULT | ✅ | ✅ | Direct |
| EXCLUSION | ✅ | ❌ | Not used |

---

## 5. SQL Function Compatibility

| Function | PostgreSQL | MySQL 8.4 | Migration |
|----------|------------|-----------|-----------|
| `now()` / `CURRENT_TIMESTAMP` | `TIMESTAMP WITH TIME ZONE` | `DATETIME` (session TZ) | Use app-layer `utcnow()` |
| `uuid_generate_v4()` | uuid-ossp ext | `UUID()` | Not used (Python UUID) |
| `jsonb_extract` / `->` | ✅ | ✅ (`->`, `->>`) | Compatible |
| `jsonb_set` | ✅ | ✅ (`JSON_SET`) | Compatible |
| `COALESCE` | ✅ | ✅ | Direct |
| `NULLIF` | ✅ | ✅ | Direct |
| `GREATEST/LEAST` | ✅ | ✅ | Direct |

---

## 6. Transaction Behavior Differences

| Behavior | PostgreSQL | MySQL (InnoDB) | Impact on Financial Code |
|----------|------------|----------------|-------------------------|
| Default Isolation | READ COMMITTED | REPEATABLE_READ | MySQL prevents phantoms |
| `SELECT FOR UPDATE` | Row locks | Next-key locks (row + gap) | More lock contention |
| `SELECT FOR UPDATE SKIP LOCKED` | ✅ 9.5+ | ✅ 8.0+ | **Use for worker claiming** |
| `SELECT FOR UPDATE NOWAIT` | ✅ | ✅ | Compatible |
| Deadlock Detection | ✅ | ✅ | Auto-rollback one TX |
| Savepoints | ✅ | ✅ | Compatible |
| Serializable Isolation | Predicate locking | Gap locking | Different but both strict |

### Financial Code Impact Analysis

```python
# ledger.py - Current patterns (MySQL compatible)

# 1. Row locking for duplicate detection - WORKS
existing = db.execute(select(Transaction).where(...).with_for_update()).scalar_one_or_none()

# 2. Worker message claiming - NEEDS SKIP LOCKED
# CURRENT (may block):
message = db.execute(select(Message).where(...).with_for_update()).scalar_one_or_none()
# MYSQL FIX:
message = db.execute(select(Message).where(...).with_for_update(skip_locked=True)).scalar_one_or_none()

# 3. Idempotency recovery - WORKS
# Uses message_id lookup after IntegrityError

# 4. Balance calculation - WORKS (read-only)
entries = db.execute(select(LedgerEntry).join(Transaction)...).scalars().all()
```

---

## 7. Migration Risk Assessment

### HIGH RISK (Must Test Thoroughly)

| Risk | Description | Mitigation |
|------|-------------|------------|
| **DECIMAL Precision** | Financial calculations must be exact | Explicit `DECIMAL(18,2)`; test boundary values |
| **Next-key Locking** | MySQL locks gaps, may cause deadlocks | Use `SKIP LOCKED` for worker claiming; test concurrency |
| **Timezone Handling** | MySQL DATETIME has no TZ; app must use UTC | All datetimes UTC in app; verify `utcnow()` |
| **Partial Indexes** | Syntax differs (`mysql_where`) | Rewrite all 3 partial indexes in alembic |

### MEDIUM RISK

| Risk | Description | Mitigation |
|------|-------------|------------|
| **JSONB → JSON** | Different storage, similar API | Test JSON queries; use `->>` for text extraction |
| **Enum CHECK Constraints** | MySQL 8.0.16+ required | Verify MySQL version; test enum validation |
| **Connection Pooling** | MySQL wait_timeout default 8h | Set `pool_recycle=3600`; `pool_pre_ping=True` |
| **Worker Concurrency** | Gap locks may increase deadlocks | Implement retry with backoff |

### LOW RISK

| Risk | Description | Mitigation |
|------|-------------|------------|
| **String PKs** | `String(36)` works on both | No change needed |
| **Foreign Keys** | InnoDB supports FK | No change needed |
| **Unique Constraints** | Standard SQL | No change needed |
| **Standard Indexes** | B-tree compatible | No change needed |

---

## 8. Required Alembic Migration Rewrites

### 0001_initial.py
- **Change**: Ensure MySQL dialect creates correct types
- **Action**: Test `Base.metadata.create_all()` on MySQL

### 0002_add_messages_and_message_id.py
- **Changes Required**:
  1. `postgresql.JSONB` → `sa.JSON` (or `mysql.JSON`)
  2. `postgresql_where` → `mysql_where` for 3 indexes
  3. `server_default=sa.func.now()` → MySQL `CURRENT_TIMESTAMP(6)`
  4. `DateTime(timezone=True)` → `DateTime(timezone=True).with_variant(DATETIME(6), "mysql")`

### 0003_add_recall_tokens.py
- **Changes Required**:
  1. `server_default=sa.func.now()` → MySQL `CURRENT_TIMESTAMP(6)`
  2. `DateTime(timezone=True)` → MySQL variant

### 0004_add_worker_id_to_messages.py
- **Changes**: Minimal - standard SQL

### 0005_add_attachment_ids_and_ai_fields.py
- **Changes**: Minimal - `sa.JSON` already generic

---

## 9. Test Matrix for MySQL Validation

### 9.1 Schema Tests
| Test | Expected Result |
|------|-----------------|
| `alembic upgrade head` | All 5 migrations apply cleanly |
| `alembic check` | No pending migrations |
| `SHOW CREATE TABLE accounts` | `opening_balance DECIMAL(18,2)` |
| `SHOW CREATE TABLE transactions` | `amount DECIMAL(18,2)` |
| `SHOW CREATE TABLE ledger_entries` | `amount DECIMAL(18,2)` |
| `SHOW INDEX FROM messages` | 4 indexes including 2 partial |
| `DESCRIBE worker_status` | `metadata JSON` |
| `SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='users' AND COLUMN_NAME='role'` | `varchar(20)` with CHECK |

### 9.2 Financial Precision Tests
| Test | Input | Expected |
|------|-------|----------|
| Max DECIMAL(18,2) | 9999999999999999.99 | Stored exactly |
| Min DECIMAL(18,2) | -9999999999999999.99 | Stored exactly |
| Zero | 0.00 | Stored exactly |
| Two decimals | 123.45 | Stored exactly |
| Three decimals (should round/error) | 123.456 | **STRICT MODE: Error** |
| Confidence DECIMAL(5,4) | 0.9999 | Stored exactly |
| Confidence 5 decimals | 0.99999 | **STRICT MODE: Error** |

### 9.3 Concurrency Tests
| Test | Scenario | Expected |
|------|----------|----------|
| Worker claiming | 5 workers, 10 messages | Each message claimed once |
| Balance updates | 10 concurrent CREDITs | Final balance = sum |
| Idempotency | 100 parallel same request | 1 transaction created |
| Deadlock retry | Forced deadlock | Retry succeeds |

---

## 10. MySQL-Specific Optimizations

### 10.1 JSON Column Indexing (If Needed)
```sql
-- For frequent JSON queries, add virtual column + index
ALTER TABLE extracted_transactions 
ADD COLUMN confidence_idx DECIMAL(5,4) 
GENERATED ALWAYS AS (JSON_EXTRACT(field_confidences, '$.confidence')) STORED,
ADD INDEX idx_confidence (confidence_idx);
```

### 10.2 Covering Indexes for Common Queries
```sql
-- Message polling query
CREATE INDEX ix_messages_polling ON messages (status, created_at, conversation_id)
WHERE status IN ('pending', 'processing');

-- Ledger balance query
CREATE INDEX ix_ledger_balance ON ledger_entries (effective_at, created_at)
WHERE status = 'VERIFIED';
```

---

## 11. Rollback Plan

If MySQL migration fails validation:

1. **Stop** - Do not proceed to Phase 7
2. **Document** - Record all failures in `17_mysql_test_results.md`
3. **Revert** - `git checkout` to pre-Phase-6 state
4. **Analyze** - Root cause each failure
5. **Fix** - Address in new migration attempt
6. **Re-test** - Full test suite on MySQL

**No production data migration in Phase 6** - Only fresh initialization tested.

---

**Status: COMPATIBILITY MATRIX COMPLETE - Ready for Schema Design**