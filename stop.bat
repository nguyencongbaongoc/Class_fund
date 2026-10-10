@echo off
chcp 65001 > nul
call "%~dp0scripts\windows\02_stop_all.bat" %*
exit /b %errorlevel%

