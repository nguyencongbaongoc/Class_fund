@echo off
chcp 65001 > nul
call "%~dp0scripts\windows\01_start_all.bat" %*
exit /b %errorlevel%

