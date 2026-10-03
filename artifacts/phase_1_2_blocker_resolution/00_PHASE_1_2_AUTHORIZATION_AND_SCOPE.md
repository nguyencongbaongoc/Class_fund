# 00_PHASE_1_2_AUTHORIZATION_AND_SCOPE.md

## Phase 1.2 Authorization

**Phase**: PHASE 1.2 — BLOCKER RESOLUTION & INTEGRATION READINESS

**Repository**: `C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB`

**Authorization Date**: 2026-10-03

**Authorized By**: User (explicit authorization in prompt)

**Predecessor Phases Completed**:
- Phase 0 — Compatibility Audit ✅
- Phase 1 — Integration Contract ✅
- Phase 1.1 — Contract Review ✅
- Phase 1.1.1 — Audit Correction & Financial Invariant Clarification ✅

## Scope of Authorization

### Authorized Modifications

| Area | Files | Authorization |
|------|-------|---------------|
| Backend source code | `class-fund-backend-v0.1/class-fund-backend/app/**/*.py` | ✅ FULL |
| Backend tests | `class-fund-backend-v0.1/class-fund-backend/tests/*.py` | ✅ FULL |
| Database migrations | `class-fund-backend-v0.1/class-fund-backend/alembic/versions/*.py` | ✅ FULL |
| Frontend source code | `classfund/classfund/src/**/*.tsx`, `*.ts` | ✅ FULL |
| AI services | `ai/**/*.py` | ✅ FULL |
| Development config | `*.toml`, `*.ini`, `docker-compose.yml` | ✅ FULL |
| Integration adapters | New files in `app/services/`, `worker/` | ✅ FULL |

### NOT Authorized

| Action | Reason |
|--------|--------|
| Start Phase 2 | Explicitly prohibited |
| Production database operations | Safety rule |
| Real financial transactions | Safety rule |
| Production credential exposure | Safety rule |
| Bypass financial gatekeeper | Safety rule |
| Commit secrets to Git | Safety rule |
| Automatic deployment | Safety rule |

## Workstreams Authorized

All 10 workstreams (A-J) as defined in the Phase 1.2 mandate:

| Workstream | Focus | Priority |
|------------|-------|----------|
| A | Idempotency - stable message-level identity | CRITICAL |
| B | Exception & Worker Result Contract - deterministic enum | CRITICAL |
| C | Database Integrity - models, constraints, migrations | CRITICAL |
| D | Financial Gatekeeper - preserve & audit existing | CRITICAL |
| E | Recall Authorization & Reversal - secure tokens, race-safe | CRITICAL |
| F | Persistent Worker - Supabase-backed, offline-capable | CRITICAL |
| G | Vision & Ollama Adapter - local model integration | HIGH |
| H | Supabase Integration - auth, RLS, storage, realtime | HIGH |
| I | Frontend Integration - React/TS with backend contracts | HIGH |
| J | Testing & Security - comprehensive test suite | HIGH |

## Completion Gate

Phase 1.2 can ONLY be declared COMPLETE if:

- [ ] Every actionable source-level blocker resolved
- [ ] All critical financial invariants have passing tests
- [ ] Idempotency stable across retries (same key = same result)
- [ ] Duplicate and concurrent posting protections verified
- [ ] Ambiguous commit recovery tested
- [ ] Recall authorization implemented and tested
- [ ] Recall-before-post is race-safe and tested
- [ ] Reversal is safe and tested
- [ ] Worker crash/restart recovery tested
- [ ] Vision adapter has real local execution evidence OR explicitly marked BLOCKED
- [ ] Supabase integration has real environment evidence OR explicitly marked BLOCKED
- [ ] Existing financial regression tests pass
- [ ] No unexplained regression remains
- [ ] All 17 required artifacts exist and are evidence-backed

## Evidence Standard

Every artifact MUST distinguish:
- **IMPLEMENTED** - Code written and in repository
- **SOURCE-VERIFIED** - Verified by reading source code
- **TEST-VERIFIED** - Unit/integration test passes
- **ENVIRONMENT-VERIFIED** - Tested against real environment (DB, Ollama, Supabase)
- **BLOCKED** - Cannot proceed due to external dependency
- **UNVERIFIED** - Not yet tested or verified

## Reporting Requirements

Final report must include:
- Exact modified files with line numbers
- Exact new files created
- Database migrations created and execution status
- Tests run with actual output
- Unresolved blockers with reasons
- Security limitations
- Git branch and HEAD
- Working tree cleanliness
- Evidence-based verdict: `PHASE_1_2_COMPLETE — PHASE_2_ENTRY_READY` OR `PHASE_1_2_PARTIAL — PHASE_2_ENTRY_BLOCKED`

## Stop Condition

**STOP AFTER PHASE 1.2.** Do not open Phase 2. Do not begin production deployment. Do not perform real financial transactions. Wait for separate explicit authorization.