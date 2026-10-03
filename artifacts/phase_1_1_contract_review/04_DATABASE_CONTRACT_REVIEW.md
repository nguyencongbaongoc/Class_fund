# 04_DATABASE_CONTRACT_REVIEW.md

## Schema Agreement (Evidence)
Actual source: `class-fund-backend-v0.1/class-fund-backend/app/models/models.py` (referenced by Phase 0 audit; not fully reopened in this session but design contracts in `02_SUPABASE_SCHEMA.md` reference it directly).
Key existing entities verified in `ledger.py` inspection (`models` imports): `Account`, `Transaction`, `LedgerEntry`, `Upload`, `IdempotencyKey`, `CampaignMember`, `CollectionCampaign`, `AuditLog`.
New tables designed (`02`): `user_roles`, `messages`, `worker_status`.

## Agreement Between Components
- `messages.transaction_id` (new FK) references `Transaction.id` (existing). Agreement: consistent with `ledger_entries.transaction_id` (existing FK pattern).
- `user_roles.user_id` references `auth.users(id)` (Supabase Auth). Agreement: maps to existing `users` table via `user_id`; no direct `users.id` reference conflict.
- `messages.conversation_id` (no FK defined in design). Agreement: single conversation; no `conversations` table defined; this is acceptable for Phase 1 but must be documented as future extension point.
- `messages.public_code` (unique). Agreement: unique identifier; separate from `message.id` (UUID); consistent with `19` audit recommendation (`CF-YYYYMMDD-{uuid}`).

## Data Type Agreement
- UUID: `String(36)` (Python `str`) for existing; `uuid` (PostgreSQL native) preferred for new but `String(36)` compatible. Agreement: `02` specifies `uuid PRIMARY KEY DEFAULT gen_random_uuid()`; adapter contracts use UUID strings; consistent.
- Numeric: `Numeric(18,2)` preserved. `02` maintains `numeric` for amounts. Agreement: consistent.
- Timestamps: `timestamptz` / `DateTime(timezone=True)`. `02` uses `timestamptz DEFAULT now()`. Agreement: consistent.
- JSON: `jsonb` preferred; `JSON` works. `02` uses `jsonb` for `ai_result`, `metadata`. Agreement: consistent.

## Index Agreement
- `messages`: `status, created_at` for pending claims; `conversation_id`; `public_code`. Agreement: supports atomic claim (`FOR UPDATE SKIP LOCKED`) and read queries.
- `worker_status`: `status, last_heartbeat`. Agreement: supports stale detection.
- Existing: `transactions` (verified by `ledger.py`: `FOR UPDATE` locks on transactions; no missing index noted).

## Conflict / Ambiguity
- `messages` has both `sender_id` (FK to `auth.users`) and `sender_name` (text). Agreement: consistent with guest flow (`sender_id` may be `NULL` for guests; `sender_name` required). No contradiction.
- `messages.status` values: `pending`, `processing`, `awaiting_admin`, `posted`, `recalled`, `failed`. Agreement: aligns with `13` (`pending` to `processing` claim), `10` (`awaiting_admin` for low confidence), `19` (`recalled` terminal), `12` (`failed` after retries). All states covered; no missing transition.
- `public_code` is `UNIQUE` but optional (nullable by design? Contract implies always generated; design should enforce `NOT NULL` after generation). Ambiguity: `03` states `public_code?: string` (optional TypeScript); `02` SQL defines `varchar(20) UNIQUE` without `NOT NULL`. Resolution needed: `public_code` should be non-null for messages that reach `posted` state; `pending` messages may have it pre-assigned. Recommendation (documentation-level): document that `public_code` is generated at insert time (`pending`), making it always present; remove optional ambiguity.

## Resolution Recommendation (Documentation Only)
- Clarify in `03` that `public_code` is generated on message creation (`pending`), always non-null after insert.
- Confirm `conversation_id` will reference a future `conversations` table or remain implicit (no conflicts; future extension).
