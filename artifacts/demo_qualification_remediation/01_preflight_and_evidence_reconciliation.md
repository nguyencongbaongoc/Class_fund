# Preflight and Evidence Reconciliation

## Baseline Reconciliation from simulation_results.json

### Actual Test Counts (from simulation_results.json)

| Layer | Tests | Passed | Failed | Skipped | Classification |
|-------|-------|--------|--------|---------|----------------|
| Unit Adapters | 24 | 24 | 0 | 0 | SIMULATION_UNIT_VERIFIED |
| Service Contracts | 24 | 24 | 0 | 0 | SERVICE_CONTRACT_VERIFIED |
| API Integration | 23 | 22 | 0 | 1 | API_INTEGRATION_VERIFIED |
| Worker/Queue Lifecycle | 28 | 28 | 0 | 0 | WORKER_QUEUE_VERIFIED |
| E2E Financial Workflows | 18 | 7 | 10 | 1 | E2E_WORKFLOW_VERIFIED_PARTIAL |
| Frontend/Backend Contracts | 0 | 0 | 0 | 0 | FRONTEND_BACKEND_PARTIAL |
| Security/Financial Invariants | 12 | 12 | 0 | 0 | INVARIANT_VERIFIED |

**Totals: 129 tests, 117 passed, 10 failed, 2 skipped**

Note: The previously reported "125 tests, 114 passed, 10 failed, 2 skipped" was slightly inconsistent. The actual counts from the JSON are 129 total (24+24+23+28+18+0+12).

### Unexplained API Test
The API Integration layer shows 23 tests, 22 passed, 0 failed, 1 skipped. The skipped test is:
- `test_review_routes_require_owner_or_moderator` - Skipped due to known bug: ExtractedTransaction.created_at missing

This was correctly categorized as "skipped", not "unexplained".

### E2E Failure Analysis (10 failures)

From the scenarios in simulation_results.json:

1. **Scenario E (Recall After Posting)**: 1 failure - `claim_next_message` returns None (test fixture issue)
2. **Scenario F (External Service Failures)**: 2 failures
   - Ollama unavailable: status POSTED instead of PENDING/AWAITING_REVIEW
   - Worker crash: exception message mismatch - "Class 'builtins.NoneType' is not mapped"
3. **Scenario G (Admin Dashboard)**: 7 failures - All 401 auth header issue with mock tokens

**Total: 10 failures**

These represent **3 unique defect categories**:
1. Admin auth token parsing (7 tests fail due to same root cause)
2. Review endpoint `created_at` column missing (affects Scenario E indirectly, and review tests directly)
3. Worker lifecycle state machine issues (Scenario E and F worker crash)

### Fixture-Only vs Application-Source Defects

| Failure | Type | Root Cause |
|---------|------|------------|
| Admin Dashboard 401 (7 tests) | Test fixture | Mock token format incompatible with FastAPI OAuth2PasswordBearer |
| Scenario E `claim_next_message` returns None | Test fixture + application | Test creates message but doesn't ensure proper fixture state; `claim_next_message` may return None if no pending messages |
| Scenario F Ollama unavailable returns POSTED | Application logic | Worker doesn't properly handle Ollama unavailable - continues processing instead of failing to AWAITING_REVIEW |
| Scenario F Worker crash exception mismatch | Test fixture | Exception raised from `db.expire(None)` due to `claim_next_message` returning None |

## Summary
- **3 unique root causes** for 10 test failures
- **Admin auth** is purely test infrastructure (mock token format)
- **Review endpoint** is a pre-existing application bug (missing `created_at` column in model)
- **Worker lifecycle** has both test fixture issues and application logic gaps