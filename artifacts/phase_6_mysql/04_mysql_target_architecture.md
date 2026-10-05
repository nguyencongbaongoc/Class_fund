# Phase 6 MySQL Target Architecture

## Overview
This document defines the target MySQL 8.4 LTS architecture for CLASS_FUND_WEB, including configuration, connection management, transaction handling, and operational requirements.

---

## 1. MySQL Version and Edition

| Property | Value |
|----------|-------|
| **Version** | MySQL 8.4 LTS (Long Term Support) |
| **Storage Engine** | InnoDB (default, only supported) |
| **Character Set** | utf8mb4 |
| **Collation** | utf8mb4_unicode_ci (or utf8mb4_0900_ai_ci) |
| **Timezone** | UTC (server and connection) |
| **SQL Mode** | STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION |

---

## 2. Database Configuration

### 2.1 Docker Compose Service

```yaml
# docker-compose.yml (MySQL version)
services:
  mysql:
    image: mysql:8.4
    platform: linux/amd64  # For Apple Silicon compatibility
    environment:
      MYSQL_DATABASE: classfund
      MYSQL_USER: classfund
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}  # From .env
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}  # From .env
      TZ: UTC
    command:
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --default-time-zone=+00:00
      - --sql-mode=STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION
      - --innodb-buffer-pool-size=256M
      - --innodb-log-file-size=64M
      - --innodb-flush-log-at-trx-commit=1
      - --max-connections=200
    ports:
      - "3306:3306"  # Only for local dev; NOT exposed in production
    volumes:
      - classfund_mysql_data:/var/lib/mysql
      - ./mysql/init:/docker-entrypoint-initdb.d  # Optional init scripts
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "classfund", "-p${MYSQL_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

volumes:
  classfund_mysql_data:
```

### 2.2 SQLAlchemy Engine Configuration

```python
# app/db/session.py (MySQL version)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool
from app.core.config import get_settings

settings = get_settings()

# MySQL-specific engine options
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,           # Critical for MySQL - handles stale connections
    pool_recycle=3600,            # Recycle connections before MySQL wait_timeout (default 8h)
    pool_timeout=30,              # Wait up to 30s for connection from pool
    future=True,
    connect_args={
        "charset": "utf8mb4",
        "autocommit": False,
        "use_unicode": True,
    },
    isolation_level="REPEATABLE_READ",  # InnoDB default; explicit for clarity
)

SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    class_=Session,
    expire_on_commit=False  # Keep objects accessible after commit
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.3 Connection URL Format

```python
# app/core/config.py
database_url: str = "mysql+pymysql://classfund:${MYSQL_PASSWORD}@mysql:3306/classfund?charset=utf8mb4"
# For local dev without Docker:
# database_url: str = "mysql+pymysql://classfund:classfund@localhost:3306/classfund?charset=utf8mb4"
```

**Driver**: `pymysql` (pure Python, no system dependencies) or `mysqlclient` (C extension, faster)

---

## 3. Schema Design Decisions

### 3.1 Data Type Mapping

| PostgreSQL | MySQL 8.4 | SQLAlchemy | Notes |
|------------|-----------|------------|-------|
| `UUID` (native) | `CHAR(36)` | `String(36)` | Keep as string for portability |
| `TIMESTAMP WITH TIME ZONE` | `DATETIME(6)` | `DateTime(timezone=True).with_variant(DATETIME(6), "mysql")` | App handles UTC |
| `NUMERIC(18,2)` | `DECIMAL(18,2)` | `Numeric(18, 2)` | **Exact match for money** |
| `NUMERIC(5,4)` | `DECIMAL(5,4)` | `Numeric(5, 4)` | Confidence scores |
| `JSONB` | `JSON` | `JSON` | Native MySQL JSON |
| `TEXT` | `LONGTEXT` | `Text` | |
| `BOOLEAN` | `TINYINT(1)` | `Boolean` | |
| `ENUM` (native) | `VARCHAR + CHECK` | `Enum(..., native_enum=False)` | Portable |
| `BIGSERIAL` | `BIGINT AUTO_INCREMENT` | Not used (we use UUID strings) | |

### 3.2 Enum Handling

```python
# models.py - Keep native_enum=False for portability
from sqlalchemy import Enum
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy import CheckConstraint

# Option 1: SQLAlchemy Enum with native_enum=False (RECOMMENDED)
role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False), default=Role.MEMBER)

# Option 2: VARCHAR with CHECK constraint (more explicit)
# role: Mapped[str] = mapped_column(VARCHAR(20), default=Role.MEMBER.value)
# __table_args__ = (CheckConstraint("role IN ('OWNER_TREASURER','MODERATOR','MEMBER','PUBLIC')"),)
```

**Decision**: Use `Enum(..., native_enum=False)` - creates VARCHAR with CHECK constraint on MySQL 8.0.16+

### 3.3 Partial Indexes

```python
# models.py - Use mysql_where for MySQL 8.0.13+
from sqlalchemy import Index, text
from sqlalchemy.dialects.mysql import DATETIME

class Message(Base):
    __tablename__ = "messages"
    # ...
    __table_args__ = (
        Index("ix_messages_status_created", "status", "created_at", 
              mysql_where=text("status = 'pending'")),
        Index("ix_messages_conversation_status_created", "conversation_id", "status", "created_at"),
        Index("ix_messages_processing_lease", "status", "lease_expires_at", 
              mysql_where=text("status = 'processing'")),
        Index("ix_messages_worker_id", "worker_id"),
    )
```

### 3.4 DateTime with Microsecond Precision

```python
# models.py - Use MySQL variant for DATETIME(6)
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy import DateTime

# For all timestamp columns:
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True).with_variant(DATETIME(6), "mysql"), 
    default=utcnow
)
```

### 3.5 JSON Columns

```python
# models.py - SQLAlchemy JSON maps to MySQL JSON
from sqlalchemy import JSON

aliases: Mapped[list | None] = mapped_column(JSON, nullable=True)
field_confidences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
attachment_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
metadata: Mapped[dict] = mapped_column(JSON, default=dict)
before_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
after_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
response_body: Mapped[dict] = mapped_column(JSON)
```

---

## 4. Transaction and Locking Strategy

### 4.1 Isolation Level

```python
# InnoDB default: REPEATABLE_READ
# For financial transactions: REPEATABLE_READ (prevents phantom reads)
# Use explicit locking for critical sections
```

### 4.2 Row Locking Patterns

```python
# ledger.py - Existing patterns (compatible with MySQL)

# 1. SELECT FOR UPDATE - Row lock (MySQL: next-key lock)
existing = db.execute(select(Transaction).where(...).with_for_update()).scalar_one_or_none()

# 2. SELECT FOR UPDATE SKIP LOCKED - For worker job claiming (MySQL 8.0+)
# NEW: Add to worker message claiming
message = db.execute(
    select(Message)
    .where(Message.status == MessageStatus.PENDING.value)
    .order_by(Message.created_at)
    .with_for_update(skip_locked=True)  # MySQL 8.0+, PostgreSQL 9.5+
).scalar_one_or_none()

# 3. SELECT FOR UPDATE NOWAIT - Fail immediately if locked
# Use for idempotency checks where we don't want to wait
```

### 4.3 Deadlock Handling

```python
# MySQL InnoDB detects deadlocks automatically and rolls back one transaction
# Application must retry on deadlock error (error code 1213)

from sqlalchemy.exc import OperationalError
import pymysql.err

def execute_with_retry(db, operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except OperationalError as e:
            if e.orig.args[0] == 1213:  # Deadlock
                db.rollback()
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
            else:
                raise
```

---

## 5. Connection Pooling and Lifecycle

### 5.1 Pool Sizing

| Environment | pool_size | max_overflow | Rationale |
|-------------|-----------|--------------|-----------|
| Development | 5 | 10 | Low concurrency |
| Testing | 10 | 20 | Parallel test runs |
| Production | 20 | 40 | Based on CPU cores and expected load |

### 5.2 Connection Health

```python
# pool_pre_ping=True executes "SELECT 1" before each checkout
# Handles: MySQL server restart, network blips, wait_timeout expiry

# Additional: Monitor pool status
from sqlalchemy import event

@event.listens_for(engine, "checkout")
def check_connection(dbapi_conn, conn_record, conn_proxy):
    # Optional: Custom validation
    pass
```

### 5.3 Graceful Shutdown

```python
# In FastAPI lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    engine.dispose()  # Close all connections gracefully
```

---

## 6. Backup and Recovery

### 6.1 Logical Backup (mysqldump)

```bash
# Full backup with stored routines, triggers, events
mysqldump \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --hex-blob \
  --default-character-set=utf8mb4 \
  --master-data=2 \
  -u classfund -p classfund > backup_$(date +%Y%m%d_%H%M%S).sql

# For financial data consistency: --single-transaction ensures consistent snapshot
```

### 6.2 Point-in-Time Recovery

```bash
# Enable binary logging in MySQL config:
# log_bin = mysql-bin
# binlog_format = ROW
# expire_logs_days = 7

# Recovery:
# 1. Restore from mysqldump
# 2. Apply binary logs up to desired point:
mysqlbinlog --start-datetime="2026-10-04 10:00:00" mysql-bin.000001 | mysql -u classfund -p classfund
```

### 6.3 Backup Schedule (Three-Machine Compatibility)

| Machine | Role | Backup Method |
|---------|------|---------------|
| Machine A (Active) | Primary writer | mysqldump daily + binary logs |
| Machine B (Standby) | Read replica (future) | Not implemented in Phase 6 |
| Machine C (Offline) | Cold standby | Restore from backup when activated |

**Phase 6 Scope**: Single Active machine with mysqldump backup. Multi-machine replication is Phase 7+.

---

## 7. Security Configuration

### 7.1 User Accounts

```sql
-- Application user (limited privileges)
CREATE USER 'classfund'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON classfund.* TO 'classfund'@'%';
-- NO: DROP, ALTER, CREATE, GRANT OPTION

-- Admin user (for migrations only)
CREATE USER 'classfund_admin'@'%' IDENTIFIED BY '${MYSQL_ADMIN_PASSWORD}';
GRANT ALL PRIVILEGES ON classfund.* TO 'classfund_admin'@'%';
```

### 7.2 SSL/TLS

```yaml
# docker-compose.yml - For production
mysql:
  command:
    - --require-secure-transport=ON
  volumes:
    - ./mysql/ssl:/etc/mysql/ssl:ro
```

### 7.3 Password Policy

```sql
-- Enforce strong passwords
INSTALL COMPONENT 'file://component_validate_password';
SET GLOBAL validate_password.length = 32;
SET GLOBAL validate_password.mixed_case_count = 1;
SET GLOBAL validate_password.number_count = 1;
SET GLOBAL validate_password.special_char_count = 1;
```

---

## 8. Monitoring and Observability

### 8.1 Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Connection pool usage | < 70% | > 85% |
| Query latency (p95) | < 100ms | > 500ms |
| Deadlocks/min | 0 | > 5/min |
| Slow queries | 0 | > 10/min |
| Replication lag (future) | N/A | > 30s |
| Disk usage | < 70% | > 85% |

### 8.2 Slow Query Log

```ini
# MySQL config
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
log_queries_not_using_indexes = 1
```

---

## 9. Migration Strategy

### 9.1 Fresh Installation (New Environments)
1. Start MySQL container
2. Run `alembic upgrade head` - creates all tables with MySQL types
3. Verify schema with `alembic check`
4. Run test suite

### 9.2 Existing Data Migration (Not in Phase 6 Scope)
- Phase 6 assumes fresh database initialization
- Production data migration requires separate plan:
  1. Export from PostgreSQL: `pg_dump --data-only --inserts`
  2. Transform: Adjust types, enums, timestamps
  3. Import to MySQL: `mysql < transformed_data.sql`
  4. Verify: Row counts, checksums, financial reconciliation

---

## 10. Environment Configurations

### 10.1 Development (.env)
```bash
MYSQL_PASSWORD=dev_password_change_in_prod
MYSQL_ROOT_PASSWORD=dev_root_password
DATABASE_URL=mysql+pymysql://classfund:dev_password_change_in_prod@localhost:3306/classfund?charset=utf8mb4
```

### 10.2 Testing (testcontainers)
```python
# tests/conftest.py - Use testcontainers for real MySQL
import testcontainers.mysql

@session_scope
def mysql_container():
    container = testcontainers.mysql.MySqlContainer("mysql:8.4")
    container.start()
    yield container.get_connection_url()
    container.stop()
```

### 10.3 Production (Docker Swarm / Kubernetes)
```yaml
# Secrets from external secret manager
environment:
  MYSQL_PASSWORD_FILE: /run/secrets/mysql_password
  MYSQL_ROOT_PASSWORD_FILE: /run/secrets/mysql_root_password
```

---

## 11. InnoDB Tuning for Financial Workload

```ini
# my.cnf / docker command overrides
[mysqld]
# Durability - CRITICAL for financial data
innodb_flush_log_at_trx_commit = 1
sync_binlog = 1

# Buffer pool - size based on RAM (70-80%)
innodb_buffer_pool_size = 1G
innodb_buffer_pool_instances = 8

# Log files
innodb_log_file_size = 256M
innodb_log_files_in_group = 2

# Concurrency
innodb_thread_concurrency = 0  # Auto
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# File per table (easier management)
innodb_file_per_table = ON

# Page size (default 16K - keep)
# innodb_page_size = 16384

# Statistics
innodb_stats_persistent = ON
innodb_stats_auto_recalc = ON
```

---

## 12. Compatibility Checklist

| Feature | MySQL 8.4 Support | Implementation Status |
|---------|-------------------|----------------------|
| UTF8MB4 | ✅ Native | Configured |
| JSON | ✅ Native | Use `sa.JSON` |
| Partial Indexes | ✅ 8.0.13+ | Use `mysql_where` |
| CHECK Constraints | ✅ 8.0.16+ | Via `native_enum=False` |
| CTEs (WITH) | ✅ 8.0+ | SQLAlchemy compatible |
| Window Functions | ✅ 8.0+ | SQLAlchemy compatible |
| SKIP LOCKED | ✅ 8.0+ | Use in worker claiming |
| NOWAIT | ✅ | Available |
| Savepoints | ✅ | SQLAlchemy compatible |
| DECIMAL Precision | ✅ 65 digits | Use `DECIMAL(18,2)` |
| Timezone Support | ✅ | App-layer UTC |
| Generated Columns | ✅ 8.0+ | For JSON indexing if needed |

---

## 13. Files to Create/Modify

### New Files
1. `docker-compose.mysql.yml` - MySQL service definition
2. `mysql/init/01-init.sql` - Optional initialization (timezone, sql_mode)
3. `alembic/env.mysql.py` - MySQL-specific alembic environment (or modify env.py)
4. `tests/conftest.mysql.py` - MySQL test fixtures

### Modified Files
1. `app/core/config.py` - MySQL database URL
2. `alembic.ini` - MySQL SQLAlchemy URL
3. `app/db/session.py` - MySQL engine options
4. `app/models/models.py` - MySQL variants for DateTime, indexes
5. All 5 alembic versions - Rewrite for MySQL
6. `docker-compose.yml` - Replace PostgreSQL with MySQL
7. `.env.example` - MySQL environment variables
8. `tests/conftest.py` - MySQL test database
9. `pyproject.toml` - Add `pymysql` or `mysqlclient`

---

**Status: TARGET ARCHITECTURE DEFINED - Ready for Compatibility Matrix**