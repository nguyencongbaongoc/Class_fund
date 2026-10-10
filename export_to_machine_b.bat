@echo off
chcp 65001 > nul
call "%~dp0scripts\windows\05_export_machine_a.bat" %*
exit /b %errorlevel%

