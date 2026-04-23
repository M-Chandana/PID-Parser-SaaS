$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot "logs\b4"
$pidsFile = Join-Path $logDir "pids.json"

if (-not (Test-Path $pidsFile)) {
  Write-Host "No PID file found at $pidsFile"
  exit 0
}

$pids = Get-Content $pidsFile | ConvertFrom-Json
$targetPids = @($pids.backendPid, $pids.workerPid, $pids.aiPid)

foreach ($procId in $targetPids) {
  if ($null -eq $procId) {
    continue
  }

  try {
    $proc = Get-Process -Id $procId -ErrorAction Stop
    Stop-Process -Id $procId -Force
    Write-Host "Stopped PID $procId ($($proc.ProcessName))"
  } catch {
    Write-Host "PID $procId already stopped or not found"
  }
}

Write-Host "B4 staging stack stop complete."
