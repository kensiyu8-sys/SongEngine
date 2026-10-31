@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if not exist ".venv\Scripts\python.exe" (
 echo Run Install.bat first, or use the portable Windows app ZIP.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" app.py
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" pause
exit /b %ERR%
