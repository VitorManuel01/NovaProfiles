@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Rode INSTALAR.cmd primeiro.
  pause
  exit /b 1
)
set "QML_IMPORT_TRACE=1"
set "QT_LOGGING_RULES=qt.qml.*=true"
".venv\Scripts\python.exe" main.py
set "ERR=%ERRORLEVEL%"
echo.
echo Exit code: %ERR%
echo Startup log: %TEMP%\NovaProfiles-startup-error.log
if exist "%TEMP%\NovaProfiles-startup-error.log" (
  echo.
  type "%TEMP%\NovaProfiles-startup-error.log"
)
pause
