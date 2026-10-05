# Phase 5 — Deferred Live Verification Checklist

## Level B — Demo/Live Qualification (DEFERRED)

The following items require live external services and are **deferred to a later Demo & Debug stage**. They are **NOT** marked as PASS and must not be described as live verification success.

### PostgreSQL Database
- [ ] PostgreSQL migration and schema verification
- [ ] Production database connection pooling
- [ ] Alembic migration execution on live PostgreSQL
- [ ] Database performance under load

### Supabase Services
- [ ] Supabase Auth integration (JWT validation, user management)
- [ ] Supabase RLS policies enforcement on live database
- [ ] Supabase Storage (file upload, signed URLs, bucket policies)
- [ ] Supabase Realtime (WebSocket subscriptions for live updates)

### AI Processing
- [ ] Live Ollama service connectivity
- [ ] Vision model inference on real receipt images
- [ ] OCR accuracy on production receipt formats
- [ ] AI confidence calibration on real data

### Worker Processing
- [ ] Real worker process deployment and monitoring
- [ ] Worker lease renewal and crash recovery under load
- [ ] Bounded retry behavior with exponential backoff
- [ ] Duplicate detection with persistent state

### End-to-End Financial Workflows
- [ ] Full receipt upload → AI extraction → Review → Approval → Ledger posting
- [ ] Manual credit/debit entry with idempotency
- [ ] Transaction revert (REVERT) with audit trail
- [ ] Concurrent operations under live database conditions
- [ ] Race condition handling in financial posting

### Security & Authorization
- [ ] JWT token validation with Supabase Auth
- [ ] Role-based access control on live endpoints
- [ ] RLS policy enforcement on all tables
- [ ] Service-role key isolation (not exposed to frontend)

### Performance & Reliability
- [ ] API response times under load
- [ ] Database query optimization
- [ ] Worker processing throughput
- [ ] Error rates and retry success rates

---

## Source-Level Verification Status (COMPLETED)

The following items have been **verified at source level** and are **PASSED**:

### Backend Implementation
- ✅ Admin stats endpoint (`GET /admin/stats`) - implemented and tested
- ✅ Audit log endpoint (`GET /admin/audit-logs`) - implemented and tested
- ✅ Worker status endpoint (`GET /admin/workers`) - implemented and tested
- ✅ System health endpoint (`GET /admin/health`) - implemented and tested
- ✅ Queue status endpoint (`GET /admin/queue-status`) - implemented and tested
- ✅ All existing financial, idempotency, recall tests pass (20/20)
- ✅ New admin tests pass (4/4)

### Frontend Implementation
- ✅ Admin Dashboard View - implemented with real API integration
- ✅ AI Review Queue View - implemented with real API integration
- ✅ Admin Ledger View - implemented with real API integration
- ✅ Audit Log View - implemented with real API integration
- ✅ System Monitoring View - implemented with real API integration
- ✅ Admin API client (`src/lib/adminApi.ts`) - implemented
- ✅ TypeScript strict check passes
- ✅ Production build succeeds

### Authorization & Security
- ✅ Role-based access on all new endpoints (OWNER_TREASURER, MODERATOR)
- ✅ No financial mutations in admin endpoints (read-only)
- ✅ All existing authorization logic preserved
- ✅ No secrets in frontend code

---

## Verification Protocol

### When running live verification:
1. Each item must be **actually executed and evidenced**
2. Results must be **recorded with timestamps and logs**
3. Any failures must be **documented with root cause**
4. Items are only marked **PASS** after successful live execution
5. Items not yet executed remain **unchecked** (not PASS, not FAIL)

### Reporting Format
```
LIVE_VERIFICATION_DEFERRED_TO_DEMO: [N items unchecked]
LIVE_VERIFICATION_PASSED: [N items verified]
LIVE_VERIFICATION_FAILED: [N items failed with evidence]
```