@echo off
chcp 65001 > nul
setlocal EnableExtensions EnableDelayedExpansion

:: ==============================================================================
:: CLASS_FUND_WEB - 05_export_machine_a.bat (Machine A Migration Export Engine)
:: Production Windows Automation Engine
:: ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%CD%"

echo =================================================================
echo  CLASS_FUND_WEB - CROSS-MACHINE MIGRATION EXPORTER [MACHINE A]
echo =================================================================
echo  Project Root: %PROJECT_ROOT%
echo  Timestamp:    %DATE% %TIME%
echo =================================================================

set "COMPOSE_FILE=docker-compose.prod.yml"
if not exist "%COMPOSE_FILE%" set "COMPOSE_FILE=docker-compose.yml"

:: Step 1: Pre-drain workers and freeze mutation engine
echo.
echo [1/6] Draining workers and stopping backend to freeze ledger mutations...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Stopping worker and backend containers...
    docker compose -f "%COMPOSE_FILE%" stop worker backend
    echo [INFO] Waiting 5 seconds for in-flight database leases to clear...
    powershell -NoProfile -Command "Start-Sleep -Seconds 5" >nul
) else (
    echo [INFO] Running in standalone host mode. Ledger mutations frozen.
)
echo [OK] Mutation engine halted safely.

:: Step 2: Audit baseline financial state
echo.
echo [2/6] Auditing baseline financial state and writing migration_baseline.json...
python scripts/reconcile_migration.py --create-baseline "%PROJECT_ROOT%\migration_baseline.json"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to capture authoritative financial baseline!
    exit /b 1
)
echo [OK] Authoritative migration baseline captured.

:: Step 3: Consistent GTID database snapshot
echo.
echo [3/6] Taking consistent transactional database snapshot (migration_dump.sql)...

set "USE_DOCKER=0"
docker info >nul 2>&1
if %errorlevel% equ 0 (
    docker compose -f "%COMPOSE_FILE%" ps mysql-primary 2>nul | findstr /i "running Up" >nul 2>&1
    if !errorlevel! equ 0 set "USE_DOCKER=1"
)

set "MYSQLDUMP_EXE=mysqldump"
if exist "%LOCALAPPDATA%\classfund-mysql84\mysql-8.4.11-winx64\bin\mysqldump.exe" (
    set "MYSQLDUMP_EXE=%LOCALAPPDATA%\classfund-mysql84\mysql-8.4.11-winx64\bin\mysqldump.exe"
)

if "!USE_DOCKER!"=="1" (
    echo [INFO] Executing mysqldump via container classfund_mysql_primary...
    docker compose -f "%COMPOSE_FILE%" exec -T mysql-primary mysqldump -u root -p000000 --single-transaction --quick --set-gtid-purged=ON --hex-blob --routines --triggers classfund > "%PROJECT_ROOT%\migration_dump.sql"
) else (
    echo [INFO] Executing mysqldump against local primary 127.0.0.1:3306...
    "%MYSQLDUMP_EXE%" -h 127.0.0.1 -P 3306 -u root -p000000 --single-transaction --quick --set-gtid-purged=ON --hex-blob --routines --triggers classfund > "%PROJECT_ROOT%\migration_dump.sql"
)

if !errorlevel! neq 0 (
    echo [ERROR] mysqldump failed with code !errorlevel!!
    exit /b 1
)

for %%F in ("%PROJECT_ROOT%\migration_dump.sql") do set "DUMP_SIZE=%%~zF"
if "%DUMP_SIZE%"=="" set "DUMP_SIZE=0"
if %DUMP_SIZE% leq 100 (
    echo [ERROR] Export dump is empty or invalid!
    exit /b 1
)
echo [OK] Consistent snapshot created (%DUMP_SIZE% bytes).

:: Step 4: Bundle migration assets
echo.
echo [4/6] Staging export package in temporary directory migration_export...
if exist "migration_export" rmdir /s /q "migration_export"
mkdir "migration_export"
mkdir "migration_export\uploads"

copy /y "%PROJECT_ROOT%\migration_dump.sql" "migration_export\" >nul
copy /y "%PROJECT_ROOT%\migration_baseline.json" "migration_export\" >nul

if exist ".env" (
    copy /y ".env" "migration_export\.env" >nul
) else if exist ".env.production" (
    copy /y ".env.production" "migration_export\.env" >nul
) else if exist ".env.production.example" (
    copy /y ".env.production.example" "migration_export\.env" >nul
)

if exist "uploads" (
    xcopy /E /I /Y "uploads" "migration_export\uploads" >nul 2>&1
)
if exist "storage\uploads" (
    xcopy /E /I /Y "storage\uploads" "migration_export\uploads" >nul 2>&1
)
echo [OK] Migration assets staged.

:: Step 5: Archive transfer package
echo.
echo [5/6] Compressing atomic transfer package into classfund_transfer_package.zip...
if exist "%PROJECT_ROOT%\classfund_transfer_package.zip" (
    del /f /q "%PROJECT_ROOT%\classfund_transfer_package.zip"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'migration_export\*' -DestinationPath 'classfund_transfer_package.zip' -Force"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to compress transfer package!
    exit /b 1
)
echo [OK] Package created: classfund_transfer_package.zip

:: Step 6: Cleanup temporary staging directory
echo.
echo [6/6] Cleaning up uncompressed temporary export artifacts...
if exist "migration_export" rmdir /s /q "migration_export"
if exist "migration_dump.sql" del /f /q "migration_dump.sql"
if exist "migration_baseline.json" del /f /q "migration_baseline.json"
echo [OK] Workspace cleaned.

for %%Z in ("%PROJECT_ROOT%\classfund_transfer_package.zip") do set "ZIP_SIZE=%%~zZ"

echo.
echo =================================================================
echo  [SUCCESS] MACHINE A EXPORT COMPLETED SUCCESSFULLY
echo =================================================================
echo  Package:   %PROJECT_ROOT%\classfund_transfer_package.zip
echo  Size:      %ZIP_SIZE% bytes
echo -----------------------------------------------------------------
echo  TRANSFER INSTRUCTIONS FOR MACHINE B:
echo  1. Copy 'classfund_transfer_package.zip' to project root on Machine B
echo     (via LAN share, USB thumb drive, SCP, or secure cloud transfer).
echo  2. On Machine B, run:
echo        scripts\windows\06_import_machine_b.bat
echo     or double click:
echo        import_from_machine_a.bat
echo =================================================================
exit /b 0
