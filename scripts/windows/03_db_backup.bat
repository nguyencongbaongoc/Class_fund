@echo off
chcp 65001 > nul
setlocal EnableExtensions EnableDelayedExpansion

:: ==============================================================================
:: CLASS_FUND_WEB - 03_db_backup.bat (Automated Consistent Database Backup)
:: Production Windows Automation Engine
:: ==============================================================================

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_ROOT=%CD%"

echo =================================================================
echo  CLASS_FUND_WEB - AUTOMATED GTID DATABASE BACKUP ENGINE
echo =================================================================
echo  Project Root: %PROJECT_ROOT%
echo  Timestamp:    %DATE% %TIME%
echo =================================================================

:: Ensure backups directory exists
if not exist "backups" mkdir "backups"

:: Generate locale-independent timestamp YYYYMMDD_HHMMSS
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set "TIMESTAMP=%%i"
set "BACKUP_FILE=%PROJECT_ROOT%\backups\db_backup_%TIMESTAMP%.sql"
set "META_FILE=%PROJECT_ROOT%\backups\db_backup_%TIMESTAMP%.meta.json"

set "COMPOSE_FILE=docker-compose.prod.yml"
if not exist "%COMPOSE_FILE%" set "COMPOSE_FILE=docker-compose.yml"

echo.
echo [1/4] Preparing snapshot destination:
echo  Target SQL:  %BACKUP_FILE%
echo  Target Meta: %META_FILE%

:: Check if Docker is running
set "USE_DOCKER=0"
docker info >nul 2>&1
if %errorlevel% equ 0 (
    docker compose -f "%COMPOSE_FILE%" ps mysql-primary 2>nul | findstr /i "running Up" >nul 2>&1
    if %errorlevel% equ 0 set "USE_DOCKER=1"
)

:: Locate mysqldump binary for fallback
set "MYSQLDUMP_EXE=mysqldump"
if exist "%LOCALAPPDATA%\classfund-mysql84\mysql-8.4.11-winx64\bin\mysqldump.exe" (
    set "MYSQLDUMP_EXE=%LOCALAPPDATA%\classfund-mysql84\mysql-8.4.11-winx64\bin\mysqldump.exe"
)

echo.
echo [2/4] Executing consistent transactional snapshot...
if "%USE_DOCKER%"=="1" (
    echo [INFO] Running mysqldump inside container classfund_mysql_primary...
    docker compose -f "%COMPOSE_FILE%" exec -T mysql-primary mysqldump -u root -p000000 --single-transaction --quick --set-gtid-purged=ON --hex-blob --routines --triggers classfund > "%BACKUP_FILE%"
) else (
    echo [INFO] Running mysqldump against primary host 127.0.0.1:3306...
    "%MYSQLDUMP_EXE%" -h 127.0.0.1 -P 3306 -u root -p000000 --single-transaction --quick --set-gtid-purged=ON --hex-blob --routines --triggers classfund > "%BACKUP_FILE%"
)

if %errorlevel% neq 0 (
    echo [ERROR] mysqldump command failed with exit code %errorlevel%!
    if exist "%BACKUP_FILE%" del /f /q "%BACKUP_FILE%"
    exit /b 1
)

:: Check that backup file is non-empty
for %%F in ("%BACKUP_FILE%") do set "BACKUP_SIZE=%%~zF"
if "%BACKUP_SIZE%"=="" set "BACKUP_SIZE=0"
if %BACKUP_SIZE% leq 100 (
    echo [ERROR] Backup file is empty or corrupted! Size: %BACKUP_SIZE% bytes.
    exit /b 1
)
echo [OK] SQL Snapshot created successfully (%BACKUP_SIZE% bytes).

:: Step 3: Compute SHA256 and generate metadata
echo.
echo [3/4] Computing SHA256 hash and recording ledger metadata...
for /f "usebackq tokens=*" %%H in (`python -c "import hashlib; print(hashlib.sha256(open(r'%BACKUP_FILE%', 'rb').read()).hexdigest())"`) do set "SHA256_HASH=%%H"

python -c "import json, sys, pymysql; from decimal import Decimal; conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='000000', database='classfund'); cur = conn.cursor(); cur.execute('SELECT COUNT(*), COALESCE(SUM(opening_balance), 0) FROM accounts;'); acc_cnt, acc_sum = cur.fetchone(); cur.execute('SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM ledger_entries;'); led_cnt, led_sum = cur.fetchone(); cur.execute('SELECT @@GLOBAL.GTID_EXECUTED;'); gtid = cur.fetchone()[0]; conn.close(); meta = {'timestamp': '%TIMESTAMP%', 'backup_file': r'%BACKUP_FILE%', 'sha256': '%SHA256_HASH%', 'file_size_bytes': %BACKUP_SIZE%, 'accounts_count': acc_cnt, 'accounts_opening_balance_sum': str(Decimal(str(acc_sum))), 'ledger_count': led_cnt, 'ledger_sum_vnd': str(Decimal(str(led_sum))), 'gtid_executed': gtid.strip(), 'status': 'VERIFIED_SNAPSHOT'}; open(r'%META_FILE%', 'w', encoding='utf-8').write(json.dumps(meta, indent=2))"

if %errorlevel% neq 0 (
    echo [WARNING] Could not record full JSON metadata, saving fallback SHA256.
    echo %SHA256_HASH% > "%BACKUP_FILE%.sha256"
) else (
    echo [OK] Backup metadata saved: %META_FILE%
)

:: Step 4: Apply 7-day / 7-backup retention policy
echo.
echo [4/4] Enforcing backup retention policy (retaining 7 most recent backups)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files = Get-ChildItem -Path 'backups' -Filter 'db_backup_*.sql' | Sort-Object CreationTime -Descending; if ($files.Count -gt 7) { $files | Select-Object -Skip 7 | ForEach-Object { $sqlPath = $_.FullName; $metaPath = $sqlPath -replace '\.sql$', '.meta.json'; Write-Host ('[PURGE] Removing expired backup: ' + $_.Name); Remove-Item $sqlPath -Force -ErrorAction SilentlyContinue; if (Test-Path $metaPath) { Remove-Item $metaPath -Force -ErrorAction SilentlyContinue } } } else { Write-Host ('[OK] Total backups: ' + $files.Count + ' (within retention limit <= 7)') }"

echo.
echo =================================================================
echo  [SUCCESS] DATABASE BACKUP COMPLETED
echo  Backup File: %BACKUP_FILE%
echo  SHA256 Hash: %SHA256_HASH%
echo =================================================================
exit /b 0
