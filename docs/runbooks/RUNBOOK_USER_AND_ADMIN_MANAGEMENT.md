# Operational Runbook: User Administration, RBAC & Financial Reconciliation SOP

**Document Reference:** `RUNBOOK-SRE-004`  
**Classification:** Day-2 Production Operations Manual  
**Applies To:** CLASS_FUND_WEB Administrative Portal & Identity Management  
**Authoritative Path:** `app/models/models.py`, `scripts/seed_admin.py`, `app/api/routes/admin.py`  
**Service Level Objectives:** Zero Privilege Escalation | 100% Audit Trail Logging | Invariant Ledger Immutability  

---

## 1. Identity & Role-Based Access Control (RBAC) Architecture

The `CLASS_FUND_WEB` system implements strict hierarchical role separation:

| Role Identifier | Role Title | Key Privileges | Restrictions |
| :--- | :--- | :--- | :--- |
| `OWNER_TREASURER` | Class Fund Owner & Primary Treasurer | Full system control, ledger review, campaign creation, manual adjustments, admin user creation, audit log export. | Bound by ledger double-entry rules; cannot delete historical records. |
| `MODERATOR` | Secondary Treasurer / Committee Member | Receipt OCR review, transaction matching confirmation, student payment flagging. | Cannot alter opening balances or promote users to `OWNER_TREASURER`. |
| `MEMBER` | Class Student / Parent Contributor | View personal contribution status, submit payment receipts, inspect public ledger balance. | Read-only access to own profile and public transparency views. |

---

## 2. Administrator Account Provisioning

### 2.1. Initial Super-Admin Seeding
To provision or reset the initial `OWNER_TREASURER` account during environment bootstrap:
```bash
# In Linux / Docker:
SEED_ADMIN_EMAIL="treasurer@classfund.local" \
SEED_ADMIN_PASSWORD="YourSecureComplexPassword123!" \
SEED_ADMIN_NAME="Chief Treasurer" \
python3 scripts/seed_admin.py

# In Windows / PowerShell:
$env:SEED_ADMIN_EMAIL="treasurer@classfund.local"
$env:SEED_ADMIN_PASSWORD="YourSecureComplexPassword123!"
$env:SEED_ADMIN_NAME="Chief Treasurer"
python scripts/seed_admin.py
```

### 2.2. Interactive Admin Management via API
Administrative endpoints are exposed under `/api/v1/admin/*`:
- `POST /api/v1/admin/users`: Create new administrative users (requires `OWNER_TREASURER` bearer token).
- `PATCH /api/v1/admin/users/{user_id}/role`: Elevate or demote user role.
- `POST /api/v1/admin/users/{user_id}/deactivate`: Instantly revoke user login and terminate active tokens.

---

## 3. Handling Contested Receipts & Matching Discrepancies

### 3.1. Dispute Scenarios
1. **Ambiguous OCR Matching:** OCR extracted student name with low confidence score (< 90%).
2. **Duplicate Payment Claims:** Two students or parents submit receipts for the same bank transaction.
3. **Mismatched Amounts:** Transferred amount differs from campaign contribution quota.

### 3.2. Standard Operating Procedure for Disputed Receipts
1. **Navigate to Review Queue:**
   Access `/admin/review` in the web application or query `/api/v1/review/pending`.
2. **Verify Cryptographic Perceptual Hash (pHash):**
   Examine `image_phash` on the `Upload` record to verify if the physical image was uploaded previously.
3. **Inspect Extracted Metadata:**
   Compare bank transaction timestamp, transaction code, and transfer memo with bank statement feed.
4. **Adjudication Decisions:**
   - **CONFIRM MATCH:** If verified, select student and campaign, then trigger `verify_and_post_from_ai()`.
   - **REJECT RECEIPT:** Mark status as `REJECTED` with audit note explaining rejection (e.g., "Duplicate receipt code #TX9982").
   - **SPLIT PAYMENT:** For multi-student group contributions, create linked matching records.

---

## 4. Financial Reversal & Recall Protocol (Strict Immutability)

### 4.1. Non-Negotiable Ledger Rule
Under no circumstances may an `UPDATE` or `DELETE` statement be executed against the `transactions` or `ledger_entries` tables.
All corrections must follow double-entry compensating reversal principles.

### 4.2. Executing a Transaction Reversal (`REVERT`)
When a posted transaction must be reversed (e.g., bank transfer bounced, duplicate verified post-posting):
1. **Call Authorized Recall Endpoint:**
   ```http
   POST /api/v1/transactions/{transaction_id}/recall
   Authorization: Bearer <OWNER_TREASURER_TOKEN>
   Content-Type: application/json

   {
     "reason": "Bank transfer chargeback received from sender"
   }
   ```
2. **System Behavior:**
   - Appends a new compensating entry to `transactions` with type `REVERT`.
   - Links `referenced_transaction_id` to the original transaction ID.
   - Adjusts running account balance while preserving original transaction in historical audit logs.
   - Generates immutable entry in `audit_logs` recording the operator identity and reason.

---

## 5. Security & Audit Logging Review

### 5.1. Audit Trail Querying
All administrative mutations produce structured JSON logs in `audit_logs`:
```sql
SELECT 
    id, 
    user_id, 
    action, 
    target_type, 
    target_id, 
    details, 
    created_at 
FROM audit_logs 
ORDER BY created_at DESC 
LIMIT 50;
```

### 5.2. Monthly Audit Sign-Off
At the conclusion of each billing/school month:
1. Generate Monthly Financial Ledger Snapshot.
2. Run Cluster Parity Check:
   ```bash
   python scripts/failover_manager.py --reconcile
   ```
3. Export verified ledger report as PDF/CSV.
4. Obtain co-signatures from `OWNER_TREASURER` and Advisory Board.
