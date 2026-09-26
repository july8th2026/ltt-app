# Deploy script - Run with Administrator privileges
# Usage: Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File",".\deploy.ps1"

$deployRoot = "C:\LTTPlatform"
$deployScript = Join-Path $PSScriptRoot "deploy\windows\install.ps1"

# Copy entire tree to C:\LTTPlatform\app
Write-Host "Copying D:\LTTSTUDIOSAPP to C:\LTTPlatform\app..."

robocopy "D:\LTTSTUDIOSAPP" "C:\LTTPlatform\app" /E /DCOPY:DAT /COPY:DAT

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: robocopy failed"
    exit 1
}

Write-Host "Copy completed"
Write-Host "Running install script..."

& $deployScript -Root $deployRoot -Port 8100

Write-Host "Deployment completed"
