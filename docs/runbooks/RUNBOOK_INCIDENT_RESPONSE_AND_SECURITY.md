# Operational Runbook: Incident Response, Security & Secret Rotation

**Document Reference:** `RUNBOOK-SRE-003`  
**Classification:** Day-2 Production Operations Manual  
**Applies To:** CLASS_FUND_WEB Backend, Asynchronous Worker & Infrastructure  
**Authoritative Path:** `app/core/security.py`, `app/core/alerting.py`, `worker/main.py`  
**Service Level Objectives:** MTTR < 15 minutes | Zero Compromised Ledger Data | Zero Stale Worker Leases  

---

## 1. Incident Classification Matrix

| Severity | Definition | Example Scenarios | Response Time |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Financial ledger corruption, split-brain, total system outage, active security intrusion. | Primary DB crashed without replica, JWT key compromise, balance divergence > 0.00 VND. | < 5 minutes |
| **SEV-2 (High)** | Degradation of critical business capability, worker pipeline stall, OCR offline. | OCR circuit breaker tripped, replication lag > 10s, worker batch leasing deadlock. | < 15 minutes |
| **SEV-3 (Medium)** | Minor feature failure, transient error burst, edge proxy rate limiting valid clients. | Upload queue backlog > 50 messages, occasional 502 Bad Gateway from Ollama. | < 1 hour |
| **SEV-4 (Low)** | Non-impacting telemetry failure, log formatting warnings. | Prometheus metric scrape delay, minor documentation mismatch. | < 24 hours |

---

## 2. OCR Circuit Breaker Triage & Recovery

### 2.1. Trigger Condition
The AI/OCR pipeline incorporates an automated circuit breaker (`CircuitBreaker` in `app/core/alerting.py`). If Ollama vision/text requests fail **3 consecutive times** within 60 seconds (HTTP 500, timeout > 30s, or unreachable), the circuit breaker transitions to **OPEN**.
- Telemetry: `classfund_circuit_breaker_trips_total` incremented.
- Alert: `CIRCUIT_BREAKER_TRIPPED` dispatched.
- Behavior: Uploads are placed into `PENDING_REVIEW` or fallback OCR mode without worker crash.

### 2.2. Triage & Diagnostic Steps
1. **Check Ollama Inference Service Health:**
   ```bash
   curl -I http://127.0.0.1:11434/api/tags
   ```
2. **Inspect Ollama GPU / Resource Constraints:**
   ```powershell
   nvidia-smi
   Get-Process ollama* | Select-Object Id, CPU, WorkingSet64
   ```
3. **Verify Models Loaded in VRAM:**
   ```bash
   curl -s http://127.0.0.1:11434/api/tags | jq .models
   # Ensure 'qwen2.5vl:3b' and 'qwen3.5:4b' are present
   ```

### 2.3. Remediating Tripped Circuit Breaker
1. If Ollama hung, restart the service:
   ```powershell
   Restart-Service Ollama -ErrorAction SilentlyContinue
   ```
2. Reset circuit breaker manually via backend management CLI or restart worker container:
   ```bash
   docker restart classfund_worker
   ```
3. The circuit enters **HALF-OPEN** state: next request tests inference. Upon success, normal processing resumes.

---

## 3. Resolving Stuck Worker Leases (`SKIP LOCKED`)

### 3.1. Architecture of Worker Leasing
Workers claim batches of pending uploads atomically using:
```sql
SELECT * FROM uploads 
WHERE status = 'PENDING' AND (locked_until IS NULL OR locked_until < NOW())
ORDER BY created_at ASC 
LIMIT 10 
FOR UPDATE SKIP LOCKED;
```
If a worker crashes mid-processing, leases expire after **300 seconds (5 minutes)**.

### 3.2. Detecting Worker Lease Stalls
Check for uploads stranded in `PROCESSING` status with expired leases:
```sql
SELECT id, status, locked_by, locked_until, created_at 
FROM uploads 
WHERE status = 'PROCESSING' AND locked_until < NOW();
```

### 3.3. Manual Lease Recovery Procedure
To immediately release all stranded leases without waiting for TTL:
```sql
UPDATE uploads 
SET status = 'PENDING', locked_by = NULL, locked_until = NULL 
WHERE status = 'PROCESSING' AND locked_until < NOW();
```
Worker nodes will pick up released tasks on the next polling cycle.

---

## 4. Production Secret Rotation Protocols

### 4.1. JWT Secret Rotation (Zero User Interruption)
To rotate `JWT_SECRET` without invalidating existing active sessions:
1. **Dual-Key Phase:**
   - Generate high-entropy secret:
     ```bash
     openssl rand -hex 64
     ```
   - Update `.env.production`:
     ```env
     JWT_SECRET=<NEW_SECRET>
     JWT_SECRET_PREVIOUS=<OLD_SECRET>
     ```
   - Deploy backend. The JWT decoder checks `NEW_SECRET` first; if invalid, verifies with `OLD_SECRET`. All newly issued tokens use `NEW_SECRET`.
2. **Decommission Phase (After 60 minutes):**
   - Once all old tokens have expired (`ACCESS_TOKEN_MINUTES=60`), remove `JWT_SECRET_PREVIOUS` from `.env.production`.

### 4.2. MySQL Database Password Rotation
1. **Connect to Primary as Administrator:**
   ```sql
   ALTER USER 'classfund'@'%' IDENTIFIED BY '<NEW_STRONG_PASSWORD>';
   FLUSH PRIVILEGES;
   ```
2. **Update Application Environment:**
   Update `MYSQL_PASSWORD=<NEW_STRONG_PASSWORD>` in `.env.production`.
3. **Rolling Restart Backend & Worker:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d --no-deps backend worker
   ```
4. **Verify Deep Health Check:**
   ```bash
   curl -f http://127.0.0.1:8000/api/v1/health/deep
   ```

### 4.3. Redis Password Rotation
1. **Set New Password Live on Redis Instance:**
   ```bash
   redis-cli -a "<OLD_PASSWORD>" CONFIG SET requirepass "<NEW_PASSWORD>"
   ```
2. **Update `.env.production`:**
   ```env
   REDIS_PASSWORD=<NEW_PASSWORD>
   REDIS_URL=redis://:<NEW_PASSWORD>@redis:6379/0
   ```
3. **Restart Application Services:**
   ```bash
   docker compose -f docker-compose.prod.yml restart backend worker
   ```

---

## 5. Edge Rate-Limiting & DDoS Mitigation

### 5.1. Rate Limiting Rules in Caddy Edge Proxy
Rate limits are configured in `docker/proxy/Caddyfile`:
- Global API limit: `100 requests / minute` per client IP.
- Upload endpoint (`/api/v1/uploads/`): `10 requests / minute` per client IP.
- Login endpoint (`/api/v1/auth/login`): `5 requests / minute` per client IP.

### 5.2. Emergency Rate Limit Adjustment
If a legitimate high-volume burst requires temporary ceiling relaxation:
1. Edit `docker/proxy/Caddyfile` and increase limits.
2. Reload Caddy configuration with zero downtime:
   ```bash
   docker exec classfund_proxy caddy reload --config /etc/caddy/Caddyfile
   ```

---

## 6. Financial Ledger Security & Intrusion Protocol
In the event of suspected unauthorized database access:
1. **Execute Emergency Read-Only Lock:**
   ```bash
   python scripts/failover_manager.py --status
   # Immediately enforce super_read_only across all nodes:
   mysql -h 127.0.0.1 -P 3306 -u root -p000000 -e "SET GLOBAL super_read_only = ON;"
   ```
2. **Run Authoritative Ledger Integrity Check:**
   ```bash
   python scripts/failover_manager.py --reconcile
   ```
3. **Inspect Audit Log Table:**
   ```sql
   SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100;
   ```
4. **Isolate Backend Traffic** via edge proxy maintenance mode until forensic review is signed off.

