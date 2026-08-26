@echo off
REM LTT Studios CamCLI launcher.
REM ASCII only, no BOM. Business logic stays in cam_cli.py.
setlocal
cd /d "%~dp0"

if exist "%~dp0LTTStudios-CamCLI.exe" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0cam_cli_launcher.ps1" -Exe "%~dp0LTTStudios-CamCLI.exe"
  exit /b %ERRORLEVEL%
)

REM Source-tree fallback for developers. The installed package uses the branch
REM above and does not require Python.
set PY=
for %%P in (py.exe python.exe) do (
  if not defined PY where %%P >nul 2>nul && set PY=%%P
)
if not defined PY (
  echo Python was not found, and the packaged EXE is not next to this file.
  pause
  exit /b 1
)

%PY% cam_cli_gui.py
if "%ERRORLEVEL%"=="2" (
  echo GUI dependency is missing. Use: %PY% cam_cli.py xem
  pause
)
exit /b %ERRORLEVEL%
