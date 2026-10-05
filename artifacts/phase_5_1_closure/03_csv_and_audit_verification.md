# Phase 5.1 — CSV Export and Audit Immutability Verification

## Findings Summary

**Verdict: `AUDIT_EXPORT_PARTIAL`** — CSV export uses authoritative backend data and enforces authorization, but has limitations in filter consistency, error handling, and audit immutability claims that need clarification.

## CSV Export — Admin Ledger View

### Implementation
**File:** `classfund/classfund/src/views/AdminLedgerView.tsx:55-74`

```typescript
const exportTransactions = () => {
    const headers = ['Thời gian', 'Loại', 'Mã GD', 'Người gửi', 'Số tiền', 'Trạng thái', 'Nguồn', 'Ghi chú'];
    const rows = transactions.map(tx => [
      tx.created_at,
      tx.type,
      tx.transaction_code,
      tx.sender_name,
      formatVND(tx.amount),
      tx.status,
      tx.source,
      tx.note || '',
    ]);
    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `ledger_export_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };
```

### Data Source
- Uses `transactions` state populated by `loadTransactions()` (line 32-48)
- `loadTransactions()` calls `adminApi.getAuditLogs({ limit: pageSize, offset, entityType: 'TRANSACTION' })`
- Backend: `GET /admin/audit-logs` with `entity_type=TRANSACTION` filter
- Returns paginated results (50 per page by default)

### Authorization
- Button visible only for `currentUser.role === 'TREASURER'` (line 93)
- API call uses JWT token from `localStorage` (adminApi.ts:49-53)
- Backend enforces `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)` on `/admin/audit-logs`

### Issues Identified

#### 1. Pagination Limits Export to Current Page Only
**Critical:** The `exportTransactions` function only exports `transactions` state, which contains **only the current page** (50 records). The user must manually navigate through all pages and export each, or the pagination must be disabled for export.

**Evidence:**
- `loadTransactions()` uses `offset = (page - 1) * pageSize` (line 36)
- `pageSize = 50` (line 29)
- No "export all" option — only exports visible rows

#### 2. Filters Not Applied to Export Consistently
- Search query, type filter, status filter are applied to `loadTransactions` via dependency array `[page, typeFilter, statusFilter, searchQuery]`
- Export uses current `transactions` state, so **filters are reflected** in export
- However, if user changes filters without waiting for reload, stale data may be exported

#### 3. CSV Escaping Incomplete
```typescript
const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(',')).join('\n');
```
- Only wraps values in double quotes
- **No escaping of embedded double quotes** — if `tx.note` contains `"`, CSV will be malformed
- No handling of newlines within fields
- **Formula injection risk:** Values starting with `=`, `+`, `-`, `@` could execute in spreadsheet apps

#### 4. No Error Handling for Export
- If `transactions.length === 0`, button is disabled (good)
- But if export fails (blob creation, URL creation), no user feedback
- Silent failure possible

#### 5. Sensitive Fields
Exported fields: `created_at`, `type`, `transaction_code`, `sender_name`, `amount`, `status`, `source`, `note`
- **No PII beyond sender_name** (which is transaction data)
- No `actor_id`, `ip`, `before_data`, `after_data` (those are in audit logs, not transaction export)
- This is appropriate for ledger export

## Audit Log Immutability

### Backend Audit Model
**File:** `class-fund-backend-v0.1/class-fund-backend/app/models/models.py:222-232`

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4_str)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(120))
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    before_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

### Audit Write Service
**File:** `class-fund-backend-v0.1/class-fund-backend/app/services/audit.py`

```python
def write_audit(db: Session, *, actor_id: str | None, action: str, entity_type: str, entity_id: str | None,
                before: Any = None, after: Any = None, ip: str | None = None) -> None:
    db.add(AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_data=before,
        after_data=after,
        ip=ip,
    ))
```

### Immutability Analysis

#### Application-Level Immutability (Implemented)
- ✅ No `DELETE` or `UPDATE` endpoints for `/admin/audit-logs`
- ✅ `AuditLog` model has no update methods in service layer
- ✅ `write_audit` only does `db.add()` — no update/delete
- ✅ Frontend `AuditLogView` has no edit/delete buttons
- ✅ Backend authorization: `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)` read-only

#### Database-Level Immutability (NOT Enforced)
- ❌ No `ON DELETE RESTRICT` or triggers preventing deletion
- ❌ No `REVOKE DELETE ON audit_logs FROM application_role`
- ❌ No `pg_audit` or equivalent audit extension
- ❌ Direct database access (service role, migrations, admin) can delete/modify

#### REVERT Events Preserve Original Records
**Verified:** Financial reverts create compensating `REVERT` transactions and mark original as `REVERTED` status.
- Original transaction remains in `transactions` table with `status=REVERTED`
- `LedgerEntry` has `original_entry_id` linking revert to original
- Audit log captures both original and revert actions

### Frontend Audit Log View

**File:** `classfund/classfund/src/views/AuditLogView.tsx`

#### Features
- Paginated, filterable display from `/admin/audit-logs`
- Filters: action, entity_type, entity_id, actor_id, date range
- Detail modal shows before/after JSON
- CSV export of current page (similar pagination issue as ledger)
- No edit/delete UI

#### CSV Export (Audit Log View)
**Lines 88-100:**
```typescript
const exportLogs = () => {
    const headers = ['Thời gian', 'Hành động', 'Loại thực thể', 'ID thực thể', 'Người thực hiện', 'Vai trò', 'IP', 'Trước', 'Sau'];
    const rows = logs.map(log => [
      new Date(log.createdAt).toLocaleString('vi-VN'),
      log.action,
      log.entityType,
      log.entityId || '',
      log.actorName || 'System',
      log.actorRole || '',
      log.ip || '',
      log.beforeData ? JSON.stringify(log.beforeData) : '',
      log.afterData ? JSON.stringify(log.afterData) : '',
    ]);
    // ... same CSV generation as ledger
};
```
- Same pagination limitation (current page only)
- Same CSV escaping issues
- Exports `beforeData` and `afterData` as JSON strings (good for audit)

## Authorization Verification

### Backend
- `/admin/audit-logs`: `require_roles(Role.OWNER_TREASURER, Role.MODERATOR)`
- `/fund/credit`, `/fund/debit`, `/fund/transactions/{id}/revert`: `require_roles(Role.OWNER_TREASURER)`
- No `MODERATOR` can mutate financial records

### Frontend
- Admin tabs only shown for `TREASURER` or `MODERATOR` (Navbar.tsx:27)
- Manual entry button only for `TREASURER` (AdminLedgerView.tsx:93)
- Expense modal only for `TREASURER` or `MODERATOR` (DashboardView.tsx:187)

### Gap
Frontend uses `TREASURER` string, backend uses `OWNER_TREASURER` — see Role Mapping verification.

## Conclusion

### CSV Export — `AUDIT_EXPORT_PARTIAL`
| Aspect | Status |
|--------|--------|
| Authoritative data source | ✅ Yes (via `/admin/audit-logs` → `AuditLog` model) |
| Authorization enforced | ✅ Backend + Frontend |
| Filter consistency | ⚠️ Current page only |
| Full dataset export | ❌ Pagination limits to 50 records |
| CSV escaping | ❌ Incomplete (quotes, newlines, formula injection) |
| Error handling | ❌ Silent failures possible |

### Audit Immutability — `AUDIT_EXPORT_PARTIAL`
| Aspect | Status |
|--------|--------|
| Application-level append-only | ✅ Yes (no delete/update API) |
| Database-level immutability | ❌ Not enforced (no triggers, no revoked DELETE) |
| REVERT preserves originals | ✅ Yes (tested) |
| Frontend no edit/delete UI | ✅ Yes |
| "Immutable" claim accuracy | ⚠️ Application-level only, not database-enforced |

### Recommended Remediation
1. Add "Export All" option that fetches all pages or uses a dedicated export endpoint
2. Implement proper CSV escaping (escape quotes, handle newlines)
3. Add formula injection protection (prefix `=` `+` `-` `@` with `'`)
4. Add export error handling with toast notification
5. Document: "Audit logs are application-level immutable; database-level immutability requires operational controls"
6. Consider database-level protections for production (triggers, REVOKE DELETE, pg_audit)