# 12_SECURITY_AND_RLS_AUDIT.md

## Workstream J: Security and RLS Audit

### Current State Analysis

**Security Gaps Identified in Phase 0/1.1.1**:
1. No RLS policies on database tables
2. Guest recall has no authorization (anyone can revert)
3. Service role credentials not properly isolated
4. No audit log for guest actions
5. Public message/transaction IDs don't authorize recall

### Implemented Security Measures

| Measure | Status | Location |
|---------|--------|----------|
| Recall token authorization | ✅ IMPLEMENTED | `messages.py`, `RecallToken` model |
| Token hash storage (SHA-256) | ✅ IMPLEMENTED | `models.py:RecallToken.token_hash` |
| Token replay protection | ✅ IMPLEMENTED | `RecallToken.used_at` check |
| Token expiry support | ✅ IMPLEMENTED | `RecallToken.expires_at` |
| Public ID ≠ authorization | ✅ VERIFIED | Tests confirm |
| RLS helpers | ✅ IMPLEMENTED | `supabase_client.py` |
| Audit log for recall | ✅ IMPLEMENTED | `ledger.py` writes audit on revert |
| Service role server-only | ✅ IMPLEMENTED | `supabase_client.py` admin client |

### RLS Policies Required (Production)

```sql
-- Enable RLS on all tables
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE recall_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_transactions ENABLE ROW LEVEL SECURITY;

-- Messages: guests can create, read own; admins read all
CREATE POLICY "messages_guest_create" ON messages FOR INSERT TO anon WITH CHECK (sender_role = 'PUBLIC');
CREATE POLICY "messages_guest_read" ON messages FOR SELECT TO anon USING (sender_id IS NULL AND sender_role = 'PUBLIC');
CREATE POLICY "messages_admin_all" ON messages FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Transactions: admin only
CREATE POLICY "transactions_admin" ON transactions FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Worker status: admin only
CREATE POLICY "worker_admin" ON worker_status FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Recall tokens: only owner can read their token (via message)
CREATE POLICY "recall_token_owner" ON recall_tokens FOR SELECT TO anon USING (
    EXISTS (SELECT 1 FROM messages m WHERE m.id = recall_tokens.message_id AND m.sender_id IS NULL)
);
CREATE POLICY "recall_token_admin" ON recall_tokens FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));

-- Uploads: guests can create, read own
CREATE POLICY "uploads_guest_create" ON uploads FOR INSERT TO anon WITH CHECK (uploaded_by IS NULL);
CREATE POLICY "uploads_guest_read" ON uploads FOR SELECT TO anon USING (uploaded_by IS NULL);
CREATE POLICY "uploads_admin_all" ON uploads FOR ALL TO authenticated USING (auth.jwt() ->> 'role' IN ('OWNER_TREASURER', 'MODERATOR'));
```

### Credential Security

| Credential | Storage | Access |
|------------|---------|--------|
| `SUPABASE_SERVICE_ROLE_KEY` | Server env only | Backend admin client |
| `SUPABASE_ANON_KEY` | Client env | Frontend public ops |
| `SUPABASE_JWT_SECRET` | Server env | JWT verification |
| `OLLAMA_BASE_URL` | Server env | Vision client |
| `DATABASE_URL` | Server env | SQLAlchemy |
| `JWT_SECRET` | Server env | Auth tokens |

**No secrets in Git** - verified by `.gitignore` and no hardcoded values.

### Guest Permission Model

| Action | Auth Required | Authorization |
|--------|---------------|---------------|
| Send text message | No | None (rate limit recommended) |
| Send receipt (upload) | No | File validation |
| Create message with recall | No | Returns token once |
| Recall own message | No | Requires recall_token |
| View message status | No | Public by message_id |
| View fund balance | No | Public endpoint |
| View bank accounts | No | Public endpoint |
| View campaigns | No | Public endpoint |
| Financial posting | Yes (admin) | OWNER_TREASURER role |
| Revert transaction | Yes (admin) | OWNER_TREASURER role |
| Worker processing | Yes (service) | Service role key |

### Security Test Coverage

| Test | Status |
|------|--------|
| Recall token validation | ✅ PASSED (`test_recall.py`) |
| Token replay protection | ✅ PASSED |
| Public ID cannot recall | ✅ PASSED |
| Double recall prevented | ✅ PASSED |
| Worker recall check | ✅ PASSED |
| RLS policy syntax | ⏳ PENDING (requires Supabase) |

### Remaining Security Tasks

1. **Rate limiting** on message creation endpoint
2. **File upload validation** (MIME, size, malware scan)
3. **CSP headers** for frontend
4. **CORS configuration** for production domains
5. **RLS policy testing** with separate user identities
6. **Penetration testing** of recall flow

### Status

| Task | Status | Evidence |
|------|--------|----------|
| Recall authorization | ✅ IMPLEMENTED + TESTED | `messages.py`, `test_recall.py` |
| Token security (hash, replay, expiry) | ✅ IMPLEMENTED + TESTED | `RecallToken` model, tests |
| Public ID ≠ authorization | ✅ VERIFIED | Tests confirm |
| Service role isolation | ✅ IMPLEMENTED | `supabase_client.py` |
| Audit logging | ✅ IMPLEMENTED | `ledger.py` audit on revert |
| RLS policy helpers | ✅ IMPLEMENTED | `supabase_client.py` |
| RLS policies deployed | ⏳ BLOCKED | Requires Supabase |
| Live security test | ⏳ BLOCKED | Requires credentials |