@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Execute INSTALAR.cmd primeiro.
  if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
  exit /b 1
)

set "QML_IMPORT_TRACE=1"
set "QT_LOGGING_RULES=qt.qml.*=true"
".venv\Scripts\python.exe" main.py %*
set "RESULT=%ERRORLEVEL%"

echo.
echo Codigo de saida: %RESULT%
echo Log de inicializacao: %TEMP%\NovaProfiles-startup-error.log
if exist "%TEMP%\NovaProfiles-startup-error.log" (
  echo.
  type "%TEMP%\NovaProfiles-startup-error.log"
)

if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
exit /b %RESULT%
