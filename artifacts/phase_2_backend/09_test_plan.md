# 09_TEST_PLAN.md

## Phase 2 Test Plan

**Status**: ✅ BASELINE TESTS PASS (20/20) — Phase 2 expansion defined
**Scope**: Financial core, idempotency, worker lifecycle, recall, API contracts, security

### 1. Test Categories

| Category | Baseline (Phase 1.2) | Phase 2 Expansion | Status |
|----------|---------------------|-------------------|--------|
| Financial Core | 4 tests | +5 tests | ✅/⏳ |
| Idempotency | 8 tests | +4 tests | ✅/⏳ |
| Recall Authorization | 8 tests | +3 tests | ✅/⏳ |
| Worker Lifecycle | 0 integration | +8 tests | ⏳ |
| API Contract | 0 | +12 tests | ⏳ |
| Security | 0 | +10 tests | ⏳ |
| Supabase Integration | 0 | +6 tests | BLOCKED |
| Concurrency | 1 (simulated) | +5 tests | ⏳/BLOCKED |

### 2. Baseline Tests (Already Passing)

#### 2.1 Financial Core (`test_financial_core.py` - 4 tests)
- [x] `test_credit_debit_and_balance` — Basic ledger operations
- [x] `test_revert_restores_balance_without_deleting_original` — Reversal logic
- [x] `test_ai_low_confidence_does_not_post` — Gatekeeper threshold
- [x] `test_ai_retry_same_upload_does_not_double_post` — Upload-level dedup

#### 2.2 Idempotency (`test_idempotency.py` - 8 tests)
- [x] `test_idempotent_same_key_same_payload` — Basic idempotency
- [x] `test_idempotent_different_retry_count_same_payload` — Retry stability
- [x] `test_idempotent_same_message_modified_amount_rejected` — Fingerprint mismatch
- [x] `test_different_message_same_bank_transaction` — Bank-level uniqueness
- [x] `test_concurrent_requests_no_double_post` — Concurrent simulation
- [x] `test_ambiguous_commit_recovery` — Recovery via message_id
- [x] `test_worker_crash_after_commit_recovery` — Restart recovery
- [x] `test_verify_and_post_from_ai_idempotent` — Gatekeeper idempotency

#### 2.3 Recall (`test_recall.py` - 8 tests)
- [x] `test_recall_token_generation_and_validation` — Token crypto
- [x] `test_recall_before_post` — No transaction created
- [x] `test_recall_after_post_creates_reversal` — Reversal on recall
- [x] `test_double_recall_prevented` — Used token rejected
- [x] `test_recall_token_replay_protection` — Replay attack prevention
- [x] `test_public_message_id_cannot_authorize_recall` — ID ≠ auth
- [x] `test_public_transaction_id_cannot_authorize_recall` — TX ID ≠ auth
- [x] `test_worker_checks_recall_before_posting` — Worker gate

### 3. Phase 2 Test Expansion

#### 3.1 Financial Core Additional Tests

| Test ID | Name | Description | Priority |
|---------|------|-------------|----------|
| FC-01 | `test_manual_credit_requires_idempotency` | POST /fund/credit rejects missing header | HIGH |
| FC-02 | `test_manual_debit_insufficient_balance` | Debit > balance → 409 | HIGH |
| FC-03 | `test_revert_requires_owner_role` | Non-owner → 403 | HIGH |
| FC-04 | `test_opening_balance_audit_trail` | Audit log written on balance change | MEDIUM |
| FC-05 | `test_multi_account_isolation` | Transactions scoped to account | MEDIUM |

#### 3.2 Idempotency Additional Tests

| Test ID | Name | Description | Priority |
|---------|------|-------------|----------|
| ID-01 | `test_idempotency_key_ttl_cleanup` | Expired keys can be cleaned | MEDIUM |
| ID-02 | `test_cross_account_same_key_rejected` | Same key different account → 409 | HIGH |
| ID-03 | `test_idempotency_fingerprint_includes_all_fields` | Verify fingerprint composition | MEDIUM |
| ID-04 | `test_concurrent_idempotency_postgres` | True concurrent test (PostgreSQL) | HIGH* |

*BLOCKED_EXTERNAL_DEPENDENCY - requires PostgreSQL

#### 3.3 Recall Additional Tests

| Test ID | Name | Description | Priority |
|---------|------|-------------|----------|
| RC-01 | `test_recall_token_expiry` | Expired token → 403 | MEDIUM |
| RC-02 | `test_recall_token_revocation` | Revoked token → 403 | MEDIUM |
| RC-03 | `test_admin_can_recall_without_token` | Admin bypass (if implemented) | LOW |

#### 3.4 Worker Lifecycle Tests (NEW - Critical)

| Test ID | Name | Description | Priority |
|---------|------|-------------|----------|
| WL-01 | `test_worker_startup_reclaims_stale` | Stale leases reset to pending | HIGH |
| WL-02 | `test_worker_claim_atomic_skip_locked` | Only one worker gets message | HIGH |
| WL-03 | `test_worker_lease_expiry_reclaim` | Expired lease → reclaimable | HIGH |
| WL-04 | `test_worker_graceful_shutdown` | SIGTERM → offline status | HIGH |
| WL-05 | `test_worker_heartbeat_updates` | Status updated per loop | MEDIUM |
| WL-06 | `test_worker_recall_during_processing` | Recall check prevents post | HIGH |
| WL-07 | `test_worker_exponential_backoff` | Retry delays: 60s, 120s, 240s | MEDIUM |
| WL-08 | `test_worker_crash_recovery_integration` | Full crash→restart→reprocess | HIGH* |

*BLOCKED_EXTERNAL_DEPENDENCY - requires PostgreSQL for true crash simulation

#### 3.5 API Contract Tests (NEW)

| Test ID | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| API-01 | `POST /messages` | Creates message, returns recall_token once | HIGH |
| API-02 | `POST /messages/{id}/recall` | Validates token, creates reversal if posted | HIGH |
| API-03 | `GET /messages/{id}` | Returns status without auth | HIGH |
| API-04 | `GET /messages?conversation_id=` | Lists with pagination | HIGH |
| API-05 | `GET /fund/balance` | Returns balance without auth | HIGH |
| API-06 | `GET /fund/transactions` | Lists with pagination | HIGH |
| API-07 | `POST /fund/credit` | Requires OWNER_TREASURER + Idempotency-Key | HIGH |
| API-08 | `POST /fund/debit` | Requires OWNER_TREASURER + balance check | HIGH |
| API-09 | `POST /fund/revert` | Requires OWNER_TREASURER + Idempotency-Key | HIGH |
| API-10 | `POST /uploads` | Accepts file, returns upload_id | HIGH |
| API-11 | `POST /internal/ai/uploads/{id}/result` | Service auth, idempotency, gatekeeper | HIGH |
| API-12 | `GET /health` | Returns component status | MEDIUM |

#### 3.6 Security Tests (NEW)

| Test ID | Name | Description | Priority |
|---------|------|-------------|----------|
| SEC-01 | `test_rate_limit_messages` | 31st request in minute → 429 | HIGH |
| SEC-02 | `test_rate_limit_uploads` | 11th request in minute → 429 | HIGH |
| SEC-03 | `test_file_type_validation` | Invalid MIME → 400 | HIGH |
| SEC-04 | `test_file_size_limit` | >10MB → 400 | HIGH |
| SEC-05 | `test_file_magic_bytes` | Fake extension → 400 | MEDIUM |
| SEC-06 | `test_cors_headers` | Allowed origin gets headers | MEDIUM |
| SEC-07 | `test_security_headers` | X-Content-Type-Options, etc. | MEDIUM |
| SEC-08 | `test_no_service_role_in_frontend` | Anon key only in client build | HIGH |
| SEC-09 | `test_jwt_validation_expired` | Expired token → 401 | HIGH |
| SEC-10 | `test_jwt_validation_invalid_sig` | Tampered token → 401 | HIGH |

#### 3.7 Concurrency Tests (PostgreSQL Required)

| Test ID | Name | Description | Priority |
|---------|------|-------------|----------|
| CON-01 | `test_concurrent_worker_claim` | 2 workers, 1 message → 1 claim | HIGH* |
| CON-02 | `test_concurrent_financial_post` | 2 requests same idempotency key | HIGH* |
| CON-03 | `test_concurrent_bank_transaction` | 2 messages same bank tx code | HIGH* |
| CON-04 | `test_concurrent_recall_and_post` | Recall during worker processing | HIGH* |
| CON-05 | `test_concurrent_revert` | 2 reverts same transaction | MEDIUM* |

*BLOCKED_EXTERNAL_DEPENDENCY - requires PostgreSQL with multiple connections

#### 3.8 Supabase Integration Tests (BLOCKED)

| Test ID | Name | Description | Status |
|---------|------|-------------|--------|
| SB-01 | `test_storage_upload_download` | Receipt round-trip | BLOCKED |
| SB-02 | `test_realtime_message_subscription` | Frontend receives updates | BLOCKED |
| SB-03 | `test_jwt_verification` | Supabase JWT valid | BLOCKED |
| SB-04 | `test_rls_policy_enforcement` | User sees only own data | BLOCKED |
| SB-05 | `test_admin_bypass_rls` | Service role sees all | BLOCKED |
| SB-06 | `test_health_check_supabase` | Supabase connectivity | BLOCKED |

### 4. Test Infrastructure

#### 4.1 Test Database
- **Baseline**: SQLite in-memory (fast, no external deps)
- **Integration**: PostgreSQL (Supabase or local) - REQUIRED for concurrency
- **Fixtures**: `conftest.py` with `db` session, `account`, `bank_account`, `upload` factories

#### 4.2 Test Utilities
```python
# tests/conftest.py (to be created)
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.models import *

@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def account(db):
    acc = Account(name="Test Fund", currency="VND", opening_balance=Decimal("0"), active=True)
    db.add(acc)
    db.commit()
    return acc

@pytest.fixture
def bank_account(db):
    ba = BankAccount(bank_name="Test", account_name="Fund", account_number="123")
    db.add(ba)
    db.commit()
    return ba
```

#### 4.3 Mock Supabase Client (for unit tests)
```python
# tests/mocks/supabase.py
from unittest.mock import MagicMock
from app.services.supabase_client import SupabaseClient

def mock_supabase_client():
    client = MagicMock(spec=SupabaseClient)
    client.admin.storage.from_.return_value.upload.return_value = None
    client.admin.storage.from_.return_value.get_public_url.return_value = "https://test.supabase.co/storage/v1/object/public/receipts/uploads/test.png"
    client.admin.storage.from_.return_value.download.return_value = b"fake"
    client.verify_jwt.return_value = {"id": "test-user", "role": "OWNER_TREASURER"}
    return client
```

### 5. Test Execution

#### 5.1 Baseline (Current)
```bash
cd class-fund-backend-v0.1/class-fund-backend
python -m pytest tests/ -v
# 20 passed in ~1.3s
```

#### 5.2 Phase 2 Target
```bash
# All tests (baseline + Phase 2)
python -m pytest tests/ -v --tb=short

# With coverage
python -m pytest tests/ --cov=app --cov=worker --cov-report=term-missing

# Specific categories
python -m pytest tests/test_financial_core.py tests/test_idempotency.py tests/test_recall.py -v
python -m pytest tests/test_worker_lifecycle.py -v  # NEW
python -m pytest tests/test_api_contract.py -v      # NEW
python -m pytest tests/test_security.py -v          # NEW
```

#### 5.3 CI/CD Integration (Future)
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    python -m pytest tests/ --cov=app --cov=worker --cov-fail-under=80
```

### 6. Test Data Management

| Data Type | Strategy |
|-----------|----------|
| Unit test data | Created per-test via fixtures |
| Integration test data | Transactional rollback per test |
| Concurrency test data | Isolated PostgreSQL schemas |
| Load test data | Separate dataset, not in CI |

### 7. Acceptance Criteria

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Baseline tests pass | 100% | 20/20 ✅ |
| Financial core coverage | >90% | `coverage report` |
| Idempotency coverage | >95% | `coverage report` |
| Worker lifecycle tests | 8/8 pass | New test file |
| API contract tests | 12/12 pass | New test file |
| Security tests | 10/10 pass | New test file |
| Concurrency tests | 5/5 pass | PostgreSQL required |
| Supabase integration | 6/6 pass | Credentials required |

### 8. Test Results Tracking

**File**: `10_TEST_RESULTS.md` (to be updated after each run)

| Run | Date | Baseline | Phase 2 New | Blocked | Notes |
|-----|------|----------|-------------|---------|-------|
| 1 | 2026-10-03 | 20/20 ✅ | 0/38 ⏳ | 11 | Baseline verified |

---

**Status**: ✅ BASELINE DEFINED AND PASSING — Phase 2 test expansion planned with 38 new tests across 6 categories. 11 tests require PostgreSQL/Supabase (BLOCKED_EXTERNAL_DEPENDENCY). Implementation of new tests is Phase 2 work.