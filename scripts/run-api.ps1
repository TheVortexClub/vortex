<#
.SYNOPSIS
  Runs the Vortex API on this machine (no Docker), against your local Ollama.
.EXAMPLE
  .\scripts\run-api.ps1               # http://127.0.0.1:8000  (docs at /docs)
  .\scripts\run-api.ps1 -Lan          # also reachable from other devices on your network
  .\scripts\run-api.ps1 -Mock         # no model needed (simulated answers)
#>
param(
  [int]$Port = 8000,
  [switch]$Lan,
  [switch]$Mock
)
$ErrorActionPreference = "Stop"
$api = Join-Path (Split-Path -Parent $PSScriptRoot) "apps\api"

# Keep the venv on a short path: deep paths break some compiled wheels on Windows (MAX_PATH).
$venv = Join-Path $env:LOCALAPPDATA "vortex\venv"
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $python)) {
  Write-Host "[vortex] creating virtualenv in $venv ..."
  if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv $venv } else { python -m venv $venv }
}
& $python -m pip install --quiet --disable-pip-version-check -e "$api[dev]"

if ($Mock) { $env:VORTEX_MOCK_BACKEND = "true" }
$bind = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }

Push-Location $api
try {
  & $python -m alembic upgrade head
  Write-Host "[vortex] API on http://${bind}:$Port  (Swagger: http://localhost:$Port/docs)"
  & $python -m uvicorn vortex_api.main:create_app --factory --host $bind --port $Port
} finally {
  Pop-Location
}
