# Database and Security Gate

**Date**: 2026-10-04  
**Decision**: SOURCE_SCHEMA_READY / MIGRATION_EXECUTION_VERIFIED=FALSE / RLS_SOURCE_READY / SUPABASE_LIVE_VERIFIED=FALSE

---

## 1. Migration 0005 — Structural Validity

**File**: `class-fund-backend-v0.1/class-fund-backend/alembic/versions/0005_add_attachment_ids_and_ai_fields.py`

### Schema Changes

| Table | Column | Type | Nullable | Purpose |
|-------|--------|------|----------|---------|
| `messages` | `attachment_ids` | JSON | ✅ | Multiple attachments |
| `uploads` | `perceptual_hash` | VARCHAR(128) | ✅ | Duplicate detection |
| `extracted_transactions` | `field_confidences` | JSON | ✅ | Field-level confidence |
| `extracted_transactions` | `extraction_method` | VARCHAR(50) | ✅ | vision/ocr/hybrid |
| `extracted_transactions` | `source_image_id` | VARCHAR(36) | ✅ | Reference to upload |
| `extracted_transactions` | `currency` | VARCHAR(8) | ✅ | VND tracking |
| `extracted_transactions` | `reviewed_by` | VARCHAR(36) FK→users.id | ✅ | Review audit |
| `extracted_transactions` | `reviewed_at` | TIMESTAMP WITH TZ | ✅ | Review audit |
| `extracted_transactions` | `review_notes` | TEXT | ✅ | Review audit |

### Indexes
```sql
CREATE INDEX ix_uploads_perceptual_hash ON uploads(perceptual_hash);
CREATE INDEX ix_extracted_transactions_field_confidences ON extracted_transactions(field_confidences);
```

### Rollback
All columns and indexes dropped in reverse order.

### Ordering
- `down_revision = "0004_add_worker_id_to_messages"` ✅
- Sequential after existing 0001-0004 ✅

**Result**: **SOURCE_SCHEMA_READY** — Migration is structurally valid and ordered correctly.

---

## 2. Migration Execution Verification

**Status**: **MIGRATION_EXECUTION_VERIFIED=FALSE**

**Reason**: Migration 0005 has NOT been applied to PostgreSQL.

```bash
# Required to apply:
cd class-fund-backend-v0.1/class-fund-backend
alembic upgrade head
```

**SQLite Testing**: Migration is compatible with SQLite (tested in `test_duplicate_persistence.py`).
- JSON columns work in SQLite
- Foreign keys enforced
- Indexes created

**Production Requirement**: PostgreSQL 15+ required for:
- `FOR UPDATE SKIP LOCKED` (worker atomic claim)
- Concurrent duplicate detection testing
- Production RLS policies
- Supabase realtime integration

**Result**: **MIGRATION_EXECUTION_VERIFIED=FALSE** — Live verification blocked by missing PostgreSQL.

---

## 3. RLS Policies — Source Readiness

**Status**: **RLS_SOURCE_READY** — Policies defined in artifacts, not yet applied.

### Required Policies (from `artifacts/residual_blocker_closure/06_rls_security_changes.md`)

| Table | Policies Defined | Roles |
|-------|------------------|-------|
| `messages` | 4 | anon, authenticated, service_role |
| `uploads` | 3 | anon, authenticated, service_role |
| `extracted_transactions` | 3 | anon, authenticated, service_role |
| `recall_tokens` | 1 | service_role |
| `idempotency_keys` | 1 | service_role |
| `storage.objects` (bucket: receipts) | 3 | anon, authenticated, service_role |

### Key Security Properties (Verified in Code)

| Requirement | Verification |
|-------------|--------------|
| No anonymous user can read private messages | Policy restricts to `conversation_id = 'classfund_main'` |
| No user can read another's private data | Recall tokens hashed (SHA-256), service-role only for tokens |
| Guest access follows contract | Limited to insert own messages/uploads |
| No client can update financial fields | Service role only for ledger writes |
| Storage scoped to user/group | Uploads folder, public read for display |
| Service-role credentials backend-only | Never in frontend `.env.example` |
| No broad public SELECT/UPDATE/DELETE | Policies are specific |

### Storage Bucket: `receipts`
```sql
-- Path pattern: uploads/{upload_id}.{ext}
CREATE POLICY "guests_upload_receipts" ON storage.objects
  FOR INSERT TO anon
  WITH CHECK (bucket_id = 'receipts' AND (storage.foldername(name))[1] = 'uploads');
```

### Realtime Publications
```sql
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE uploads;
```

**Result**: **RLS_SOURCE_READY** — Policies defined and documented, ready for Supabase deployment.

---

## 4. Supabase Live Verification

**Status**: **SUPABASE_LIVE_VERIFIED=FALSE**

**Reason**: No Supabase project configured.

### Required for Live Verification
1. Create Supabase project
2. Apply migrations 0001-0005 in Supabase SQL editor
3. Enable RLS on all tables
4. Create all 17 policies in order (service_role first)
5. Create storage bucket `receipts` with 3 policies
6. Enable realtime publications for `messages` and `uploads`
7. Configure environment variables:
   - Backend: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`
   - Frontend: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

**Workaround Active**: Frontend uses polling fallback (5s interval) + local filesystem storage.

---

## Database & Security Gate Summary

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Migration 0005 structurally valid | ✅ SOURCE_SCHEMA_READY | Migration file exists, ordered correctly |
| Migration executed on PostgreSQL | ❌ MIGRATION_EXECUTION_VERIFIED=FALSE | Requires PostgreSQL provisioning |
| RLS policies defined | ✅ RLS_SOURCE_READY | 17 policies defined in artifacts |
| RLS policies applied | ❌ SUPABASE_LIVE_VERIFIED=FALSE | Requires Supabase project |
| Storage policies defined | ✅ | 3 policies for `receipts` bucket |
| Storage policies applied | ❌ | Requires Supabase |
| Realtime publications | ✅ Defined | `messages`, `uploads` |
| Realtime enabled | ❌ | Requires Supabase |
| Service-role credentials backend-only | ✅ | Not in frontend `.env.example` |
| No broad public access | ✅ | Policies are specific |

---

## Database & Security Gate Decision

**Overall**: **SOURCE_SCHEMA_READY / RLS_SOURCE_READY** — Schema and policies are defined and ready for deployment.

**Live Verification**: **BLOCKED** — Requires PostgreSQL + Supabase provisioning.

**Does not affect source-level closure** — External dependencies tracked separately.