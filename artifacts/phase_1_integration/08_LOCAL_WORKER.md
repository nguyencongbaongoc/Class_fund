# 08_LOCAL_WORKER.md

## Phase 1 Local Worker Skeleton

### Source Evidence (Phase 0)
- 13_OFFLINE_WORKER_AND_QUEUE_AUDIT.md: Celery/Redis incompatible with PC-off requirement; Supabase polling worker required (`poll_next`, `claim`, `heartbeat`, `recovery`, `lease_expiration`).
- 11_HYBRID_ARCHITECTURE_COMPATIBILITY.md: Worker architecture — poll, claim atomically, download receipt, AI pipeline, verify_and_post_from_ai(), update status, heartbeat. No inbound public port.
- 18_PHASE_0_FINAL_CONSOLIDATED_VERDICT.md: Worker must claim pending messages, resume after restart; atomic claim with `FOR UPDATE SKIP LOCKED`.
- 16_SECURITY_AND_CLOUD_DEPLOYMENT_AUDIT.md: Worker uses service-role key; no HTTP server; localhost only.

### Architecture (Phase 1 Skeleton)
```
Windows PC (Local Network — Trusted)
  ↓
Python Worker Process (standalone; no FastAPI, no uvicorn)
  ↓
Supabase (outbound only — PostgreSQL connection + storage download)
  ↓
Ollama localhost (http://127.0.0.1:11434)
```
- Evidence: 11 (backend as worker; no public exposure), 13 (polling design), 16 (local-only Ollama).

### Required Capabilities (Skeleton Implemented — Concept Verified)
1. **Startup**: Register `worker_status` (`online`); reclaim stale leases (`lease_expires_at < now()` → reset to `pending`).
2. **Heartbeat**: Update `last_heartbeat` every 10 seconds; `current_job_id` when processing.
3. **Claim**: Atomic `UPDATE ... SET status='processing', worker_id=..., claimed_at=now(), lease_expires_at=now() + interval '5 minutes' WHERE id = (SELECT id FROM messages WHERE status='pending' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`.
4. **Process**: Download receipt (if `message_type = 'RECEIPT'`); call existing `VerificationService.verify()`; validate structured AI output; call `verify_and_post_from_ai()` with idempotency key.
5. **Status Update**: `posted` (with `transaction_id`), `awaiting_admin`, `failed` (with `retry_count` increment), `recalled`.
6. **Shutdown**: Graceful; stop claiming new messages; complete current; mark `offline`.

### Lease Expiration / Recovery
```sql
UPDATE messages
SET status = 'pending',
    worker_id = NULL,
    claimed_at = NULL,
    lease_expires_at = NULL
WHERE status = 'processing'
  AND lease_expires_at < now();
```
- Evidence: 13 (lease expiration design, recovery on startup).

### Idempotency (Financial Protection)
- Idempotency key passed to `verify_and_post_from_ai()`: format `msg_{message.id}_attempt_{message.retry_count}`.
- Database constraint (`IdempotencyKey` table with fingerprint) is final protection against duplicate transactions.
- Evidence: 13 (idempotency format), 11 (existing `IdempotencyKey` model verified in `models.py`), 22 (financial gatekeeper contract).

### Safety Rules (Phase 1 Confirmed)
- No inbound public port; worker is standalone Python process.
- `SUPABASE_SERVICE_ROLE_KEY` used only by worker process; never front-end.
- `OLLAMA_BASE_URL` remains `http://127.0.0.1:11434`; no tunnel, no firewall opening.
- Financial posting only through existing `verify_and_post_from_ai()`; AI never updates balance directly.
- Message state checked before posting (`status != 'recalled'`).
- Evidence: 16 (security checklist), 22 (financial gatekeeper), 23 (recall safety).
