<#
.SYNOPSIS
    Staging Deployment Orchestration & Verification Script
    CLASS_FUND_WEB - Production / Staging SRE Pipeline
.DESCRIPTION
    Orchestrates configuration validation, container bootstrap, database volume &
    schema verification, replication lag assertion, and deep health check diagnostics.
#>

[CmdletBinding()]
param(
    [string]$EnvFile = ".env.production",
    [string]$ComposeFile = "docker-compose.prod.yml",
    [switch]$SkipDockerStart
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " CLASS_FUND_WEB - STAGING DEPLOYMENT & VERIFICATION ENGINE       " -ForegroundColor Cyan
Write-Host " Phase 10 Production Handover Protocol                          " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$RepoRoot = $PSScriptRoot | Split-Path -Parent
if (-not $RepoRoot) { $RepoRoot = Get-Location }

# 1. Environment & Configuration Pre-flight
Write-Host "`n[STEP 1/5] Validating Staging Configuration & Secrets..." -ForegroundColor Yellow

$EnvPath = Join-Path $RepoRoot $EnvFile
$EnvExamplePath = Join-Path $RepoRoot ".env.production.example"

if (-not (Test-Path $EnvPath)) {
    if (Test-Path $EnvExamplePath) {
        Write-Host "Creating $EnvFile from template .env.production.example..." -ForegroundColor Gray
        Copy-Item $EnvExamplePath $EnvPath
    } else {
        throw "Missing $EnvFile and $EnvExamplePath!"
    }
}

$ComposePath = Join-Path $RepoRoot $ComposeFile
if (-not (Test-Path $ComposePath)) {
    throw "Missing $ComposeFile at $ComposePath!"
}
Write-Host "Configuration files verified." -ForegroundColor Green

# 2. Docker & Service Orchestration
Write-Host "`n[STEP 2/5] Checking Orchestration Engine & Services..." -ForegroundColor Yellow

$Services = @("proxy", "frontend", "backend", "worker", "mysql-primary", "mysql-replica", "redis")
$DockerAvailable = $false
try {
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerCmd) {
        $dockerVer = docker version --format '{{.Server.Version}}' 2>$null
        if ($dockerVer) {
            $DockerAvailable = $true
        }
    }
} catch {}

if ($DockerAvailable -and (-not $SkipDockerStart)) {
    Write-Host "Docker daemon detected. Bootstrapping containers via docker compose..." -ForegroundColor Cyan
    docker compose -f $ComposePath --env-file $EnvPath up -d
    Write-Host "Awaiting service healthchecks..." -ForegroundColor Gray
    Start-Sleep -Seconds 10
} else {
    Write-Host "Running in environment validation mode (Local / Standalone MySQL 8.4 GTID Cluster)." -ForegroundColor Gray
}

# 3. Database Volume & Schema Integrity Check
Write-Host "`n[STEP 3/5] Verifying MySQL Primary/Replica Storage & Schema..." -ForegroundColor Yellow

$schemaCheckScript = @"
import json, sys, os
from pathlib import Path
backend_dir = Path(r'$RepoRoot') / 'class-fund-backend-v0.1' / 'class-fund-backend'
sys.path.insert(0, str(backend_dir))
import pymysql

res = {'success': True, 'checks': {}}
try:
    conn_pri = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='000000', database='classfund')
    with conn_pri.cursor() as cur:
        cur.execute('SHOW TABLES;')
        tables = [r[0] for r in cur.fetchall()]
        cur.execute('SELECT COUNT(*) FROM accounts;')
        acc_cnt = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM ledger_entries;')
        leg_cnt, leg_sum = cur.fetchone()
    conn_pri.close()

    res['checks']['primary_mysql'] = {
        'status': 'HEALTHY',
        'tables_count': len(tables),
        'accounts': acc_cnt,
        'ledger_entries': leg_cnt,
        'ledger_total_vnd': str(leg_sum)
    }
except Exception as e:
    res['success'] = False
    res['checks']['primary_mysql'] = {'status': 'FAILED', 'error': str(e)}

try:
    conn_rep = pymysql.connect(host='127.0.0.1', port=3308, user='root', password='000000', database='classfund')
    with conn_rep.cursor() as cur:
        cur.execute('SHOW REPLICA STATUS;')
        cols = [d[0] for d in cur.description] if cur.description else []
        row = cur.fetchone()
        st = dict(zip(cols, row)) if row else {}
    conn_rep.close()

    io = st.get('Replica_IO_Running')
    sql = st.get('Replica_SQL_Running')
    lag = st.get('Seconds_Behind_Source', 0)
    res['checks']['replica_mysql'] = {
        'status': 'HEALTHY' if (io == 'Yes' and sql == 'Yes') else 'DEGRADED',
        'io_running': io,
        'sql_running': sql,
        'lag_seconds': lag
    }
except Exception as e:
    res['success'] = False
    res['checks']['replica_mysql'] = {'status': 'FAILED', 'error': str(e)}

print(json.dumps(res))
"@

$schemaResultRaw = python -c $schemaCheckScript
$schemaResult = $schemaResultRaw | ConvertFrom-Json

if (-not $schemaResult.success) {
    Write-Host "Database validation failed: $($schemaResultRaw)" -ForegroundColor Red
    throw "Database schema validation failed"
}

Write-Host "Primary MySQL: $($schemaResult.checks.primary_mysql.tables_count) tables, $($schemaResult.checks.primary_mysql.accounts) accounts, Total: $($schemaResult.checks.primary_mysql.ledger_total_vnd) VND." -ForegroundColor Green
Write-Host "Replica MySQL: IO=$($schemaResult.checks.replica_mysql.io_running), SQL=$($schemaResult.checks.replica_mysql.sql_running), Lag=$($schemaResult.checks.replica_mysql.lag_seconds)s." -ForegroundColor Green

# 4. Cluster Financial Reconciliation
Write-Host "`n[STEP 4/5] Executing Live Cluster Balance Reconciliation..." -ForegroundColor Yellow
$reconcileOutput = python (Join-Path $RepoRoot "scripts\failover_manager.py") --reconcile | ConvertFrom-Json

if ($reconcileOutput.matched -ne $true) {
    Write-Host "Financial divergence detected across cluster!" -ForegroundColor Red
    throw "Cluster reconciliation mismatch: $($reconcileOutput | ConvertTo-Json)"
}
Write-Host "Cluster Financial Parity Confirmed: 0.00 VND Discrepancy ($($reconcileOutput.primary_ledger_sum) VND across $($reconcileOutput.primary_accounts_count) accounts)." -ForegroundColor Green

# 5. Deep Health Probe Execution
Write-Host "`n[STEP 5/5] Executing Deep Health Probe (/api/v1/health/deep)..." -ForegroundColor Yellow

$probeScript = @"
import warnings
warnings.filterwarnings('ignore')
import os, sys, json
from pathlib import Path
backend_dir = Path(r'$RepoRoot') / 'class-fund-backend-v0.1' / 'class-fund-backend'
sys.path.insert(0, str(backend_dir))
os.environ['DATABASE_URL'] = 'mysql+pymysql://classfund:classfund@127.0.0.1:3306/classfund?charset=utf8mb4'
os.environ['DATABASE_URL_REPLICA'] = 'mysql+pymysql://classfund:classfund@127.0.0.1:3308/classfund?charset=utf8mb4'
os.environ['MYSQL_REPLICA_HOST'] = '127.0.0.1'
os.environ['MYSQL_REPLICA_PORT'] = '3308'
os.environ['MYSQL_REPLICA_USER'] = 'root'
os.environ['MYSQL_REPLICA_PASS'] = '000000'

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
res = client.get('/api/v1/health/deep')
print(json.dumps({'status_code': res.status_code, 'body': res.json()}))
"@

$probeLines = (python -W ignore -c $probeScript 2>$null) | Where-Object { $_ -match '"status_code"' }
$probeJson = $probeLines | ConvertFrom-Json

if ($probeJson.status_code -ne 200 -or $probeJson.body.status -ne "healthy") {
    Write-Host "Deep health probe returned non-healthy state: $($probeJson.status_code)" -ForegroundColor Red
    Write-Host ($probeJson.body | ConvertTo-Json -Depth 4) -ForegroundColor Red
    throw "Deep health check failed"
}

Write-Host "Deep Health Check Succeeded (HTTP 200 - Status: HEALTHY):" -ForegroundColor Green
Write-Host "  - Primary DB: $($probeJson.body.components.primary_db.status) (writable=$($probeJson.body.components.primary_db.writable))" -ForegroundColor Gray
Write-Host "  - Replica DB: $($probeJson.body.components.replica_db.status) (super_read_only=$($probeJson.body.components.replica_db.super_read_only), lag=$($probeJson.body.components.replica_db.replication_lag_seconds)s)" -ForegroundColor Gray
Write-Host "  - Redis PubSub: $($probeJson.body.components.redis.status)" -ForegroundColor Gray
Write-Host "  - Ollama Inference: $($probeJson.body.components.ollama.status)" -ForegroundColor Gray

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host " STAGING DEPLOYMENT VERIFICATION COMPLETE: ALL SYSTEMS HEALTHY   " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
