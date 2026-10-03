# 07_PHASE_1_1_CORRECTION_REGISTER.md

## Purpose
Record corrections, clarifications, and contradictions resolved during Phase 1.1.1, with references to original Phase 1.1 artifacts (preserved, not deleted) and the new evidence from `ledger.py` source inspection performed in this phase.

## Phase 1.1 Artifact Inventory (Preserved — Not Deleted or Modified)

Directory: `artifacts/phase_1_1_contract_review/`
Files (17): 00–16.
- `00_PHASE_1_1_SCOPE.md`
- `01_EVIDENCE_INVENTORY.md`
- `02_ARTIFACT_COUNT_RECONCILIATION.md`
- `03_IMPLEMENTATION_STATUS_MATRIX.md`
- `04_DATABASE_CONTRACT_REVIEW.md`
- `05_AUTH_RLS_SECURITY_REVIEW.md`
- `06_MESSAGE_LIFECYCLE_REVIEW.md`
- `07_WORKER_RELIABILITY_REVIEW.md`
- `08_FINANCIAL_IDEMPOTENCY_AUDIT.md`
- `09_RECALL_AND_REVERSAL_REVIEW.md`
- `10_AI_CONTRACT_REVIEW.md`
- `11_FRONTEND_REALTIME_CONTRACT_REVIEW.md`
- `12_TEAM_OWNERSHIP_AND_BOUNDARIES.md`
- `13_CONTRACT_CONFLICT_REGISTER.md`
- `14_PHASE_2_ENTRY_CRITERIA.md`
- `15_PHASE_1_1_TEST_AND_EVIDENCE_REPORT.md`
- `16_PHASE_1_1_FINAL_REPORT.md`

No files deleted; no modifications to these artifacts in Phase 1.1.1.

## Corrections Registered (Evidence-Based)

### Correction 1 — Exception Flow Contradiction

Source: `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` (Phase 1.1) claimed both:
- "`post_transaction()` raises `HTTPException(409, 'Duplicate transaction code')`."
- "`verify_and_post_from_ai()` catches `IntegrityError` and converts duplicate into `None`."

These are not interchangeable. Actual source (`ledger.py` line 59–242) confirms:
- `post_transaction()` raises `HTTPException(409)` for DB duplicate pre-check (`line 86`) and for `IntegrityError` at commit (`line 117`); it does NOT return `None`.
- `verify_and_post_from_ai()` catches ONLY `IntegrityError` (`line 236`); it does NOT catch `HTTPException`. A `HTTPException` raised by `post_transaction()` DB duplicate check (`line 86`) propagates out of `verify_and_post_from_ai()` unmodified.
- `verify_and_post_from_ai()` returns `None` for DB duplicate check (`line 199–202`) and for `IntegrityError` at final commit (`line 236–242`), but these are different paths from `post_transaction()` exception behavior.

Corrected assessment: The exception behavior depends on the caller (`post_transaction()` direct vs `verify_and_post_from_ai()` caller) and on whether the duplicate is detected before insert (`FOR UPDATE`) vs at commit (`IntegrityError`). The previous documentation did not fully distinguish these paths.

Reference: `01_EXCEPTION_FLOW_FORENSIC_AUDIT.md` (this phase) provides full trace with line numbers.

Status: CORRECTED (evidence preserved; contradiction explained; no previous artifact deleted).

### Correction 2 — DB FOR UPDATE Semantics

Source: Previous documentation (`08_FINANCIAL_IDEMPOTENCY_AUDIT.md`, `04_DATABASE_CONTRACT_REVIEW.md`, `13_CONTRACT_CONFLICT_REGISTER.md`) referenced `SELECT ... FOR UPDATE` as duplicate protection.

Corrected assessment (`02_DATABASE_UNIQUENESS_AUDIT.md` this phase):
- `FOR UPDATE` acquires a row-level lock ONLY when the matching row exists.
- When NO matching row exists, `FOR UPDATE` acquires NO lock. Concurrent transactions processing the same new duplicate can both receive `None` from the query, both proceed to insert, and one receives `IntegrityError` at commit.
- The actual duplicate-prevention guarantee comes from the DB `UniqueConstraint` (`uq_bank_transaction_code`) combined with `IntegrityError` catch (`post_transaction()` line 113–117; `verify_and_post_from_ai()` line 236–242).
- The claim that `FOR UPDATE` alone prevents concurrent duplicate inserts must be qualified; it prevents concurrent modification of existing duplicates but not concurrent insertion of new duplicates.

Status: CORRECTED (evidence preserved; clarification added).

### Correction 3 — Idempotency Key Stability

Source: Design contracts (`11_FINANCIAL_GATEKEEPER.md`, `03_MESSAGE_CONTRACT.md`, `08_LOCAL_WORKER.md`) propose `msg_{message.id}_attempt_{retry_count}`. `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` documents the conflict.

Corrected assessment (`03_IDEMPOTENCY_KEY_AND_FINGERPRINT_AUDIT.md` this phase):
- The proposed format is UNSTABLE (key changes with `retry_count`).
- Fingerprint (`_make_request_fingerprint`) is stable but excludes `message.id` and `retry_count`.
- A retry with incremented `retry_count` produces a different `key` but the same fingerprint. `check_idempotency()` returns `None` (new key). DB duplicate check then either raises (`post_transaction()` direct) or returns graceful `None` (`verify_and_post_from_ai()` with new upload; or returns existing `tx` if same `upload.id`).
- The design proposes `message.transaction_id` pre-check but it is not implemented; this gap must be resolved in Phase 2.

Status: CORRECTED (design conflict preserved; clarification added; Phase 2 prerequisite recorded).

### Correction 4 — Idempotency Test Matrix Reversal

Source: `08_FINANCIAL_IDEMPOTENCY_AUDIT.md` and `14_PHASE_2_ENTRY_CRITERIA.md` reference a matrix scenario: "Different key with same fingerprint raises 409."

Corrected assessment (`04_CORRECTED_IDEMPOTENCY_TEST_MATRIX.md` this phase):
- The statement must be qualified by caller path:
  - Direct `post_transaction()` call: raises `HTTPException(409)` (DB duplicate check `line 86`).
  - `verify_and_post_from_ai()` call with same `upload.id`: returns existing `tx` cleanly (`line 178–179`), not `409`.
  - `verify_and_post_from_ai()` call with different `upload.id`: sets `upload.status = DUPLICATE`; returns `None` (`line 199–202`), not `409`.
- The previous matrix did not distinguish these paths clearly; the corrected matrix (artifact 04) provides the full breakdown with verified source behavior.

Status: CORRECTED.

### Correction 5 — Recall/Reversal Consistency

No contradiction found between `09_RECALL_AND_REVERSAL_REVIEW.md` and actual `post_revert()` source; corrections are clarifications rather than contradiction fixes:
- Authorization mechanism is confirmed missing (not incorrectly documented); design contracts correctly state it is missing (`BLOCKED`).
- `message.status = 'recalled'` check is confirmed unimplemented; design contracts correctly document it as `DESIGNED`/`BLOCKED`.
- `post_revert()` behavior fully matches design: preserves original, creates new `REVERT`, prevents double-revert, stable fingerprint (independent of message retry count).

Status: VERIFIED (consistency confirmed; no contradiction; clarifications added in `06_RECALL_AND_REVERSAL_CONSISTENCY.md`).

## Artifact Count Reconciliation

- Phase 0: 15 artifacts (numbered 00–14 in `phase_0_compatibility_audit/` and related)
- Phase 1: 15 artifacts (verified by `phase_1_integration/` file list)
- Phase 1.1: 17 artifacts (`phase_1_1_contract_review/`: 00–16)
- Phase 1.1.1: 10 artifacts (`phase_1_1_1_audit_correction/`: 00–09; note: 09 = evidence/test report; 10 = final report)

Wait: the required artifact list in section 3 of authorization lists 10 files: 00 through 10 (with 09 and 10 included). This is consistent. The artifact count for Phase 1.1.1 is 10 files (00–09 plus 10 final report = 11? Let me recount from authorization).

Required artifacts (authorization section 3):
00, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10 = 11 files.
Wait, authorization lists:
00, 01, 02, 03, 04, 05, 06, 07, 08, 09, 10.
That's 11 artifacts. My count earlier said 10; the authorization clearly lists 11 (00 through 10 inclusive). I have created 00 through 06 so far; I still need 07, 08, 09, 10.
This is a counting discrepancy. I need to finish creating all artifacts.

But the user asked me to work through Phase 1.1.1 methodically. I have created 00–06. I still need 07, 08, 09, 10. I'll complete them.
