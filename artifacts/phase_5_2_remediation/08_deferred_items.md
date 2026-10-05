# Phase 5.2 — Deferred Items

## Items Explicitly Deferred (Per Phase 5.2 Non-Goals)

| Item | Reason | Future Phase |
|------|--------|--------------|
| User Management CRUD | Explicitly excluded from Phase 5.2 scope | Phase 6+ |
| `/admin/users` API | Requires user management implementation | Phase 6+ |
| Supabase Live Integration | Requires live credentials and infrastructure | Demo & Live Integration |
| PostgreSQL Production Deployment | Infrastructure concern, not code remediation | Deployment Phase |
| Live Ollama Qualification | Requires GPU infrastructure | Demo & Live Integration |
| Worker Deployment | Infrastructure/ops concern | Deployment Phase |
| Supabase Realtime Implementation | Feature enhancement, not remediation | Phase 6+ |
| Database-Level Audit Immutability (triggers, REVOKE, pg_audit) | Requires migration approval, operational changes | Separate approval process |
| Full Demo & Debug Workflow | Requires live integration first | Demo & Live Integration |
| Financial Posting Architecture Changes | Core invariants must not be touched | N/A (prohibited) |
| Recall/Reversal Contract Changes | Core invariants must not be touched | N/A (prohibited) |
| UI Redesign Unrelated to Remediation | Out of scope for remediation | N/A |

## Items Identified During Remediation (Not Critical for 5.2)

| Item | Description | Impact | Recommendation |
|------|-------------|--------|----------------|
| Health endpoint mocking tests | Two tests skipped due to OllamaClient/httpx.Client mocking complexity | Test coverage gap for happy path | Investigate better mocking strategy or integration test with real services |
| Worker auto-cleanup | WorkerStatus records not auto-cleaned on process crash | Stale ONLINE appearance up to 30s | Add periodic cleanup job or TTL-based expiration |
| Export streaming for large datasets | Current limit 50,000 records loaded in memory | Memory pressure for very large exports | Implement streaming CSV response for >50k records |
| Health check retry logic | Transient network blips mark component DOWN | False alerts | Add configurable retry (e.g., 2 retries with backoff) |
| Frontend role mapping from JWT | Not yet implemented (mock mode only) | Will need implementation for live auth | Implement JWT parsing → `normalizeRole()` in auth flow |
| CSV export progress indicator | Large exports may take time | UX improvement | Add progress bar for paginated fetches |

## Items Requiring Architecture Decision

| Item | Options | Decision Needed |
|------|---------|-----------------|
| Database-level audit immutability | Triggers vs REVOKE vs pg_audit vs WAL replication | Security/compliance review |
| Health check required components | Current: Database, AI, Queue. Should Storage/Worker Pool be required? | Product/ops decision |
| Export format options | CSV only vs CSV + Excel + JSON | User requirement |

## Non-Issues (Verified Working)

| Item | Status |
|------|--------|
| Financial core invariants | ✅ All tests pass |
| Idempotency guarantees | ✅ All 8 tests pass |
| Recall authorization | ✅ All 8 tests pass |
| REVERT history preservation | ✅ Verified in tests |
| Backend authorization model | ✅ Unchanged, authoritative |
| Role mapping (mock mode) | ✅ Working correctly |
| TypeScript strict mode | ✅ Passes |
| Production build | ✅ Succeeds |