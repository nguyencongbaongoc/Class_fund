# Phase 6 ORM Migration Report

## Overview
This document details the changes required to migrate SQLAlchemy ORM models and queries from PostgreSQL to MySQL 8.4 compatibility. All changes are backward-compatible where possible.

---

## 1. Model Changes Summary

### 1.1 Files Modified
- `app/models/models.py` - Core model definitions
- `app/db/base.py` - Base class with MySQL type variants
- `app/db/session.py` - Engine configuration for MySQL

### 1.2 Key Changes

| Change | PostgreSQL | MySQL | Files |
|--------|------------|-------|-------|
| DateTime timezone | `DateTime(timezone=True)` | `.with_variant(DATETIME(6), "mysql")` | models.py |
| JSON columns | `JSON` (maps to JSONB) | `JSON.with_variant(MYSQL_JSON, "mysql")` | models.py |
| Partial indexes | `postgresql_where` | `mysql_where` | models.py |
| Enum handling | `Enum(..., native_enum=False)` | Same (VARCHAR+CHECK) | models.py |
| Numeric precision | `Numeric(18,2)` | Same (maps to DECIMAL) | models.py |

---

## 2. Detailed Model Modifications

### 2.1 DateTime Columns (All Tables)

**Before:**
```python
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

**After:**
```python
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy import DateTime

created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
    default=utcnow
)
```

**Affected Columns:** All `created_at`, `updated_at`, `effective_at`, `expires_at`, `used_at`, `revoked_at`, `claimed_at`, `lease_expires_at`, `processed_at`, `last_heartbeat`, `last_processed_at`, `reviewed_at`, `start_at`, `end_at`, `transaction_time` across all 18 tables.

### 2.2 JSON Columns

**Before:**
```python
from sqlalchemy import JSON
aliases: Mapped[list | None] = mapped_column(JSON, nullable=True)
```

**After:**
```python
from sqlalchemy import JSON
from sqlalchemy.dialects.mysql import JSON as MYSQL_JSON

aliases: Mapped[list | None] = mapped_column(
    JSON.with_variant(MYSQL_JSON, "mysql"), 
    nullable=True
)
```

**Affected Columns:**
- `students.aliases`
- `extracted_transactions.field_confidences`
- `messages.attachment_ids`
- `worker_status.metadata` (was JSONB in PG migration)
- `audit_logs.before_data`, `after_data`
- `idempotency_keys.response_body`

### 2.3 Partial Indexes (Message Table)

**Before:**
```python
Index("ix_messages_status_created", "status", "created_at", 
      postgresql_where=text("status = 'pending'")),
Index("ix_messages_processing_lease", "status", "lease_expires_at", 
      postgresql_where=text("status = 'processing'")),
```

**After:**
```python
Index("ix_messages_status_created", "status", "created_at", 
      mysql_where=text("status = 'pending'")),
Index("ix_messages_processing_lease", "status", "lease_expires_at", 
      mysql_where=text("status = 'processing'")),
```

### 2.4 Enum Columns

**No change required** - `Enum(..., native_enum=False)` works on both:
- PostgreSQL: Creates VARCHAR with CHECK constraint
- MySQL 8.0.16+: Creates VARCHAR with CHECK constraint

**Verification:** MySQL version must be 8.0.16+ for CHECK constraint support.

---

## 3. Query Compatibility Analysis

### 3.1 SQLAlchemy ORM Queries (Compatible)

All existing ORM queries in `ledger.py`, route handlers, and services use standard SQLAlchemy 2.0 syntax:

```python
# These work identically on MySQL:
select(LedgerEntry).join(Transaction, ...).where(...).order_by(...)
db.execute(select(Transaction).where(...).with_for_update())
db.get(Model, id)
db.scalars(select(Model).where(...)).all()
```

### 3.2 Raw SQL / Text Queries (Need Review)

**Found in codebase:**
- `postgresql_where` in Index definitions (models.py) - **Fixed above**
- `sa.func.now()` in alembic migrations - **Rewrite migrations**
- No `text()` raw SQL in services/routes

### 3.3 Database Functions

| Function | PostgreSQL | MySQL | Status |
|----------|------------|-------|--------|
| `utcnow()` (Python) | ✅ | ✅ | Use Python function |
| `sa.func.now()` | Returns TZ-aware | Returns session TZ | **Avoid in models** |
| `uuid_generate_v4()` | Extension | `UUID()` | Not used (Python UUID) |

**Decision:** All timestamps generated in Python via `utcnow()` - no database defaults needed for created_at.

---

## 4. Session and Engine Configuration

### 4.1 Updated session.py

```python
# app/db/session.py - MySQL optimized
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # Critical for MySQL
    pool_recycle=3600,         # Recycle before wait_timeout
    pool_timeout=30,
    future=True,
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
        "use_unicode": True,
    },
    isolation_level="REPEATABLE_READ",  # InnoDB default
)

SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    class_=Session,
    expire_on_commit=False,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 4.2 Connection URL

```python
# app/core/config.py
database_url: str = "mysql+pymysql://classfund:${MYSQL_PASSWORD}@mysql:3306/classfund?charset=utf8mb4"
```

**Driver:** `pymysql` (pure Python) or `mysqlclient` (C extension)
- `pymysql`: Easier deployment, no system deps
- `mysqlclient`: Better performance, requires mysqlclient dev headers

---

## 5. Migration Impact on Services

### 5.1 ledger.py - Financial Core

**Impact: LOW** - All queries use SQLAlchemy ORM
- `calculate_balance()` - Read-only, uses joins and ordering
- `post_transaction()` - Uses `with_for_update()` for row locking
- `post_revert()` - Uses `with_for_update()` on transaction and ledger_entry
- `verify_and_post_from_ai()` - Uses `with_for_update()` for duplicate detection

**MySQL Considerations:**
- `with_for_update()` uses next-key locks (row + gap)
- Add `skip_locked=True` for worker message claiming (new)
- Deadlock retry logic already implemented

### 5.2 supabase_client.py - TO BE REMOVED

This entire file will be replaced (see auth/storage/realtime replacement designs).

### 5.3 ollama_client.py - No Database Changes

Pure HTTP client for AI vision - no database interaction.

### 5.4 audit.py, activity.py - Compatible

Standard ORM inserts - compatible.

---

## 6. Alembic Migration Strategy

### 6.1 Approach: Fresh MySQL Migrations

Since PostgreSQL migrations use PG-specific syntax, create new MySQL-specific migration history:

1. **Archive** existing `alembic/versions/` (keep for reference)
2. **Create** new `0001_initial_mysql.py` with all tables
3. **Configure** `alembic/env.py` for MySQL
4. **Test** fresh `alembic upgrade head` on MySQL

### 6.2 Alembic Environment (env.py)

```python
# alembic/env.py - Key MySQL settings
from alembic import context
from sqlalchemy import text

def run_migrations_online() -> None:
    connectable = engine_from_config(...)
    
    with connectable.connect() as connection:
        # MySQL session configuration
        connection.execute(text("SET time_zone = '+00:00'"))
        connection.execute(text(
            "SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,"
            "NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'"
        ))
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for MySQL ALTER TABLE
        )
        ...
```

### 6.3 render_as_batch=True

Required for MySQL because:
- MySQL doesn't support transactional DDL
- Batch mode groups operations
- Avoids "Can't DROP COLUMN" errors

---

## 7. Testing Strategy

### 7.1 Unit Tests (SQLite → MySQL)

**Current:** All tests use SQLite in-memory
**Required:** Add MySQL testcontainers for CI

```python
# tests/conftest.py - Add MySQL fixture
import testcontainers.mysql

@pytest.fixture(scope="session")
def mysql_container():
    container = testcontainers.mysql.MySqlContainer("mysql:8.4")
    container.start()
    yield container.get_connection_url()
    container.stop()

@pytest.fixture(scope="function")
def mysql_db(mysql_container):
    engine = create_engine(mysql_container, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
```

### 7.2 Financial Tests on MySQL

Must run all financial tests against real MySQL:
- `test_financial_core.py`
- `test_idempotency.py`
- `test_recall.py`
- `test_admin.py`
- Simulation tests

### 7.3 Concurrency Tests on MySQL

Critical for MySQL next-key locking behavior:
- Worker claiming with `SKIP LOCKED`
- Concurrent balance updates
- Idempotency under load
- Deadlock detection and retry

---

## 8. Code Changes Checklist

### 8.1 Models (models.py)
- [ ] Add MySQL imports (`DATETIME`, `VARCHAR`, `JSON as MYSQL_JSON`)
- [ ] Update all DateTime columns with `.with_variant(DATETIME(6), "mysql")`
- [ ] Update all JSON columns with `.with_variant(MYSQL_JSON, "mysql")`
- [ ] Change `postgresql_where` to `mysql_where` in Message indexes
- [ ] Verify all Enum columns use `native_enum=False`
- [ ] Verify all Numeric(18,2) columns for financial data

### 8.2 Database Config
- [ ] Update `app/core/config.py` database_url for MySQL
- [ ] Update `alembic.ini` sqlalchemy.url for MySQL
- [ ] Update `app/db/session.py` with MySQL pool settings
- [ ] Update `app/db/base.py` with MySQL type variants

### 8.3 Migrations
- [ ] Create new `0001_initial_mysql.py` with full schema
- [ ] Update `alembic/env.py` for MySQL session settings
- [ ] Archive old PostgreSQL migrations
- [ ] Test `alembic upgrade head` on clean MySQL

### 8.4 Dependencies
- [ ] Add `pymysql` or `mysqlclient` to `pyproject.toml`
- [ ] Remove `psycopg2` / `psycopg` from dependencies
- [ ] Add `testcontainers` to test dependencies

### 8.5 Docker
- [ ] Update `docker-compose.yml` with MySQL 8.4 service
- [ ] Add MySQL health check
- [ ] Configure MySQL command-line options

---

## 9. Rollback Plan

If ORM migration fails:

1. **Git revert** model changes
2. **Restore** PostgreSQL `docker-compose.yml`
3. **Restore** PostgreSQL `alembic.ini` and migrations
4. **Document** failures in `19_known_limitations.md`
5. **Analyze** root causes
6. **Retry** with fixes

---

## 10. Verification Commands

```bash
# 1. Check model compilation
python -c "from app.models.models import *; print('Models OK')"

# 2. Check alembic environment
cd class-fund-backend-v0.1/class-fund-backend && alembic check

# 3. Test fresh migration
alembic upgrade head

# 4. Verify schema
mysql -u classfund -p classfund -e "SHOW TABLES"
mysql -u classfund -p classfund -e "SHOW CREATE TABLE transactions\G"

# 5. Run financial tests
pytest tests/test_financial_core.py -v
pytest tests/test_idempotency.py -v
pytest tests/test_recall.py -v
```

---

**Status: ORM MIGRATION REPORT COMPLETE - Ready for Alembic Migration Report**