<#
.SYNOPSIS
  Builds the Vortex model in your local Ollama from an open-weight base + models/Modelfile.
.EXAMPLE
  .\scripts\create-model.ps1                      # base: llama3.2:3b (fast on CPU)
  .\scripts\create-model.ps1 -Base qwen2.5:7b-instruct-q4_K_M
#>
param(
  [string]$Base = "llama3.2:3b",
  [string]$Name = "vortex:0.2.1"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$installed = (ollama list) -join "`n"
if ($installed -notmatch [regex]::Escape($Base)) {
  Write-Host "[vortex] base model $Base not found locally, pulling it..."
  ollama pull $Base
}

$modelfile = Get-Content (Join-Path $root "models\Modelfile") -Raw
$modelfile = [regex]::Replace($modelfile, "(?m)^FROM .*$", "FROM $Base")
$tmp = Join-Path $env:TEMP "vortex.Modelfile"
[IO.File]::WriteAllText($tmp, $modelfile)  # UTF-8 without BOM

Write-Host "[vortex] building $Name from $Base ..."
ollama create $Name -f $tmp
Remove-Item $tmp
Write-Host "[vortex] done. Test it: ollama run $Name `"Quem e voce?`""
