# Phase 6 PostgreSQL Dependency Inventory

## Overview
This document inventories all PostgreSQL-specific SQL, migrations, functions, triggers, policies, and extensions currently in use. This is distinct from Supabase dependencies - it covers the PostgreSQL database engine features that must be translated for MySQL 8.4 compatibility.

---

## 1. Alembic Migrations Analysis

### 0001_initial.py
```python
"""initial class fund schema"""
Base.metadata.create_all(bind=op.get_bind())
```
- **PostgreSQL-specific**: None directly (uses SQLAlchemy ORM)
- **Tables created**: All 17 tables via models.py
- **Risk**: Models contain PostgreSQL-specific constructs (see below)

### 0002_add_messages_and_message_id.py
```python
# PostgreSQL-specific elements:
1. postgresql.JSONB for worker_status.metadata (line 58)
2. postgresql_where partial indexes (lines 38-39, 42-44)
   - ix_messages_status_created WHERE status = 'pending'
   - ix_messages_processing_lease WHERE status = 'processing'
3. sa.func.now() for server_default (line 31)
```
- **MySQL 8.4 Equivalents**:
  - JSONB → JSON (MySQL 8.0+ native JSON)
  - Partial indexes → CREATE INDEX ... WHERE (MySQL 8.0.13+)
  - sa.func.now() → CURRENT_TIMESTAMP (timezone handling differs)

### 0003_add_recall_tokens.py
```python
# Standard SQL - no PostgreSQL-specific features
# sa.func.now() for server_default (line 18)
```

### 0004_add_worker_id_to_messages.py
```python
# Standard SQL - no PostgreSQL-specific features
```

### 0005_add_attachment_ids_and_ai_fields.py
```python
# sa.JSON for attachment_ids, field_confidences (lines 13, 19)
# sa.func.now() not used
# Standard indexes (no partial)
```

---

## 2. SQLAlchemy Models PostgreSQL-Specific Constructs

### 2.1 Enum Types (models.py lines 20-62)
```python
class Role(str, enum.Enum): ...
class LedgerType(str, enum.Enum): ...
class LedgerSource(str, enum.Enum): ...
class LedgerStatus(str, enum.Enum): ...
class UploadStatus(str, enum.Enum): ...
class CampaignStatus(str, enum.Enum): ...
class CampaignMemberStatus(str, enum.Enum): ...
class MessageStatus(str, enum.Enum): ...

# Column usage:
role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.MEMBER)
status: Mapped[UploadStatus] = mapped_column(Enum(UploadStatus, native_enum=False), default=UploadStatus.PENDING, index=True)
# ... all enums use native_enum=False
```

**PostgreSQL Behavior**: `native_enum=False` creates VARCHAR column with CHECK constraint
**MySQL Behavior**: Same - VARCHAR with CHECK constraint (MySQL 8.0.16+ supports CHECK)
**Risk**: LOW - Compatible with `native_enum=False`

### 2.2 JSON/JSONB Columns
```python
# models.py
aliases: Mapped[list | None] = mapped_column(JSON, nullable=True)  # students.aliases
field_confidences: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # extracted_transactions.field_confidences
attachment_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)  # messages.attachment_ids
metadata: Mapped[dict] = mapped_column(JSON, default=dict)  # worker_status.metadata (alembic uses JSONB)
before_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # audit_logs.before_data
after_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # audit_logs.after_data
response_body: Mapped[dict] = mapped_column(JSON)  # idempotency_keys.response_body
```

**PostgreSQL**: JSONB (binary, indexed, fast)
**MySQL 8.4**: JSON (native, indexed via virtual columns, fast)
**Risk**: LOW - SQLAlchemy `JSON` type maps to MySQL JSON

### 2.3 Timestamp with Timezone
```python
# All datetime columns use:
DateTime(timezone=True)
default=utcnow  # Python function returning datetime.now(timezone.utc)
# Alembic: server_default=sa.func.now()
```

**PostgreSQL**: `TIMESTAMP WITH TIME ZONE` - stores UTC, converts on read
**MySQL**: `TIMESTAMP` - stores UTC, converts on read (but only until 2038); `DATETIME(6)` - no timezone conversion
**Risk**: MEDIUM - Must use `DATETIME(6)` and handle timezone in application layer

### 2.4 Partial Indexes (models.py lines 281-286)
```python
__table_args__ = (
    Index("ix_messages_status_created", "status", "created_at", 
          postgresql_where=text("status = 'pending'")),
    Index("ix_messages_conversation_status_created", "conversation_id", "status", "created_at"),
    Index("ix_messages_processing_lease", "status", "lease_expires_at", 
          postgresql_where=text("status = 'processing'")),
    Index("ix_messages_worker_id", "worker_id"),
)
```

**PostgreSQL**: Partial indexes via `postgresql_where`
**MySQL 8.0.13+**: Partial indexes via `WHERE` clause in CREATE INDEX
**Migration**: Use `mysql_where` in SQLAlchemy 2.0+ or raw SQL in alembic

### 2.5 Numeric Precision (Financial)
```python
# All monetary amounts:
amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"))  # Account.opening_balance
amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # Transaction.amount, LedgerEntry.amount
expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # CollectionCampaign.expected_amount
confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)  # ExtractedTransaction.confidence
confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))  # PaymentMatch.confidence
```

**PostgreSQL**: `NUMERIC(18,2)` - exact decimal, arbitrary precision
**MySQL**: `DECIMAL(18,2)` - exact decimal, fixed precision (max 65 digits)
**Risk**: **CRITICAL** - Must preserve exact precision; test all financial calculations

### 2.6 UUID as String(36)
```python
# All primary keys and foreign keys:
id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
# Foreign keys:
uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
# ... all FKs are String(36)
```

**PostgreSQL**: Could use native UUID type, but using String(36) for compatibility
**MySQL**: CHAR(36) or BINARY(16) - String(36) works fine
**Risk**: LOW - Compatible

### 2.7 Unique Constraints
```python
# models.py
__table_args__ = (UniqueConstraint("campaign_id", "student_id", name="uq_campaign_student"),)  # CampaignMember
__table_args__ = (UniqueConstraint("bank_account_id", "transaction_code", name="uq_bank_transaction_code"),)  # Transaction
# upload_id unique on ExtractedTransaction
# transaction_id unique on LedgerEntry, PaymentMatch
# key unique on IdempotencyKey
# message_id unique on RecallToken
```

**PostgreSQL/MySQL**: Standard unique constraints - compatible

---

## 3. Database Functions and Triggers

### Current State: **NONE**
- No PostgreSQL functions defined in migrations
- No triggers defined in migrations
- All business logic in Python (ledger.py, services)
- No stored procedures

### Supabase RPC Calls (in supabase_client.py)
```python
def enable_rls(self, table: str):
    self.admin.rpc("enable_rls", {"table_name": table}).execute()

def create_policy(self, table: str, policy_name: str, definition: str, roles: list = None):
    self.admin.rpc("create_policy", {
        "table_name": table,
        "policy_name": policy_name,
        "definition": definition,
        "roles": roles or ["anon", "authenticated"]
    }).execute()
```
- These are **Supabase-specific RPC functions**, not PostgreSQL functions
- Not used in current codebase (no calls found)
- **Replacement**: Application-level authorization (already implemented)

---

## 4. Row Level Security (RLS) Policies

### Current State: **NOT ENABLED**
- No `ENABLE ROW LEVEL SECURITY` in migrations
- No policies created
- Supabase client has helpers but they're unused
- All authorization in application layer (FastAPI dependencies)

---

## 5. PostgreSQL Extensions

### Current State: **NONE REQUIRED**
- No `CREATE EXTENSION` in migrations
- No use of: pg_trgm, uuid-ossp, citext, pgcrypto, etc.
- UUID generation in Python (`uuid4_str()`)

---

## 6. Raw SQL Queries

### Search Results: **NONE FOUND**
- All queries use SQLAlchemy ORM (`select()`, `session.execute()`)
- No `text()` raw SQL in services/routes (except `postgresql_where` in indexes)
- No direct psycopg2 usage

---

## 7. Connection and Pool Settings

### Current (session.py)
```python
engine = create_engine(
    settings.database_url, 
    pool_pre_ping=True, 
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
```

### PostgreSQL Defaults
- Default isolation level: READ COMMITTED
- Connection pool: SQLAlchemy default (QueuePool, pool_size=5, max_overflow=10)

### MySQL 8.4 Requirements
- Isolation level: REPEATABLE READ (InnoDB default) - **must verify financial transactions work**
- Pool settings: Adjust for MySQL connection limits
- `pool_pre_ping=True` - essential for MySQL (handles stale connections)
- Consider `pool_recycle=3600` (MySQL default wait_timeout=28800)

---

## 8. Transaction Behavior Differences

| Aspect | PostgreSQL | MySQL (InnoDB) | Impact |
|--------|------------|----------------|--------|
| Default Isolation | READ COMMITTED | REPEATABLE READ | Phantom reads possible in PG, not MySQL |
| SELECT FOR UPDATE | Locks rows | Locks rows + gaps (next-key) | MySQL may have more lock contention |
| SELECT FOR UPDATE SKIP LOCKED | 9.5+ | 8.0+ | **Available in both** - use for worker claiming |
| NOWAIT | YES | YES | Compatible |
| Serializable | Predicate locking | Gap locking | Different behavior |
| Savepoints | YES | YES | Compatible |

### Financial Transaction Impact
```python
# ledger.py uses:
with_for_update()  # Row locking
# MySQL: Uses next-key locking (row + gap)
# Risk: Gap locks may cause more deadlocks under high concurrency
# Mitigation: Use SELECT FOR UPDATE SKIP LOCKED for worker claiming
```

---

## 9. MySQL 8.4 Specific Requirements

### SQL Mode (Strict)
```sql
-- Required for financial data integrity:
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
```

### Character Set and Collation
```sql
-- Database level:
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci

-- Connection:
charset=utf8mb4
```

### Timezone Configuration
```sql
-- Server timezone: UTC
-- Connection timezone: UTC
-- Application: All datetimes in UTC (already implemented via utcnow())
```

### InnoDB Settings
```ini
# Recommended for financial workload:
innodb_flush_log_at_trx_commit = 1
innodb_buffer_pool_size = 1G  # Adjust for RAM
innodb_log_file_size = 256M
innodb_file_per_table = ON
```

---

## 10. Migration Risk Matrix

| PostgreSQL Feature | MySQL 8.4 Support | Migration Effort | Risk Level |
|-------------------|-------------------|------------------|------------|
| VARCHAR + CHECK (enums) | Full (8.0.16+) | Low | LOW |
| JSON/JSONB | Full (native JSON) | Low | LOW |
| TIMESTAMP WITH TIME ZONE | DATETIME(6) + app TZ | Medium | MEDIUM |
| Partial Indexes | Full (8.0.13+) | Low | LOW |
| NUMERIC(18,2) | DECIMAL(18,2) | None | **CRITICAL - TEST** |
| UUID as String(36) | CHAR(36) | None | LOW |
| Unique Constraints | Full | None | LOW |
| Foreign Keys | Full | None | LOW |
| SELECT FOR UPDATE | Full (next-key) | None | MEDIUM |
| SELECT FOR UPDATE SKIP LOCKED | Full (8.0+) | None | LOW |
| Savepoints | Full | None | LOW |
| CTEs (WITH) | Full (8.0+) | None | LOW |
| Window Functions | Full (8.0+) | None | LOW |
| JSON Functions (->, ->>) | Full (8.0+) | Low | LOW |
| Generated Columns | Full (8.0+) | Low | LOW |

---

## 11. Required MySQL Schema Adjustments

### 11.1 Alembic Migration Rewrites Required

Each migration must be rewritten for MySQL:

| Migration | Changes Needed |
|-----------|----------------|
| 0001_initial | Base metadata create - ensure MySQL dialect |
| 0002_messages | Replace `postgresql.JSONB` with `sa.JSON`; Replace `postgresql_where` with `mysql_where`; Use `DATETIME(6)` |
| 0003_recall_tokens | Use `DATETIME(6)` |
| 0004_worker_id | No changes |
| 0005_ai_fields | Use `sa.JSON` (already generic) |

### 11.2 Model Adjustments (models.py)

```python
# 1. DateTime columns - specify MySQL variant
from sqlalchemy.dialects.mysql import DATETIME
# Use: DateTime(timezone=True).with_variant(DATETIME(6), "mysql")

# 2. Partial indexes - use mysql_where
Index("ix_messages_status_created", "status", "created_at", 
      mysql_where=text("status = 'pending'")),

# 3. Enum native_enum=False - keep (works on MySQL)

# 4. JSON columns - keep sa.JSON (maps to MySQL JSON)

# 5. Numeric(18,2) - keep (maps to DECIMAL(18,2))
```

### 11.3 New MySQL-Specific Alembic Environment

```python
# alembic/env.py - MySQL specific
from sqlalchemy.dialects.mysql import DATETIME

# In run_migrations_online:
# Ensure connection uses utf8mb4
```

---

## 12. Verification Tests Required

### Schema Tests
- [ ] Fresh MySQL initialization creates all 17 tables
- [ ] All 5 alembic migrations upgrade successfully
- [ ] All foreign keys enforce referential integrity
- [ ] All unique constraints prevent duplicates
- [ ] DECIMAL(18,2) preserves exact precision (test 9999999999999999.99)
- [ ] DECIMAL(5,4) preserves confidence precision
- [ ] Partial indexes created and used by optimizer
- [ ] JSON columns store and retrieve correctly
- [ ] DATETIME(6) stores microsecond precision

### Financial Tests (on MySQL)
- [ ] calculate_balance() returns exact Decimal
- [ ] post_transaction() commits atomically
- [ ] post_revert() creates correct REVERT entries
- [ ] verify_and_post_from_ai() gatekeeps correctly
- [ ] Idempotency prevents duplicates under concurrency
- [ ] Concurrent balance updates serialize correctly
- [ ] Double reversal prevented

### Performance Tests
- [ ] Worker claiming with SKIP LOCKED works
- [ ] Message polling uses partial indexes
- [ ] JSON queries perform adequately

---

## 13. Files Requiring Changes

| File | Change Type |
|------|-------------|
| `app/core/config.py` | MySQL database URL |
| `alembic.ini` | MySQL SQLAlchemy URL |
| `app/db/session.py` | MySQL engine options (pool_recycle, isolation_level) |
| `app/models/models.py` | MySQL variants for DateTime, partial indexes |
| `alembic/env.py` | MySQL connection config |
| `alembic/versions/0001_initial.py` | Verify MySQL compatibility |
| `alembic/versions/0002_add_messages_and_message_id.py` | Rewrite for MySQL |
| `alembic/versions/0003_add_recall_tokens.py` | Rewrite for MySQL |
| `alembic/versions/0004_add_worker_id_to_messages.py` | Verify |
| `alembic/versions/0005_add_attachment_ids_and_ai_fields.py` | Verify |
| `docker-compose.yml` | MySQL 8.4 service |
| `tests/conftest.py` | MySQL test database (testcontainers) |

---

**Status: INVENTORY COMPLETE - Ready for Compatibility Matrix**