@echo off
setlocal
cd /d "%~dp0"

echo NovaProfiles - instalacao reproduzivel
echo Python 3.11 a 3.14 x64 e Windows sao obrigatorios.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "packaging\install.ps1"
set "RESULT=%ERRORLEVEL%"

if not "%RESULT%"=="0" (
  echo.
  echo A instalacao falhou com o codigo %RESULT%.
) else (
  echo.
  echo Instalacao concluida. Execute EXECUTAR.cmd.
)

if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
exit /b %RESULT%
