$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend-service"
$aiDir = Join-Path $repoRoot "ai-service"
$logDir = Join-Path $repoRoot "logs\b4"
$pidsFile = Join-Path $logDir "pids.json"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backendLog = Join-Path $logDir "backend-$timestamp.log"
$backendErr = Join-Path $logDir "backend-$timestamp.err.log"
$workerLog = Join-Path $logDir "worker-$timestamp.log"
$workerErr = Join-Path $logDir "worker-$timestamp.err.log"
$aiLog = Join-Path $logDir "ai-$timestamp.log"
$aiErr = Join-Path $logDir "ai-$timestamp.err.log"

Write-Host "Starting B4 staging stack..."
Write-Host "Logs directory: $logDir"

$backendProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory $backendDir -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr -PassThru

$workerProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run worker" -WorkingDirectory $backendDir -RedirectStandardOutput $workerLog -RedirectStandardError $workerErr -PassThru

$aiProc = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $aiDir -RedirectStandardOutput $aiLog -RedirectStandardError $aiErr -PassThru

$pids = [ordered]@{
  startedAt = (Get-Date).ToString("o")
  backendPid = $backendProc.Id
  workerPid = $workerProc.Id
  aiPid = $aiProc.Id
  backendLog = $backendLog
  backendErr = $backendErr
  workerLog = $workerLog
  workerErr = $workerErr
  aiLog = $aiLog
  aiErr = $aiErr
}

$pids | ConvertTo-Json | Set-Content -Path $pidsFile

Write-Host "Started backend PID: $($backendProc.Id)"
Write-Host "Started worker PID: $($workerProc.Id)"
Write-Host "Started ai PID: $($aiProc.Id)"
Write-Host "PID file: $pidsFile"
Write-Host "B4 staging bootstrap complete."
