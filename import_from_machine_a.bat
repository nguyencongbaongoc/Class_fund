@echo off
chcp 65001 > nul
call "%~dp0scripts\windows\06_import_machine_b.bat" %*
exit /b %errorlevel%

