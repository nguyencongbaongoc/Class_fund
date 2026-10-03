# 06_MESSAGE_LIFECYCLE_REVIEW.md

## Lifecycle States Agreement (Evidence)
`03_MESSAGE_CONTRACT.md`: `pending` → `processing` → (`posted` / `awaiting_admin` / `failed`) + terminal (`recalled`).
`02_SUPABASE_SCHEMA.md`: `status` column (`varchar(30)`) with default `pending`.
`13_TEST_RESULTS.md`: References lifecycle from `pending` through `recalled`.
`08_LOCAL_WORKER.md`: Claim updates `pending` → `processing` (`claimed_at`, `lease_expires_at`, `worker_id`).
`11_FINANCIAL_GATEKEEPER.md`: Before posting: `message.status = 'recalled'` abort; after posting: `REVERT` creates reversal; original preserved.
`12_RECALL_SAFETY.md`: `recalled` terminal; no delete; compensation via `REVERT`.

## Agreement Verification
- Immutable message UUID (`message.id`): `02` (`uuid PRIMARY KEY`); `03` (UUID contract). Agreement: consistent.
- Public message code (`public_code`): `02` (`varchar(20) UNIQUE`); `03` (`CF-...`). Agreement: consistent; note ambiguity (`NOT NULL` missing — see `04` resolution recommendation).
- Status sequence: `pending` (insert) → `processing` (claim) → `awaiting_admin` (low confidence) / `posted` (successful gatekeeper) / `failed` (max retries) → `recalled` (token validated, compensation created). Agreement: no missing transition; all states have design contracts.
- Recall before posting (`08` claim design + `12` recall design): Claim selects `status='pending'`; before `verify_and_post_from_ai()` (new contract), `message.status` must be checked (contract defines check; source not implemented). Agreement: design consistent; execution unverified.
- Recall after posting (`11` `post_revert()` + `12`): `REVERT` entry links to original; message `status='recalled'`; original `Transaction` preserved; `original_entry_id` on `LedgerEntry`. Agreement: consistent with `ledger.py` inspection (lines 121–169).

## Contradictions / Ambiguities (Critical: Recall Authorization Missing)
`19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md` (Phase 0): Zero authorization mechanism exists (`revertTransaction` has no ownership check; no token; no session).
`12_RECALL_SAFETY.md` (Phase 1): Proposes private token (`recall_token_hash` = SHA-256 of token); token returned only to sender.
`05_AUTH_RLS_SECURITY_REVIEW.md`: Token mechanism is design-only (`BLOCKED`); authorization endpoint not implemented.
Contradiction: Contract claims recall authorization is secure (`public_code` excluded; private token required), but no source mechanism exists to validate the token. The design depends on an unimplemented token generation and authorization endpoint.
Evidence: `12` design (token hash); `03` message contract (no authorization mechanism in TypeScript contract); `08` worker skeleton (no recall endpoint); `05` security review (authorization gap marked `BLOCKED`).

## Resolution Recommendation (Documentation Only)
- Confirm in `12` contract that `recall_token_hash` requires a server-side token generation mechanism before authorization can be verified.
- Confirm in `03` that `public_code` must never be passed as authorization parameter to any endpoint.
- Confirm in `11` that `message.status = 'recalled'` must be checked before `verify_and_post_from_ai()` (contract exists; execution unverified).
