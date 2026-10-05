# Phase 5 — API Contract Mapping

## Existing Backend Contracts (Reuse Without Changes)

### Fund API (`/api/v1/fund`) - `app/api/routes/fund.py`

| Endpoint | Method | Auth | Roles | Response | Used By |
|----------|--------|------|-------|----------|---------|
| `/balance` | GET | JWT | All authenticated | `AccountOut` (id, name, currency, opening_balance, balance) | AdminDashboard, AdminLedger |
| `/transactions` | GET | JWT | All authenticated | `TransactionOut[]` | AdminDashboard, AdminLedger |
| `/accounts/{id}/opening-balance` | PUT | JWT | OWNER_TREASURER | `AccountOut` | AdminLedger (settings) |
| `/bank-accounts` | GET | JWT | All authenticated | `BankAccount[]` | AdminDashboard, AdminLedger |
| `/bank-accounts` | POST | JWT | OWNER_TREASURER | `BankAccount` | AdminLedger (settings) |
| `/credit` | POST | JWT + Idempotency-Key | OWNER_TREASURER | `TransactionOut` | AdminLedger (manual entry) |
| `/debit` | POST | JWT + Idempotency-Key | OWNER_TREASURER | `TransactionOut` | AdminLedger (manual entry) |
| `/transactions/{id}/revert` | POST | JWT + Idempotency-Key | OWNER_TREASURER | `TransactionOut` | AdminLedger (revert action) |

### AI Review API (`/api/v1/internal/review`) - `app/api/routes/review.py`

| Endpoint | Method | Auth | Roles | Request | Response | Used By |
|----------|--------|------|-------|---------|----------|---------|
| `/` | GET | JWT | OWNER_TREASURER, MODERATOR | Query: status=NEEDS_REVIEW, limit, offset | `ReviewListItem[]` | AIReviewQueue |
| `/{extraction_id}` | GET | JWT | OWNER_TREASURER, MODERATOR | - | `ReviewDetail` | AIReviewQueue (detail modal) |
| `/{extraction_id}/approve` | POST | JWT | OWNER_TREASURER, MODERATOR | `ReviewApproveRequest` {confirm: bool} | `ReviewResponse` | AIReviewQueue (approve) |
| `/{extraction_id}/reject` | POST | JWT | OWNER_TREASURER, MODERATOR | `ReviewRejectRequest` {reason: string} | `ReviewResponse` | AIReviewQueue (reject) |

### AI Internal API (`/api/v1/internal/ai`) - `app/api/routes/ai_internal.py`

| Endpoint | Method | Auth | Request | Response | Used By |
|----------|--------|------|---------|----------|---------|
| `/uploads/{upload_id}/file` | GET | AI Service Key | - | FileResponse | AIReviewQueue (view original image) |
| `/uploads/{upload_id}/result` | POST | AI Service Key | `AIResultIn` | Processing result | Worker (not frontend) |

### Auth API (`/api/v1/auth`) - `app/api/routes/auth.py`

| Endpoint | Method | Auth | Request | Response | Used By |
|----------|--------|------|---------|----------|---------|
| `/login` | POST | None | `LoginRequest` {email, password} | `TokenResponse` {access_token, token_type} | Login Page |
| `/logout` | POST | JWT | - | {ok: true} | Navbar (logout) |
| `/me` | GET | JWT | - | `UserOut` {id, name, email, role} | App init, role check |

### Public API (`/api/v1/public`) - `app/api/routes/public.py`

| Endpoint | Method | Auth | Response | Used By |
|----------|--------|------|----------|---------|
| `/fund` | GET | None | `PublicFundResponse` | PublicFundView |
| `/bank-accounts` | GET | None | `BankAccountResponse[]` | BankQRView, DonateView |

---

## Missing Backend Contracts (Need Implementation)

### Admin Stats API (NEW - `/api/v1/admin/stats`)

**Purpose:** Aggregated dashboard statistics in single call

```
GET /api/v1/admin/stats
Auth: JWT
Roles: OWNER_TREASURER, MODERATOR
Response: AdminStatsResponse
```

```python
class AdminStatsResponse(BaseModel):
    # Financial
    current_balance: Decimal
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    transaction_count: int
    
    # AI Review
    pending_review_count: int
    processing_review_count: int
    
    # System
    worker_online_count: int
    worker_total_count: int
    queue_pending_count: int
    queue_processing_count: int
    
    # Time
    last_transaction_at: datetime | None
    last_review_at: datetime | None
```

### Audit Log API (NEW - `/api/v1/admin/audit-logs`)

**Purpose:** Paginated, filterable audit log listing

```
GET /api/v1/admin/audit-logs
Auth: JWT
Roles: OWNER_TREASURER, MODERATOR
Query Params:
  - limit: int (1-100, default 50)
  - offset: int (default 0)
  - action: str | None (filter by action type)
  - entity_type: str | None (filter by entity)
  - entity_id: str | None (filter by specific entity)
  - actor_id: str | None (filter by actor)
  - date_from: datetime | None
  - date_to: datetime | None
Response: PaginatedAuditLogsResponse
```

```python
class AuditLogItemResponse(BaseModel):
    id: str
    actor_id: str | None
    actor_name: str | None  # Join from User
    actor_role: str | None  # Join from User
    action: str
    entity_type: str
    entity_id: str | None
    before_data: dict | None
    after_data: dict | None
    ip: str | None
    created_at: datetime

class PaginatedAuditLogsResponse(BaseModel):
    items: list[AuditLogItemResponse]
    total: int
    limit: int
    offset: int
```

### Worker Status API (NEW - `/api/v1/admin/workers`)

**Purpose:** List all workers with health status

```
GET /api/v1/admin/workers
Auth: JWT
Roles: OWNER_TREASURER, MODERATOR
Response: WorkerStatusResponse[]
```

```python
class WorkerStatusResponse(BaseModel):
    worker_id: str
    status: str  # online, offline, degraded
    model_name: str | None
    last_heartbeat: datetime | None
    last_processed_at: datetime | None
    current_job_id: str | None
    metadata: dict
    # Computed fields
    health: Literal["ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN"]
    seconds_since_heartbeat: int | None
```

**Health Logic:**
- `last_heartbeat < 30s ago` → ONLINE
- `last_heartbeat < 5m ago` → DEGRADED
- `last_heartbeat > 5m ago` → OFFLINE
- `last_heartbeat is None` → UNKNOWN

### System Health API (NEW - `/api/v1/admin/health`)

**Purpose:** System component health checks

```
GET /api/v1/admin/health
Auth: JWT
Roles: OWNER_TREASURER, MODERATOR
Response: SystemHealthResponse
```

```python
class ComponentHealth(BaseModel):
    name: str
    status: Literal["HEALTHY", "DEGRADED", "DOWN", "NOT_CONFIGURED"]
    last_check: datetime
    details: str | None
    latency_ms: int | None

class SystemHealthResponse(BaseModel):
    overall: Literal["HEALTHY", "DEGRADED", "DOWN"]
    components: list[ComponentHealth]
    checked_at: datetime
```

**Components to Check:**
1. Database (PostgreSQL connection)
2. AI Service (Ollama connectivity)
3. Storage (Supabase/local filesystem)
4. Message Queue (pending/processing counts)
5. Worker Pool (online count vs expected)

### Queue Status API (NEW - `/api/v1/admin/queue-status`)

**Purpose:** Message processing queue metrics

```
GET /api/v1/admin/queue-status
Auth: JWT
Roles: OWNER_TREASURER, MODERATOR
Response: QueueStatusResponse
```

```python
class QueueStatusResponse(BaseModel):
    pending: int
    processing: int
    awaiting_review: int
    posted_today: int
    failed_today: int
    recalled_today: int
    oldest_pending_age_seconds: int | None
    avg_processing_time_seconds: float | None
```

---

## Frontend API Client Extensions (NEW - `src/lib/adminApi.ts`)

### Types
```typescript
// Admin Stats
interface AdminStats {
  currentBalance: number;
  openingBalance: number;
  totalIncome: number;
  totalExpense: number;
  transactionCount: number;
  pendingReviewCount: number;
  processingReviewCount: number;
  workerOnlineCount: number;
  workerTotalCount: number;
  queuePendingCount: number;
  queueProcessingCount: number;
  lastTransactionAt: string | null;
  lastReviewAt: string | null;
}

// Audit Logs
interface AuditLogItem {
  id: string;
  actorId: string | null;
  actorName: string | null;
  actorRole: string | null;
  action: string;
  entityType: string;
  entityId: string | null;
  beforeData: Record<string, unknown> | null;
  afterData: Record<string, unknown> | null;
  ip: string | null;
  createdAt: string;
}

interface PaginatedAuditLogs {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
}

// Worker Status
type WorkerHealth = 'ONLINE' | 'OFFLINE' | 'DEGRADED' | 'UNKNOWN';

interface WorkerStatus {
  workerId: string;
  status: string;
  modelName: string | null;
  lastHeartbeat: string | null;
  lastProcessedAt: string | null;
  currentJobId: string | null;
  metadata: Record<string, unknown>;
  health: WorkerHealth;
  secondsSinceHeartbeat: number | null;
}

// System Health
type ComponentStatus = 'HEALTHY' | 'DEGRADED' | 'DOWN' | 'NOT_CONFIGURED';

interface ComponentHealth {
  name: string;
  status: ComponentStatus;
  lastCheck: string;
  details: string | null;
  latencyMs: number | null;
}

interface SystemHealth {
  overall: 'HEALTHY' | 'DEGRADED' | 'DOWN';
  components: ComponentHealth[];
  checkedAt: string;
}

// Queue Status
interface QueueStatus {
  pending: number;
  processing: number;
  awaitingReview: number;
  postedToday: number;
  failedToday: number;
  recalledToday: number;
  oldestPendingAgeSeconds: number | null;
  avgProcessingTimeSeconds: number | null;
}
```

### API Client Methods
```typescript
export const adminApi = {
  // Stats
  async getStats(): Promise<AdminStats> {
    const response = await fetch(`${API_BASE}/admin/stats`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    return handleResponse<AdminStats>(response);
  },

  // Audit Logs
  async getAuditLogs(params: {
    limit?: number;
    offset?: number;
    action?: string;
    entityType?: string;
    entityId?: string;
    actorId?: string;
    dateFrom?: string;
    dateTo?: string;
  }): Promise<PaginatedAuditLogs> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.set(key, String(value));
    });
    const response = await fetch(`${API_BASE}/admin/audit-logs?${searchParams}`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    return handleResponse<PaginatedAuditLogs>(response);
  },

  // Workers
  async getWorkers(): Promise<WorkerStatus[]> {
    const response = await fetch(`${API_BASE}/admin/workers`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    return handleResponse<WorkerStatus[]>(response);
  },

  // System Health
  async getHealth(): Promise<SystemHealth> {
    const response = await fetch(`${API_BASE}/admin/health`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    return handleResponse<SystemHealth>(response);
  },

  // Queue Status
  async getQueueStatus(): Promise<QueueStatus> {
    const response = await fetch(`${API_BASE}/admin/queue-status`, {
      headers: { Authorization: `Bearer ${getToken()}` }
    });
    return handleResponse<QueueStatus>(response);
  },
};
```

---

## Contract Compatibility Notes

### No Breaking Changes Required
- All existing `/fund` endpoints remain unchanged
- All existing `/internal/review` endpoints remain unchanged
- All existing `/internal/ai` endpoints remain unchanged
- All existing `/auth` endpoints remain unchanged
- All existing `/public` endpoints remain unchanged

### New Endpoints Are Additive
- Admin endpoints under `/admin` prefix (new router)
- No overlap with existing routes
- Role-based access consistent with existing patterns

### Data Consistency
- Admin stats computed from same authoritative sources as individual endpoints
- Audit logs from existing `AuditLog` model
- Worker status from existing `WorkerStatus` model
- Queue status from existing `Message` model queries