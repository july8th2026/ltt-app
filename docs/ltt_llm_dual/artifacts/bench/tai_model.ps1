# tai_model.ps1 - tai cac tep GGUF cua LTT-3.5 (Qwen3.5-9B) ve may B.
#
# Task 3.1 cua ke hoach LTT LLM Dual-Model. Chay duoc nhieu lan: tep nao da co
# va dung hash thi bo qua, nen chay lai sau khi mat dien khong tai lai tu dau.
#
# Vi sao Scheduled Task chu khong chay thang qua ssh: phien ssh dut thi tien
# trinh con bi giet, ma bon tep nay ~17 GB. Xem memory `lo-do-dai-tren-may-b`.
#
# Hash doi chieu la `lfs.oid` tra ve tu HuggingFace API - HF dung sha256 lam
# oid, nen `Get-FileHash -Algorithm SHA256` so thang duoc, khong can tin vao
# con so nao chep tay.

$ErrorActionPreference = 'Stop'

$ThuMuc = 'H:\LTT_LLM\models'
$Log    = 'E:\AI\ltt_dual\tai_model.log'

function Ghi([string]$dong) {
    $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    # Add-Content mo/dong tep moi lan goi => da xuong dia ngay. Windows Update
    # khoi dong lai may luc 01:00 thi phan da ghi van con.
    Add-Content -Path $Log -Value "$t  $dong" -Encoding UTF8
}

# Bon tep: hai ung vien Q6_K (G3 cua Task 3.2 se chon mot) va mmproj cua tung
# kho. `mmproj-F16.gguf` cua unsloth TRUNG TEN voi mmproj cua ban 27B dang co
# tren dia, nen phai doi ten khi luu.
$DsTep = @(
    @{ Ten = 'Qwen3.5-9B-Q6_K-unsloth.gguf'
       Url = 'https://huggingface.co/unsloth/Qwen3.5-9B-MTP-GGUF/resolve/main/Qwen3.5-9B-Q6_K.gguf'
       Sha = '8ae8fd04e30c5a4af3ef72654729fb0d7f33615cac1ba335dd88084a56287934'
       Byte = 7684551008 }
    @{ Ten = 'mmproj-9B-F16-unsloth.gguf'
       Url = 'https://huggingface.co/unsloth/Qwen3.5-9B-MTP-GGUF/resolve/main/mmproj-F16.gguf'
       Sha = '5a40d1f771686432172a4981018a0d30d03a5aaf5793a5badd5416573362a232'
       Byte = 918165984 }
    @{ Ten = 'Qwen3.5-9B-Q6_K-lmstudio.gguf'
       Url = 'https://huggingface.co/lmstudio-community/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q6_K.gguf'
       Sha = 'b2ccc477f0a2449de299bef560b63e498cae94a2f3a3bae13df01168d77773e6'
       Byte = 7359259040 }
    @{ Ten = 'mmproj-9B-BF16-lmstudio.gguf'
       Url = 'https://huggingface.co/lmstudio-community/Qwen3.5-9B-GGUF/resolve/main/mmproj-Qwen3.5-9B-BF16.gguf'
       Sha = '330d17547bfdbcd0e7a0cb3f4b06b4ceeac0aaa1e449122d9d66ef957aeb74b3'
       Byte = 921704480 }
)

New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null
New-Item -ItemType Directory -Force -Path $ThuMuc | Out-Null

Ghi "=== BAT DAU === $($DsTep.Count) tep, dich $ThuMuc"
$loi = 0

foreach ($t in $DsTep) {
    $dich = Join-Path $ThuMuc $t.Ten
    $tam  = "$dich.part"

    if (Test-Path $dich) {
        $co = (Get-FileHash -Path $dich -Algorithm SHA256).Hash
        if ($co -ieq $t.Sha) { Ghi "BO QUA  $($t.Ten): da co, hash khop"; continue }
        Ghi "LAI     $($t.Ten): da co nhung hash LECH ($co) => tai lai"
        Remove-Item -Path $dich -Force
    }

    Ghi "TAI     $($t.Ten) <- $($t.Url)"
    $t0 = Get-Date
    # -C - : tiep tuc tu cho dut. --retry-all-errors de HF tra 5xx luc dong.
    & curl.exe -L --retry 5 --retry-delay 10 --retry-all-errors -C - `
        --silent --show-error -o $tam $t.Url
    if ($LASTEXITCODE -ne 0) {
        Ghi "LOI     $($t.Ten): curl thoat $LASTEXITCODE"
        $loi++
        continue
    }
    $giay = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    $co_byte = (Get-Item $tam).Length
    Ghi "XONG    $($t.Ten): $co_byte byte trong $giay s"

    if ($co_byte -ne $t.Byte) {
        Ghi "LOI     $($t.Ten): co $co_byte byte, cho $($t.Byte)"
        $loi++
        continue
    }
    $h = (Get-FileHash -Path $tam -Algorithm SHA256).Hash
    if ($h -ine $t.Sha) {
        Ghi "LOI     $($t.Ten): sha256 $h != $($t.Sha)"
        Remove-Item -Path $tam -Force
        $loi++
        continue
    }
    Move-Item -Path $tam -Destination $dich -Force
    Ghi "KHOP    $($t.Ten): sha256 $h"
}

Ghi "=== KET THUC === $loi loi"
exit $loi
