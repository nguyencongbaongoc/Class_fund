# Phase 5.1 — Health Semantics Verification

## Findings Summary

**Verdict: `HEALTH_SEMANTICS_PARTIAL`** — Backend health computation logic is correct and well-tested, but frontend rendering has gaps in distinguishing `NOT_CONFIGURED` vs `DOWN`, and some error handling paths may produce misleading indicators.

## Worker Health — Backend (Verified Correct)

**File:** `class-fund-backend-v0.1/class-fund-backend/app/api/routes/admin.py:199-236`

```python
@router.get("/workers", response_model=list[WorkerStatusResponse])
def get_workers(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    workers = db.execute(select(WorkerStatus)).scalars().all()
    now = datetime.now(timezone.utc)
    
    result = []
    for w in workers:
        seconds_since_heartbeat = None
        health: Literal["ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN"] = "UNKNOWN"
        
        if w.last_heartbeat:
            # Ensure both datetimes are timezone-aware for comparison
            heartbeat = w.last_heartbeat
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=timezone.utc)
            now_aware = datetime.now(timezone.utc)
            seconds_since_heartbeat = int((now_aware - heartbeat).total_seconds())
            if seconds_since_heartbeat < 30:
                health = "ONLINE"
            elif seconds_since_heartbeat < 300:
                health = "DEGRADED"
            else:
                health = "OFFLINE"
        
        result.append(WorkerStatusResponse(
            worker_id=w.worker_id,
            status=w.status,
            model_name=w.model_name,
            last_heartbeat=w.last_heartbeat,
            last_processed_at=w.last_processed_at,
            current_job_id=w.current_job_id,
            metadata=w.worker_metadata or {},
            health=health,
            seconds_since_heartbeat=seconds_since_heartbeat,
        ))
    
    return result
```

### Health Thresholds (Correct)
| Status | Condition | Meaning |
|--------|-----------|---------|
| `ONLINE` | `seconds_since_heartbeat < 30` | Worker heartbeat < 30s ago |
| `DEGRADED` | `30 <= seconds < 300` | Heartbeat 30s-5m ago |
| `OFFLINE` | `seconds >= 300` | Heartbeat > 5m ago |
| `UNKNOWN` | `last_heartbeat is None` | No heartbeat ever recorded |

### Test Coverage (Verified)
**File:** `class-fund-backend-v0.1/class-fund-backend/tests/test_admin.py:169-207`

```python
def test_worker_health_computation():
    # w1: heartbeat 10s ago → ONLINE
    # w2: heartbeat 2m ago → DEGRADED
    # w3: heartbeat 10m ago → OFFLINE
    # w4: no heartbeat → UNKNOWN
    
    assert w1_result.health == "ONLINE"
    assert w2_result.health == "DEGRADED"
    assert w3_result.health == "OFFLINE"
    assert w4_result.health == "UNKNOWN"
```

✅ **All 4 worker health states correctly computed and tested.**

## System Health — Backend (Mostly Correct)

**File:** `class-fund-backend-v0.1/class-fund-backend/app/api/routes/admin.py:239-373`

### Component Checks
1. **Database** — `SELECT 1` with latency measurement
2. **AI Service (Ollama)** — HTTP GET to `/api/tags` with 5s timeout
3. **Storage (Supabase)** — `list_buckets()` call
4. **Message Queue** — Counts of PENDING/PROCESSING messages
5. **Worker Pool** — Counts online workers

### Status Values (Backend)
| Status | When Used |
|--------|-----------|
| `HEALTHY` | Component check succeeds |
| `DEGRADED` | Component check succeeds but with warnings (queue > 100, worker pool 0 online) |
| `DOWN` | Component check fails (exception) |
| `NOT_CONFIGURED` | Storage check fails with non-SUPABASE error |

### Overall Status Logic
```python
if "DOWN" in statuses:
    overall = "DOWN"
elif "DEGRADED" in statuses or "NOT_CONFIGURED" in statuses:
    overall = "DEGRADED"
else:
    overall = "HEALTHY"
```

### Issues Identified

#### 1. Storage Check — Ambiguous `NOT_CONFIGURED` Logic
**Lines 308-315:**
```python
except Exception as e:
    components.append(ComponentHealth(
        name="Storage (Supabase)",
        status="NOT_CONFIGURED" if "SUPABASE" not in str(e).upper() else "DOWN",
        ...
    ))
```

**Problem:** String matching on exception message is fragile. Many exceptions won't contain "SUPABASE" in uppercase, leading to misleading `NOT_CONFIGURED` when actually `DOWN`.

#### 2. AI Service Check — No `NOT_CONFIGURED` Path
If Ollama URL is not configured (empty string), `httpx.Client` will raise an exception that gets caught and marked `DOWN`, not `NOT_CONFIGURED`.

#### 3. Timeout Handling
All external checks have 5-second timeout (good), but no retry logic. A transient network blip = `DOWN`.

## Frontend Health Rendering

### AdminDashboardView
**File:** `classfund/classfund/src/views/AdminDashboardView.tsx:83-110`

```typescript
const getHealthIcon = (status: string) => {
  switch (status) {
    case 'HEALTHY': return <CheckCircle className="w-5 h-5 text-emerald-400" />;
    case 'DEGRADED': return <AlertTriangle className="w-5 h-5 text-amber-400" />;
    case 'DOWN': return <XCircle className="w-5 h-5 text-rose-400" />;
    case 'NOT_CONFIGURED': return <Wifi className="w-5 h-5 text-neutral-500" />;
    default: return <Loader2 className="w-5 h-5 text-neutral-500 animate-spin" />;
  }
};
```

### SystemMonitoringView
**File:** `classfund/classfund/src/views/SystemMonitoringView.tsx:72-99`

Same `getHealthIcon` implementation.

### Frontend Issues

#### 1. Missing `UNKNOWN` Worker Health in Frontend
Backend returns `UNKNOWN` for workers with no heartbeat, but frontend `getWorkerHealthColor` (DashboardView:93-101, SystemMonitoringView:82-90) handles only ONLINE/DEGRADED/OFFLINE/UNKNOWN — but the `getHealthIcon` function doesn't have a case for worker health at all.

#### 2. No Distinction Between `NOT_CONFIGURED` and `DOWN` in Overall Status Badge
**DashboardView:293-298:**
```typescript
<span className={`...${
  health?.overall === 'HEALTHY' ? '...' :
  health?.overall === 'DEGRADED' ? '...' :
  'bg-rose-500/10 text-rose-400 border-rose-500/20'
}`}>
  {health?.overall || 'UNKNOWN'}
</span>
```

The fallback `'bg-rose-500/10 text-rose-400 border-rose-500/20'` treats `NOT_CONFIGURED`, `DOWN`, and any unknown value as red (rose). This loses the distinction that `NOT_CONFIGURED` means "not set up yet" vs `DOWN` means "broken."

#### 3. Component Detail Shows Correct Status
The component list (DashboardView:303-326, SystemMonitoringView:125-155) correctly renders each component's individual status with proper icons and colors including `NOT_CONFIGURED` as neutral (wifi icon, neutral-500).

## Missing Heartbeat Handling

### Backend Correct
- No heartbeat → `UNKNOWN` (lines 208-222 in admin.py)
- This is correct and tested

### Frontend Worker Display
Shows "Heartbeat: Xs trước" for workers with heartbeat, nothing for `UNKNOWN` workers (DashboardView:359-363). This is acceptable.

## Stale Heartbeat Risk

### Potential Issue
If a worker process crashes but the database record isn't cleaned up, and the `last_heartbeat` timestamp is recent (< 30s), the worker will appear `ONLINE` until the 30-second threshold passes.

**Mitigation:** Worker startup runs `reclaim_stale_leases()` (worker/main.py:76-88) which resets messages stuck in PROCESSING with expired leases. But the `WorkerStatus` record itself is not auto-cleaned.

**Impact:** Brief window (up to 30s) where dead worker appears `ONLINE`. Acceptable for admin monitoring.

## Test Evidence Summary

| Test | Status | Coverage |
|------|--------|----------|
| `test_worker_health_computation` | ✅ PASS | All 4 worker health states |
| `test_queue_status_metrics` | ✅ PASS | Queue counts |
| `test_admin_stats_aggregation` | ✅ PASS | Worker counts in stats |
| `test_audit_log_pagination_and_filters` | ✅ PASS | N/A |

**No test for system health endpoint** — the `/admin/health` route is not unit tested.

## Conclusion

### Verified Correct
- ✅ Worker health 4-state logic with correct thresholds
- ✅ Worker health tests cover all states
- ✅ Component-level health checks for 5 components
- ✅ Frontend renders component details correctly
- ✅ Timezone-aware datetime comparisons

### Partial / Issues
- ⚠️ `NOT_CONFIGURED` detection fragile (string matching on exception)
- ⚠️ Overall status badge conflates `NOT_CONFIGURED` with `DOWN` (red badge)
- ⚠️ No test coverage for `/admin/health` endpoint
- ⚠️ AI service check lacks `NOT_CONFIGURED` path
- ⚠️ No retry/transient-failure handling for external checks

**Verdict: `HEALTH_SEMANTICS_PARTIAL`** — Core logic correct and tested, but edge cases and frontend presentation have gaps that could mislead operators during live operations.