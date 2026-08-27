@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo Execute INSTALAR.cmd primeiro.
  if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
  exit /b 1
)

start "NovaProfiles" /b ".venv\Scripts\pythonw.exe" main.py --background %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo Nao foi possivel iniciar o NovaProfiles em segundo plano.
  if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
)
exit /b %RESULT%
