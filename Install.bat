@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
if defined SONGENGINE_PYTHON (
 "%SONGENGINE_PYTHON%" -c "import sys,struct,tkinter; assert sys.version_info[:3]==(3,11,9) and struct.calcsize('P')==8, 'Use Python 3.11.9 x64 with Tcl/Tk'"
 if errorlevel 1 goto fail
 "%SONGENGINE_PYTHON%" -m venv .venv
) else (
 py -3.11 -c "import sys,struct,tkinter; assert sys.version_info[:3]==(3,11,9) and struct.calcsize('P')==8, 'Use Python 3.11.9 x64 with Tcl/Tk'"
 if errorlevel 1 goto fail
 py -3.11 -m venv .venv
)
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto fail
echo Ready. Double-click Run_Desktop.bat.
pause
exit /b 0
:fail
echo Setup failed. Read README.md. Install standard Python 3.11.9 x64 with Tcl/Tk.
pause
exit /b 1
