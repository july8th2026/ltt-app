@echo off
REM chay_nghiem_thu.cmd - dung ca ba tang roi nghiem thu tu dau den cuoi. TREN MAY B.
REM   [3] llm_gateway :8299  ->  [2] llama-swap :8280  ->  [1] llama-server :828x
setlocal enabledelayedexpansion
set ROOT=H:\LTT_LLM
set ENVF=C:\ProgramData\LTTLlm\gateway.env
REM `llm_gateway` nam o %ROOT%\gateway, khong phai trong site-packages: ma nguon
REM deploy bang script chu khong pip install. Dat NGAY DAY (khong doi tang [3])
REM vi buoc don dep ben duoi da goi `python -m llm_gateway.gpu_uuid`.
set PYTHONPATH=%ROOT%\gateway

REM !! DUNG THEO PID TREN DUNG MOT CARD, KHONG `taskkill /im llama-server.exe`.
REM
REM    Tu 09/2026 may B chay HAI engine: `qwen38-api` tren 3090 va `qwen35-api`
REM    tren 5060 Ti. Dung theo TEN ANH giet ca hai - tuc giet luot dang chay cua
REM    model ta khong nghiem thu, va giet trong im lang. Bai nghiem thu phai dung
REM    dung thu no noi no dung.
REM
REM    `llama-swap` la cha: dung no truoc, no tu dung cac `llama-server` no quan.
REM    Con sot lai thi liet ke PID theo tung card roi dung theo PID.
taskkill /f /im llama-swap.exe   >nul 2>&1
ping -n 3 127.0.0.1 >nul
call :dung_engine ltt38
call :dung_engine ltt35
ping -n 2 127.0.0.1 >nul

echo ============ Doc cau hinh ============
for /f "tokens=1,* delims==" %%a in ('findstr /b "LTT_LLM_" "%ENVF%"') do set %%a=%%b
echo   models_mo = %LTT_LLM_MODELS%
if "%LTT_LLM_MODELS%"=="" (
  echo   LOI: LTT_LLM_MODELS rong. Fail-closed dang lam dung viec, nhung nghiem thu
  echo        can it nhat mot model. Mo bang cach sua %ENVF%.
  goto ket_thuc
)

echo.
echo ============ [2] llama-swap :8280 ============
start "" /b "%ROOT%\bin\llamaswap\llama-swap.exe" ^
  -config "%ROOT%\gateway\llama-swap.yaml" -listen 127.0.0.1:8280 ^
  > "%ROOT%\logs\nt_swap.log" 2>&1
ping -n 5 127.0.0.1 >nul
for /f %%c in ('curl -s -m 5 -o nul -w "%%{http_code}" http://127.0.0.1:8280/health 2^>nul') do set C=%%c
echo   llama-swap /health = !C!
if not "!C!"=="200" ( powershell -NoProfile -Command "Get-Content '%ROOT%\logs\nt_swap.log' -Tail 20" & goto ket_thuc )

echo.
echo ============ [3] llm_gateway :8299 ============
REM `PYTHONPATH` da dat o dau tep (buoc don dep can no truoc buoc nay).
cd /d "%ROOT%\gateway"
start "" /b "%ROOT%\venv\Scripts\python.exe" -m llm_gateway.main ^
  > "%ROOT%\logs\nt_gateway.log" 2>&1
ping -n 7 127.0.0.1 >nul
REM Gui bearer: /health CO xac thuc. Mot cai 401 o day nghia la cong song VA khoa
REM dang bat - nhung phep kiem san sang thi phai gui token, khong thi no bao nham.
for /f %%c in ('curl -s -m 5 -o nul -w "%%{http_code}" -H "Authorization: Bearer %LTT_LLM_TOKEN%" http://127.0.0.1:8299/health 2^>nul') do set G=%%c
echo   llm_gateway /health = !G!
if not "!G!"=="200" ( powershell -NoProfile -Command "Get-Content '%ROOT%\logs\nt_gateway.log' -Tail 25" & goto ket_thuc )

echo.
"%ROOT%\venv\Scripts\python.exe" "%ROOT%\gateway\llm_gateway\deploy\nghiem_thu.py" --token %LTT_LLM_TOKEN%
set RC=%errorlevel%

:ket_thuc
echo.
echo ============ DON DEP ============
taskkill /f /im llama-swap.exe   >nul 2>&1
call :dung_engine ltt38
call :dung_engine ltt35
for /f "tokens=2" %%p in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr PID') do (
  wmic process where "ProcessId=%%p" get CommandLine 2>nul | findstr /c:"llm_gateway.main" >nul && taskkill /f /pid %%p >nul 2>&1
)
ping -n 5 127.0.0.1 >nul
curl -s -m 20 -X POST -H "Content-Type: application/json" -d "{\"unload_models\":true,\"free_memory\":true}" -o nul -w "" http://127.0.0.1:8188/free
ping -n 5 127.0.0.1 >nul
REM !! Xin ca cot `uuid`: voi hai card, mot bang hai dong khong ghi ten card nao
REM    la mot bang KHONG DOC DUOC - va nguoi doc se gan dong dau cho card ho dang
REM    nghi toi.
nvidia-smi --query-gpu=uuid,name,memory.used,memory.free --format=csv,noheader
echo XONG-NGHIEM-THU rc=%RC%
endlocal
goto :eof

REM --- dung_engine <vai> : dung llama-server dang tinh tren DUNG card cua <vai> --
REM     `python -m llm_gateway.gpu_uuid pid <vai>` in ra "PID ten mib" tung dong.
REM     Khong nhung Python inline (quy tac 3 CLAUDE.md) - goi module that.
:dung_engine
set VAI=%~1
for /f "tokens=1,2" %%i in ('"%ROOT%\venv\Scripts\python.exe" -m llm_gateway.gpu_uuid pid %VAI% 2^>nul') do (
  echo %%j | findstr /i "llama-server" >nul && (
    echo   dung PID %%i ^(%%j^) tren card %VAI%
    taskkill /f /pid %%i >nul 2>&1
  )
)
goto :eof
