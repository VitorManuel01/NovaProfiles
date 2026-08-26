@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Run INSTALAR.cmd first.
  pause
  exit /b 1
)

echo Installing build tools...
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :fail

echo Building portable Windows application...
".venv\Scripts\pyinstaller.exe" ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "NovaProfiles" ^
  --icon "assets\NovaProfiles.ico" ^
  --add-data "qml;qml" ^
  --add-data "assets;assets" ^
  main.py

if errorlevel 1 goto :fail

echo.
echo Build complete:
echo   dist\NovaProfiles\NovaProfiles.exe
echo.
pause
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
