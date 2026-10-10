@echo off
chcp 65001 > nul
call "%~dp0scripts\windows\03_db_backup.bat" %*
exit /b %errorlevel%

