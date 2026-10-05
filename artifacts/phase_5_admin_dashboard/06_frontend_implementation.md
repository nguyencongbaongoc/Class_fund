# Phase 5 — Frontend Implementation Summary

## New Admin Views Created

### 1. AdminDashboardView (`src/views/AdminDashboardView.tsx`)
**Purpose:** Main administrative overview dashboard
**Features:**
- Real-time stats from `/admin/stats` endpoint (financial, review, worker, queue metrics)
- System health overview from `/admin/health` (Database, AI Service, Storage, Queue, Worker Pool)
- Worker status grid from `/admin/workers` with computed health (ONLINE/DEGRADED/OFFLINE/UNKNOWN)
- Queue status metrics from `/admin/queue-status` (pending, processing, awaiting_review, posted/failed/recalled today)
- Quick navigation cards to other admin views
- Auto-refresh every 30 seconds
- Loading, error, and empty states

### 2. AIReviewQueueView (`src/views/AIReviewQueueView.tsx`)
**Purpose:** AI extraction review queue for OWNER_TREASURER and MODERATOR
**Features:**
- Lists pending extractions from `/internal/review` endpoint
- Detail modal with extracted fields, confidence scores, raw OCR, field confidences
- Original image viewer via `/internal/ai/uploads/{id}/file`
- Associated upload and message information
- Warning indicators: low confidence (<90%), missing transaction code, high confidence (≥95%)
- Approve workflow: calls `/internal/review/{id}/approve` with confirmation
- Reject workflow: calls `/internal/review/{id}/reject` with reason
- Toast notifications for success/warning/error
- Real-time queue refresh after actions

### 3. AdminLedgerView (`src/views/AdminLedgerView.tsx`)
**Purpose:** Administrative ledger management with full filtering and pagination
**Features:**
- Transaction table from `/admin/audit-logs` (entity_type=TRANSACTION)
- Search by transaction code, sender, note
- Filter by type (CREDIT/DEBIT/REVERT/ALL) and status (VERIFIED/NEEDS_REVIEW/REVERTED/REJECTED/DUPLICATE/ALL)
- Pagination with page size 50
- CSV export functionality
- Transaction detail click-through
- Visual indicators for type, status, and source

### 4. AuditLogView (`src/views/AuditLogView.tsx`)
**Purpose:** Immutable audit trail viewer
**Features:**
- Paginated audit logs from `/admin/audit-logs` endpoint
- Filters: action, entity_type, entity_id, actor_id, date_from, date_to
- Dynamic filter dropdowns populated from data
- Detail view with before/after data (JSON)
- Actor name/role joined from User table
- CSV export
- Pagination with total count

### 5. SystemMonitoringView (`src/views/SystemMonitoringView.tsx`)
**Purpose:** System health, worker pool, and queue monitoring
**Features:**
- Overall system health from `/admin/health` with component breakdown
- Worker status grid from `/admin/workers` with health computation
- Queue metrics from `/admin/queue-status`
- Metric cards for key queue statistics
- Auto-refresh every 30 seconds
- Quick links to API docs and manual refresh

## API Client Layer

### `src/lib/adminApi.ts`
**Complete typed API client for all admin endpoints:**
- `adminApi.getStats()` → AdminStats
- `adminApi.getAuditLogs(params)` → PaginatedAuditLogs
- `adminApi.getWorkers()` → WorkerStatus[]
- `adminApi.getHealth()` → SystemHealth
- `adminApi.getQueueStatus()` → QueueStatus
- `adminApi.getReviewQueue(params)` → ReviewQueueItem[]
- `adminApi.getReviewDetail(id)` → ReviewDetail
- `adminApi.approveExtraction(id, confirm)` → ReviewResponse
- `adminApi.rejectExtraction(id, reason)` → ReviewResponse
- `adminApi.getImageUrl(uploadId)` → string (for image viewer)

**Type Definitions:**
- AdminStats, PaginatedAuditLogs, AuditLogItem
- WorkerStatus, WorkerHealth
- SystemHealth, ComponentHealth, ComponentStatus
- QueueStatus
- ReviewQueueItem, ReviewDetail, ReviewResponse

## Integration Points

### App.tsx
- Added imports for all 5 new admin views
- Extended `tabOrder` array with admin tabs
- Added conditional rendering for admin tabs in `MainContent`

### Navbar.tsx
- Dynamic `navItems` array based on `currentUser.role`
- Admin tabs shown only for TREASURER and MODERATOR
- Uses type assertion `as ViewTab` for new admin tab values

### Types (`src/types/index.ts`)
- Extended `ViewTab` union type with admin tabs:
  - `'admin-dashboard'`
  - `'admin-review'`
  - `'admin-ledger'`
  - `'admin-audit'`
  - `'admin-system'`
  - `'admin-users'` (placeholder)

## UI/UX Patterns Used

### Consistent with Existing Codebase
- **LiquidCard** components for all cards (clear/frosted variants)
- **Lucide React** icons throughout
- **Tailwind CSS** with custom classes (apple-btn-primary, apple-frosted-glass, etc.)
- **Responsive design** (mobile-first, tablet, desktop breakpoints)
- **Loading states** with skeleton/spinner patterns
- **Error states** with retry buttons
- **Empty states** with helpful messaging
- **Toast notifications** via existing `addToast` context

### Accessibility
- Semantic HTML structure
- ARIA labels where appropriate
- Focus-visible states
- Keyboard navigable
- Color contrast compliance

### Data Integrity
- All financial data from authoritative backend endpoints
- No mock data in admin views
- Real-time data with configurable refresh intervals
- Proper error handling with user feedback

## Role-Based Access

| View | TREASURER | MODERATOR | MEMBER | PUBLIC |
|------|-----------|-----------|--------|--------|
| AdminDashboardView | ✅ | ✅ | ❌ | ❌ |
| AIReviewQueueView | ✅ | ✅ | ❌ | ❌ |
| AdminLedgerView | ✅ | ✅ | ❌ | ❌ |
| AuditLogView | ✅ | ✅ | ❌ | ❌ |
| SystemMonitoringView | ✅ | ✅ | ❌ | ❌ |

Enforced at:
- **Backend**: `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)` on all `/admin/*` routes
- **Frontend**: Conditional rendering in Navbar based on `currentUser.role`