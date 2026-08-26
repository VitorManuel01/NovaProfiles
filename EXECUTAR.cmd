@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Rode INSTALAR.cmd primeiro.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" main.py
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo.
  echo Nova Profiles terminou com erro %ERR%.
  echo O diagnostico tambem foi salvo em:
  echo   %TEMP%\NovaProfiles-startup-error.log
  echo.
  if exist "%TEMP%\NovaProfiles-startup-error.log" type "%TEMP%\NovaProfiles-startup-error.log"
  echo.
  pause
)
exit /b %ERR%
