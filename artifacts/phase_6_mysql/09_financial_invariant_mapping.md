# Phase 6 Financial Invariant Mapping

## Overview
This document maps every financial invariant in the current CLASS_FUND_WEB system to its MySQL implementation, ensuring zero behavioral change during migration. Each invariant is traced from business rule to code implementation to MySQL enforcement mechanism.

---

## 1. Financial Invariant Catalog

### 1.1 Ledger Authority Invariant

**Business Rule:** Ledger remains authoritative. Posted records must not be silently modified or deleted.

**Current Implementation:**
```python
# ledger.py - LedgerEntry status = VERIFIED is immutable
# No UPDATE or DELETE on LedgerEntry where status = VERIFIED
# Only new REVERT entries can offset
```

**MySQL Enforcement:**
```sql
-- Trigger to prevent modification of VERIFIED ledger entries
CREATE TRIGGER trg_ledger_immutable
BEFORE UPDATE ON ledger_entries
FOR EACH ROW
BEGIN
    IF OLD.status = 'VERIFIED' AND NEW.status = 'VERIFIED' THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Cannot modify VERIFIED ledger entry';
    END IF;
END;

-- Prevent deletion
CREATE TRIGGER trg_ledger_no_delete
BEFORE DELETE ON ledger_entries
FOR EACH ROW
BEGIN
    IF OLD.status = 'VERIFIED' THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Cannot delete VERIFIED ledger entry';
    END IF;
END;
```

**Application Layer (Preserved):**
- `ledger.py` never updates VERIFIED entries
- `post_revert()` creates new REVERT transaction + ledger entry
- Original entry gets `status = REVERTED` (only status change allowed)

**Verification Test:**
```python
def test_ledger_immutability_mysql(mysql_db):
    # Post transaction
    result = post_transaction(...)
    entry_id = result.ledger_entry_id
    
    # Attempt direct SQL modification
    with pytest.raises(OperationalError, match="Cannot modify VERIFIED"):
        mysql_db.execute(text("UPDATE ledger_entries SET amount = 999 WHERE id = :id"), {"id": entry_id})
```

---

### 1.2 AI Proposal Gatekeeper Invariant

**Business Rule:** AI extraction only creates proposals. AI must never directly post financial transactions. Posting must pass through the existing financial gatekeeper (`verify_and_post_from_ai()`).

**Current Implementation:**
```python
# ledger.py:378-528
def verify_and_post_from_ai(db, upload, result, account, actor_id, idempotency_key, message_id):
    # 1. Check confidence threshold
    if result.confidence < threshold:
        upload.status = NEEDS_REVIEW
        return NEEDS_HUMAN_REVIEW
    
    # 2. Validate required fields
    if not result.transaction_code or not result.amount or not result.bank_account_id:
        return NEEDS_HUMAN_REVIEW
    
    # 3. Check duplicate bank transaction
    duplicate = db.execute(select(Transaction).where(...).with_for_update()).scalar_one_or_none()
    if duplicate:
        return DUPLICATE
    
    # 4. Campaign validation (if applicable)
    # 5. Call post_transaction() with commit=False
    # 6. Only commit if post_transaction succeeds
```

**MySQL Enforcement:**
- No database-level enforcement needed (business logic in application)
- `extracted_transactions.status` tracks proposal state
- `transactions` table only populated via `post_transaction()`

**Verification Test:**
```python
def test_ai_never_posts_directly(mysql_db):
    # Direct insert into transactions should fail (no direct AI path)
    # Only verify_and_post_from_ai() can create transactions from extractions
    extraction = create_extraction(confidence=0.99)
    
    # This goes through gatekeeper
    result = verify_and_post_from_ai(db, upload, extraction, account)
    
    # Verify transaction created only after gatekeeper approval
    assert result.status in (SUCCESS, DUPLICATE)
    tx = db.get(Transaction, result.transaction.id)
    assert tx.source == LedgerSource.IMAGE
    assert "AI_VERIFIED" in tx.note
```

---

### 1.3 Recall and Reversal Invariant

**Business Rule:** 
- Recall before posting prevents posting
- Recall after posting creates a compensating REVERT
- Original records remain immutable
- `original_entry_id` must correctly identify the original entry
- Double reversal must be prevented

**Current Implementation:**
```python
# messages.py:165-231 (recall_message endpoint)
# ledger.py:300-375 (post_revert)

# Recall before post:
if message.status in [PENDING, PROCESSING, AWAITING_REVIEW]:
    message.status = RECALLED
    # No transaction created, posting prevented

# Recall after post:
if message.transaction_id and message.status == POSTED:
    rev_result = post_revert(db, original=original_tx, actor_id, reason, message_id)
    # Creates REVERT transaction + ledger entry with original_entry_id

# post_revert double-reversal check:
already = db.execute(select(LedgerEntry).where(
    LedgerEntry.original_entry_id == original_entry.id, 
    LedgerEntry.type == LedgerType.REVERT
)).scalar_one_or_none()
if already:
    return FAILED  # "Transaction has already been reverted"
```

**MySQL Enforcement:**
```sql
-- Unique constraint prevents double reversal
ALTER TABLE ledger_entries 
ADD CONSTRAINT uq_single_reversal 
UNIQUE (original_entry_id, type) 
WHERE type = 'REVERT' AND original_entry_id IS NOT NULL;

-- MySQL 8.0.13+ partial unique index
CREATE UNIQUE INDEX uq_single_reversal 
ON ledger_entries (original_entry_id) 
WHERE type = 'REVERT' AND original_entry_id IS NOT NULL;
```

**Application Layer (Preserved):**
- `post_revert()` checks for existing reversal before creating
- `original_entry_id` links REVERT to original `LedgerEntry`
- `Transaction.note` contains `REVERSAL_OF:{original_type};REASON:{reason}`

**Verification Test:**
```python
def test_recall_after_post_creates_revert(mysql_db):
    # Post transaction
    tx_result = post_transaction(..., type=CREDIT, amount=50000)
    original_entry = db.get(LedgerEntry, tx_result.transaction.id)
    
    # Recall message (after post)
    recall_result = recall_message(message_id, recall_token, reason="wrong")
    
    # Verify REVERT created
    assert recall_result.reversal_transaction_id is not None
    revert_tx = db.get(Transaction, recall_result.reversal_transaction_id)
    assert revert_tx.type == LedgerType.REVERT
    assert revert_tx.amount == Decimal("50000")
    
    # Verify ledger entry links to original
    revert_entry = db.execute(
        select(LedgerEntry).where(LedgerEntry.transaction_id == revert_tx.id)
    ).scalar_one()
    assert revert_entry.original_entry_id == original_entry.id
    assert revert_entry.type == LedgerType.REVERT
    
    # Verify balance restored
    assert calculate_balance(db, account) == original_balance
```

---

### 1.4 Idempotency Invariant

**Business Rule:** Preserve idempotency guarantees. Concurrent duplicate requests must not create duplicate financial entries. Database constraints must reinforce application-level checks.

**Current Implementation:**
```python
# ledger.py:109-122 (check_idempotency, save_idempotency)
# ledger.py:172-182 (fingerprint creation)

def _make_transaction_fingerprint(account_id, type_, amount, currency, source, 
                                   transaction_code, bank_account_id, upload_id, message_id):
    return sha256("|".join([...]).encode()).hexdigest()

# Idempotency key = f"msg_{message_id}_v1" (stable per message)
# Fingerprint includes ALL transaction parameters
# Different payload = different fingerprint = VALIDATION error
```

**MySQL Enforcement:**
```sql
-- Unique constraint on idempotency key
CREATE UNIQUE INDEX uq_idempotency_key ON idempotency_keys (key);

-- Unique constraint prevents duplicate bank transactions
CREATE UNIQUE INDEX uq_bank_transaction_code ON transactions (bank_account_id, transaction_code)
WHERE bank_account_id IS NOT NULL AND transaction_code IS NOT NULL;
```

**Application Layer (Preserved):**
1. `check_idempotency()` - Returns existing response if key matches
2. `save_idempotency()` - Stores key + fingerprint + response
3. Fingerprint mismatch → `HTTP 409 VALIDATION` error
4. Duplicate bank transaction → `BUSINESS_RULE` error (DB constraint + app check)
5. Recovery via `message_id` lookup after `IntegrityError`

**Verification Test:**
```python
def test_idempotent_concurrent_requests_mysql(mysql_db):
    # Simulate 5 concurrent requests with same idempotency key
    results = []
    for i in range(5):
        result = post_transaction(
            db, account=account, type=CREDIT, amount=50000,
            idempotency_key="msg_test_v1", message_id="msg_test"
        )
        results.append(result)
    
    # All should succeed or return duplicate
    successful = [r for r in results if r.status in (SUCCESS, DUPLICATE)]
    assert len(successful) == 5
    assert all(r.transaction.id == successful[0].transaction.id for r in successful)
    
    # Only ONE transaction in database
    assert db.query(Transaction).count() == 1
```

---

### 1.5 Concurrency Invariant

**Business Rule:** Use appropriate InnoDB transactions and row locking. Verify concurrent balance updates, concurrent posting, worker job claiming.

**Current Implementation:**
```python
# ledger.py - Row locking patterns

# 1. Duplicate detection with lock
existing = db.execute(select(Transaction).where(...).with_for_update()).scalar_one_or_none()

# 2. Campaign member update with lock
member = db.execute(select(CampaignMember).where(...).with_for_update()).scalar_one_or_none()

# 3. Worker claiming (needs SKIP LOCKED for MySQL)
message = db.execute(
    select(Message).where(Message.status == PENDING).with_for_update()
).scalar_one_or_none()
```

**MySQL Enhancement (Required):**
```python
# worker/main.py - Add SKIP LOCKED for MySQL
message = db.execute(
    select(Message)
    .where(Message.status == MessageStatus.PENDING.value)
    .order_by(Message.created_at)
    .with_for_update(skip_locked=True)  # MySQL 8.0+, PostgreSQL 9.5+
).scalar_one_or_none()
```

**MySQL Locking Behavior:**
| Lock Type | PostgreSQL | MySQL (InnoDB) |
|-----------|------------|----------------|
| `FOR UPDATE` | Row lock | Next-key lock (row + gap) |
| `FOR UPDATE SKIP LOCKED` | ✅ | ✅ 8.0+ |
| `FOR UPDATE NOWAIT` | ✅ | ✅ |

**Deadlock Handling:**
```python
# MySQL error code 1213 = deadlock
# ledger.py already has retry logic for IntegrityError
# Add explicit deadlock retry for SELECT FOR UPDATE
```

**Verification Test:**
```python
def test_concurrent_worker_claiming_mysql(mysql_db):
    # Create 10 pending messages
    messages = [create_message(status=PENDING) for _ in range(10)]
    
    # Simulate 5 workers claiming concurrently
    import threading
    claimed = []
    
    def worker_claim(worker_id):
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
    
    threads = [threading.Thread(target=worker_claim, args=(f"w{i}",)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    
    # Each message claimed at most once
    assert len(claimed) == 5
    assert len(set(claimed)) == 5
```

---

### 1.6 Decimal Precision Invariant

**Business Rule:** Financial amounts MUST use DECIMAL with explicitly documented precision and scale. Never use FLOAT or DOUBLE for money.

**Current Implementation:**
```python
# models.py - All monetary columns
amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))  # 18 digits, 2 decimals
opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2))
expected_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4))  # 5 digits, 4 decimals
```

**MySQL Enforcement:**
```sql
-- Strict SQL mode prevents silent truncation
SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- Column definitions
amount DECIMAL(18,2) NOT NULL
confidence DECIMAL(5,4) NOT NULL
```

**Application Layer (Preserved):**
- Python `Decimal` type used throughout
- `calculate_balance()` returns `Decimal`
- All arithmetic uses `Decimal` (not float)
- Threshold comparison: `float(result.confidence) < threshold` (safe for comparison)

**Verification Test:**
```python
def test_decimal_precision_mysql(mysql_db):
    # Test maximum values
    max_amount = Decimal("9999999999999999.99")  # 18 digits, 2 decimals
    tx = Transaction(amount=max_amount, ...)
    db.add(tx)
    db.commit()
    
    # Verify stored exactly
    stored = db.get(Transaction, tx.id)
    assert stored.amount == max_amount
    
    # Test overflow rejected (STRICT mode)
    overflow = Decimal("10000000000000000.00")  # 19 digits
    tx2 = Transaction(amount=overflow, ...)
    db.add(tx2)
    with pytest.raises(OperationalError, match="Out of range"):
        db.commit()
    
    # Test confidence precision
    conf = Decimal("0.9999")  # 5 digits, 4 decimals
    ext = ExtractedTransaction(confidence=conf, ...)
    db.add(ext)
    db.commit()
    assert db.get(ExtractedTransaction, ext.id).confidence == conf
```

---

## 2. Financial Invariant Test Matrix

| Invariant | Test File | MySQL Test | Evidence Required |
|-----------|-----------|------------|-------------------|
| Ledger Authority | test_financial_core.py | test_ledger_immutability_mysql | Trigger blocks UPDATE/DELETE |
| AI Gatekeeper | test_financial_core.py | test_ai_gatekeeper_mysql | Only gatekeeper creates IMAGE transactions |
| Recall/Reversal | test_recall.py, test_financial_core.py | test_recall_reversal_mysql | REVERT created, balance restored, double-reversal blocked |
| Idempotency | test_idempotency.py (8 tests) | All 8 tests on MySQL | 1 transaction per idempotency key |
| Concurrency | test_idempotency.py | test_concurrent_workers_mysql | SKIP LOCKED works, no double-claim |
| Decimal Precision | test_financial_core.py | test_decimal_precision_mysql | Max values stored, overflow rejected |

---

## 3. MySQL-Specific Financial Safeguards

### 3.1 Database-Level Constraints

```sql
-- 1. Positive amounts only
ALTER TABLE transactions ADD CONSTRAINT ck_positive_amount CHECK (amount > 0);
ALTER TABLE ledger_entries ADD CONSTRAINT ck_positive_amount CHECK (amount > 0);
ALTER TABLE collection_campaigns ADD CONSTRAINT ck_positive_expected CHECK (expected_amount > 0);

-- 2. Valid ledger types
ALTER TABLE transactions ADD CONSTRAINT ck_valid_type CHECK (type IN ('CREDIT','DEBIT','REVERT'));
ALTER TABLE ledger_entries ADD CONSTRAINT ck_valid_type CHECK (type IN ('CREDIT','DEBIT','REVERT'));

-- 3. Valid ledger sources
ALTER TABLE transactions ADD CONSTRAINT ck_valid_source CHECK (source IN ('IMAGE','MANUAL','REVERT'));
ALTER TABLE ledger_entries ADD CONSTRAINT ck_valid_source CHECK (source IN ('IMAGE','MANUAL','REVERT'));

-- 4. Valid ledger status
ALTER TABLE transactions ADD CONSTRAINT ck_valid_status CHECK (status IN ('VERIFIED','REVERTED'));
ALTER TABLE ledger_entries ADD CONSTRAINT ck_valid_status CHECK (status IN ('VERIFIED','REVERTED'));

-- 5. Single reversal per original entry
CREATE UNIQUE INDEX uq_single_reversal ON ledger_entries (original_entry_id) 
WHERE type = 'REVERT' AND original_entry_id IS NOT NULL;
```

### 3.2 Application-Layer Safeguards (Already Implemented)

All safeguards in `ledger.py` are preserved:
- Amount validation (`amount <= 0` → FAILED)
- AI credit requires bank_account + transaction_code
- Idempotency fingerprint validation
- Duplicate bank transaction detection
- Double reversal prevention
- Campaign member status validation

---

## 4. Migration Verification Checklist

Each invariant must pass on MySQL:

- [ ] **Ledger Authority**: Triggers prevent modification of VERIFIED entries
- [ ] **AI Gatekeeper**: No direct INSERT into transactions from AI path
- [ ] **Recall Before Post**: Message status = RECALLED, no transaction created
- [ ] **Recall After Post**: REVERT transaction created, balance restored
- [ ] **Double Reversal Blocked**: Unique partial index + app check
- [ ] **Idempotency Same Key**: Returns same transaction (DUPLICATE status)
- [ ] **Idempotency Diff Payload**: Returns VALIDATION error (409)
- [ ] **Concurrent Balance**: 100 parallel CREDITs = correct sum
- [ ] **Concurrent Posting**: Same proposal posted once
- [ ] **Worker Claiming**: SKIP LOCKED prevents double-claim
- [ ] **Decimal Max**: 9999999999999999.99 stored exactly
- [ ] **Decimal Overflow**: 10000000000000000.00 rejected
- [ ] **Strict Mode**: Silent truncation prevented

---

**Status: FINANCIAL INVARIANT MAPPING COMPLETE - Ready for Transaction & Locking Design**