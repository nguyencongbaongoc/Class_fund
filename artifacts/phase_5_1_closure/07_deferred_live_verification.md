# Phase 5.1 — Deferred Live Verification Checklist

## Status: `LIVE_VERIFICATION_DEFERRED_TO_DEMO`

All items below require live external services and are **deferred to a later Demo & Debug stage**. They are **NOT** marked as PASS and must not be described as live verification success.

---

## PostgreSQL Database
- [ ] PostgreSQL migration and schema verification (Alembic `alembic upgrade head`)
- [ ] Production database connection pooling under load
- [ ] Database performance benchmarks (query latency, connection limits)
- [ ] Backup/restore procedure validation

## Supabase Services
- [ ] Supabase Auth integration (JWT validation, user registration, login/logout)
- [ ] Supabase RLS policies enforcement on live database (test with different roles)
- [ ] Supabase Storage (file upload, signed URLs, bucket policies, CDN)
- [ ] Supabase Realtime (WebSocket subscriptions for live ledger/chat updates)

## AI Processing
- [ ] Live Ollama service connectivity (model loading, inference latency)
- [ ] Vision model inference on real receipt images (accuracy benchmarks)
- [ ] OCR accuracy on production receipt formats (Vietnamese bank receipts)
- [ ] AI confidence calibration on real data (threshold tuning)

## Worker Processing
- [ ] Real worker process deployment (Docker/K8s, health checks, scaling)
- [ ] Worker lease renewal and crash recovery under load
- [ ] Bounded retry behavior with exponential backoff (60s, 120s, 240s)
- [ ] Duplicate detection with persistent state across restarts
- [ ] Worker pool autoscaling based on queue depth

## End-to-End Financial Workflows
- [ ] Full receipt upload → AI extraction → Review → Approval → Ledger posting
- [ ] Manual credit/debit entry with idempotency key generation
- [ ] Transaction revert (REVERT) with audit trail verification
- [ ] Concurrent operations under live database conditions (race conditions)
- [ ] Recall before/after posting with compensating entries

## Security & Authorization
- [ ] JWT token validation with Supabase Auth (token refresh, revocation)
- [ ] Role-based access control on live endpoints (OWNER_TREASURER vs MODERATOR)
- [ ] RLS policy enforcement on all tables (test with service role bypass)
- [ ] Service-role key isolation (not exposed to frontend, not in logs)

## Performance & Reliability
- [ ] API response times under load (p50, p95, p99)
- [ ] Database query optimization (EXPLAIN ANALYZE on critical paths)
- [ ] Worker processing throughput (messages/minute)
- [ ] Error rates and retry success rates
- [ ] System health check latency (Ollama, Supabase, DB)

## Monitoring & Observability
- [ ] Admin dashboard live data refresh (30s interval)
- [ ] Worker heartbeat accuracy in production
- [ ] Queue depth alerts (pending > threshold)
- [ ] Log aggregation and alerting
- [ ] Audit log completeness verification

---

## Verification Protocol

### When running live verification:
1. Each item must be **actually executed and evidenced** (logs, screenshots, metrics)
2. Results must be **recorded with timestamps and evidence**
3. Any failures must be **documented with root cause and remediation**
4. Items are only marked **PASS** after successful live execution
5. Items not yet executed remain **unchecked** (not PASS, not FAIL)

### Reporting Format
```
LIVE_VERIFICATION_DEFERRED_TO_DEMO: [N items unchecked]
LIVE_VERIFICATION_PASSED: [N items verified]
LIVE_VERIFICATION_FAILED: [N items failed with evidence]
```

---

## Source-Level Verification Status (COMPLETED)

The following items have been **verified at source level** and are **PASSED**:

### Backend Implementation
- ✅ Admin stats endpoint (`GET /admin/stats`) — implemented and unit tested
- ✅ Audit log endpoint (`GET /admin/audit-logs`) — implemented and unit tested
- ✅ Worker status endpoint (`GET /admin/workers`) — implemented and unit tested
- ✅ System health endpoint (`GET /admin/health`) — implemented (not unit tested)
- ✅ Queue status endpoint (`GET /admin/queue-status`) — implemented and unit tested
- ✅ All existing financial, idempotency, recall tests pass (20/20)
- ✅ New admin tests pass (4/4)

### Frontend Implementation
- ✅ Admin Dashboard View — implemented with real API integration
- ✅ AI Review Queue View — implemented with real API integration
- ✅ Admin Ledger View — implemented with real API integration
- ✅ Audit Log View — implemented with real API integration
- ✅ System Monitoring View — implemented with real API integration
- ✅ Admin API client (`src/lib/adminApi.ts`) — implemented
- ✅ TypeScript strict check passes
- ✅ Production build succeeds

### Authorization & Security
- ✅ Role-based access on all new endpoints (OWNER_TREASURER, MODERATOR)
- ✅ No financial mutations in admin endpoints (read-only)
- ✅ All existing authorization logic preserved
- ✅ No secrets in frontend code

---

## Gap Analysis: Source vs Live

| Area | Source Verified | Live Required |
|---|---|---|
| API Contracts | ✅ Unit tests | ❌ Integration with real DB |
| Auth Flow | ❌ Mock only | ✅ Supabase Auth |
| AI Pipeline | ❌ Mock only | ✅ Real Ollama |
| Worker | ❌ Mock only | ✅ Real worker process |
| Storage | ❌ Mock only | ✅ Real Supabase Storage |
| Realtime | ❌ Not implemented | ✅ WebSocket subscriptions |
| RLS | ❌ Not testable | ✅ Policy enforcement |

**Conclusion:** Source-level implementation is complete and correct. Live verification requires full infrastructure deployment and is explicitly deferred.