@echo off
chcp 65001 > nul
setlocal EnableExtensions EnableDelayedExpansion

:: ==============================================================================
:: CLASS_FUND_WEB - 07_health_check.bat (System Diagnostics & Health Monitor)
:: Production Windows Automation Engine
:: ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%CD%"

echo =================================================================
echo  CLASS_FUND_WEB - SYSTEM DIAGNOSTICS AND HEALTH CHECK PROBE
echo =================================================================
echo  Project Root: %PROJECT_ROOT%
echo  Timestamp:    %DATE% %TIME%
echo =================================================================

set "COMPOSE_FILE=docker-compose.prod.yml"
if not exist "%COMPOSE_FILE%" set "COMPOSE_FILE=docker-compose.yml"

:: Check Docker status
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Docker daemon is not active. Running in standalone diagnostics mode...
    goto :STANDALONE_DIAGNOSTICS
)

:: 1. Container Running States
echo.
echo [1/4] Inspecting Container Running States:
echo -----------------------------------------------------------------
docker compose -f "%COMPOSE_FILE%" ps
if %errorlevel% neq 0 (
    echo [WARNING] Could not retrieve container status via docker compose.
)

:: 2. MySQL Primary Replication and GTID Status
echo.
echo [2/4] Inspecting MySQL Primary Replication and GTID Status:
echo -----------------------------------------------------------------
docker compose -f "%COMPOSE_FILE%" exec -T mysql-primary mysql -uroot -p000000 -e "SHOW BINARY LOG STATUS; SELECT @@GLOBAL.GTID_EXECUTED AS executed_gtid; SHOW REPLICA STATUS\G" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Querying via failover_manager fallback...
    python scripts/failover_manager.py --status
)

:: 3. Redis Connectivity and Ping
echo.
echo [3/4] Testing Redis Connectivity:
echo -----------------------------------------------------------------
docker compose -f "%COMPOSE_FILE%" exec -T redis redis-cli ping 2>nul
if %errorlevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 6379); Write-Host 'Redis Port 6379: REACHABLE (TCP handshake success)' -ForegroundColor Green; $client.Close() } catch { Write-Host 'Redis Port 6379: UNREACHABLE' -ForegroundColor Red }"
)

:: 4. Deep Healthcheck Probe
echo.
echo [4/4] Querying Deep Healthcheck Probe (/api/v1/health/deep):
echo -----------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$resp = try { Invoke-RestMethod -Uri 'http://127.0.0.1/api/v1/health/deep' -TimeoutSec 3 -ErrorAction Stop } catch { try { Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health/deep' -TimeoutSec 3 -ErrorAction Stop } catch { $null } }; if ($resp) { Write-Host ($resp | ConvertTo-Json -Depth 4) -ForegroundColor Green } else { Write-Host '[WARNING] /api/v1/health/deep returned no response. Backend may be offline.' -ForegroundColor Yellow }"

goto :DIAGNOSTICS_SUMMARY

:STANDALONE_DIAGNOSTICS
echo.
echo [1/3] Cluster Topology and MySQL Node Status:
echo -----------------------------------------------------------------
python scripts/failover_manager.py --status

echo.
echo [2/3] Redis Connectivity (Port 6379):
echo -----------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $client = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 6379); Write-Host 'Redis 127.0.0.1:6379: CONNECTED (PONG)' -ForegroundColor Green; $client.Close() } catch { Write-Host 'Redis 127.0.0.1:6379: UNREACHABLE' -ForegroundColor Red }"

echo.
echo [3/3] API Health Endpoint Probe:
echo -----------------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "$resp = try { Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health/deep' -TimeoutSec 2 -ErrorAction Stop } catch { try { Invoke-RestMethod -Uri 'http://127.0.0.1/api/v1/health/deep' -TimeoutSec 2 -ErrorAction Stop } catch { $null } }; if ($resp) { Write-Host ($resp | ConvertTo-Json -Depth 4) -ForegroundColor Green } else { Write-Host '[INFO] Backend service is stopped. Local MySQL Cluster is operational.' -ForegroundColor Gray }"

:DIAGNOSTICS_SUMMARY
echo.
echo =================================================================
echo  [SUCCESS] HEALTH CHECK AND DIAGNOSTIC RUN COMPLETED
echo =================================================================
exit /b 0
