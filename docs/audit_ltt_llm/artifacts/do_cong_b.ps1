# do_cong_b.ps1 - Prompt 03 §1: ranh gioi cong VLM may B. CHI DOC + request binh thuong.
# Chay TREN MAY B qua Nexus. Khong stress test, khong doi cau hinh, khong kill gi.
$ErrorActionPreference = 'Continue'
$ra = 'H:\LTT_LLM\work\ket_do_cong_b.txt'
$so = New-Object System.Collections.ArrayList

function Ghi($s) { [void]$so.Add($s); Write-Host $s }

$e = Get-Content "C:\ProgramData\LTTLlm\gateway.env" | Where-Object { $_ -match "^LTT_LLM_TOKEN=" }
$tok = ($e -split "=",2)[1].Trim()
$OK  = @{ Authorization = "Bearer $tok" }
$SAI = @{ Authorization = "Bearer khong-phai-token-that-dau-nhe" }
$B   = "http://127.0.0.1:8299"

function Goi($duong, $dau, $than, $method, $timeout) {
    $t0 = Get-Date
    try {
        if ($than) {
            $r = Invoke-WebRequest "$B$duong" -Method $method -Headers $dau -Body $than `
                 -ContentType "application/json" -TimeoutSec $timeout -UseBasicParsing
        } else {
            $r = Invoke-WebRequest "$B$duong" -Method $method -Headers $dau `
                 -TimeoutSec $timeout -UseBasicParsing
        }
        return @{ ma = $r.StatusCode; than = $r.Content
                  giay = [math]::Round(((Get-Date)-$t0).TotalSeconds,2)
                  retry = $r.Headers['Retry-After'] }
    } catch {
        $ma = $_.Exception.Response.StatusCode.value__
        $th = ""
        try { $th = $_.ErrorDetails.Message } catch {}
        $rt = ""
        try { $rt = $_.Exception.Response.Headers['Retry-After'] } catch {}
        return @{ ma = $ma; than = $th
                  giay = [math]::Round(((Get-Date)-$t0).TotalSeconds,2); retry = $rt }
    }
}

Ghi "===== PROMPT 03 §1 - RANH GIOI CONG VLM MAY B ====="
Ghi "thoi diem: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Ghi ""

# ---- C01/C11/C12: /live khong can khoa, va no KHONG duoc noi gi them ----
Ghi "-- C01/C11/C12  GET /live  (KHONG kem khoa)"
$r = Goi "/live" @{} $null "GET" 15
Ghi "   ma=$($r.ma)  $($r.giay)s  than=$($r.than)"

Ghi "-- C12  GET /health  (KHONG kem khoa) - phai 401"
$r = Goi "/health" @{} $null "GET" 15
Ghi "   ma=$($r.ma)  $($r.giay)s"

# ---- C02: bearer sai ----
Ghi "-- C02  GET /health  (khoa SAI) - phai 401"
$r = Goi "/health" $SAI $null "GET" 15
Ghi "   ma=$($r.ma)  $($r.giay)s"

Ghi "-- C02  POST /v1/responses (khoa SAI) - phai 401, KHONG duoc cham GPU"
$than = '{"model":"qwen38-api","max_output_tokens":8,"input":[{"role":"user","content":[{"type":"input_text","text":"hi"}]}]}'
$r = Goi "/v1/responses" $SAI $than "POST" 30
Ghi "   ma=$($r.ma)  $($r.giay)s"

# ---- C03: model ngoai danh sach trang ----
Ghi ""
Ghi "-- C03  model KHONG trong danh sach trang - phai 404 fail-closed"
foreach ($m in @("gpt-4o","llama-3","qwen38-api-x","")) {
    $t = '{"model":"' + $m + '","max_output_tokens":8,"input":[{"role":"user","content":[{"type":"input_text","text":"hi"}]}]}'
    $r = Goi "/v1/responses" $OK $t "POST" 30
    $tn = if ($m) { $m } else { "(rong)" }
    Ghi "   model=$($tn.PadRight(16)) ma=$($r.ma)  $($r.giay)s"
}

# ---- C05: tu choi TRUOC GPU ----
Ghi ""
Ghi "-- C05  vuot tran INPUT - phai 413 va phai NHANH (truoc GPU)"
$dai = "a" * 300000
$t = @{ model="qwen38-api"; max_output_tokens=8
        input=@(@{ role="user"; content=@(@{ type="input_text"; text=$dai }) }) } | ConvertTo-Json -Depth 8 -Compress
$r = Goi "/v1/responses" $OK $t "POST" 60
Ghi "   ma=$($r.ma)  $($r.giay)s  <- neu <2s thi no chan TRUOC khi cham GPU"
Ghi "   than=$($r.than)"

Ghi "-- C05  vuot tran OUTPUT - phai 413"
$t = '{"model":"qwen38-api","max_output_tokens":999999,"input":[{"role":"user","content":[{"type":"input_text","text":"hi"}]}]}'
$r = Goi "/v1/responses" $OK $t "POST" 60
Ghi "   ma=$($r.ma)  $($r.giay)s"
Ghi "   than=$($r.than)"

# ---- C04: than khong hop le ----
Ghi ""
Ghi "-- C04  than KHONG hop le"
foreach ($t in @('{}', '{"model":"qwen38-api"}', 'khong phai json')) {
    $r = Goi "/v1/responses" $OK $t "POST" 30
    Ghi "   than=$($t.PadRight(26)) ma=$($r.ma)  $($r.giay)s"
}

# ---- Trang thai truoc phan nang ----
Ghi ""
Ghi "-- /health day du (co khoa)"
$r = Goi "/health" $OK $null "GET" 20
Ghi "   $($r.than)"

Ghi ""
Ghi "-- /v1/models"
$r = Goi "/v1/models" $OK $null "GET" 20
Ghi "   $($r.than)"

[IO.File]::WriteAllText($ra, ($so -join "`r`n"), (New-Object Text.UTF8Encoding($false)))
Write-Host "`nDA LUU: $ra"
