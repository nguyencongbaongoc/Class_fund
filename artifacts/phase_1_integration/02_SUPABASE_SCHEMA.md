# 02_SUPABASE_SCHEMA.md

## Phase 1 Supabase Schema Foundation

### Source Evidence (Phase 0)
- 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md: Existing schema uses UUID String(36), Numeric(18,2), DateTime(timezone=True), ForeignKey, UniqueConstraint, JSON. All compatible.
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: New `messages` (extended chat), `worker_status`, `user_roles` tables required.
- 13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md: `messages` needs `status`, `lease_expires_at`, `claimed_at`, `retry_count`, `conversation_id`.
- 14_ADMIN_AUTH_AND_RBAC_AUDIT.md: `user_roles` maps existing 4 roles: `OWNER_TREASURER`, `MODERATOR`, `MEMBER`, `PUBLIC`.
- 19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md: `messages` needs `sender_photo`, `public_code`, `recall_token_hash`, `status`.

### Existing Tables (Preserved — Not Rewritten)
- `accounts`, `bank_accounts`, `transactions`, `ledger_entries`
- `uploads`, `extracted_transactions`, `audit_logs`
- `collection_campaigns`, `campaign_members`, `students`, `payment_matches`
- `chat_messages` (legacy; extended by new `messages` for hybrid flow)
- `users` (mapped via `user_roles` to Supabase Auth `auth.users`)

### New Tables (Phase 1 Foundation Only)

#### `user_roles`
```sql
CREATE TABLE user_roles (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role varchar(30) NOT NULL CHECK (role IN ('OWNER_TREASURER', 'MODERATOR', 'MEMBER', 'PUBLIC')),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
CREATE INDEX idx_user_roles_role ON user_roles(role);
```
- Evidence: 14_ADMIN_AUTH_AND_RBAC_AUDIT.md (maps existing Role enum).

#### `messages` (Extended Chat / Guest Message)
```sql
CREATE TABLE messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL,
    sender_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
    sender_name text NOT NULL,
    sender_photo text,  -- reference to storage path or URL, not binary
    content text NOT NULL,
    message_type varchar(50) NOT NULL DEFAULT 'TEXT',
    status varchar(30) NOT NULL DEFAULT 'pending',  -- pending, processing, awaiting_admin, processed, failed, recalled
    public_code varchar(20) UNIQUE,  -- e.g., CF-20261003-A8F42C; NOT authorization credential
    ai_intent varchar(50),
    ai_result jsonb,
    ai_confidence numeric(5,4),
    transaction_id uuid REFERENCES transactions(id) ON DELETE SET NULL,
    recall_token_hash text,
    error_message text,
    retry_count int DEFAULT 0,
    created_at timestamptz DEFAULT now(),
    claimed_at timestamptz,
    lease_expires_at timestamptz,
    processed_at timestamptz
);
CREATE INDEX idx_messages_status_created ON messages(status, created_at) WHERE status = 'pending';
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_public_code ON messages(public_code);
```
- Evidence: 12 (new table design), 13 (atomic claim fields), 19 (guest identity/status/recall), 15 (realtime publication).

#### `worker_status`
```sql
CREATE TABLE worker_status (
    worker_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status varchar(20) NOT NULL DEFAULT 'offline',  -- online, offline, processing, error
    model_name varchar(100),
    last_heartbeat timestamptz,
    last_processed_at timestamptz,
    current_job_id uuid REFERENCES messages(id) ON DELETE SET NULL,
    metadata jsonb DEFAULT '{}'
);
CREATE INDEX idx_worker_status_heartbeat ON worker_status(status, last_heartbeat);
```
- Evidence: 13 (heartbeat/status/recovery), 15 (realtime subscription).

### Constraints and Integrity
- UUID primary keys (`gen_random_uuid()` / Python `uuid4_str()`).
- Numeric/decimal for all money-related fields (`Numeric(18,2)` preserved from 12).
- UTC timestamps (`timestamptz` / `DateTime(timezone=True)`).
- Foreign keys: `messages.transaction_id → transactions.id`; `messages.conversation_id` (no FK required for conversation table in Phase 1).
- Unique constraints: `messages.public_code`; `user_roles.user_id`.
- Idempotency: `public_code` and `message.id` used as integration contracts; `messages.retry_count` prevents duplicate processing loops.

### Indexes for Worker Queries
- `idx_messages_status_created` (pending claims).
- `idx_worker_status_heartbeat` (stale detection).

### Migration Strategy
- Use Alembic revisions (not `create_all`), per 12 recommendation.
- Preserve existing `Base.metadata` for legacy tables; add new revisions for `user_roles`, `messages`, `worker_status`.
- Migrations applied to Supabase via `alembic upgrade head` with PgBouncer-compatible engine config.

### Realtime Publications (Documented — SQL Contract)
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE worker_status;
ALTER PUBLICATION supabase_realtime ADD TABLE ledger_entries;
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;
```
- Evidence: 15 (realtime setup), 12 (publication setup).
