# Phase 5 — Admin Dashboard Implementation Scope

## Project Context
- **Project:** CLASS_FUND_WEB
- **Phase:** 5 — Admin Dashboard
- **Branch:** master
- **Execution Mode:** IMPLEMENTATION (source-level only)

## Authorization Status
- Phase 5 explicitly authorized to begin
- Implementation directly on existing `master` branch
- Phase 3.1 and Phase 4.1 accepted as `CLOSED_SOURCE_LEVEL`
- Live integration status: `LIVE_VERIFICATION_BLOCKED`

## Implementation Scope (from requirements)

### 3.1 Admin Dashboard Overview
- Current authoritative fund balance (from ledger endpoint)
- Total income and expenditure
- Transaction statistics
- Pending AI extraction/review count
- Recent ledger activity
- Recent administrative activity
- System and worker health summary
- Loading, empty, unavailable, and error states

### 3.2 Fund and Ledger Management
- Ledger entries administrative view
- Income and expenditure views
- Transaction details
- Transaction status
- Transaction history
- Filtering and pagination
- Relevant transaction metadata
- Preserve existing ledger contracts
- No direct frontend mutation of financial records

### 3.3 AI Review Queue
Integrate existing Phase 3.1 review APIs:
- `GET /internal/review` - List pending reviews
- `GET /internal/review/{extraction_id}` - Extraction details
- `POST /internal/review/{extraction_id}/approve` - Approve extraction
- `POST /internal/review/{extraction_id}/reject` - Reject extraction

Implement:
- Review queue listing
- Extraction details with fields and confidence
- Original uploaded image access
- Duplicate warnings
- Validation warnings
- Approval/rejection workflows
- Review history and audit trail
- Must use existing gatekeeper for approval

### 3.4 User and Role Management
Existing role model:
- `OWNER_TREASURER`
- `MODERATOR`
- `MEMBER`
- `PUBLIC`

Implement only operations supported by existing backend.
Enforce permissions on backend (not frontend hiding).
Do not grant additional privileges.

### 3.5 Audit Log
Administrative audit interface for:
- Financial operations
- AI review decisions
- Approval and rejection events
- Administrative actions
- Recall and reversal events
- Actor identity
- Event timestamps
- Entity references
- Operation results
- Preserve immutable audit history

### 3.6 Worker and System Monitoring
Monitoring views for:
- Worker status
- Queue status
- Processing activity
- Last heartbeat
- Error and retry status
- AI service availability
- Database/API availability

Status categories:
- `ONLINE`
- `OFFLINE`
- `DEGRADED`
- `UNKNOWN`
- `NOT_CONFIGURED`

Only display when backed by real backend evidence.

### 3.7 Administrative UX
- Responsive layout
- Sidebar/navigation
- Dashboard overview
- Ledger management
- AI review
- User/role management (where supported)
- Audit log
- System monitoring
- Search, filtering, pagination
- Confirmation for consequential actions
- Accessible error/success feedback
- Use existing frontend framework (React, Tailwind, Lucide)
- Do not introduce new UI framework

## Architecture Rules
- Reuse Phase 2 backend API contracts
- Reuse existing authentication and role middleware
- Reuse existing ledger APIs
- Reuse existing AI review APIs
- Reuse existing audit/event structures
- Reuse existing worker status infrastructure
- Reuse existing frontend routing and components
- Reuse Supabase integration
- No duplicate APIs
- No second financial data source
- No service-role credentials in frontend
- No internal worker service exposure
- Use existing API auth mechanisms

## Financial & Security Invariants (Non-negotiable)
1. Ledger remains authoritative financial source
2. AI extraction cannot independently post transactions
3. AI approval must use existing gatekeeper
4. Idempotency must remain intact
5. Recall before posting preserves cancellation behavior
6. Recall after posting uses existing compensating REVERT
7. Original financial records preserved
8. Double reversal impossible
9. Worker atomic claim, lease, recovery, bounded retry intact
10. Backend authorization authoritative
11. RLS policies not weakened
12. No secrets in frontend code

## Testing Strategy

### Level A — Source-Level Qualification (REQUIRED NOW)
- New component tests
- New API integration tests
- Authorization tests
- Role-based access tests
- Ledger display and data integrity tests
- Review approval/rejection workflow tests
- Audit log tests
- Worker monitoring state tests
- Error and unavailable-state tests
- Frontend TypeScript strict checks
- Frontend production build
- Targeted regression tests

### Level B — Demo/Live Qualification (DEFERRED)
- PostgreSQL migration verification
- Supabase Auth/RLS/Storage/Realtime
- Live Ollama processing
- Real worker processing
- End-to-end financial workflows
- Concurrent operations under live conditions
- Deferred to Demo & Debug stage

## Acceptance Criteria
Phase 5 marked `PHASE_5_SOURCE_COMPLETE` when:
- Required dashboard functionality implemented
- Real backend contracts integrated
- No fabricated business/financial data displayed
- Role and permission boundaries enforced
- AI review uses existing gatekeeper
- Financial invariants preserved
- Audit and monitoring interfaces work with available contracts
- Targeted tests pass
- TypeScript strict checks pass
- Production build succeeds
- All required artifacts complete

Live qualification reported separately as `LIVE_VERIFICATION_DEFERRED_TO_DEMO`