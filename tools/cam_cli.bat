@echo off
REM cam_cli.bat - vo boc de bam dup, khong phai noi chua logic.
REM
REM !! MOI THU O DAY PHAI LA ASCII THUAN va khong BOM. `.bat` doc theo bang ma
REM    ANSI cua he thong; mot dau tieng Viet lam hong ca cau lenh va bao loi o
REM    mot dong khac (cung ho voi quy tac 2 cua CLAUDE.md cho .ps1).
REM
REM !! KHONG viet lai logic o day. Toan bo nam trong cam_cli.py vi Python test
REM    duoc con .bat thi khong. Tep nay chi lam DUNG hai viec: tim python, va
REM    giu cua so mo de nguoi dung doc duoc ket qua.

setlocal
cd /d "%~dp0"

set PY=
for %%P in (py.exe python.exe) do (
    if not defined PY (
        where %%P >nul 2>nul && set PY=%%P
    )
)

if not defined PY (
    echo.
    echo Khong tim thay Python tren may nay.
    echo Cai tai https://www.python.org/downloads/ roi chay lai tep nay.
    echo Nho tich "Add python.exe to PATH" luc cai.
    echo.
    pause
    exit /b 1
)

if "%~1"=="" goto :menu

%PY% cam_cli.py %*
echo.
pause
exit /b %ERRORLEVEL%

:menu
echo.
echo   ============================================================
echo    LTT Studios - cam Codex / Claude Code vao API cua ban
echo   ============================================================
echo.
echo    1. Xem dang cam gi          (khong doi gi ca)
echo    2. Cam vao                  (can khoa ltt_sk_...)
echo    3. Kiem bang mot luot goi that
echo    4. Go ra, tra ve nguyen trang
echo.
set /p CHON="   Chon 1-4 (Enter de thoat): "

if "%CHON%"=="1" ( %PY% cam_cli.py xem & goto :xong )
if "%CHON%"=="3" ( %PY% cam_cli.py kiem & goto :xong )
if "%CHON%"=="4" ( %PY% cam_cli.py go & goto :xong )
if "%CHON%"=="2" goto :cam
goto :xong

:cam
echo.
echo   Lay khoa o: https://app.lttstudios.com/developers/keys
echo   Khoa chi hien MOT LAN luc tao.
echo.
set /p KHOA="   Dan khoa ltt_sk_... vao day: "
if "%KHOA%"=="" goto :xong
%PY% cam_cli.py cam --khoa %KHOA%

:xong
echo.
pause
endlocal
