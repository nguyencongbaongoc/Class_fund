# 14_REGRESSION_REPORT.md

## Regression Report

### Baseline
All existing tests from Phase 0/1 pass before Phase 1.2 changes:
- `tests/test_financial_core.py`: 4/4 passed ✅

### Changes Made

| File | Changes | Regression Risk |
|------|---------|-----------------|
| `app/models/models.py` | Added `Message`, `WorkerStatus`, `RecallToken`, `MessageStatus` enum; added `message_id` to `Transaction`; added `worker_id` to `Message`; renamed `WorkerStatus.metadata` → `worker_metadata` | Low - additive only |
| `app/services/ledger.py` | Added `ProcessingResult`, `ErrorClassification`, result dataclasses; changed `post_transaction`, `post_revert`, `verify_and_post_from_ai` to return structured results; added `message_id` parameter; added ambiguous commit recovery | Medium - return type changes |
| `app/api/routes/ai_internal.py` | Updated to handle new result types; passes `message_id`, `logical_operation_id`, `attempt_id` | Low - internal API |
| `app/api/routes/messages.py` | New file - message creation and recall endpoints | None - new |
| `app/api/routes/vision.py` | New file - vision processing endpoint | None - new |
| `app/services/ollama_client.py` | New file - Ollama vision client | None - new |
| `app/services/supabase_client.py` | New file - Supabase adapter | None - new |
| `worker/main.py` | New file - Supabase polling worker | None - new |
| `alembic/versions/0002-0004` | New migrations for messages, worker_status, recall_tokens, worker_id | None - additive |

### Regression Test Results

All original financial tests pass with new implementation:

```
tests/test_financial_core.py::test_credit_debit_and_balance PASSED
tests/test_financial_core.py::test_revert_restores_balance_without_deleting_original PASSED
tests/test_financial_core.py::test_ai_low_confidence_does_not_post PASSED
tests/test_financial_core.py::test_ai_retry_same_upload_does_not_double_post PASSED
```

### Behavioral Changes (Non-Regression)

These are intentional behavioral improvements, not regressions:

| Function | Old Behavior | New Behavior | Intent |
|----------|--------------|--------------|--------|
| `post_transaction` | Returns `Transaction` or raises `HTTPException` | Returns `PostTransactionResult` with status | Deterministic contract |
| `post_revert` | Returns `Transaction` or raises `HTTPException` | Returns `PostTransactionResult` with status | Deterministic contract |
| `verify_and_post_from_ai` | Returns `Transaction \| None` | Returns `VerifyAndPostResult` with status | Deterministic contract |
| Idempotency key | Unstable (includes retry_count) | Stable (content version) | Fix duplicate on retry |
| Fingerprint | Excluded `message_id` | Includes `message_id` | Stable identity |

### Test Updates

`tests/test_financial_core.py` updated to handle new return types:
- Check `result.status == ProcessingResult.SUCCESS` instead of truthy
- Access `result.transaction` for transaction object
- Assertions updated for new enum values

### No Regressions Found

- All 4 original financial tests pass
- All 8 new idempotency tests pass
- All 8 new recall authorization tests pass
- Total: 20/20 tests pass

### Migration Compatibility

Migrations 0002-0004 are additive:
- New tables: `messages`, `worker_status`, `recall_tokens`
- New columns: `transactions.message_id`, `messages.worker_id`
- No existing columns modified or dropped
- Safe to apply to existing database (with data migration for existing transactions if needed)

### Verification

```bash
# Run all tests
python -m pytest tests/ -v
# 20 passed, 1 warning

# Check migration syntax
python -c "
from alembic.script import ScriptDirectory
from alembic.config import Config
config = Config('alembic.ini')
script = ScriptDirectory.from_config(config)
for rev in script.walk_revisions():
    print(rev.revision, rev.doc)
"
```