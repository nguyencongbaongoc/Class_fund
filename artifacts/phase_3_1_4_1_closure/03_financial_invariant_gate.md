# Financial Invariant Gate

**Date**: 2026-10-04  
**Decision**: PASS — All Phase 2 invariants preserved

---

## 1. Financial Gatekeeper Authority

**Criterion**: `verify_and_post_from_ai()` or equivalent remains the ONLY approved AI-to-ledger posting path.

**Evidence**:
- **Source**: `class-fund-backend-v0.1/class-fund-backend/app/services/ledger.py:378-528` (`verify_and_post_from_ai`)
- **Review API** (`review.py:235-242`) calls this function exclusively
- **Worker** (`worker/main.py:181-187`) calls this function exclusively
- **No other code path** creates `LedgerSource.IMAGE` transactions

**Test**: `test_ai_low_confidence_does_not_post` — low confidence extraction blocked from posting.

**Result**: ✅ PASS

---

## 2. Idempotency Stability

**Criterion**: Stable idempotency keys prevent duplicate ledger entries across retries.

**Key Format**: `msg_{message_id}_v{content_version}` where `content_version = SHA256(payload)[:8]`, payload = `{tx_code}|{amount}|{bank_account_id}`

**Backend Enforcement**: `app/services/ledger.py:109-117` (`check_idempotency`)

```python
if existing_response.request_fingerprint != fingerprint:
    raise HTTPException(409, "Idempotency key was reused with a different request")
```

**Tests** (7/7 PASS):
| Test | Invariant |
|------|-----------|
| `test_idempotent_same_key_same_payload` | Same key + same payload → existing |
| `test_idempotent_different_retry_count_same_payload` | Retry count doesn't change key |
| `test_idempotent_same_message_modified_amount_rejected` | Modified payload → 409 |
| `test_different_message_same_bank_transaction` | Business duplicate blocked |
| `test_concurrent_requests_no_double_post` | Concurrent safety |
| `test_ambiguous_commit_recovery` | Lost response recovery |
| `test_worker_crash_after_commit_recovery` | Worker crash recovery |
| `test_verify_and_post_from_ai_idempotent` | Gatekeeper idempotency |

**Result**: ✅ PASS

---

## 3. Recall-Before-Post Enforcement

**Criterion**: Recall checked before any ledger posting.

**Worker Check** (`worker/main.py:143-148`):
```python
db.expire(message)
if message.status == MessageStatus.RECALLED.value:
    print(f"Message {message.id} was recalled, skipping")
    return
```

**API Check** (`messages.py:197-199`):
```python
if message.status == MessageStatus.RECALLED.value:
    raise HTTPException(409, "Message already recalled")
```

**Test**: `test_recall_before_post` — Recall before processing prevents posting.

**Result**: ✅ PASS

---

## 4. Reversal Preserves Original

**Criterion**: Post-post recall creates REVERT transaction; original preserved.

**Source**: `app/services/ledger.py:300-375` (`post_revert`)

```python
# Creates REVERT transaction with note: "REVERSAL_OF:{original_type.value};REASON:{reason}"
# Original transaction status → REVERTED (NOT deleted)
# Original ledger entry preserved
```

**Test**: `test_revert_restores_balance_without_deleting_original`

**Result**: ✅ PASS

---

## 4. Double Reversal Prevention

**Criterion**: Cannot revert a reversal; cannot double-revert same transaction.

**Source** (`ledger.py:317-333`):
```python
already = db.execute(select(LedgerEntry).where(
    LedgerEntry.original_entry_id == original_entry.id,
    LedgerEntry.type == LedgerType.REVERT
)).scalar_one_or_none()
if already:
    return FAILED("Transaction has already been reverted")
```

**Recall endpoint** (`messages.py:182-183`):
```python
if recall_token.used_at:
    raise HTTPException(409, "Recall token already used")
```

**Test**: `test_double_recall_prevented` — Second recall returns 409.

**Result**: ✅ PASS

---

## 5. Worker Lease & Recovery

**Criterion**: Atomic claim, lease handling, expired lease recovery, bounded retries.

**Atomic Claim** (`worker/main.py:116-138`):
```sql
UPDATE messages SET status='processing', worker_id=..., claimed_at=..., lease_expires_at=...
WHERE id = (SELECT id FROM messages WHERE status='pending' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
```

**Stale Lease Reclaim** (`reclaim_stale_leases` in `startup()`):
```sql
UPDATE messages SET status='pending', worker_id=NULL, claimed_at=NULL, lease_expires_at=NULL
WHERE status='processing' AND lease_expires_at < :now
```

**Retry Logic** (`fail_message`):
- 3 max retries
- Exponential backoff: 60s, 120s, 240s
- After 3 failures → FAILED (terminal)

**Test**: `test_worker_crash_after_commit_recovery` — Stale lease recovery works.

**Result**: ✅ PASS

---

## 6. Security Boundaries

**Criterion**: No service-role key in frontend, no public Ollama, no unauthenticated ledger mutation, no AI-controlled posting.

| Boundary | Implementation | Verification |
|----------|----------------|--------------|
| No service-role in frontend | `.env.example` only has `VITE_SUPABASE_ANON_KEY` | ✅ |
| Ollama internal only | `ollama_client.py` used only by `/internal/vision` with `require_ai_service` | ✅ |
| No unauthenticated ledger mutation | Only `verify_and_post_from_ai()` creates IMAGE transactions | ✅ |
| No AI-controlled posting | AI extracts → validation → gatekeeper → ledger | ✅ |
| No trust in client-supplied financial status | Recall checked before posting; server-side validation | ✅ |

---

## Financial Invariant Gate Decision

**Decision**: **PASS**

All Phase 2 financial invariants preserved with source code evidence and test traceability.