# 07_REALTIME.md

## Phase 1 Realtime Adapter Foundation

### Source Evidence (Phase 0)
- 15_CHAT_REALTIME_COMPATIBILITY.md: `ChatView` feature-complete; needs `useRealtimeMessages()` hook; realtime events (`INSERT`, `UPDATE`) handle message list and status badges; duplicate event protection needed.
- 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md: `ALTER PUBLICATION supabase_realtime ADD TABLE messages;` required.
- 13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md: `messages` status updates (`pending` → `processing` → `posted`/`failed`) must reflect in frontend without refresh.

### Real-Time Behavior Contract
```
Guest sends message
  ↓
INSERT messages (status='pending')
  ↓
Realtime INSERT event → all clients add message
  ↓
Worker claims → UPDATE messages (status='processing', claimed_at=now(), lease_expires_at=...)
  ↓
Realtime UPDATE event → clients update status to 'processing'
  ↓
AI validation complete → UPDATE messages (status='posted', transaction_id=..., ai_result=...)
OR
Status 'awaiting_admin' / 'failed' / 'recalled'
  ↓
Realtime UPDATE event → clients reflect final state
```
- Evidence: 9 (integration flow), 15 (realtime subscription design).

### Subscription Design (Skeleton Hook)
```typescript
const channel = supabase
  .channel(`messages:${conversationId}`)
  .on('postgres_changes', {
    event: 'INSERT',
    schema: 'public',
    table: 'messages',
    filter: `conversation_id=eq.${conversationId}`
  }, payload => setMessages(prev => [...prev, payload.new]))
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'messages',
    filter: `conversation_id=eq.${conversationId}`
  }, payload => setMessages(prev => prev.map(m => m.id === payload.new.id ? payload.new : m)))
  .subscribe()
```
- Evidence: 15 (`useRealtimeMessages` design, duplicate event handling).

### Idempotency / Deduplication (Concept)
- Track processed event IDs (`eventType:id:commit_timestamp`) to avoid duplicate updates from reconnect/retry.
- UI state updates idempotent: same payload produces same result regardless of event count.
- Evidence: 15 (deduplication strategy, bounded set).

### Reconnection Handling
- Supabase client handles auto-reconnect; adapter resubscribes channels on `TOKEN_REFRESHED`.
- `useRealtimeWithReconnect` skeleton defines `connected` state; UI shows offline indicator when disconnected.
- Evidence: 15 (reconnection logic).

### Required Publications (Documented — SQL Already in 02)
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE worker_status;
ALTER PUBLICATION supabase_realtime ADD TABLE ledger_entries;
ALTER PUBLICATION supabase_realtime ADD TABLE transactions;
```

### Status Badge Contract (UI — Not Fully Implemented)
- `pending`: Default (no badge needed initially)
- `processing`: Spinner / "AI đang xử lý..." (concept from 15)
- `awaiting_admin`: Warning badge; admin review action
- `posted`: Green check / verified indicator
- `failed`: Red alert + retry option (future)
- `recalled`: Recall status shown; no further actions allowed
- Evidence: 15 (visual indicators for processing/awaiting_admin/failed).
