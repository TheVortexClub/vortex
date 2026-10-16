<#
.SYNOPSIS
  Liga as ferramentas do Vortex que rodam no Docker (uma vez só):
    1. Pesquisa na web: SearXNG local em http://127.0.0.1:8888
    2. Ambiente isolado de código: imagem "vortex-sandbox" (Python + pandas + matplotlib)
  Precisa do Docker Desktop aberto. Baixa ~600 MB na primeira vez.
.EXAMPLE
  .\scripts\setup-tools.ps1
  .\scripts\setup-tools.ps1 -Remove    # desliga e remove os dois
#>
param([switch]$Remove)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Invoke-Docker {
  & docker @args
  if ($LASTEXITCODE -ne 0) { throw "docker $($args -join ' ') falhou (código $LASTEXITCODE)." }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Instale o Docker Desktop (https://www.docker.com/products/docker-desktop/) e abra-o."
}
docker info --format "{{.ServerVersion}}" *> $null
if ($LASTEXITCODE -ne 0) { throw "O Docker não está rodando. Abra o Docker Desktop e tente de novo." }

if ($Remove) {
  docker rm -f vortex-searxng *> $null
  docker image rm vortex-sandbox *> $null
  Write-Host "Pesquisa (SearXNG) e ambiente de código removidos."
  return
}

# 1. SearXNG ------------------------------------------------------------------
Write-Host "[vortex] ligando a pesquisa na web (SearXNG)..."
$secret = -join ((48..57) + (97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
docker rm -f vortex-searxng *> $null
$settings = Join-Path $root "infra\searxng\settings.yml"
Invoke-Docker run -d --name vortex-searxng --restart unless-stopped `
  -p 127.0.0.1:8888:8080 `
  -e "SEARXNG_SECRET=$secret" `
  -v "${settings}:/etc/searxng/settings.yml:ro" `
  searxng/searxng:latest | Out-Null

# 2. Sandbox ------------------------------------------------------------------
Write-Host "[vortex] montando o ambiente isolado de código (vortex-sandbox)..."
Invoke-Docker build -t vortex-sandbox (Join-Path $root "infra\sandbox")

# 3. Check --------------------------------------------------------------------
Write-Host "[vortex] conferindo..."
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 "http://127.0.0.1:8888/healthz"
    if ($r.StatusCode -eq 200) { $ok = $true; break }
  } catch { Start-Sleep -Seconds 2 }
}
$test = "print('ok')" | docker run --rm -i --network none vortex-sandbox
Write-Host ""
Write-Host ("  Pesquisa na web:      " + ($(if ($ok) { "pronta" } else { "ainda iniciando (confira em 1 min)" })))
Write-Host ("  Ambiente de código:   " + ($(if ($test -eq "ok") { "pronto" } else { "falhou" })))
Write-Host ""
Write-Host "No Vortex, abra Ferramentas e clique em 'Verificar de novo'."
Write-Host "Geração de imagens (ComfyUI) é um passo à parte: veja docs\ferramentas.md."
