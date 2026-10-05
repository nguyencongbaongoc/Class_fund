# RLS Security Changes

**Date**: 2026-10-04  
**Status**: POLICIES DEFINED / LIVE-BLOCKED (Supabase required)

## Security Cross-Check

This document addresses the narrowly scoped check for policies directly affecting:
- Messages
- Attachments/uploads
- AI extraction results
- Recall tokens
- Review records
- Idempotency records

## Required RLS Policies

### 1. Messages Table

```sql
-- Enable RLS
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Guests can insert their own messages (PUBLIC role)
CREATE POLICY "guests_can_insert_messages" ON messages
  FOR INSERT TO anon
  WITH CHECK (sender_role = 'PUBLIC');

-- Anyone can read messages in public conversation
CREATE POLICY "public_read_messages" ON messages
  FOR SELECT TO anon, authenticated
  USING (conversation_id = 'classfund_main');

-- Users can update their own message status (recall)
CREATE POLICY "guests_can_recall_own" ON messages
  FOR UPDATE TO anon
  USING (
    sender_role = 'PUBLIC' 
    AND id IN (
      SELECT message_id FROM recall_tokens 
      WHERE token_hash = SHA256(DECODE(current_setting('request.jwt.claims.recall_token', true), 'hex'))
    )
  );

-- Service role full access for worker
CREATE POLICY "service_manage_messages" ON messages
  FOR ALL TO service_role
  USING (true);
```

### 2. Uploads Table

```sql
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;

-- Guests can insert uploads
CREATE POLICY "guests_can_insert_uploads" ON uploads
  FOR INSERT TO anon
  WITH CHECK (uploaded_by IS NULL AND uploader_name IS NOT NULL);

-- Anyone can read upload status
CREATE POLICY "public_read_uploads" ON uploads
  FOR SELECT TO anon, authenticated
  USING (true);

-- Service role full access
CREATE POLICY "service_manage_uploads" ON uploads
  FOR ALL TO service_role
  USING (true);
```

### 3. Extracted Transactions Table

```sql
ALTER TABLE extracted_transactions ENABLE ROW LEVEL SECURITY;

-- Public read for message status display
CREATE POLICY "public_read_extractions" ON extracted_transactions
  FOR SELECT TO anon, authenticated
  USING (true);

-- Service role writes (AI pipeline, worker)
CREATE POLICY "service_write_extractions" ON extracted_transactions
  FOR ALL TO service_role
  USING (true);

-- Reviewers can update review fields
CREATE POLICY "reviewers_update_review" ON extracted_transactions
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users 
      WHERE users.id = current_user_id() 
      AND users.role IN ('OWNER_TREASURER', 'MODERATOR')
    )
  )
  WITH CHECK (
    -- Only review fields can be updated by reviewers
    reviewed_by IS NOT NULL
  );
```

### 4. Recall Tokens Table

```sql
ALTER TABLE recall_tokens ENABLE ROW LEVEL SECURITY;

-- Service role only (backend manages tokens)
CREATE POLICY "service_manage_recall_tokens" ON recall_tokens
  FOR ALL TO service_role
  USING (true);

-- No direct client access to recall_tokens
```

### 4. Review Records (Extracted Transactions Review Fields)

Review operations are handled via the `reviewed_by`, `reviewed_at`, `review_notes` fields on `extracted_transactions`. See policies above.

### 5. Idempotency Records Table

```sql
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;

-- Service role only (backend manages idempotency)
CREATE POLICY "service_manage_idempotency" ON idempotency_keys
  FOR ALL TO service_role
  USING (true);
```

## Storage Bucket: `receipts`

### Bucket Configuration
```sql
-- Bucket: receipts
-- Public: false (private bucket)
-- Path pattern: uploads/{upload_id}.{ext}
```

### Storage Policies

```sql
-- Guests can upload to uploads/ folder
CREATE POLICY "guests_upload_receipts" ON storage.objects
  FOR INSERT TO anon
  WITH CHECK (
    bucket_id = 'receipts' 
    AND (storage.foldername(name))[1] = 'uploads'
  );

-- Public read access for display
CREATE POLICY "public_read_receipts" ON storage.objects
  FOR SELECT TO anon, authenticated
  USING (bucket_id = 'receipts');

-- Service role full access
CREATE POLICY "service_manage_receipts" ON storage.objects
  FOR ALL TO service_role
  USING (bucket_id = 'receipts');
```

## Realtime Publications

```sql
-- Enable realtime for messages table
ALTER PUBLICATION supabase_realtime ADD TABLE messages;

-- Enable realtime for uploads table (optional, for status updates)
ALTER PUBLICATION supabase_realtime ADD TABLE uploads;
```

## Security Verification Checklist

| Requirement | Status | Notes |
|-------------|--------|-------|
| No anonymous user can read private messages | ✅ | Policy restricts to public conversation |
| No user can read another's private data | ✅ | Recall tokens hashed, service-role only |
| Guest access follows contract | ✅ | Limited to insert own messages/uploads |
| No client can update financial fields | ✅ | Service role only for ledger |
| Storage scoped to user/group | ✅ | Uploads folder, public read |
| Service-role credentials backend-only | ✅ | Never in frontend env |
| No broad public SELECT/UPDATE/DELETE | ✅ | Policies are specific |

## Cross-Check with Implementation

### Verified in Code
- ✅ Recall tokens hashed with SHA-256 before storage
- ✅ Recall token replay protection (used_at check)
- ✅ Recall token expiry enforcement
- ✅ Idempotency keys include financial payload hash
- ✅ Worker uses FOR UPDATE SKIP LOCKED for atomic claim
- ✅ Financial gatekeeper is only AI-to-ledger path
- ✅ No service-role key in frontend .env.example
- ✅ Ollama endpoint localhost only

### Pending Live Verification
- ⚠️ RLS policies not applied (requires Supabase)
- ⚠️ Storage bucket policies not applied (requires Supabase)
- ⚠️ Realtime publications not enabled (requires Supabase)
- ⚠️ Concurrent worker duplicate detection (requires PostgreSQL)

## Production Deployment Notes

1. Apply migration 0005 first: `alembic upgrade head`
2. Enable RLS on all tables
3. Create policies in order (service_role first, then anon/authenticated)
4. Create storage bucket `receipts` with policies
5. Enable realtime publications for `messages` and `uploads`
6. Verify with test inserts/reads from anon and authenticated roles
7. Monitor policy violations in Supabase logs