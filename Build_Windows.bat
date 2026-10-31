@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if not exist ".venv\Scripts\python.exe" (
 echo Run Install.bat first.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto fail
".venv\Scripts\python.exe" app.py --self-test-ui
if errorlevel 1 goto fail
".venv\Scripts\python.exe" build_windows.py
if errorlevel 1 goto fail
echo Build ready in dist\SongEngine. Keep the whole folder together.
pause
exit /b 0
:fail
echo Build failed. Check the messages above.
pause
exit /b 1
