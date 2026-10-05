# Phase 5 — Dashboard Architecture

## Module Structure

### Backend Module Extensions (class-fund-backend-v0.1/class-fund-backend/app/)
```
api/
  routes/
    admin.py           # NEW: Admin dashboard endpoints
    audit.py           # NEW: Audit log listing
    workers.py         # NEW: Worker/system monitoring
schemas/
  admin.py             # NEW: Admin-specific request/response models
services/
  admin.py             # NEW: Admin business logic
  monitoring.py        # NEW: System health checks
```

### Frontend Module Extensions (classfund/classfund/src/)
```
views/
  AdminDashboardView.tsx      # Main admin overview
  AIReviewQueueView.tsx       # AI extraction review
  AdminLedgerView.tsx         # Enhanced ledger management
  AuditLogView.tsx            # Audit trail viewer
  SystemMonitoringView.tsx    # Worker/system health
  UserManagementView.tsx      # User/role management (if supported)
components/
  admin/
    AdminSidebar.tsx          # Admin navigation sidebar
    StatCard.tsx              # Dashboard metric cards
    ReviewQueueTable.tsx      # AI review queue table
    AuditLogTable.tsx         # Audit log table
    WorkerStatusCard.tsx      # Worker health cards
    ConfirmationModal.tsx     # Action confirmations
hooks/
  useAdminAuth.ts             # Admin authentication state
  useReviewQueue.ts           # Review queue data fetching
  useAuditLogs.ts             # Audit log data fetching
  useWorkerStatus.ts          # Worker status data fetching
lib/
  adminApi.ts                 # Admin API client extensions
types/
  admin.ts                    # Admin-specific TypeScript types
```

## Screen-to-API Mapping

| Screen | Primary API Endpoints | Auth Required | Roles |
|--------|----------------------|---------------|-------|
| Admin Dashboard Overview | `GET /fund/balance`, `GET /fund/transactions?limit=5`, `GET /internal/review?limit=5`, `GET /admin/workers`, `GET /admin/stats` | Yes | OWNER_TREASURER, MODERATOR |
| AI Review Queue | `GET /internal/review`, `GET /internal/review/{id}`, `POST /internal/review/{id}/approve`, `POST /internal/review/{id}/reject`, `GET /internal/ai/uploads/{id}/file` | Yes | OWNER_TREASURER, MODERATOR |
| Admin Ledger Management | `GET /fund/transactions`, `GET /fund/balance`, `POST /fund/credit`, `POST /fund/debit`, `POST /fund/transactions/{id}/revert` | Yes | OWNER_TREASURER |
| Audit Log | `GET /admin/audit-logs` | Yes | OWNER_TREASURER, MODERATOR |
| System Monitoring | `GET /admin/workers`, `GET /admin/health`, `GET /admin/queue-status` | Yes | OWNER_TREASURER, MODERATOR |
| User Management | `GET /admin/users`, `PUT /admin/users/{id}/role` | Yes | OWNER_TREASURER |

## Navigation Structure

### Admin Tabs (for OWNER_TREASURER/MODERATOR)
```
Dashboard (/) → AdminDashboardView
AI Review (/admin/review) → AIReviewQueueView  
Ledger (/admin/ledger) → AdminLedgerView
Audit Log (/admin/audit) → AuditLogView
System (/admin/system) → SystemMonitoringView
Users (/admin/users) → UserManagementView (if backend supports)
```

### Public/Member Tabs (unchanged)
```
Dashboard (/dashboard) → DashboardView
Ledger (/ledger) → LedgerView
Upload (/upload) → UploadReceiptView
Campaign (/campaign) → CampaignView
Chat (/chat) → ChatView
Guest Chat (/guest-chat) → GuestChatPage
Bank (/bank) → BankQRView
Donate (/donate) → DonateView
Public (/public) → PublicFundView
```

## State Management

### AppContext Extensions
```typescript
// Admin-specific state
adminTabs: AdminViewTab[];
currentAdminTab: AdminViewTab;
setCurrentAdminTab: (tab: AdminViewTab) => void;
isAdminMode: boolean;
adminUser: User | null;

// Data fetching states
reviewQueue: ReviewQueueItem[];
reviewQueueLoading: boolean;
reviewQueueError: Error | null;
auditLogs: AuditLogItem[];
auditLogsLoading: boolean;
workerStatuses: WorkerStatus[];
workerStatusLoading: boolean;
systemHealth: SystemHealth | null;
```

## Component Hierarchy

```
App
├── AppProvider (Context)
├── Navbar (with admin mode indicator)
├── AdminSidebar (when in admin mode)
├── MainContent
│   ├── AdminDashboardView
│   │   ├── StatCard (balance, income, expense, pending reviews)
│   │   ├── RecentActivityTable (ledger + admin actions)
│   │   └── SystemHealthSummary
│   ├── AIReviewQueueView
│   │   ├── ReviewQueueTable
│   │   ├── ReviewDetailModal
│   │   └── ImageViewer
│   ├── AdminLedgerView
│   │   ├── EnhancedFilterBar
│   │   ├── LedgerTable (with admin actions)
│   │   ├── ManualEntryModal
│   │   └── RevertConfirmationModal
│   ├── AuditLogView
│   │   ├── AuditLogTable
│   │   ├── FilterBar
│   │   └── DetailModal
│   ├── SystemMonitoringView
│   │   ├── WorkerStatusGrid
│   │   ├── QueueStatusPanel
│   │   └── HealthIndicators
│   └── UserManagementView (conditional)
└── Modals/Toasts (shared)
```

## Data Flow

### Admin Dashboard Load
1. User authenticates (JWT token)
2. Role check: OWNER_TREASURER or MODERATOR
3. Parallel API calls:
   - `GET /fund/balance` → current balance, opening balance
   - `GET /fund/transactions?limit=10` → recent transactions
   - `GET /internal/review?limit=10` → pending reviews
   - `GET /admin/workers` → worker statuses
   - `GET /admin/stats` → aggregated stats
4. Render dashboard with real data
5. Loading/error states per widget

### AI Review Flow
1. Load queue: `GET /internal/review`
2. User clicks review item → `GET /internal/review/{id}`
3. Display extraction details, confidence, raw OCR, image
4. User approves → `POST /internal/review/{id}/approve` with `{confirm: true}`
5. Backend processes through gatekeeper → returns transaction_id
6. Update UI: remove from queue, show success, refresh dashboard stats
7. User rejects → `POST /internal/review/{id}/reject` with `{reason: "..."}`
8. Backend marks REJECTED → update UI, refresh stats

### Audit Log Flow
1. Load logs: `GET /admin/audit-logs?limit=50&offset=0&action=...&entity_type=...`
2. Display in paginated table
3. Click row → detail modal with before/after data
4. Filter by action, entity_type, date range, actor

### System Monitoring Flow
1. Load workers: `GET /admin/workers`
2. Determine status per worker:
   - `last_heartbeat < 30s ago` → ONLINE
   - `last_heartbeat < 5m ago` → DEGRADED
   - `last_heartbeat > 5m ago` → OFFLINE
   - No record → UNKNOWN
3. Load queue status: `GET /admin/queue-status` (pending, processing counts)
4. Load health: `GET /admin/health` (DB, AI service, Storage)
5. Display status cards with timestamps

## Error Handling Strategy

### API Error Types
- `401 Unauthorized` → Redirect to login
- `403 Forbidden` → Show "Insufficient permissions"
- `404 Not Found` → Show "Resource not found"
- `409 Conflict` → Show business rule violation (e.g., "Already posted")
- `500 Internal Error` → Show "Server error", log details
- `503 Service Unavailable` → Show "Service degraded", retry option

### UI States
- **Loading**: Skeleton loaders for cards/tables
- **Empty**: "No data available" with action button
- **Error**: Inline error message with retry button
- **Unavailable**: "Service not configured" with admin action hint

## Responsive Breakpoints
- Mobile: < 640px (stacked cards, horizontal scroll tables)
- Tablet: 640px - 1024px (2-column grid, condensed tables)
- Desktop: > 1024px (full layout, sidebar navigation)

## Integration Points with Existing Code

### Reuse from Phase 3.1/4.1
- `review.py` endpoints (no changes needed)
- `fund.py` endpoints (no changes needed)
- `models.py` - AuditLog, WorkerStatus, User, Role
- `services/audit.py` - write_audit function
- `services/ledger.py` - calculate_balance, post_transaction, post_revert
- `worker/main.py` - WorkerStatus upsert pattern
- Frontend: LiquidCard, Navbar, ToastContainer, formatVND utility

### New Backend Endpoints Required
1. `GET /admin/stats` - Aggregated dashboard stats
2. `GET /admin/audit-logs` - Paginated audit log listing
3. `GET /admin/workers` - Worker status listing
4. `GET /admin/health` - System health checks
5. `GET /admin/queue-status` - Message queue status
6. `GET /admin/users` - User listing (if implementing user mgmt)
7. `PUT /admin/users/{id}/role` - Role update (if implementing user mgmt)