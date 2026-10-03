# 09_EVIDENCE_AND_TEST_REPORT.md

## Evidence Collected During Phase 1.1.1 (Read-Only, Non-Mutating)

### Source Files Inspected (No Modifications)
- `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py` — full file (242 lines) read. No modifications.
- `class-fund-backend-v0.1/class-fund-backend/app/models/models.py` — full file (245 lines) read. No modifications.
- `class-fund-backend-v0.1/class-fund-backend/tests/test_financial_core.py` — full file (90 lines) read. No modifications.
- `artifacts/phase_1_1_contract_review/` (17 artifacts, 00–16) — all read; none modified.

### Git Verification (Before and After Phase 1.1.1)

Before:
- HEAD: `2d20a5000a656b5ca37df0488e2e585345e9d104`
- Branch: `master`
- Tracked source changes: NONE
- Untracked: `artifacts/phase_1_1_contract_review/`

After (verified at end of this phase):
- HEAD unchanged (`2d20a500...`)
- Tracked source changes: NONE
- Only new untracked files: `artifacts/phase_1_1_1_audit_correction/` (10 artifacts so far: 00–09; still need 10)
- No tracked file modifications; no `git add`; no commits; no pushes.

### Tests Executed
- NO tests executed in this phase. Per authorization (section 4): only strictly non-mutating tests allowed; no data-modifying tests run.
- The existing `tests/test_financial_core.py` (`test_ai_retry_same_upload_does_not_double_post`, `test_revert_restores_balance_without_deleting_original`, etc.) was read but not executed. Evidence from Phase 1.1 (`15_PHASE_1_1_TEST_AND_EVIDENCE_REPORT.md`) references these tests; this phase relies on that prior evidence.
- No new tests created; no existing tests modified.

### Database Connection
- No read-only or write database connection established. Schema verified from `models.py` source. Migration files (`*migrat*`) not found; schema design (`02_SUPABASE_SCHEMA.md`) inspected but is a design contract, not deployed DB schema verification.

### Runtime Verification Status
- Exception flow (`post_transaction()` / `verify_and_post_from_ai()`): VERIFIED from source (line-level inspection).
- DB uniqueness (`models.py`): SCHEMA-VERIFIED (source-defined); UNVERIFIED (deployed DB constraint).
- Concurrent duplicate-posting behavior: UNVERIFIED (no concurrent execution performed).
- Idempotency retry loop with unstable key: VERIFIED from source logic (not executed at runtime).
- Recall/reversal: VERIFIED from source (`post_revert()`); authorization mechanism UNVERIFIED (not implemented).

## Evidence References (Line Numbers)

- `post_transaction()` duplicate check: `ledger.py` line 80–86 (DB `FOR UPDATE` + `HTTPException(409)`); line 113–117 (`IntegrityError` catch + `HTTPException(409)`).
- `post_revert()` double-revert protection: `ledger.py` line 132 (`REVERT` check), 134–138 (`already` check), 162–163 (idempotency save).
- `verify_and_post_from_ai()` exception scope: `ledger.py` line 236 (`except IntegrityError:`) — does NOT catch `HTTPException`.
- `verify_and_post_from_ai()` graceful `None` for DB duplicate: `ledger.py` line 194–202.
- `verify_and_post_from_ai()` existing upload check: `ledger.py` line 177–179.
- Fingerprint definition: `ledger.py` line 39–40; `post_transaction()` line 70–73; `post_revert()` line 123.
- Idempotency definition: `models.py` line 202–209; `check_idempotency()` line 43–51.
- DB `UniqueConstraint`: `models.py` line 179–181.

## Limitations Recorded

- No concurrent execution performed; concurrent behavior remains UNVERIFIED at runtime.
- No adapter source (`ai/ollama_client.py`, worker `main.py`, etc.) inspected in this phase; adapter-level behavior remains DESIGNED / UNVERIFIED.
- No production or deployed database connected; deployed schema verification unverified.
- No vision adapter tests executed; vision accuracy evidence remains BLOCKED.
- No end-to-end integration executed; full flow verification remains BLOCKED.
