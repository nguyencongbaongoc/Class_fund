# 00_PHASE_1_1_1_AUTHORIZATION_AND_SCOPE.md

## Authorization

Phase 1.1.1 — Audit Correction & Financial Invariant Clarification
Only authorized work: read-only forensic inspection of existing source, tests, schema, migrations, and audit artifacts; create/update Phase 1.1.1 documentation artifacts only; produce corrected assessments; produce explicit Phase 2 entry decision.

Not authorized: implement adapter; modify source, tests, dependencies, environment, schema, data; execute migrations; start Phase 2; commit/push.

Status: AUTHORIZED (read-only documentation audit only).

## Scope

Forensic correction of contradictions discovered in Phase 1.1 artifacts, specifically:
- Exception-flow discrepancy (post_transaction raises HTTPException(409) vs verify_and_post_from_ai catches IntegrityError and returns None).
- Database uniqueness enforcement (Transaction UniqueConstraint + IdempotencyKey unique key; SELECT ... FOR UPDATE semantics).
- Idempotency key stability (`msg_{message.id}_attempt_{retry_count}` changes with retry_count; fingerprint excludes message.id/retry_count).
- Idempotency test matrix (corrected for same-key/different-key behavior observed in `check_idempotency()` and `post_transaction()`).
- Financial invariant assessment (exactly-once vs at-least-once vs DB-level prevention only).
- Recall/reversal consistency review (design verified against source; authorization endpoint missing).

## Repository State (Recorded Before Inspection)

- Root: C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB
- Branch: master
- HEAD: 2d20a5000a656b5ca37df0488e2e585345e9d104
- Untracked: artifacts/phase_1_1_contract_review/ (17 artifacts, 00–16)
- Tracked source modifications: NONE (`git status` clean except artifacts)
- Source directory preserved unchanged: `app/services/ledger.py` not modified.

## Artifact Directory

- Phase 0: artifacts/phase_0_compatibility_audit/
- Phase 1: artifacts/phase_1_integration/
- Phase 1.1: artifacts/phase_1_1_contract_review/
- Phase 1.1.1 (this phase): artifacts/phase_1_1_1_audit_correction/

Required files for Phase 1.1.1 (10 artifacts): 00–10 as listed in section 3 of authorization instruction.

## Limitations

- No production database connection established; database-level uniqueness verified only from schema/model source (`models.py`) and from inspection of `ledger.py` DB interaction logic.
- No runtime verification of concurrent duplicate insertion (would require multi-transaction execution, not performed; marked UNVERIFIED where concurrent behavior is assumed).
- No tests executed (non-mutating inspection only; existing test `test_ai_retry_same_upload_does_not_double_post` read but not executed in this session; prior evidence from Phase 1.1 used).
- Source unchanged; design contracts (`msg_{message.id}_attempt_{retry_count}`) remain design-only (not implemented in `ledger.py` which accepts any string as `idempotency_key`).

## Verification Status Reference

Status values used in all artifacts:
- VERIFIED: confirmed by source/code inspection in this phase.
- IMPLEMENTED: source code exists and performs the behavior.
- DESIGNED: contract/design document exists; source not implemented.
- TESTED: covered by existing test; not necessarily executed this phase.
- UNVERIFIED: insufficient evidence; no runtime proof available.
- BLOCKED: critical blocker identified; must resolve before Phase 2.
- NOT_APPLICABLE.
