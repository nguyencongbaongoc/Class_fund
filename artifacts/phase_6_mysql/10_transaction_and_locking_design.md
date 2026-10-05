# Phase 6 Transaction and Locking Design

## Overview
This document defines the transaction isolation, locking strategy, and concurrency control mechanisms for MySQL 8.4 InnoDB to preserve all financial invariants under concurrent access.

---

## 1. Transaction Isolation Levels

### 1.1 MySQL InnoDB Default: REPEATABLE READ

```python
# app/db/session.py
engine = create_engine(
    settings.database_url,
    isolation_level="REPEATABLE_READ",  # Explicit for clarity
    ...
)
```

**Characteristics:**
- Prevents dirty reads, non-repeatable reads, phantom reads
- Uses next-key locking (row + gap) for `SELECT FOR UPDATE`
- Consistent snapshot for duration of transaction
- **Risk:** Gap locks can cause more deadlocks under high concurrency

### 1.2 Alternative: READ COMMITTED (If Needed)

```python
# Only if REPEATABLE_READ causes excessive deadlocks
isolation_level="READ_COMMITTED"
```

**Trade-offs:**
- Allows phantom reads (new rows visible in subsequent reads)
- Fewer gap locks → fewer deadlocks
- Requires application-level handling for phantoms

**Decision:** Start with **REPEATABLE_READ** (InnoDB default). Monitor deadlock rate. Switch only if proven necessary.

---

## 2. Locking Patterns

### 2.1 Current Locking in ledger.py

| Operation | Lock Type | Purpose |
|-----------|-----------|---------|
| Duplicate transaction check | `SELECT FOR UPDATE` | Prevent concurrent duplicate bank transactions |
| Campaign member update | `SELECT FOR UPDATE` | Prevent double payment to same member |
| Idempotency recovery | `SELECT FOR UPDATE` (on retry) | Recover from ambiguous commit |

### 2.2 Required MySQL Enhancements

#### 2.2.1 Worker Message Claiming - ADD SKIP LOCKED

**Current (blocks):**
```python
# worker/main.py or messages.py
message = db.execute(
    select(Message)
    .where(Message.status == MessageStatus.PENDING.value)
    .order_by(Message.created_at)
    .with_for_update()  # Blocks if row locked
).scalar_one_or_none()
```

**MySQL Enhanced (non-blocking):**
```python
# worker/main.py - Updated for MySQL
message = db.execute(
    select(Message)
    .where(Message.status == MessageStatus.PENDING.value)
    .order_by(Message.created_at)
    .with_for_update(skip_locked=True)  # MySQL 8.0+, skips locked rows
).scalar_one_or_none()
```

**Benefits:**
- Workers don't block each other
- Each message claimed by exactly one worker
- No deadlock on message claiming

#### 2.2.2 Idempotency Check - NOWAIT Option

```python
# For high-contention idempotency checks
existing = db.execute(
    select(Transaction)
    .where(Transaction.bank_account_id == bank_account_id,
           Transaction.transaction_code == transaction_code)
    .with_for_update(nowait=True)  # Fail immediately if locked
).scalar_one_or_none()
```

---

## 3. Deadlock Prevention and Handling

### 3.1 Deadlock Sources in MySQL

| Source | Description | Mitigation |
|--------|-------------|------------|
| Gap locks | Next-key locking locks gaps between rows | Use `SKIP LOCKED` for claiming |
| Lock ordering | Different transactions lock rows in different order | Consistent ordering (by PK) |
| Long transactions | Holding locks too long | Minimize transaction scope |
| Index locking | Secondary index locks + clustered index | Covering indexes |

### 3.2 Deadlock Retry Logic

```python
# app/services/ledger.py - Add deadlock retry decorator
import time
from sqlalchemy.exc import OperationalError
import pymysql.err

def retry_on_deadlock(max_retries=3, base_delay=0.1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    # MySQL deadlock error code: 1213
                    # Lock wait timeout: 1205
                    if hasattr(e, 'orig') and e.orig.args[0] in (1213, 1205):
                        db = args[0]  # Assume first arg is db session
                        db.rollback()
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(base_delay * (2 ** attempt))  # Exponential backoff
                    else:
                        raise
        return wrapper
    return decorator

# Usage on critical functions:
@retry_on_deadlock(max_retries=3)
def post_transaction(db: Session, ...) -> PostTransactionResult:
    ...

@retry_on_deadlock(max_retries=3)
def post_revert(db: Session, ...) -> PostTransactionResult:
    ...
```

### 3.3 Consistent Lock Ordering

```python
# Always lock in consistent order to prevent deadlocks:
# 1. accounts (by id)
# 2. transactions (by id)
# 3. ledger_entries (by id)
# 4. messages (by id)
# 5. campaign_members (by id)

# In post_transaction:
# - Locks transaction row (via duplicate check)
# - Locks campaign_member (if campaign payment)
# Order: transaction first, then campaign_member (consistent)

# In post_revert:
# - Locks original transaction
# - Locks original ledger_entry
# Order: transaction first, then ledger_entry (consistent)
```

---

## 4. Transaction Boundaries

### 4.1 Current Transaction Boundaries

```python
# ledger.py:post_transaction
def post_transaction(db: Session, ..., commit: bool = True) -> PostTransactionResult:
    # 1. Create Transaction + LedgerEntry (flush)
    db.add(tx)
    db.flush()
    db.add(entry)
    db.flush()
    
    # 2. Audit + Activity (flush)
    write_audit(...)
    emit_activity(...)
    
    # 3. Idempotency record (flush)
    save_idempotency(...)
    
    # 4. Commit (if requested)
    if commit:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Recovery logic
```

### 4.2 Transaction Scope Rules

| Rule | Implementation |
|------|----------------|
| Single financial operation = one transaction | `post_transaction`, `post_revert`, `verify_and_post_from_ai` |
| No nested transactions | SQLAlchemy doesn't support nested; use savepoints if needed |
| Read-only operations outside transaction | `calculate_balance()` uses plain SELECT |
| Explicit commit control | `commit` parameter for testing/recovery |

### 4.3 Savepoints for Partial Rollback

```python
# If needed for complex operations:
from sqlalchemy import event

@event.listens_for(Session, "after_begin")
def create_savepoint(session, transaction, connection):
    # Optional: Create savepoint at transaction start
    pass

# Usage:
try:
    db.begin_nested()  # SAVEPOINT
    # ... operations ...
    db.commit()  # RELEASE SAVEPOINT
except Exception:
    db.rollback()  # ROLLBACK TO SAVEPOINT
```

---

## 5. Connection Pool and Transaction Lifecycle

### 5.1 Pool Configuration for Concurrency

```python
# app/db/session.py
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,           # Base connections
    max_overflow=40,        # Burst capacity
    pool_pre_ping=True,     # Validate before use
    pool_recycle=3600,      # Recycle before MySQL wait_timeout
    pool_timeout=30,        # Max wait for connection
    future=True,
    isolation_level="REPEATABLE_READ",
)
```

### 5.2 Session Lifecycle per Request

```python
# FastAPI dependency (app/db/session.py)
def get_db():
    db = SessionLocal()
    try:
        yield db
        # If no exception: commit handled by route
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

**Route Responsibility:**
- Routes call `db.commit()` explicitly after successful operation
- Routes call `db.rollback()` on error (or let exception handler do it)
- `post_transaction(commit=True)` commits internally
- `post_transaction(commit=False)` for testing/recovery

---

## 6. Optimistic Locking (Alternative)

### 5.1 Version Column for High-Contention Entities

```python
# For entities with very high contention (e.g., account balance)
class Account(Base):
    ...
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    __table_args__ = (
        # Optimistic lock: UPDATE ... WHERE version = expected_version
    )

# Usage:
account = db.get(Account, account_id, with_for_update=True)  # Pessimistic
# OR
account = db.get(Account, account_id)
# Update with version check:
result = db.execute(
    update(Account)
    .where(Account.id == account_id, Account.version == account.version)
    .values(balance=new_balance, version=account.version + 1)
)
if result.rowcount == 0:
    raise OptimisticLockError("Concurrent modification")
```

**Decision:** Not needed for current workload. Pessimistic locking (`FOR UPDATE`) sufficient.

---

## 6. Long-Running Transactions

### 6.1 Avoid Long Transactions

| Anti-pattern | Solution |
|--------------|----------|
| HTTP request → DB transaction → External API call | Do external calls OUTSIDE transaction |
| Transaction spans multiple user interactions | Use idempotency keys, not long transactions |
| Batch processing in single transaction | Process in chunks, commit per chunk |

### 6.2 Current Long Transaction Check

```python
# verify_and_post_from_ai - calls post_transaction(commit=False)
# Then does campaign member update, payment match
# Then commits
# Duration: ~100-500ms (acceptable)

# Worker message processing:
# 1. Claim message (short)
# 2. Call Ollama (EXTERNAL - outside transaction!)
# 3. verify_and_post_from_ai (transaction)
# 4. Update message status (short)
```

**Good:** External AI call is outside database transaction.

---

## 7. Monitoring and Debugging

### 7.1 Lock Monitoring Queries

```sql
-- Current locks
SELECT * FROM performance_schema.data_locks 
WHERE OBJECT_SCHEMA = 'classfund';

-- Lock waits
SELECT * FROM performance_schema.data_lock_waits;

-- Deadlock history (if enabled)
SELECT * FROM information_schema.innodb_trx 
WHERE trx_state = 'LOCK WAIT';

-- Transaction status
SELECT * FROM information_schema.innodb_trx;
```

### 7.2 Application Metrics

```python
# Add to ledger.py for monitoring
import time
from functools import wraps

def measure_transaction_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.perf_counter() - start
            # Log slow transactions
            if duration > 1.0:  # > 1 second
                logger.warning(f"Slow transaction: {func.__name__} took {duration:.3f}s")
    return wrapper
```

---

## 8. Testing Concurrency

### 8.1 Test Scenarios

```python
# tests/test_concurrency_mysql.py
import threading
import concurrent.futures
from decimal import Decimal

def test_concurrent_balance_updates(mysql_db):
    """100 concurrent CREDITs to same account."""
    account = create_account(balance=0)
    
    def credit():
        return post_transaction(db, account=account, type=CREDIT, amount=Decimal("100"), ...)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(credit) for _ in range(100)]
        results = [f.result() for f in futures]
    
    # All should succeed
    assert all(r.status == SUCCESS for r in results)
    assert calculate_balance(db, account) == Decimal("10000")

def test_concurrent_posting_same_proposal(mysql_db):
    """Multiple workers try to post same AI proposal."""
    upload, extraction = create_high_confidence_extraction()
    
    def approve():
        return verify_and_post_from_ai(db, upload, extraction, account, idempotency_key="same")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(approve) for _ in range(10)]
        results = [f.result() for f in futures]
    
    # One SUCCESS, rest DUPLICATE
    success = [r for r in results if r.status == SUCCESS]
    duplicates = [r for r in results if r.status == DUPLICATE]
    assert len(success) == 1
    assert len(duplicates) == 9
    assert db.query(Transaction).count() == 1

def test_worker_claiming_no_double_claim(mysql_db):
    """Multiple workers claim messages concurrently."""
    messages = [create_message(status=PENDING) for _ in range(20)]
    
    def claim_worker(worker_id):
        claimed = []
        for _ in range(5):  # Each worker tries 5 times
            msg = db.execute(
                select(Message)
                .where(Message.status == PENDING)
                .order_by(Message.created_at)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()
            if msg:
                msg.status = PROCESSING
                msg.worker_id = worker_id
                db.commit()
                claimed.append(msg.id)
        return claimed
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(claim_worker, f"w{i}") for i in range(10)]
        all_claimed = [msg_id for f in futures for msg_id in f.result()]
    
    # No double claims
    assert len(all_claimed) == len(set(all_claimed))
    assert len(all_claimed) <= 20
```

### 8.2 Deadlock Injection Test

```python
def test_deadlock_retry(mysql_db):
    """Force deadlock and verify retry works."""
    # This is complex to test reliably
    # Alternative: Monitor deadlock count in production
    pass
```

---

## 9. Configuration Summary

### 9.1 MySQL Server Configuration

```ini
# my.cnf / docker command
[mysqld]
# Concurrency
innodb_thread_concurrency = 0
innodb_read_io_threads = 8
innodb_write_io_threads = 8

# Locking
innodb_lock_wait_timeout = 50  # Seconds (default 50)
innodb_deadlock_detect = ON    # Default ON

# Logging for debugging
innodb_print_all_deadlocks = ON  # Log deadlocks to error log
```

### 9.2 Application Configuration

```python
# app/core/config.py additions
class Settings(BaseSettings):
    ...
    # Database pool
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    
    # Retry
    db_deadlock_max_retries: int = 3
    db_deadlock_base_delay: float = 0.1
```

---

## 10. Verification Gates

| Test | Criteria | Tool |
|------|----------|------|
| Isolation level | REPEATABLE_READ active | `SELECT @@transaction_isolation` |
| SKIP LOCKED works | Workers don't block | Concurrent claim test |
| Deadlock retry | 3 retries with backoff | Inject deadlock |
| No lost updates | Balance correct under load | Concurrent balance test |
| Lock wait timeout | 50s max wait | `innodb_lock_wait_timeout` |
| Connection pool | No exhaustion under load | Load test |

---

**Status: TRANSACTION AND LOCKING DESIGN COMPLETE - Ready for Auth Replacement Design**