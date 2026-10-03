# 11_FRONTEND_REALTIME_CONTRACT_REVIEW.md

## Real-Time Design (`07` + `15` Phase 0)
Subscription design (`07`): `supabase.channel()` with `.on('postgres_changes', ...)` for `INSERT` and `UPDATE` on `messages` (filter by `conversation_id`).
Event handling: `INSERT` appends to state; `UPDATE` maps by `id`.
Duplicate protection: event-ID tracking (`eventType:id:commit_timestamp`) in bounded set (`size > 1000` prune).
Reconnection: `supabase.auth.onAuthStateChange()` resubscribes; `useRealtimeWithReconnect()` defines `connected` state.
No adapter source (`src/lib/supabase/client.ts` or `useRealtimeMessages` hook) exists — design only.

## Agreement with Existing Frontend (`ChatView`)
`ChatView.tsx` (`classfund/src/views/ChatView.tsx`) uses `AppContext.chatMessages` (mock array); no `fetch` or `WebSocket`. Adapter design replaces this with `useRealtimeMessages()` hook; design aligns (`15` Phase 0 audit confirms `ChatView` reuse; adapter design in `15` and `07`).
No conflict: adapter adds new data source without rewriting `ChatView`.

## Agreement with Database (`02` + `07`)
`messages` table (`02`): includes `id`, `conversation_id`, `status`, `content`, `message_type`, `ai_result`, `public_code`, `sender_name`, `sender_photo`, `created_at`.
Real-time publication (`02` SQL): `ALTER PUBLICATION supabase_realtime ADD TABLE messages;`.
Subscription filter (`07`): `conversation_id=eq.${conversationId}` aligns with `messages.conversation_id` index (`02`).
Event payload (`07`): `payload.new` mapped to `ChatMessage` type; `status` updates handled; `ai_result` updates handled.
No contradiction between database schema and realtime contract.

## Unverified / Blocked Issues
- No executed subscription: `supabase.channel()` not executed; no event received; no reconnect simulated.
- No executed duplicate event test: bounded set pruning (`size > 1000`) not tested; no duplicate event stream generated.
- No executed `INSERT` from adapter: adapter (`messages.ts`) not implemented; `supabase.from('messages').insert()` not executed.
- Connection failure/reconnect (`07`): no network failure simulated; auto-reconnect design unverified.
- Real-time delivery latency (`05` Phase 0 design: target <5s claim; real-time update target <10s): unverified; no deployed environment.

## Security / Contract Conflicts (None Identified at Design Level)
- `ANON_KEY` in adapter (`06`); `SERVICE_ROLE_KEY` excluded; no secret exposure.
- `public_code` not used for authorization (`03` / `12`); realtime events expose message content to authorized clients only (`05` RLS ensures this at DB level); realtime events themselves are delivered by Supabase but authorization is DB-level, not client-level.
- Guest `sender_id` may be `NULL` (`05`); realtime event includes `new` payload; `auth.uid()` not required for insert; this aligns with guest flow (unauthenticated insert allowed by RLS policy).
- No conflict between realtime contract and message lifecycle (`03` / `06` / `07`).
