@echo off
setlocal EnableExtensions
cd /d "%~dp0"

fltmc.exe >nul 2>&1
if errorlevel 1 (
  echo Execute este arquivo como Administrador.
  if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
  exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "packaging\stop_legacy_service.ps1"
set "RESULT=%ERRORLEVEL%"

if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
exit /b %RESULT%
