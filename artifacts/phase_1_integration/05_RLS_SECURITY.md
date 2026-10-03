# 05_RLS_SECURITY.md

## Phase 1 RLS Security Foundation

### Source Evidence (Phase 0)
- 12_SUPABASE_SCHEMA_AND_DATABASE_COMPATIBILITY.md: No RLS policies currently exist. All 15+ tables need policies. Critical: `messages`, `transactions`, `ledger_entries`, `uploads`, `user_roles`, `worker_status`, `audit_logs`, `accounts`, `bank_accounts`, `collection_campaigns`, `campaign_members`, `students`.
- 14_ADMIN_AUTH_AND_RBAC_AUDIT.md: Policy examples for member read own conversation, admin all messages, treasurer fund write, worker self write.
- 16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md: Default deny (explicit policies required); service role never in frontend; RLS as defense in depth.

### Critical Security Rules (Documented)
- `SERVICE_ROLE_KEY` never in frontend; only worker environment.
- `ANON_KEY` only in frontend; all mutations subject to RLS.
- Every table exposed to frontend/authenticated access must have `ENABLE ROW LEVEL SECURITY`.
- No `DELETE` policy on `audit_logs` (immutable audit trail).
- Public policies only for read-only verified/public data (`accounts`, `ledger_entries` verified, `collection_campaigns`, `bank_accounts` active, `uploads` verified).

### RLS Policies by Table (SQL Contracts — Documented for Phase 1)

#### `messages`
```sql
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_public_messages" ON messages FOR SELECT TO anon
  USING (status = 'posted');
CREATE POLICY "auth_insert_own_message" ON messages FOR INSERT TO authenticated
  WITH CHECK (sender_id = auth.uid() OR auth.uid() IS NULL);
CREATE POLICY "auth_read_own_conversation" ON messages FOR SELECT TO authenticated
  USING (conversation_id IN (
    SELECT conversation_id FROM messages WHERE sender_id = auth.uid()
  ) OR public_code IS NOT NULL);
CREATE POLICY "admin_all_messages" ON messages FOR ALL TO authenticated
  USING (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'))
  WITH CHECK (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'));
```
- Note: Guest insert with `sender_id = NULL` allowed for unauthenticated guests; `sender_name` required. Admin policies use `current_user_role()`.

#### `transactions` / `ledger_entries`
```sql
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_verified_ledger" ON ledger_entries FOR SELECT TO anon, authenticated
  USING (status = 'VERIFIED');
CREATE POLICY "admin_write_ledger" ON transactions FOR INSERT TO authenticated
  WITH CHECK (current_user_role() = 'OWNER_TREASURER');
```
- Evidence: 12 (public read verified; treasurer-only write), 16 (security checklist).

#### `user_roles`
```sql
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "member_read_own_role" ON user_roles FOR SELECT TO authenticated
  USING (user_id = auth.uid());
CREATE POLICY "admin_manage_roles" ON user_roles FOR ALL TO authenticated
  USING (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'));
```

#### `upload` / `uploads`
```sql
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public_read_verified_upload" ON uploads FOR SELECT TO anon
  USING (status = 'VERIFIED');
CREATE POLICY "auth_read_own_upload" ON uploads FOR SELECT TO authenticated
  USING (uploaded_by = auth.uid());
CREATE POLICY "auth_upload_receipt" ON uploads FOR INSERT TO authenticated
  WITH CHECK (auth.uid() IS NOT NULL);
```

#### `worker_status`
```sql
ALTER TABLE worker_status ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_read_workers" ON worker_status FOR SELECT TO authenticated
  USING (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'));
-- Service role bypasses RLS for worker updates (not a policy; relies on service-role bypass)
```

#### `audit_logs`
```sql
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_read_audit" ON audit_logs FOR SELECT TO authenticated
  USING (current_user_role() IN ('OWNER_TREASURER', 'MODERATOR'));
-- No INSERT policy for non-service roles; service role writes audit from backend.
```

### Testing Requirements (Phase 1 Gate)
- Test as anon: `SELECT * FROM messages` returns only `status='posted'` (if any); `SELECT * FROM ledger_entries` returns only `VERIFIED`.
- Test as member: `SELECT * FROM messages` returns only own conversation; `INSERT INTO messages` succeeds only with `sender_id = auth.uid()`.
- Test as treasurer (`OWNER_TREASURER`): full access to `messages`, `transactions`, `audit_logs`, `user_roles`.
- Test worker: uses service-role key; RLS bypassed; can claim and update `messages` and `worker_status`.
- Evidence: 12 (policy syntax), 16 (testing RLS matrix required).
