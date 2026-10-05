# Phase 6 Alembic Migration Report

## Overview
This document details the Alembic migration strategy for migrating from PostgreSQL to MySQL 8.4, including migration design, implementation plan, and verification procedures.

---

## 1. Migration Strategy

### 1.1 Approach: Fresh MySQL Migration History

**Decision:** Create new MySQL-specific migration history rather than adapting PostgreSQL migrations.

**Rationale:**
- PostgreSQL migrations contain PG-specific syntax (`postgresql.JSONB`, `postgresql_where`, `sa.func.now()`)
- MySQL 8.4 has different DDL syntax and capabilities
- Clean migration history avoids technical debt
- Fresh initialization is the primary use case for Phase 6

### 1.2 Migration Structure

```
alembic/
├── env.py                 # MySQL-configured environment
├── script.py.mako         # Template (unchanged)
└── versions/
    └── 0001_initial_mysql.py   # Single comprehensive migration
```

### 1.3 Version Control

- PostgreSQL migrations archived in `alembic/versions_postgresql/`
- MySQL migrations start at `0001_initial_mysql`
- Alembic version table tracks MySQL schema version independently

---

## 2. Alembic Environment Configuration

### 2.1 env.py (MySQL Version)

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base
from app.models import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for MySQL
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Configure MySQL session
        connection.execute(text("SET time_zone = '+00:00'"))
        connection.execute(text(
            "SET sql_mode = 'STRICT_TRANS_TABLES,"
            "NO_ZERO_DATE,NO_ZERO_IN_DATE,"
            "ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'"
        ))
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for MySQL ALTER TABLE
            compare_type=True,     # Detect type changes
            compare_server_default=True,  # Detect default changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 2.2 alembic.ini (MySQL Version)

```ini
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = mysql+pymysql://classfund:${MYSQL_PASSWORD}@mysql:3306/classfund?charset=utf8mb4

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

---

## 3. Initial Migration: 0001_initial_mysql.py

### 3.1 Design Principles

1. **Single migration** - Creates all 18 tables in correct dependency order
2. **MySQL-native types** - Uses `DATETIME(6)`, `VARCHAR`, `JSON`, `DECIMAL`
3. **Explicit CHECK constraints** - For enum validation (MySQL 8.0.16+)
4. **Partial indexes** - Using `mysql_where` (MySQL 8.0.13+)
5. **InnoDB engine** - Explicit on all tables
6. **utf8mb4 charset** - Explicit on all tables

### 3.2 Table Creation Order (Dependency Respecting)

```python
# Order: Independent tables first, then dependent tables
TABLE_ORDER = [
    "revoked_tokens",      # Depends on users
    "users",               # No dependencies
    "accounts",            # No dependencies
    "bank_accounts",       # No dependencies
    "uploads",             # Depends on users
    "students",            # No dependencies
    "collection_campaigns",# No dependencies
    "campaign_members",    # Depends on campaigns, students
    "extracted_transactions", # Depends on uploads, bank_accounts, campaigns, students, users
    "transactions",        # Depends on accounts, bank_accounts, uploads, users, messages
    "ledger_entries",      # Depends on transactions, uploads, users
    "idempotency_keys",    # No dependencies
    "audit_logs",          # Depends on users
    "payment_matches",     # Depends on transactions, campaigns, students
    "messages",            # Depends on users, worker_status
    "worker_status",       # Depends on messages
    "recall_tokens",       # Depends on messages
    "chat_messages",       # Depends on users, ledger_entries
]
```

### 3.3 Key DDL Patterns

```python
# Standard table creation with MySQL options
op.create_table(
    "table_name",
    sa.Column("id", sa.String(36), primary_key=True),
    # ... columns ...
    mysql_charset="utf8mb4",
    mysql_collate="utf8mb4_unicode_ci",
    mysql_engine="InnoDB",
)

# Enum as VARCHAR + CHECK
sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
sa.CheckConstraint(
    "status IN ('PENDING','PROCESSING','NEEDS_REVIEW','VERIFIED','REJECTED','DUPLICATE')",
    name="ck_table_status"
),

# Partial index (MySQL 8.0.13+)
op.create_index(
    "ix_messages_status_created", "messages", ["status", "created_at"],
    mysql_where=sa.text("status = 'pending'")
)

# JSON column
sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),

# DATETIME(6) with UTC default
sa.Column("created_at", sa.dialects.mysql.DATETIME(6), 
          nullable=False, server_default=sa.text("CURRENT_TIMESTAMP(6)")),
```

---

## 4. Migration Operations Reference

### 4.1 Create Table with All MySQL Options

```python
def create_mysql_table(name, columns, **kwargs):
    """Helper to create table with standard MySQL options."""
    return op.create_table(
        name,
        *columns,
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
        **kwargs
    )
```

### 4.2 Enum Column Pattern

```python
def enum_column(name, values, default=None, nullable=False):
    """Create VARCHAR column with CHECK constraint for enum."""
    check_values = ",".join(f"'{v}'" for v in values)
    return [
        sa.Column(name, sa.String(30), nullable=nullable, 
                  server_default=default or values[0]),
        sa.CheckConstraint(f"{name} IN ({check_values})", name=f"ck_{name}"),
    ]
```

### 4.3 Timestamp Column Pattern

```python
def timestamp_column(name, nullable=False, default_now=True):
    """Create DATETIME(6) column with UTC timestamp."""
    col = sa.Column(
        name, 
        sa.dialects.mysql.DATETIME(6), 
        nullable=nullable
    )
    if default_now:
        col.server_default = sa.text("CURRENT_TIMESTAMP(6)")
    return col
```

### 4.4 Partial Index Pattern

```python
def partial_index(name, table, columns, where_clause):
    """Create partial index (MySQL 8.0.13+)."""
    return op.create_index(
        name, table, columns,
        mysql_where=sa.text(where_clause)
    )
```

---

## 5. Downgrade Strategy

### 5.1 Reversibility

| Operation | Reversible | Notes |
|-----------|------------|-------|
| CREATE TABLE | ✅ | DROP TABLE |
| CREATE INDEX | ✅ | DROP INDEX |
| CHECK Constraint | ✅ | DROP CONSTRAINT |
| FOREIGN KEY | ✅ | DROP FOREIGN KEY |
| UNIQUE Constraint | ✅ | DROP CONSTRAINT |

### 5.2 Downgrade Order (Reverse of Upgrade)

```python
def downgrade() -> None:
    # Reverse order - dependent tables first
    op.drop_table("chat_messages")
    op.drop_table("recall_tokens")
    op.drop_table("worker_status")
    op.drop_table("messages")
    op.drop_table("payment_matches")
    op.drop_table("audit_logs")
    op.drop_table("idempotency_keys")
    op.drop_table("ledger_entries")
    op.drop_table("transactions")
    op.drop_table("extracted_transactions")
    op.drop_table("campaign_members")
    op.drop_table("collection_campaigns")
    op.drop_table("students")
    op.drop_table("uploads")
    op.drop_table("bank_accounts")
    op.drop_table("accounts")
    op.drop_table("users")
    op.drop_table("revoked_tokens")
```

---

## 6. Migration Testing Procedures

### 6.1 Fresh Installation Test

```bash
# 1. Start MySQL container
docker-compose up -d mysql

# 2. Wait for health check
docker-compose ps mysql

# 3. Run migration
cd class-fund-backend-v0.1/class-fund-backend
alembic upgrade head

# 4. Verify
alembic current
alembic check

# 5. Inspect schema
mysql -u classfund -p classfund -e "SHOW TABLES"
mysql -u classfund -p classfund -e "SHOW CREATE TABLE transactions\G"
```

### 6.2 Schema Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| All tables exist | `SHOW TABLES` | 18 tables |
| Engine InnoDB | `SHOW TABLE STATUS` | All InnoDB |
| Charset utf8mb4 | `SHOW TABLE STATUS` | All utf8mb4 |
| DECIMAL(18,2) | `DESCRIBE transactions` | amount DECIMAL(18,2) |
| Partial indexes | `SHOW INDEX FROM messages` | 2 partial indexes |
| CHECK constraints | `SELECT * FROM INFORMATION_SCHEMA.CHECK_CONSTRAINTS` | 12+ constraints |
| Foreign keys | `SELECT * FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS` | 20+ FKs |

### 6.3 Data Integrity Test

```python
# tests/test_mysql_migration.py
def test_mysql_schema_integrity(mysql_db):
    """Verify MySQL schema matches expectations."""
    from sqlalchemy import inspect
    
    inspector = inspect(mysql_db.bind)
    
    # Check all tables
    tables = inspector.get_table_names()
    assert len(tables) == 18
    
    # Check financial tables have DECIMAL(18,2)
    for table in ['accounts', 'transactions', 'ledger_entries', 'collection_campaigns']:
        cols = {c['name']: c for c in inspector.get_columns(table)}
        if 'amount' in cols:
            assert 'DECIMAL(18,2)' in str(cols['amount']['type'])
        if 'opening_balance' in cols:
            assert 'DECIMAL(18,2)' in str(cols['opening_balance']['type'])
        if 'expected_amount' in cols:
            assert 'DECIMAL(18,2)' in str(cols['expected_amount']['type'])
    
    # Check partial indexes on messages
    indexes = inspector.get_indexes('messages')
    partial_indexes = [i for i in indexes if i.get('dialect_options', {}).get('mysql_where')]
    assert len(partial_indexes) == 2
    
    # Check CHECK constraints
    checks = inspector.get_check_constraints('users')
    assert any('role' in c['sqltext'] for c in checks)
```

---

## 7. Production Migration Considerations

### 7.1 Not in Phase 6 Scope

**Phase 6 only tests fresh initialization.** Production data migration requires:

1. **Export from PostgreSQL:**
   ```bash
   pg_dump --data-only --inserts --column-inserts classfund > pg_data.sql
   ```

2. **Transform data:**
   - Timestamp format conversion
   - Enum value validation
   - JSON/JSONB compatibility
   - UUID format verification

3. **Import to MySQL:**
   ```bash
   mysql -u classfund -p classfund < transformed_data.sql
   ```

4. **Verify:**
   - Row counts match
   - Checksums match
   - Financial reconciliation (ledger balance)

### 7.2 Zero-Downtime Strategy (Future)

1. Dual-write period
2. Read from both databases
3. Cutover reads to MySQL
4. Stop PostgreSQL writes
5. Final sync

---

## 8. Migration Commands Reference

```bash
# Development
alembic revision --autogenerate -m "description"  # Generate (if using models)
alembic upgrade head                               # Apply all
alembic downgrade -1                               # Rollback one
alembic current                                    # Show current
alembic history                                    # Show history
alembic check                                      # Check for pending

# Production
alembic upgrade head --sql > migration.sql         # Generate SQL for review
# Review migration.sql
# Execute manually or via CI/CD
```

---

## 9. Rollback Procedures

### 9.1 Development Rollback

```bash
alembic downgrade base  # Drop all tables
alembic upgrade head    # Recreate
```

### 9.2 Production Rollback (If Needed)

1. Stop application
2. Restore from mysqldump backup
3. Verify data integrity
4. Restart application

---

## 10. CI/CD Integration

### 10.1 GitHub Actions / GitLab CI

```yaml
# .github/workflows/mysql-migration-test.yml
name: MySQL Migration Test
on: [push, pull_request]
jobs:
  mysql-migration:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.4
        env:
          MYSQL_DATABASE: classfund
          MYSQL_USER: classfund
          MYSQL_PASSWORD: test
          MYSQL_ROOT_PASSWORD: root
        ports: ["3306:3306"]
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.12"}
      - run: pip install -e class-fund-backend-v0.1/class-fund-backend[test]
      - run: cd class-fund-backend-v0.1/class-fund-backend && alembic upgrade head
      - run: cd class-fund-backend-v0.1/class-fund-backend && pytest tests/ -v
```

---

## 11. Files to Create/Modify

| File | Action |
|------|--------|
| `alembic/env.py` | **REPLACE** with MySQL version |
| `alembic.ini` | **REPLACE** with MySQL URL |
| `alembic/versions/0001_initial_mysql.py` | **CREATE** new initial migration |
| `alembic/versions_postgresql/` | **CREATE** directory, move old migrations |
| `docker-compose.yml` | **REPLACE** PostgreSQL with MySQL |
| `app/core/config.py` | **UPDATE** database_url |
| `app/db/session.py` | **UPDATE** engine for MySQL |
| `tests/conftest.py` | **ADD** MySQL testcontainers fixture |

---

## 12. Verification Gates

| Gate | Criteria | Evidence |
|------|----------|----------|
| **Schema Creation** | `alembic upgrade head` succeeds | Migration output |
| **Table Count** | 18 tables created | `SHOW TABLES` |
| **Engine** | All InnoDB | `SHOW TABLE STATUS` |
| **Charset** | All utf8mb4_unicode_ci | `SHOW TABLE STATUS` |
| **Financial Precision** | DECIMAL(18,2) on money columns | `DESCRIBE` |
| **Partial Indexes** | 2 partial indexes on messages | `SHOW INDEX` |
| **CHECK Constraints** | All enums have constraints | `INFORMATION_SCHEMA` |
| **Foreign Keys** | All 20+ FKs enforced | `INFORMATION_SCHEMA` |
| **Tests Pass** | All financial tests on MySQL | pytest output |

---

**Status: ALEMBIC MIGRATION REPORT COMPLETE - Ready for Financial Invariant Mapping**