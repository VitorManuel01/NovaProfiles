@echo off
setlocal
cd /d "%~dp0"

echo NovaProfiles - build portatil Windows x64
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "packaging\build.ps1" %*
set "RESULT=%ERRORLEVEL%"

if not "%RESULT%"=="0" (
  echo.
  echo O build falhou com o codigo %RESULT%.
) else (
  echo.
  echo Build concluido em dist\NovaProfiles
  echo Quando o arquivo nao for ignorado, pacote, checksum e SBOM ficam em artifacts\
)

if /I not "%NOVAPROFILES_NO_PAUSE%"=="1" pause
exit /b %RESULT%
