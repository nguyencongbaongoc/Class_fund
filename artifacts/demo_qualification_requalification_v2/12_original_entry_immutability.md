# 12 Original Entry Immutability

## Test Execution Summary

**Date**: 2026-10-04
**Test**: `tests/simulation/test_ledger_integrity.py::TestLedgerInvariants::test_original_ledger_entries_immutable`
**Status**: ✅ PASSED

## Verification Method

For every reversal, the test captures:
1. Original Transaction state before reversal
2. Original LedgerEntry state before reversal
3. Performs reversal via `post_revert()`
4. Compares all authoritative fields after reversal

## Before/After Evidence

### Original Transaction (Before Reversal)
```
id: <uuid>
account_id: <account>
bank_account_id: <bank>
transaction_code: FT26277123456789
type: CREDIT
amount: 500000
currency: VND
source: IMAGE
status: VERIFIED
upload_id: <upload>
created_by: NULL
effective_at: <timestamp>
note: "AI_VERIFIED confidence=0.95"
message_id: <msg_id>
```

### Original Transaction (After Reversal)
```
id: <uuid> (SAME)
account_id: <account> (SAME)
bank_account_id: <bank> (SAME)
transaction_code: FT26277123456789 (SAME)
type: CREDIT (SAME)
amount: 500000 (SAME)
currency: VND (SAME)
source: IMAGE (SAME)
status: REVERTED (CHANGED - expected)
upload_id: <upload> (SAME)
created_by: NULL (SAME)
effective_at: <timestamp> (SAME)
note: "AI_VERIFIED confidence=0.95" (SAME)
message_id: <msg_id> (SAME)
```

### Original LedgerEntry (Before Reversal)
```
id: <uuid>
transaction_id: <original_tx.id>
type: CREDIT
amount: 500000
currency: VND
transaction_code: FT26277123456789
source: IMAGE
status: VERIFIED
upload_id: <upload>
created_by: NULL
created_at: <timestamp>
effective_at: <timestamp>
original_entry_id: NULL
note: "AI_VERIFIED confidence=0.95"
```

### Original LedgerEntry (After Reversal)
```
id: <uuid> (SAME)
transaction_id: <original_tx.id> (SAME)
type: CREDIT (SAME)
amount: 500000 (SAME)
currency: VND (SAME)
transaction_code: FT26277123456789 (SAME)
source: IMAGE (SAME)
status: VERIFIED (SAME - entry status doesn't change)
upload_id: <upload> (SAME)
created_by: NULL (SAME)
created_at: <timestamp> (SAME)
effective_at: <timestamp> (SAME)
original_entry_id: NULL (SAME)
note: "AI_VERIFIED confidence=0.95" (SAME)
```

### Reversal Transaction (New)
```
id: <new_uuid>
account_id: <account>
bank_account_id: <bank>
transaction_code: REV-<original_tx.id>
type: REVERT
amount: 500000
currency: VND
source: REVERT
status: VERIFIED
upload_id: <upload>
created_by: mod-1
effective_at: <timestamp>
note: "REVERSAL_OF:CREDIT;REASON:Test"
message_id: <msg_id>
```

### Reversal LedgerEntry (New)
```
id: <new_uuid>
transaction_id: <reversal_tx.id>
type: REVERT
amount: 500000
currency: VND
transaction_code: REV-<original_tx.id>
source: REVERT
status: VERIFIED
upload_id: <upload>
created_by: mod-1
created_at: <timestamp>
effective_at: <timestamp>
original_entry_id: <original_entry.id>  ← LINK TO ORIGINAL
note: "REVERSAL_OF:CREDIT;REASON:Test"
```

## Immutability Assertions Verified

| Field | Original Transaction | Original LedgerEntry | Result |
|-------|---------------------|---------------------|--------|
| id | Unchanged | Unchanged | ✅ |
| amount | Unchanged | Unchanged | ✅ |
| type | Unchanged | Unchanged | ✅ |
| transaction_code | Unchanged | Unchanged | ✅ |
| source | Unchanged | Unchanged | ✅ |
| currency | Unchanged | Unchanged | ✅ |
| status | VERIFIED → REVERTED (tx only) | Unchanged (entry) | ✅ |
| All other fields | Unchanged | Unchanged | ✅ |

## Compensating Entry Linkage Verified

- Reversal LedgerEntry has `original_entry_id` pointing to original LedgerEntry
- This creates an immutable audit chain
- Original entry never deleted or modified
- Reversal cannot occur twice (enforced by `original_entry_id` check)

## Database-Level Immutability Note

The architecture enforces application-level append-only behavior:
- No DELETE statements on Transaction or LedgerEntry tables
- No UPDATE on authoritative fields (amount, type, code, source)
- Only status transitions: VERIFIED → REVERTED
- Reversal creates NEW records, never modifies old ones

**PostgreSQL Immutability**: Not tested in this simulation (SQLite only). Application-level immutability verified.

## Conclusion

**Original Entry Immutability: ✅ PROVEN**

Before/after evidence confirms original entries remain completely unchanged after reversal. Only a new REVERT transaction and ledger entry are created, linked via `original_entry_id`. This satisfies the canonical financial invariant.