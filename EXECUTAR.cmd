@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Execute INSTALAR.cmd primeiro.
  if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
  exit /b 1
)

".venv\Scripts\python.exe" main.py %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo.
  echo NovaProfiles terminou com o codigo %RESULT%.
  echo Diagnostico: %TEMP%\NovaProfiles-startup-error.log
  if exist "%TEMP%\NovaProfiles-startup-error.log" (
    echo.
    type "%TEMP%\NovaProfiles-startup-error.log"
  )
  if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
)
exit /b %RESULT%
