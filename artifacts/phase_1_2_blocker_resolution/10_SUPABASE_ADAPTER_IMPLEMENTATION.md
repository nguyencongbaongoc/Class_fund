# 10_SUPABASE_ADAPTER_IMPLEMENTATION.md

## Workstream H: Supabase Integration

### Current State Analysis

**Problem**: No Supabase integration. Backend uses local filesystem for uploads (`uploads.py` stores to `./storage/uploads/`). No RLS policies, no realtime, no auth integration.

**Solution**: Supabase adapters for:
- PostgreSQL database (replace SQLite in production)
- Storage for receipt images
- Realtime subscriptions for message status
- Auth integration (JWT verification)
- RLS policies for data isolation

### Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Supabase client wrapper | ✅ IMPLEMENTED | `app/services/supabase_client.py` |
| Storage operations | ✅ IMPLEMENTED | `supabase_client.py:upload_receipt/download/delete` |
| Realtime subscriptions | ✅ IMPLEMENTED | `supabase_client.py:subscribe_to_messages/worker_status` |
| Auth verification | ✅ IMPLEMENTED | `supabase_client.py:verify_jwt/get_user_by_id` |
| RLS helpers | ✅ IMPLEMENTED | `supabase_client.py:enable_rls/create_policy` |
| Health check | ✅ IMPLEMENTED | `supabase_client.py:check_supabase_connection` |

### Key Features

1. **Dual Client Pattern**: Admin client (service role) for server ops, Anon client for public
2. **Storage**: Receipts in `receipts` bucket with public URLs
3. **Realtime**: Message status updates pushed to frontend
4. **Auth**: JWT verification via Supabase Auth
5. **RLS Ready**: Helpers to enable RLS and create policies

### Database Migration Notes

Migrations 0002-0004 create tables compatible with Supabase PostgreSQL:
- `messages`, `worker_status`, `recall_tokens` with proper indexes
- `transactions.message_id` for traceability
- `IdempotencyKey` table for deduplication

### RLS Policies Needed (Production)

```sql
-- Messages: public can read own, admin can read all
CREATE POLICY "messages_own" ON messages FOR SELECT TO anon USING (sender_id = auth.uid());
CREATE POLICY "messages_admin" ON messages FOR ALL TO authenticated USING (auth.jwt() ->> 'role' = 'admin');

-- Transactions: only admin can read
CREATE POLICY "transactions_admin" ON transactions FOR SELECT TO authenticated USING (auth.jwt() ->> 'role' = 'admin');

-- Worker status: admin only
CREATE POLICY "worker_admin" ON worker_status FOR ALL TO authenticated USING (auth.jwt() ->> 'role' = 'admin');
```

### Testing

- Unit tests for client wrapper
- Integration tests require Supabase credentials
- Marked BLOCKED for live integration (no credentials)

### Status

| Task | Status | Evidence |
|------|--------|----------|
| Supabase client | ✅ IMPLEMENTED | `app/services/supabase_client.py` |
| Storage operations | ✅ IMPLEMENTED | `upload_receipt`, `download_receipt`, `delete_receipt` |
| Realtime subscriptions | ✅ IMPLEMENTED | `subscribe_to_messages`, `subscribe_to_worker_status` |
| Auth verification | ✅ IMPLEMENTED | `verify_jwt`, `get_user_by_id` |
| RLS helpers | ✅ IMPLEMENTED | `enable_rls`, `create_policy` |
| Health check | ✅ IMPLEMENTED | `check_supabase_connection` |
| Unit tests | ⏳ PENDING | Requires Supabase |
| Live integration | ⏳ BLOCKED | No credentials |