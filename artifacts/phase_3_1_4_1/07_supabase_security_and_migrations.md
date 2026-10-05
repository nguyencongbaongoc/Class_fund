# Supabase Security and Migrations

**Date**: 2026-10-04
**Branch**: master

## Migration History

### Existing Migrations (0001-0004)
| Migration | Description | Tables Affected |
|-----------|-------------|-----------------|
| 0001_initial | Initial schema | users, accounts, bank_accounts, uploads, students, campaigns, campaign_members, extracted_transactions, transactions, ledger_entries, idempotency_keys, audit_logs, payment_matches, revoked_tokens |
| 0002_add_messages_and_message_id | Messages table | messages, chat_messages |
| 0003_add_recall_tokens | Recall tokens | recall_tokens |
| 0004_add_worker_id_to_messages | Worker tracking | messages (worker_id, indexes) |

### New Migration (0005)
**File**: `alembic/versions/0005_add_attachment_ids_and_ai_fields.py`

**Changes**:
```sql
-- Messages: multiple attachments support
ALTER TABLE messages ADD COLUMN attachment_ids JSON;

-- Uploads: perceptual hash for duplicate detection
ALTER TABLE uploads ADD COLUMN perceptual_hash VARCHAR(128);
CREATE INDEX ix_uploads_perceptual_hash ON uploads(perceptual_hash);

-- Extracted Transactions: AI pipeline fields
ALTER TABLE extracted_transactions ADD COLUMN field_confidences JSON;
ALTER TABLE extracted_transactions ADD COLUMN extraction_method VARCHAR(50);
ALTER TABLE extracted_transactions ADD COLUMN source_image_id VARCHAR(36);
ALTER TABLE extracted_transactions ADD COLUMN currency VARCHAR(8);
CREATE INDEX ix_extracted_transactions_field_confidences ON extracted_transactions(field_confidences);

-- Extracted Transactions: Review audit trail
ALTER TABLE extracted_transactions ADD COLUMN reviewed_by VARCHAR(36) REFERENCES users(id);
ALTER TABLE extracted_transactions ADD COLUMN reviewed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE extracted_transactions ADD COLUMN review_notes TEXT;
```

**Rollback**: All columns and indexes dropped in reverse order.

---

## RLS Policy Analysis

### Current Tables with RLS
| Table | RLS Enabled | Policies |
|-------|-------------|----------|
| users | ✅ | - |
| accounts | ✅ | - |
| bank_accounts | ✅ | - |
| uploads | ✅ | - |
| messages | ✅ | - |
| recall_tokens | ✅ | - |
| ... | ✅ | - |

### Required Policies for Guest Chat

#### Messages Table
```sql
-- Guests can insert their own messages
CREATE POLICY "guests_can_insert_messages" ON messages
  FOR INSERT TO anon
  WITH CHECK (sender_role = 'PUBLIC');

-- Anyone can read messages in public conversation
CREATE POLICY "public_read_messages" ON messages
  FOR SELECT TO anon, authenticated
  USING (conversation_id = 'classfund_main');

-- Guests can update their own message status (recall)
CREATE POLICY "guests_can_recall_own" ON messages
  FOR UPDATE TO anon
  USING (sender_role = 'PUBLIC' AND id = (SELECT message_id FROM recall_tokens WHERE token_hash = SHA256(DECODE(current_setting('request.jwt.claims.recall_token', true), 'hex'))));
```

#### Uploads Table
```sql
-- Guests can insert uploads
CREATE POLICY "guests_can_insert_uploads" ON uploads
  FOR INSERT TO anon
  WITH CHECK (uploaded_by IS NULL AND uploader_name IS NOT NULL);

-- Anyone can read upload status
CREATE POLICY "public_read_uploads" ON uploads
  FOR SELECT TO anon, authenticated
  USING (true);
```

#### Recall Tokens Table
```sql
-- Guests can insert recall tokens (via message creation)
CREATE POLICY "guests_can_insert_recall_tokens" ON recall_tokens
  FOR INSERT TO anon
  WITH CHECK (true);

-- Recall validation (service role only)
CREATE POLICY "service_manage_recall_tokens" ON recall_tokens
  FOR ALL TO service_role
  USING (true);
```

#### Extracted Transactions
```sql
-- Read access for message status
CREATE POLICY "public_read_extractions" ON extracted_transactions
  FOR SELECT TO anon, authenticated
  USING (true);

-- Worker writes extractions (service role)
CREATE POLICY "service_write_extractions" ON extracted_transactions
  FOR ALL TO service_role
  USING (true);
```

---

## Storage Bucket Policies

### Receipts Bucket
```sql
-- Bucket: receipts
-- Path pattern: uploads/{upload_id}.{ext}

-- Guests can upload
INSERT POLICY "guests_upload_receipts" ON storage.objects
  FOR INSERT TO anon
  WITH CHECK (bucket_id = 'receipts' AND (storage.foldername(name))[1] = 'uploads');

-- Public read access
SELECT POLICY "public_read_receipts" ON storage.objects
  FOR SELECT TO anon, authenticated
  USING (bucket_id = 'receipts');

-- Service role full access
ALL POLICY "service_manage_receipts" ON storage.objects
  FOR ALL TO service_role
  USING (bucket_id = 'receipts');
```

---

## Realtime Publication

### Required Publications
```sql
-- Enable realtime for messages table
ALTER PUBLICATION supabase_realtime ADD TABLE messages;

-- Enable realtime for uploads table (optional, for status updates)
ALTER PUBLICATION supabase_realtime ADD TABLE uploads;
```

### Realtime Filters
Frontend subscribes to:
```javascript
channel = supabase
  .channel(`messages:${conversationId}`)
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'messages',
    filter: `conversation_id=eq.${conversationId}`
  }, callback)
  .subscribe()
```

---

## Security Checklist

### Credential Management
- ✅ Service role key ONLY on backend (never in frontend)
- ✅ Anon key in frontend (VITE_SUPABASE_ANON_KEY)
- ✅ JWT secret for token verification
- ⚠️ Need to rotate keys for production

### API Key Isolation
- ✅ AI_SERVICE_KEY for internal vision endpoint only
- ✅ Worker uses DATABASE_URL directly (not Supabase)
- ✅ Frontend uses anon key only

### Data Access Control
- ✅ RLS enabled on all tables
- ✅ Guest insert restricted to PUBLIC role
- ✅ Recall tokens hashed with SHA-256
- ✅ Recall token replay protection (used_at)
- ⚠️ Need to add RLS policies for production

### Network Security
- ✅ Ollama endpoint localhost only (127.0.0.1:11434)
- ✅ No public exposure of AI models
- ⚠️ Supabase connection over TLS
- ⚠️ Database connection over TLS

---

## Production Deployment Requirements

### Environment Variables (Backend)
```env
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
JWT_SECRET=strong-random-secret
AI_SERVICE_KEY=strong-random-secret
SUPABASE_URL=https://project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=service-role-key
SUPABASE_ANON_KEY=anon-key
SUPABASE_JWT_SECRET=jwt-secret
OLLAMA_BASE_URL=http://localhost:11434
```

### Environment Variables (Frontend)
```env
VITE_API_URL=https://api.domain.com/api/v1
VITE_SUPABASE_URL=https://project.supabase.co
VITE_SUPABASE_ANON_KEY=anon-key
```

### Database Setup
1. Run migrations 0001-0005
2. Enable RLS on all tables
3. Create policies (see above)
4. Create storage bucket `receipts`
5. Set storage policies
6. Enable realtime publication for messages
7. Configure pg_cron for cleanup jobs (optional)

---

## Verification Commands

### Check Migration Status
```bash
alembic current
alembic history
```

### Verify RLS
```sql
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
SELECT * FROM pg_policies WHERE schemaname = 'public';
```

### Test Realtime
```bash
# Subscribe to channel and verify events
```

### Check Storage
```bash
# Verify bucket exists and policies applied
```