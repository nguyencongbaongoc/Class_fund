# Remediation Scope and Authorization

## Project
CLASS_FUND_WEB

## Phase
DEMO QUALIFICATION REMEDIATION — E2E CLOSURE

## Mode
TARGETED IMPLEMENTATION + REGRESSION VERIFICATION

## Authorization
EXPLICITLY APPROVED

## Branch
master

## Repository
C:\Users\Nguyen Cong Thong\Desktop\CLASS_FUND_WEB

## Objective
Remediate the four incomplete areas discovered during Demo & Live Integration Qualification:

1. **Admin Authentication** - Mock token generation/parsing returns 401 instead of expected 200/403
2. **Review Endpoint** - ExtractedTransaction.created_at missing causing 500 errors
3. **Worker Scenario E** - claim_next_message returns None after processing
4. **Frontend/Backend Contract Tests** - Not tested (0 tests)

## Authorized Work
- Inspect existing source and test code
- Fix identified E2E problems
- Add targeted integration tests
- Add frontend/backend contract tests
- Run targeted regression tests
- Update qualification evidence

## Not Authorized
- Phase 6
- Live Supabase integration
- Production PostgreSQL connection
- Real Ollama qualification
- Production deployment
- Real financial transactions
- Destructive database migrations
- Rewriting financial core
- Replacing production authentication with mock authentication
- Broad UI redesign
- Rebuilding the entire simulation architecture

## Repository Rules
- Work directly on master
- No branch/worktree creation
- No reset, clean, rebase, or force-push
- Preserve uncommitted user changes
- Record Git status and HEAD
- Do not overwrite unrelated files
- Never expose credentials
- Do not use real production credentials
- Keep all tests isolated and synthetic

## Acceptance Criteria
PHASE_REMEDIATION_COMPLETE requires:
- ADMIN AUTH: Valid admin simulation identity works, unauthorized roles denied, invalid/expired tokens rejected, no production auth weakening
- REVIEW: Correct model/schema/fixture contract, review listing/detail work, approve/reject work, gatekeeper preserved, audit events preserved
- WORKER: Scenario E lifecycle correctly understood and tested, claim and lease behavior atomic, retry/recovery correct, no duplicate financial posting
- FRONTEND/BACKEND: API contracts tested, TypeScript strict passes if executable, production build passes if executable, unavailable checks explicitly blocked
- REGRESSION: Financial invariants pass, security invariants pass, targeted tests pass, evidence complete