@echo off
REM LTT Studios CamCLI - administrator BAT package. ASCII only, no BOM.
setlocal
cd /d "%~dp0"

if not exist "%~dp0LTTStudios-CamCLI-Console.exe" (
  echo Missing LTTStudios-CamCLI-Console.exe next to this BAT file.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0cam_cli_admin.ps1" -Exe "%~dp0LTTStudios-CamCLI-Console.exe"
exit /b %ERRORLEVEL%
