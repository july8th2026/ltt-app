# bput_lon.ps1 -- day mot tep LON sang may B, chia khoi.
#
# !! bput.ps1 goi base64 nguyen tep trong MOT lenh, va Windows co tran do dai
#    dong lenh (~32 KB). Mot tep 59 KB lam CreateProcess tra:
#      (206, 'CreateProcess', 'The filename or extension is too long.')
#    Trieu chung khong noi gi ve kich thuoc, nen de doc nham thanh loi duong dan.
param([Parameter(Mandatory=$true)][string]$Nguon,
      [Parameter(Mandatory=$true)][string]$Dich,
      [int]$Khoi = 12000,
      [string]$reason = 'Day tep lon sang may B theo khoi')

if (-not (Test-Path -LiteralPath $Nguon)) { Write-Error "khong thay $Nguon"; exit 1 }
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($Nguon))
$tam = "$Dich.phan"
$n = [Math]::Ceiling($b64.Length / $Khoi)
Write-Host ("  {0} byte b64 -> {1} khoi" -f $b64.Length, $n)

for ($i = 0; $i -lt $n; $i++) {
    $p = $b64.Substring($i * $Khoi, [Math]::Min($Khoi, $b64.Length - $i * $Khoi))
    # Khoi dau GHI DE, cac khoi sau NOI THEM. Neu lam nguoc lai thi mot lan chay
    # lai se noi vao phan cu va cho ra mot tep hong ma van co ve day du.
    $mo = if ($i -eq 0) { 'Create' } else { 'Append' }
    $cmd = "`$s=[IO.File]::Open('$tam',[IO.FileMode]::$mo,[IO.FileAccess]::Write);`$w=New-Object IO.StreamWriter(`$s);`$w.Write('$p');`$w.Close();`$s.Close()"
    & "$PSScriptRoot\bexec.ps1" -cmd $cmd -reason "$reason (khoi $($i+1)/$n)" | Out-Null
}
$cmdCuoi = "`$t=[IO.File]::ReadAllText('$tam');[IO.File]::WriteAllBytes('$Dich',[Convert]::FromBase64String(`$t));del '$tam';'{0} byte -> {1}' -f (Get-Item '$Dich').Length,'$Dich'"
& "$PSScriptRoot\bexec.ps1" -cmd $cmdCuoi -reason "$reason (ghep)"
