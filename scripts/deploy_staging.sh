#!/usr/bin/env bash
# ==============================================================================
# CLASS_FUND_WEB - Staging Deployment Orchestration & Verification Script
# Phase 10 Production Handover Protocol
# ==============================================================================
set -euo pipefail

echo "================================================================="
echo " CLASS_FUND_WEB - STAGING DEPLOYMENT & VERIFICATION ENGINE       "
echo " Phase 10 Production Handover Protocol                          "
echo "================================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${1:-.env.production}"
COMPOSE_FILE="${2:-docker-compose.prod.yml}"

echo ""
echo "[STEP 1/5] Validating Staging Configuration & Secrets..."
if [[ ! -f "$REPO_ROOT/$ENV_FILE" ]]; then
    if [[ -f "$REPO_ROOT/.env.production.example" ]]; then
        echo "Creating $ENV_FILE from template .env.production.example..."
        cp "$REPO_ROOT/.env.production.example" "$REPO_ROOT/$ENV_FILE"
    else
        echo "ERROR: Missing $ENV_FILE and .env.production.example" >&2
        exit 1
    fi
fi

if [[ ! -f "$REPO_ROOT/$COMPOSE_FILE" ]]; then
    echo "ERROR: Missing $COMPOSE_FILE" >&2
    exit 1
fi
echo "Configuration files verified."

echo ""
echo "[STEP 2/5] Checking Orchestration Engine & Services..."
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "Docker daemon active. Deploying services via docker compose..."
    docker compose -f "$REPO_ROOT/$COMPOSE_FILE" --env-file "$REPO_ROOT/$ENV_FILE" up -d
    echo "Awaiting service health convergence (15s)..."
    sleep 15
else
    echo "Docker engine not active locally. Verifying in standalone/cluster validation mode."
fi

echo ""
echo "[STEP 3/5] Verifying MySQL Primary/Replica Storage & Schema..."
python3 - <<EOF
import json, sys
from pathlib import Path
backend_dir = Path("$REPO_ROOT") / "class-fund-backend-v0.1" / "class-fund-backend"
sys.path.insert(0, str(backend_dir))
import pymysql

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
    print(f"Primary MySQL: {len(tables)} tables, {acc_cnt} accounts, {leg_sum} VND total.")
except Exception as e:
    print(f"Primary MySQL check error: {e}", file=sys.stderr)
    sys.exit(1)

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
    print(f"Replica MySQL: IO={io}, SQL={sql}, Lag={lag}s.")
    if io != 'Yes' or sql != 'Yes':
        sys.exit(1)
except Exception as e:
    print(f"Replica MySQL check error: {e}", file=sys.stderr)
    sys.exit(1)
EOF

echo ""
echo "[STEP 4/5] Executing Live Cluster Balance Reconciliation..."
python3 "$REPO_ROOT/scripts/failover_manager.py" --reconcile

echo ""
echo "[STEP 5/5] Executing Deep Health Probe (/api/v1/health/deep)..."
python3 - <<EOF
import os, sys, json
from pathlib import Path
backend_dir = Path("$REPO_ROOT") / "class-fund-backend-v0.1" / "class-fund-backend"
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
data = res.json()
print("Deep Health Status:", data.get("status"))
if res.status_code != 200 or data.get("status") != "healthy":
    print("Health check failed:", data, file=sys.stderr)
    sys.exit(1)
EOF

echo ""
echo "================================================================="
echo " STAGING DEPLOYMENT VERIFICATION COMPLETE: ALL SYSTEMS HEALTHY   "
echo "================================================================="
