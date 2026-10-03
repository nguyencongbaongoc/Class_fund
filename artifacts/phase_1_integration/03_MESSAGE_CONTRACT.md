# 03_MESSAGE_CONTRACT.md

## Guest Message Contract

### Source Evidence (Phase 0)
- 19_GUEST_CHAT_PHOTO_MESSAGE_RECALL_AUDIT.md: Guest requires photo + full name + message; no login required; message must have UUID id; public code required; status tracking missing.
- 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md: `messages` table design with UUID, conversation, AI fields.
- 15_CHAT_REALTIME_COMPATIBILITY.md: Status states (`sending`, `sent`, `processing`, `awaiting_admin`, `processed`, `failed`).
- 13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md: `pending` → `processing` → `processed/failed/awaiting_admin` lifecycle.

### Message Schema (TypeScript / Python Contract)
```typescript
interface Message {
  id: string;                 // UUID (immutable message UUID)
  conversation_id: string;     // UUID
  sender_name: string;         // Full name (guest input)
  sender_photo?: string;       // Storage reference URL or path (not binary in message table)
  content: string;
  message_type: 'TEXT' | 'RECEIPT' | 'ANNOUNCEMENT' | 'SYSTEM';
  status: 'pending' | 'processing' | 'awaiting_admin' | 'posted' | 'recalled' | 'failed';
  public_code?: string;        // Human-readable; e.g. CF-20261003-A8F42C; NOT authorization credential
  ai_intent?: string;          // CONTRIBUTION, WITHDRAWAL, BALANCE_INQUIRY, UNKNOWN
  ai_result?: object;          // Structured JSON (validated with Pydantic/schema)
  ai_confidence?: number;      // Numeric(5,4)
  transaction_id?: string;     // UUID FK to transactions (after successful post)
  created_at: string;          // ISO UTC timestamp
}
```

### Guest Workflow (Phase 1 Foundation — Not Full Implementation)
```
Guest selects photo
    ↓
Guest enters full name (sender_name)
    ↓
Guest enters message content
    ↓
Guest sends
    ↓
Frontend inserts into messages (via adapter / Supabase)
    ↓
Message receives immutable UUID (message.id)
    ↓
Public code generated (CF-YYYYMMDD-{short_uuid})
    ↓
Status = 'pending'
    ↓
Worker claims (atomic) → 'processing'
    ↓
AI validates → 'posted' (with transaction_id) or 'awaiting_admin' or 'failed'
```
- Evidence: 9 (integration flow), 19 (guest identity), 13 (message lifecycle).

### Message States (Phase 1 Contract — All Defined)
- `pending`: Inserted; not yet claimed by worker.
- `processing`: Atomic claim completed (`claimed_at`, `lease_expires_at`, `worker_id` set); AI running.
- `awaiting_admin`: AI result below confidence threshold or requires review.
- `posted`: Financial validation passed; ledger entry created; `transaction_id` linked.
- `recalled`: Recall token validated; message preserved; future reversal creates compensating transaction (not delete).
- `failed`: Maximum retries exceeded or unrecoverable error; `error_message` set.

### Idempotency (Message Level)
- Every message has a unique `message.id` (UUID v4).
- `public_code` is unique but public (not authorization).
- Recall authorization uses a server-generated secret/token (not public `message_id` only), per 19 (recall token gap identified and addressed conceptually).
- Idempotency key format (worker contract): `msg_{message_id}_attempt_{retry_count}` — passed to `verify_and_post_from_ai()`.

### Recall Foundation (Concept)
- Recall does NOT delete the message.
- Original message status changes to `recalled`.
- Financial reversal creates a new `REVERT` ledger entry linked via `original_entry_id`.
- Double-recall prevented by existing backend `post_revert` logic (checks existing reversal).
- Before posting: re-check `message.status != 'recalled'`; after posting: recall creates reversal, not mutation.
- Evidence: 16 (security audit), 19 (recall audit), 11 (financial integrity).
