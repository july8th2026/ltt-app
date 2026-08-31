# do_cong_b2.ps1 - Prompt 03 §3/§4: dong thoi, tin hieu GPU, chuyen model.
$ErrorActionPreference = 'Continue'
$ra = 'H:\LTT_LLM\work\ket_do_cong_b2.txt'
$so = New-Object System.Collections.ArrayList
function Ghi($s) { [void]$so.Add($s); Write-Host $s }

$e = Get-Content "C:\ProgramData\LTTLlm\gateway.env" | Where-Object { $_ -match "^LTT_LLM_TOKEN=" }
$tok = ($e -split "=",2)[1].Trim()
$OK = @{ Authorization = "Bearer $tok" }
$B  = "http://127.0.0.1:8299"

function Health { (Invoke-WebRequest "$B/health" -Headers $OK -TimeoutSec 20 -UseBasicParsing).Content | ConvertFrom-Json }
function GH { $h = Health; "dang_chay=$($h.gioi_han.dang_chay)/$($h.gioi_han.max_dong_thoi) giu_lau=$($h.gioi_han.giu_lau_nhat_giay)s thu_hoi=$($h.gioi_han.da_thu_hoi)" }

Ghi "===== PROMPT 03 §3/§4 ====="
Ghi "thoi diem: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Ghi ""

# ---- Cai 14 giay: than thieu `input`, model HOP LE ----
Ghi "-- C04b  than thieu 'input' nhung model HOP LE: no di toi dau?"
$than = '{"model":"qwen38-api"}'
$job = Start-Job -ScriptBlock {
    param($B,$tok,$than)
    $t0 = Get-Date
    try { $r = Invoke-WebRequest "$B/v1/responses" -Method POST -Headers @{Authorization="Bearer $tok"} `
               -Body $than -ContentType "application/json" -TimeoutSec 90 -UseBasicParsing
          "ma=$($r.StatusCode) giay=$([math]::Round(((Get-Date)-$t0).TotalSeconds,2))" }
    catch { "ma=$($_.Exception.Response.StatusCode.value__) giay=$([math]::Round(((Get-Date)-$t0).TotalSeconds,2))" }
} -ArgumentList $B,$tok,$than
Start-Sleep -Milliseconds 1500
Ghi "   trong luc no chay: $(GH)   <- neu dang_chay=1 thi no DA CHIEM SUAT"
$kq = Receive-Job $job -Wait; Remove-Job $job
Ghi "   ket qua: $kq"
Ghi "   sau khi xong: $(GH)"

# ---- C06: hai yeu cau THAT cung luc ----
Ghi ""
Ghi "-- C06  hai yeu cau hop le CUNG LUC - phai mot 200 mot 429"
$sb = {
    param($B,$tok,$nhan)
    $t0 = Get-Date
    $than = '{"model":"qwen38-api","max_output_tokens":24,"input":[{"role":"user","content":[{"type":"input_text","text":"Dem tu 1 den 5."}]}]}'
    try { $r = Invoke-WebRequest "$B/v1/responses" -Method POST -Headers @{Authorization="Bearer $tok"} `
               -Body $than -ContentType "application/json" -TimeoutSec 180 -UseBasicParsing
          "$nhan ma=$($r.StatusCode) giay=$([math]::Round(((Get-Date)-$t0).TotalSeconds,2))" }
    catch { $rt = ""; try { $rt = $_.Exception.Response.Headers['Retry-After'] } catch {}
            "$nhan ma=$($_.Exception.Response.StatusCode.value__) giay=$([math]::Round(((Get-Date)-$t0).TotalSeconds,2)) retry_after=$rt" }
}
$j1 = Start-Job -ScriptBlock $sb -ArgumentList $B,$tok,"A"
Start-Sleep -Milliseconds 400
$j2 = Start-Job -ScriptBlock $sb -ArgumentList $B,$tok,"B"
Start-Sleep -Milliseconds 800
Ghi "   giua chung: $(GH)"
foreach ($j in @($j1,$j2)) { Ghi "   $(Receive-Job $j -Wait)"; Remove-Job $j }
Ghi "   sau khi xong: $(GH)"

# ---- C16-C21: bon tin hieu GPU doc CUNG MOT LUC ----
Ghi ""
Ghi "-- C16..C21  bon nguon tin hieu GPU, doc gan nhu dong thoi"
$smi = (& nvidia-smi --query-gpu=memory.used,utilization.gpu,temperature.gpu --format=csv,noheader) -join ""
$h = Health
$run = ""
try { $run = (Invoke-WebRequest "http://127.0.0.1:8280/running" -TimeoutSec 10 -UseBasicParsing).Content } catch { $run = "LOI: $($_.Exception.Message)" }
$pyGpu = (& nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader) -join " | "
Ghi "   nvidia-smi tong  : $smi"
Ghi "   tien trinh tren card: $pyGpu"
Ghi "   /health trong_tai : ban=$($h.trong_tai.ban) so_python_gpu=$($h.trong_tai.so_python_gpu) ram_trong=$($h.trong_tai.ram_trong_gb) ly_do='$($h.trong_tai.ly_do)'"
Ghi "   /health gpu       : tren_gpu=$($h.gpu.tren_gpu) vram=$($h.gpu.vram_dung_mb) co_model_nap=$($h.gpu.co_model_nap) ly_do='$($h.gpu.ly_do)'"
Ghi "   llama-swap /running: $run"

# ---- C23/C24: chuyen text -> vision ----
Ghi ""
Ghi "-- C23/C24  chuyen ho so text -> vision (do thoi gian)"
$t0 = Get-Date
$than = '{"model":"qwen38-vision","max_output_tokens":16,"input":[{"role":"user","content":[{"type":"input_text","text":"Xin chao"}]}]}'
try { $r = Invoke-WebRequest "$B/v1/responses" -Method POST -Headers $OK -Body $than -ContentType "application/json" -TimeoutSec 300 -UseBasicParsing
      Ghi "   ma=$($r.StatusCode) chuyen mat $([math]::Round(((Get-Date)-$t0).TotalSeconds,1))s" }
catch { Ghi "   ma=$($_.Exception.Response.StatusCode.value__) sau $([math]::Round(((Get-Date)-$t0).TotalSeconds,1))s" }
$h = Health
Ghi "   sau chuyen: vram=$($h.gpu.vram_dung_mb) co_model_nap=$($h.gpu.co_model_nap) $(GH)"
$run = ""; try { $run = (Invoke-WebRequest "http://127.0.0.1:8280/running" -TimeoutSec 10 -UseBasicParsing).Content } catch {}
Ghi "   /running: $run"

Ghi ""
Ghi "-- chuyen NGUOC vision -> text"
$t0 = Get-Date
$than = '{"model":"qwen38-api","max_output_tokens":16,"input":[{"role":"user","content":[{"type":"input_text","text":"Xin chao"}]}]}'
try { $r = Invoke-WebRequest "$B/v1/responses" -Method POST -Headers $OK -Body $than -ContentType "application/json" -TimeoutSec 300 -UseBasicParsing
      Ghi "   ma=$($r.StatusCode) chuyen mat $([math]::Round(((Get-Date)-$t0).TotalSeconds,1))s" }
catch { Ghi "   ma=$($_.Exception.Response.StatusCode.value__) sau $([math]::Round(((Get-Date)-$t0).TotalSeconds,1))s" }
Ghi "   cuoi cung: $(GH)"

[IO.File]::WriteAllText($ra, ($so -join "`r`n"), (New-Object Text.UTF8Encoding($false)))
Write-Host "`nDA LUU: $ra"
