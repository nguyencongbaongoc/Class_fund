# Known Limitations

## Simulation Architecture Limitations

### 1. No Real PostgreSQL RLS Testing
- **Impact**: Application-level authorization tested, but database-level Row Level Security policies not verified
- **Classification**: `APPLICATION_LEVEL_AUTHORIZATION_TESTED` (not `DATABASE_RLS_VERIFIED`)
- **Mitigation**: Live qualification requires PostgreSQL with RLS enabled

### 2. No Real Supabase Services
- **Auth**: JWT verification mocked; no real Supabase Auth flow tested
- **Storage**: In-memory byte dictionary; no real file upload/CDN behavior
- **Realtime**: Event emitter pattern; no WebSocket connection handling
- **Impact**: Network latency, connection pooling, failover not tested

### 3. No Real Ollama Inference
- **Impact**: Deterministic fixtures only; no actual model behavior under varying image qualities
- **Missing**: OCR accuracy, Vietnamese text handling, low-quality image degradation
- **Mitigation**: Live qualification requires actual Ollama with qwen2.5vl:3b and qwen3.5:4b

### 4. No Real Browser Automation
- **Impact**: Frontend-only behaviors not tested (loading states, empty states, visual rendering)
- **Testing Level**: API contracts only
- **Missing**: TypeScript strict check, production build verification

### 5. Synchronous Worker Simulation
- **Impact**: Worker processes synchronously in test; no true async/concurrent behavior
- **Missing**: Race conditions under load, connection pool contention, lease race conditions

### 6. No Network Partition Simulation
- **Impact**: Cannot test split-brain scenarios, partial connectivity, DNS failures
- **Mitigation**: Live qualification requires chaos engineering

### 7. In-Memory SQLite Limitations
- **No**: Connection pool exhaustion, deadlocks, replication lag, vacuum conflicts
- **No**: FOR UPDATE SKIP LOCKED (simulated with simple SELECT+UPDATE)
- **Impact**: Database-specific failure modes not tested

### 8. Review Endpoint Bug
- **Issue**: `ExtractedTransaction.created_at` column missing in model
- **Impact**: `/api/v1/internal/review` returns 500
- **Classification**: Known pre-existing bug, not introduced by simulation

### 9. Admin Dashboard Auth Header Issue
- **Issue**: Test client JWT token parsing fails with mock tokens
- **Impact**: Admin endpoint tests return 401 instead of 200/403
- **Root Cause**: Mock tokens not properly formatted for FastAPI OAuth2PasswordBearer

### 10. No TypeScript/Build Verification
- **Missing**: `npx tsc --noEmit` (TypeScript strict check)
- **Missing**: `npm run build` (production build)
- **Reason**: Node.js environment not available in test execution context

## Scope Limitations

### Not Tested
- Real financial transaction posting to production ledger
- Real Supabase project connectivity
- Real Ollama model inference
- Real PostgreSQL RLS policies
- Browser-based user interactions
- WebSocket realtime subscriptions
- File upload to real Supabase Storage
- Email/notification delivery
- Backup/restore procedures
- Database migration execution
- Load/performance testing
- Security penetration testing

### Deferred to Live Verification
All items above marked as `LIVE_VERIFICATION_NOT_PERFORMED`

## Classification Policy

| Result | Classification |
|--------|----------------|
| Simulation passes | `SIMULATED_*_VERIFIED` |
| Real service test passes | `LIVE_*_VERIFIED` |
| Mock authorization check | `APPLICATION_LEVEL_AUTHORIZATION_TESTED` |
| Real RLS test passes | `DATABASE_RLS_VERIFIED` |
| Not tested in simulation | `LIVE_VERIFICATION_NOT_PERFORMED` |