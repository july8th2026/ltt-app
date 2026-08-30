@echo off
REM LTT Studios CamCLI - administrator entry point. ASCII only, no BOM.
REM
REM WHY THIS EXISTS. The "Claude Desktop" item writes to
REM   HKCU\SOFTWARE\Policies\Claude
REM which is the Group Policy branch. Measured ACL on a real machine:
REM   <the user>              Allow ReadKey        <- read only
REM   BUILTIN\Administrators  Allow FullControl
REM So a non-elevated run CANNOT plug that item. Before 2026-08-30 it failed
REM seven times in a row and said nothing about why.
REM
REM The other three items (Codex, Claude Code CLI, VS Code extension) need no
REM elevation. Do not tell customers to always run this one.
setlocal
cd /d "%~dp0"

REM Two packages ship different binaries. The ZIP ships the console build; the
REM installer ships the GUI build. Accept either, and prefer the console build
REM when both are present because it prints its log where the user can see it.
set EXE=
if exist "%~dp0LTTStudios-CamCLI-Console.exe" set EXE=%~dp0LTTStudios-CamCLI-Console.exe
if not defined EXE if exist "%~dp0LTTStudios-CamCLI.exe" set EXE=%~dp0LTTStudios-CamCLI.exe

if not defined EXE (
  echo Neither LTTStudios-CamCLI-Console.exe nor LTTStudios-CamCLI.exe was found
  echo next to this BAT file.
  pause
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0cam_cli_admin.ps1" -Exe "%EXE%"
exit /b %ERRORLEVEL%
