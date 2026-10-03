# 16_REMAINING_GAPS_AND_EXTERNAL_DEPENDENCIES.md

## Remaining Gaps and External Dependencies

### Gaps Requiring External Dependencies

| Gap | Dependency | Impact | Mitigation |
|-----|------------|--------|------------|
| **Supabase Live Integration** | Supabase project + credentials | Cannot verify RLS, Realtime, Storage | All adapters implemented; marked BLOCKED for live test |
| **Ollama Vision Model** | Ollama server + models (`qwen2.5vl:3b`, `qwen3.5:4b`) | Cannot verify extraction accuracy | Client handles offline gracefully; marked UNVERIFIED |
| **Frontend Integration** | Frontend build + API deployment | Cannot verify end-to-end UX | API contracts defined; frontend changes documented |
| **RLS Policy Enforcement** | Supabase project | Cannot test data isolation | Policy SQL ready; helpers implemented |
| **Concurrent Worker Test** | Multiple worker processes + Supabase | Cannot verify parallel processing | Logic tested sequentially; atomic claim verified |

### Gaps Not Yet Implemented (Frontend Scope)

| Gap | Location | Effort | Blocked By |
|-----|----------|--------|------------|
| Inline photo capture in chat | `ChatView.tsx` | Medium | Frontend sprint |
| Sender name input for guests | `ChatView.tsx` | Low | Frontend sprint |
| Message status badges | `ChatView.tsx` | Low | Frontend sprint |
| Public code display | `ChatView.tsx` | Low | Frontend sprint |
| Recall (THU HỘI) button | `ChatView.tsx` | Medium | Frontend sprint |
| Recall token storage (sessionStorage) | `ChatView.tsx` / hooks | Low | Frontend sprint |
| Upload → message flow | `UploadReceiptView.tsx` | Medium | Frontend sprint |
| Realtime status subscription | `AppContext.tsx` | Medium | Supabase credentials |
| API client library | `src/lib/api.ts` | Low | Frontend sprint |

### Gaps with No Current Plan (Out of Phase 1.2 Scope)

| Gap | Reason |
|-----|--------|
| Rate limiting on message creation | DoS protection - Phase 2 |
| Malware scanning on uploads | Security hardening - Phase 2 |
| CSP headers for frontend | Production hardening - Phase 2 |
| Penetration testing | Security audit - Phase 2 |
| Load testing | Performance - Phase 2 |
| Disaster recovery procedures | Operations - Phase 2 |
| Monitoring/alerting | Observability - Phase 2 |
| Backup/restore procedures | Operations - Phase 2 |

### Environment Requirements for Full Verification

To verify all components, the following environment is needed:

1. **PostgreSQL/Supabase**
   - Database URL
   - Service role key
   - Anon key
   - JWT secret

2. **Ollama Server**
   - Running at `http://127.0.0.1:11434`
   - Models: `qwen2.5vl:3b`, `qwen3.5:4b`

3. **Frontend Build**
   - Node.js 18+
   - `npm install` in `classfund/classfund/`
   - Vite dev server or production build

4. **Worker Deployment**
   - `DATABASE_URL` pointing to Supabase
   - `WORKER_ID` unique per instance
   - `LEASE_DURATION` (default 300s)

### Verification Checklist for Phase 2 Entry

Before Phase 2, the following must be externally verified:

- [ ] Supabase project created and credentials provided
- [ ] Migrations 0002-0004 applied to Supabase
- [ ] RLS policies deployed and tested with multiple users
- [ ] Supabase Storage bucket `receipts` created with public access
- [ ] Supabase Realtime enabled for `messages`, `worker_status`
- [ ] Ollama server running with required models
- [ ] Vision model accuracy measured on labeled dataset
- [ ] Frontend integrated with API and tested end-to-end
- [ ] Worker deployed and processing messages
- [ ] Concurrent worker test passed
- [ ] Load test completed

### Current Verification Status

| Component | Source-Verified | Test-Verified | Environment-Verified |
|-----------|-----------------|---------------|---------------------|
| Financial gatekeeper | ✅ | ✅ | ✅ (SQLite) |
| Idempotency | ✅ | ✅ | ✅ (SQLite) |
| Recall authorization | ✅ | ✅ | ✅ (SQLite) |
| Persistent worker | ✅ | ⏳ | ⏳ (needs Supabase) |
| Vision adapter | ✅ | ⏳ | ⏳ (needs Ollama) |
| Supabase adapters | ✅ | ⏳ | ⏳ (needs Supabase) |
| Frontend integration | ⏳ | ⏳ | ⏳ (needs frontend) |
| RLS policies | ✅ (SQL) | ⏳ | ⏳ (needs Supabase) |

### Recommendation

**Phase 1.2 can be declared COMPLETE for source-level implementation.**

All actionable source-level blockers have been resolved with evidence-backed implementations. The remaining gaps are:
1. **External dependency verification** (Supabase, Ollama) - requires credentials/environment
2. **Frontend integration** - requires frontend development sprint
3. **End-to-end integration testing** - requires all services deployed

These are explicitly called out as BLOCKED/UNVERIFIED in the artifacts, not hidden as "done."