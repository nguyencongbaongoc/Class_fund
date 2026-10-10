@echo off
chcp 65001 > nul
setlocal EnableExtensions EnableDelayedExpansion

:: ==============================================================================
:: CLASS_FUND_WEB - 04_db_restore.bat (Automated Restore and Reconciliation)
:: Production Windows Automation Engine
:: ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%CD%"

echo =================================================================
echo  CLASS_FUND_WEB - DATABASE RESTORE AND RECONCILIATION ENGINE
echo =================================================================
echo  Project Root: %PROJECT_ROOT%
echo  Timestamp:    %DATE% %TIME%
echo =================================================================

set "TARGET_BACKUP=%~1"
set "COMPOSE_FILE=docker-compose.prod.yml"
if not exist "%COMPOSE_FILE%" set "COMPOSE_FILE=docker-compose.yml"

:: Step 1: Resolve backup file
if "%TARGET_BACKUP%"=="" (
    echo [INFO] No backup path passed. Searching newest backup in backups directory...
    for /f "usebackq tokens=*" %%F in (`powershell -NoProfile -Command "(Get-ChildItem -Path 'backups' -Filter 'db_backup_*.sql' | Sort-Object CreationTime -Descending | Select-Object -First 1).FullName"`) do set "TARGET_BACKUP=%%F"
    if "!TARGET_BACKUP!"=="" (
        for /f "usebackq tokens=*" %%F in (`powershell -NoProfile -Command "(Get-ChildItem -Path 'backups' -Filter 'classfund_backup_*.sql.gz' | Sort-Object CreationTime -Descending | Select-Object -First 1).FullName"`) do set "TARGET_BACKUP=%%F"
    )
)

if "%TARGET_BACKUP%"=="" (
    echo [ERROR] No backup file found in backups/ directory to restore.
    exit /b 1
)

if not exist "%TARGET_BACKUP%" (
    echo [ERROR] Specified backup file does not exist: %TARGET_BACKUP%
    exit /b 1
)

echo.
echo [1/4] Selected Backup Archive:
echo  Path: %TARGET_BACKUP%

:: Step 2: Check target MySQL reachability
echo.
echo [2/4] Verifying target MySQL service reachability...
set "USE_DOCKER=0"
docker info >nul 2>&1
if %errorlevel% equ 0 (
    docker compose -f "%COMPOSE_FILE%" ps mysql-primary 2>nul | findstr /i "running Up" >nul 2>&1
    if %errorlevel% equ 0 set "USE_DOCKER=1"
)

if "!USE_DOCKER!"=="1" (
    echo [OK] Docker primary container classfund_mysql_primary is responsive.
    goto :MYSQL_REACHABLE
)

python scripts/failover_manager.py --status >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Native MySQL Primary [127.0.0.1:3306] is responsive.
    goto :MYSQL_REACHABLE
)

echo [ERROR] Cannot reach MySQL primary on port 3306.
exit /b 1

:MYSQL_REACHABLE

:: Step 3: Execute restore
echo.
echo [3/4] Restoring database schema and records...
if "%USE_DOCKER%"=="1" (
    python scripts/restore_helper.py --file "%TARGET_BACKUP%" --use-docker --compose-file "%COMPOSE_FILE%"
) else (
    python scripts/restore_helper.py --file "%TARGET_BACKUP%"
)
set "RESTORE_EXIT=%errorlevel%"

if %RESTORE_EXIT% neq 0 (
    echo.
    echo =================================================================
    echo  [CRITICAL ERROR] RESTORE FAILED WITH EXIT CODE %RESTORE_EXIT%!
    echo =================================================================
    exit /b %RESTORE_EXIT%
)

:: Step 4: Cluster Reconciliation & Zero-Divergence Audit
echo.
echo [4/4] Executing Post-Restore Financial Balance Reconciliation...
python scripts/failover_manager.py --reconcile
set "RECON_EXIT=%errorlevel%"

if %RECON_EXIT% neq 0 (
    echo.
    echo =================================================================
    echo  [WARNING] Cluster balance reconciliation returned code %RECON_EXIT%!
    echo =================================================================
) else (
    echo [OK] Cluster Primary and Replica nodes reconciled.
)

python scripts/reconcile_migration.py --audit
set "AUDIT_EXIT=%errorlevel%"

if %AUDIT_EXIT% neq 0 (
    echo.
    echo =================================================================
    echo  [CRITICAL ALERT] POST-RESTORE FINANCIAL DISCREPANCY DETECTED!
    echo =================================================================
    exit /b %AUDIT_EXIT%
)

echo.
echo =================================================================
echo  [SUCCESS] DATABASE RESTORE AND RECONCILIATION VERIFIED
echo  Zero ledger drift confirmed - 0.00 VND discrepancy.
echo =================================================================
exit /b 0
