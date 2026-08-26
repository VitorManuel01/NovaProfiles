@echo off
setlocal
fltmc >nul 2>&1
if errorlevel 1 (
  echo Run this file as Administrator.
  pause
  exit /b 1
)
echo Stopping legacy GameSirAutoProfile service...
sc stop GameSirAutoProfile
echo.
echo This only STOPS the old service. It does not remove it.
pause
