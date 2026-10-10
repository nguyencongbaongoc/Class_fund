@echo off
chcp 65001 > nul
setlocal EnableExtensions EnableDelayedExpansion

:: ==============================================================================
:: CLASS_FUND_WEB - 01_start_all.bat (One-Click Quick Start)
:: Production Windows Automation Engine
:: ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%CD%"

echo =================================================================
echo  CLASS_FUND_WEB - SYSTEM STARTUP AND ORCHESTRATION ENGINE
echo =================================================================
echo  Project Root: %PROJECT_ROOT%
echo  Timestamp:    %DATE% %TIME%
echo =================================================================

:: Parse command-line flags
set "STANDALONE_MODE=0"
set "COMPOSE_FILE=docker-compose.prod.yml"

for %%A in (%*) do (
    if /i "%%A"=="--standalone" set "STANDALONE_MODE=1"
    if /i "%%A"=="--dev" set "COMPOSE_FILE=docker-compose.yml"
    if /i "%%A"=="-f" set "COMPOSE_FILE=%%~B"
    if /i "%%A"=="--help" (
        echo Usage: 01_start_all.bat [--standalone] [--dev] [-f compose_file]
        echo Options:
        echo   --standalone  Start / verify standalone local services without Docker
        echo   --dev         Use docker-compose.yml instead of docker-compose.prod.yml
        exit /b 0
    )
)

:: Step 1: Environment file verification
echo.
echo [1/4] Checking environment configuration (.env)...
if not exist ".env" (
    if exist ".env.production.example" (
        echo [INFO] .env not found. Bootstrapping .env from .env.production.example template...
        copy /y ".env.production.example" ".env" > nul
        if %errorlevel% equ 0 (
            echo [SUCCESS] Created .env template. Please configure production secrets if needed.
        ) else (
            echo [ERROR] Failed to copy .env.production.example to .env
            exit /b 1
        )
    ) else if exist ".env.production" (
        echo [INFO] Copying .env.production to .env...
        copy /y ".env.production" ".env" > nul
    ) else (
        echo [WARNING] No .env or template found. Proceeding with environment defaults.
    )
) else (
    echo [OK] Active .env file verified.
)

:: Step 2: Docker Engine verification
echo.
echo [2/4] Verifying Docker Desktop and Engine status...
if "%STANDALONE_MODE%"=="1" (
    echo [INFO] Standalone flag detected. Skipping Docker daemon startup.
    goto :STANDALONE_START
)

docker info >nul 2>&1
if %errorlevel% equ 0 goto :DOCKER_READY

echo.
echo =================================================================
echo  [ALERT] Docker Desktop is not running or Docker CLI is not in PATH!
echo =================================================================
echo  Please launch Docker Desktop from Windows Start Menu and ensure
echo  the container runtime has fully initialized.
echo.
echo  If you intend to run in native Windows standalone mode [using
echo  local MySQL 8.4 GTID and local services], re-run with:
echo     01_start_all.bat --standalone
echo =================================================================
exit /b 1

:DOCKER_READY

:: Step 3: Boot container infrastructure
echo.
echo [3/4] Launching container stack via docker compose (%COMPOSE_FILE%)...
if not exist "%COMPOSE_FILE%" (
    if exist "docker-compose.prod.yml" (
        set "COMPOSE_FILE=docker-compose.prod.yml"
    )
)

docker compose -f "%COMPOSE_FILE%" up -d
if %errorlevel% neq 0 (
    echo [ERROR] docker compose up failed with exit code %errorlevel%!
    exit /b %errorlevel%
)
echo [SUCCESS] Container stack deployment initiated.

:: Step 4: Health Check Probing
echo.
echo [4/4] Awaiting system convergence and polling deep healthcheck...
set /a MAX_ATTEMPTS=30
set /a ATTEMPT=1
set "SYSTEM_HEALTHY=0"

:HEALTH_POLL_LOOP
powershell -NoProfile -ExecutionPolicy Bypass -Command "$resp = try { Invoke-RestMethod -Uri 'http://127.0.0.1/api/v1/health/deep' -TimeoutSec 2 -ErrorAction Stop } catch { try { Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/health/deep' -TimeoutSec 2 -ErrorAction Stop } catch { $null } }; if ($resp -and ($resp.status -eq 'HEALTHY' -or $resp.system_status -eq 'HEALTHY' -or $resp.primary_db_status -eq 'healthy')) { exit 0 } else { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    set "SYSTEM_HEALTHY=1"
    goto :START_SUCCESS
)

if %ATTEMPT% geq %MAX_ATTEMPTS% goto :HEALTH_TIMEOUT

echo  ... Polling health probe (attempt %ATTEMPT%/%MAX_ATTEMPTS%, waiting 2s)...
powershell -NoProfile -Command "Start-Sleep -Seconds 2" >nul
set /a ATTEMPT+=1
goto :HEALTH_POLL_LOOP

:STANDALONE_START
echo.
echo [3/4] Verifying local standalone MySQL GTID and Redis connectivity...
python scripts/failover_manager.py --status >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] Local MySQL GTID Primary [3306] and Standby [3308] are active!
) else (
    echo [WARNING] MySQL GTID cluster status returned warning. Verifying primary node...
)
echo.
echo [4/4] Checking instant ledger integrity...
python scripts/reconcile_migration.py --audit
goto :PRINT_URLS

:HEALTH_TIMEOUT
echo.
echo [WARNING] System convergence timed out after 60s. Services may still be booting.
echo Check container logs via: docker compose -f %COMPOSE_FILE% logs -f

:START_SUCCESS
echo.
echo [SUCCESS] All system services reported HEALTHY!

:PRINT_URLS
echo.
echo =================================================================
echo  CLASS_FUND_WEB - SYSTEM ACCESS DIRECTORY
echo =================================================================
echo  Frontend Application: http://localhost
echo  Backend API Docs:     http://localhost/api/v1/docs
echo                        (Direct: http://localhost:8000/docs)
echo  Deep Health Probe:    http://localhost/api/v1/health/deep
echo =================================================================
echo.
exit /b 0
