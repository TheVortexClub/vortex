<#
.SYNOPSIS
  Runs Vortex as the server for everyone: this notebook hosts the model, the API and the website.
  Other people open http://<notebook-ip>:3000 in their browser and create their own account.
.EXAMPLE
  .\scripts\serve.ps1               # accounts on, reachable from your network
  .\scripts\serve.ps1 -Rebuild      # rebuild the website after updating the code
  .\scripts\serve.ps1 -Local        # just you: no login, only this computer
#>
param(
  [int]$Port = 3000,
  [switch]$Rebuild,
  [switch]$Local
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$api = Join-Path $root "apps\api"
$web = Join-Path $root "apps\web"

$nodeCmd = Get-Command node -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $nodeCmd) { throw "Instale o Node.js 20+ (https://nodejs.org)." }
$node = $nodeCmd.Source
# Use the npm that ships with this Node, not whatever "npm" is first on PATH.
$npm = Join-Path (Split-Path $node) "npm.cmd"
if (-not (Test-Path $npm)) { throw "npm.cmd não encontrado ao lado de $node. Reinstale o Node.js." }
function Invoke-Npm {
  & $npm @args
  if ($LASTEXITCODE -ne 0) { throw "npm $($args -join ' ') falhou (código $LASTEXITCODE)." }
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "Instale o Ollama (https://ollama.com) e rode .\scripts\create-model.ps1." }

# --- API (Python) -------------------------------------------------------------
$venv = Join-Path $env:LOCALAPPDATA "vortex\venv"   # short path: avoids Windows MAX_PATH issues
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $python)) {
  Write-Host "[vortex] criando ambiente Python em $venv ..."
  if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv $venv } else { python -m venv $venv }
}
& $python -m pip install --quiet --disable-pip-version-check -e $api

$env:VORTEX_LOCAL_MODE = if ($Local) { "true" } else { "false" }
$env:VORTEX_DATA_DIR = Join-Path $api "data"
Push-Location $api
try { & $python -m alembic upgrade head } finally { Pop-Location }

# --- Website (Node) -----------------------------------------------------------
Push-Location $web
try {
  if (-not (Test-Path "node_modules\next")) {
    Write-Host "[vortex] instalando dependências do site..."
    Invoke-Npm ci --no-audit --no-fund
  }
  if ($Rebuild -or -not (Test-Path ".next\BUILD_ID")) {
    Write-Host "[vortex] montando o site (1-2 min)..."
    $env:NEXT_TELEMETRY_DISABLED = "1"
    Invoke-Npm run build
  }
} finally { Pop-Location }

# --- Run ----------------------------------------------------------------------
$apiProc = Start-Process -FilePath $python -WorkingDirectory $api -PassThru -WindowStyle Minimized `
  -ArgumentList "-m", "uvicorn", "vortex_api.main:create_app", "--factory", "--host", "127.0.0.1", "--port", "8000"

$bind = if ($Local) { "127.0.0.1" } else { "0.0.0.0" }
Write-Host ""
Write-Host "  VORTEX v0.2.1 no ar" -ForegroundColor Cyan
Write-Host "  Neste computador:   http://localhost:$Port"
if (-not $Local) {
  Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.InterfaceAlias -notmatch "vEthernet|VirtualBox|WSL|Loopback" } |
    ForEach-Object { Write-Host "  Outros aparelhos:   http://$($_.IPAddress):$Port   ($($_.InterfaceAlias))" }
  Write-Host "  Se o Windows perguntar, permita o Node.js em redes privadas." -ForegroundColor Yellow
}
Write-Host "  Ctrl+C para parar."
Write-Host ""

$env:HOST = $bind
$env:PORT = "$Port"
$env:NODE_ENV = "production"
Push-Location $web
try {
  & $node server.mjs --prod
} finally {
  Pop-Location
  if ($apiProc -and -not $apiProc.HasExited) { Stop-Process -Id $apiProc.Id -Force }
}
