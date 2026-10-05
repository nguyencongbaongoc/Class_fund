# Phase 6 MySQL Test Results

## Overview
This document records the test results for MySQL 8.4 qualification. Tests must be run against an actual MySQL 8.4 instance (not SQLite).

---

## 1. Test Environment

| Component | Version |
|-----------|---------|
| MySQL | 8.4 LTS |
| Python | 3.12 |
| SQLAlchemy | 2.0.x |
| Alembic | 1.13.x |
| pymysql | 1.1.x |
| Test Framework | pytest |

---

## 2. Schema Tests

### 2.1 Fresh Initialization

| Test | Command | Expected | Result |
|------|---------|----------|--------|
| Create database | `mysql -e "CREATE DATABASE classfund"` | Success | [ ] PASS / [ ] FAIL |
| Run migrations | `alembic upgrade head` | All 18 tables created | [ ] PASS / [ ] FAIL |
| Verify tables | `SHOW TABLES` | 18 tables listed | [ ] PASS / [ ] FAIL |
| Verify engine | `SHOW TABLE STATUS` | All InnoDB | [ ] PASS / [ ] FAIL |
| Verify charset | `SHOW TABLE STATUS` | All utf8mb4_unicode_ci | [ ] PASS / [ ] FAIL |

### 2.2 Column Types Verification

| Table | Column | Expected Type | Actual Type | Result |
|-------|--------|---------------|-------------|--------|
| accounts | opening_balance | DECIMAL(18,2) | | [ ] PASS / [ ] FAIL |
| transactions | amount | DECIMAL(18,2) | | [ ] PASS / [ ] FAIL |
| ledger_entries | amount | DECIMAL(18,2) | | [ ] PASS / [ ] FAIL |
| collection_campaigns | expected_amount | DECIMAL(18,2) | | [ ] PASS / [ ] FAIL |
| extracted_transactions | amount | DECIMAL(18,2) | | [ ] PASS / [ ] FAIL |
| extracted_transactions | confidence | DECIMAL(5,4) | | [ ] PASS / [ ] FAIL |
| payment_matches | confidence | DECIMAL(5,4) | | [ ] PASS / [ ] FAIL |
| messages | created_at | DATETIME(6) | | [ ] PASS / [ ] FAIL |
| users | role | VARCHAR(20) + CHECK | | [ ] PASS / [ ] FAIL |
| worker_status | metadata | JSON | | [ ] PASS / [ ] FAIL |

### 2.3 Constraints Verification

| Constraint | Table | Columns | Result |
|------------|-------|---------|--------|
| PRIMARY KEY | All | id / jti / worker_id | [ ] PASS / [ ] FAIL |
| FOREIGN KEY | All | 20+ FKs | [ ] PASS / [ ] FAIL |
| UNIQUE | users | email | [ ] PASS / [ ] FAIL |
| UNIQUE | accounts | name | [ ] PASS / [ ] FAIL |
| UNIQUE | transactions | (bank_account_id, transaction_code) | [ ] PASS / [ ] FAIL |
| UNIQUE | ledger_entries | transaction_id | [ ] PASS / [ ] FAIL |
| UNIQUE | idempotency_keys | key | [ ] PASS / [ ] FAIL |
| CHECK | users | role IN (...) | [ ] PASS / [ ] FAIL |
| CHECK | uploads | status IN (...) | [ ] PASS / [ ] FAIL |
| CHECK | transactions | type IN (...) | [ ] PASS / [ ] FAIL |

### 2.4 Indexes Verification

| Index | Table | Columns | Type | Result |
|-------|-------|---------|------|--------|
| ix_users_email | users | email | UNIQUE | [ ] PASS / [ ] FAIL |
| ix_uploads_status | uploads | status | BTREE | [ ] PASS / [ ] FAIL |
| ix_messages_status_created | messages | (status, created_at) | PARTIAL (WHERE status='pending') | [ ] PASS / [ ] FAIL |
| ix_messages_processing_lease | messages | (status, lease_expires_at) | PARTIAL (WHERE status='processing') | [ ] PASS / [ ] FAIL |
| ix_messages_conversation_status_created | messages | (conversation_id, status, created_at) | BTREE | [ ] PASS / [ ] FAIL |
| ix_messages_worker_id | messages | worker_id | BTREE | [ ] PASS / [ ] FAIL |

---

## 3. Financial Precision Tests

### 3.1 DECIMAL(18,2) Boundary Tests

| Test | Input Value | Expected Behavior | Result |
|------|-------------|-------------------|--------|
| Max positive | 9999999999999999.99 | Stored exactly | [ ] PASS / [ ] FAIL |
| Max negative | -9999999999999999.99 | Stored exactly | [ ] PASS / [ ] FAIL |
| Zero | 0.00 | Stored exactly | [ ] PASS / [ ] FAIL |
| Two decimals | 12345.67 | Stored exactly | [ ] PASS / [ ] FAIL |
| Three decimals (strict) | 123.456 | **Error: Out of range** | [ ] PASS / [ ] FAIL |
| Overflow | 10000000000000000.00 | **Error: Out of range** | [ ] PASS / [ ] FAIL |

### 3.2 DECIMAL(5,4) Confidence Tests

| Test | Input Value | Expected Behavior | Result |
|------|-------------|-------------------|--------|
| Max confidence | 0.9999 | Stored exactly | [ ] PASS / [ ] FAIL |
| Min confidence | 0.0000 | Stored exactly | [ ] PASS / [ ] FAIL |
| Five decimals | 0.99999 | **Error: Out of range** | [ ] PASS / [ ] FAIL |

### 3.3 Financial Calculation Tests

| Test | Description | Expected | Result |
|------|-------------|----------|--------|
| Balance calculation | Sum of CREDIT - DEBIT + REVERT | Exact Decimal | [ ] PASS / [ ] FAIL |
| Large volume | 10000 transactions | No precision loss | [ ] PASS / [ ] FAIL |
| Concurrent updates | 100 parallel CREDITs | Final balance = sum | [ ] PASS / [ ] FAIL |

---

## 4. Transaction Tests

### 4.1 Basic Transaction Behavior

| Test | Scenario | Expected | Result |
|------|----------|----------|--------|
| Commit | Successful transaction | Data persisted | [ ] PASS / [ ] FAIL |
| Rollback | Exception in transaction | No data changed | [ ] PASS / [ ] FAIL |
| Failure before commit | Error after flush, before commit | No data changed | [ ] PASS / [ ] FAIL |
| Failure during commit | IntegrityError on commit | Rollback, recovery attempted | [ ] PASS / [ ] FAIL |

### 4.2 Atomic Multi-Table Operations

| Test | Operation | Tables Involved | Expected | Result |
|------|-----------|-----------------|----------|--------|
| post_transaction | CREDIT | transactions, ledger_entries, idempotency_keys, audit_logs, chat_messages | All or none | [ ] PASS / [ ] FAIL |
| post_revert | REVERT | transactions, ledger_entries (2), audit_logs | All or none | [ ] PASS / [ ] FAIL |
| verify_and_post_from_ai | AI post | transactions, ledger_entries, uploads, extracted_transactions, campaign_members, payment_matches, idempotency_keys | All or none | [ ] PASS / [ ] FAIL |

---

## 5. Financial Invariant Tests

### 5.1 Ledger Authority

| Test | Description | Expected | Result |
|------|-------------|----------|--------|
| VERIFIED immutability | UPDATE ledger_entries SET amount=X WHERE status=VERIFIED | Trigger blocks / App prevents | [ ] PASS / [ ] FAIL |
| VERIFIED no delete | DELETE FROM ledger_entries WHERE status=VERIFIED | Trigger blocks / App prevents | [ ] PASS / [ ] FAIL |
| REVERT creates new | Recall after post creates REVERT entry | New transaction + ledger entry | [ ] PASS / [ ] FAIL |

### 5.2 AI Gatekeeper

| Test | Description | Expected | Result |
|------|-------------|----------|--------|
| Low confidence blocked | confidence < 0.90 | NEEDS_HUMAN_REVIEW, no transaction | [ ] PASS / [ ] FAIL |
| Missing fields blocked | No transaction_code/amount/bank_account_id | NEEDS_HUMAN_REVIEW | [ ] PASS / [ ] FAIL |
| Duplicate bank tx blocked | Same bank_account_id + transaction_code | DUPLICATE status | [ ] PASS / [ ] FAIL |
| Campaign validation | Amount mismatch or member not found | NEEDS_HUMAN_REVIEW | [ ] PASS / [ ] FAIL |

### 5.3 Recall and Reversal

| Test | Description | Expected | Result |
|------|-------------|----------|--------|
| Recall before post | Message PENDING → RECALLED | No transaction created | [ ] PASS / [ ] FAIL |
| Recall after post | Message POSTED → RECALLED + REVERT | REVERT transaction created | [ ] PASS / [ ] FAIL |
| Double reversal blocked | Recall same message twice | Second fails: "already reverted" | [ ] PASS / [ ] FAIL |
| REVERT links original | REVERT ledger_entry.original_entry_id | Points to original VERIFIED entry | [ ] PASS / [ ] FAIL |
| Balance restored | Recall after CREDIT post | Balance = pre-post balance | [ ] PASS / [ ] FAIL |

### 5.4 Idempotency

| Test | Description | Expected | Result |
|------|-------------|----------|--------|
| Same key, same payload | 5 requests, same idempotency_key | 1 transaction, 1 SUCCESS + 4 DUPLICATE | [ ] PASS / [ ] FAIL |
| Same key, diff payload | Same key, different amount | VALIDATION error (409) | [ ] PASS / [ ] FAIL |
| Recovery after commit | Commit succeeded, response lost | Recovery via message_id | [ ] PASS / [ ] FAIL |
| Worker crash recovery | Worker dies after commit | Restart recovers via message_id | [ ] PASS / [ ] FAIL |

### 5.5 Concurrency

| Test | Description | Expected | Result |
|------|-------------|----------|--------|
| Concurrent balance | 100 parallel CREDITs | Final balance = sum | [ ] PASS / [ ] FAIL |
| Concurrent posting | 10 workers post same proposal | 1 SUCCESS, 9 DUPLICATE | [ ] PASS / [ ] FAIL |
| Worker claiming | 10 workers, 20 messages | Each message claimed once | [ ] PASS / [ ] FAIL |
| Lock timeout | Long transaction blocks others | Waits, then succeeds or timeout | [ ] PASS / [ ] FAIL |
| Deadlock handling | Forced deadlock | Retry with backoff succeeds | [ ] PASS / [ ] FAIL |

---

## 6. Recovery Tests

### 6.1 MySQL Restart

| Test | Procedure | Expected | Result |
|------|-----------|----------|--------|
| Graceful restart | `docker-compose restart mysql` | Connections recover, pool_pre_ping works | [ ] PASS / [ ] FAIL |
| Crash restart | `docker kill mysql` then start | No data corruption, transactions rolled back | [ ] PASS / [ ] FAIL |
| Connection pool | Backend survives MySQL restart | pool_pre_ping reconnects | [ ] PASS / [ ] FAIL |

### 6.2 Backup and Restore

| Test | Procedure | Expected | Result |
|------|-----------|----------|--------|
| Full backup | `mysqldump --single-transaction` | Backup file created, valid | [ ] PASS / [ ] FAIL |
| Full restore | Restore to empty MySQL | All tables, data intact | [ ] PASS / [ ] FAIL |
| Checksum match | CHECKSUM TABLE after restore | Matches pre-backup | [ ] PASS / [ ] FAIL |
| Financial reconciliation | calculate_balance() after restore | Matches pre-backup | [ ] PASS / [ ] FAIL |
| PITR | Restore + binlog to timestamp | Consistent state at timestamp | [ ] PASS / [ ] FAIL |

### 6.3 Cross-Architecture Restore

| Test | Procedure | Expected | Result |
|------|-----------|----------|--------|
| x86_64 → ARM64 | Backup on Windows, restore on macOS | All data intact | [ ] PASS / [ ] FAIL |
| ARM64 → x86_64 | Backup on macOS, restore on Windows | All data intact | [ ] PASS / [ ] FAIL |

---

## 7. Performance Tests (Baseline)

| Test | Metric | Target | Actual | Result |
|------|--------|--------|--------|--------|
| Simple SELECT | 1000 queries | < 100ms avg | | [ ] PASS / [ ] FAIL |
| INSERT transaction | 1000 inserts | < 500ms avg | | [ ] PASS / [ ] FAIL |
| Balance calculation | 10000 ledger entries | < 200ms | | [ ] PASS / [ ] FAIL |
| WebSocket broadcast | 100 concurrent clients | < 50ms latency | | [ ] PASS / [ ] FAIL |

---

## 8. Test Execution Log

```
# Run all tests:
cd class-fund-backend-v0.1/class-fund-backend
pytest tests/ -v --tb=short 2>&1 | tee test_results.log

# Run MySQL-specific tests:
pytest tests/ -v -k "mysql" --tb=short 2>&1 | tee mysql_test_results.log

# Run financial tests:
pytest tests/test_financial_core.py tests/test_idempotency.py tests/test_recall.py -v 2>&1 | tee financial_tests.log
```

---

## 9. Test Evidence

**Attach raw test outputs:**
- `artifacts/phase_6_mysql/raw/test_results.log`
- `artifacts/phase_6_mysql/raw/mysql_test_results.log`
- `artifacts/phase_6_mysql/raw/financial_tests.log`
- `artifacts/phase_6_mysql/raw/schema_verification.log`
- `artifacts/phase_6_mysql/raw/concurrency_tests.log`
- `artifacts/phase_6_mysql/raw/recovery_tests.log`

---

## 10. Summary

| Category | Tests Run | Passed | Failed | Skipped |
|----------|-----------|--------|--------|---------|
| Schema | | | | |
| Financial Precision | | | | |
| Transactions | | | | |
| Financial Invariants | | | | |
| Recovery | | | | |
| Performance | | | | |
| **TOTAL** | | | | |

**Overall Result:** [ ] ALL PASS / [ ] PARTIAL / [ ] FAIL

---

**Note:** This document must be filled with actual test results after running against MySQL 8.4.