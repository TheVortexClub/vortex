<#
.SYNOPSIS
  Faz o servidor do Vortex iniciar sozinho sempre que você entrar no Windows.
  Cria o atalho "Vortex Servidor" na pasta Inicializar do seu usuário (nada de serviço do sistema).
.EXAMPLE
  .\scripts\install-autostart.ps1           # liga o início automático
  .\scripts\install-autostart.ps1 -Remove   # desliga
#>
param([switch]$Remove)
$ErrorActionPreference = "Stop"

$startup = [Environment]::GetFolderPath("Startup")
$shortcut = Join-Path $startup "Vortex Servidor.lnk"

if ($Remove) {
  if (Test-Path $shortcut) { Remove-Item $shortcut; Write-Host "Início automático do Vortex desligado." }
  else { Write-Host "O início automático já estava desligado." }
  return
}

$root = Split-Path -Parent $PSScriptRoot
$serve = Join-Path $root "scripts\serve.ps1"
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($shortcut)
$link.TargetPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$link.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$serve`""
$link.WorkingDirectory = $root
$link.WindowStyle = 7  # minimizado
$link.Description = "Inicia o servidor do Vortex"
$link.Save()

Write-Host "Pronto: o Vortex vai iniciar sozinho (minimizado) quando você entrar no Windows."
Write-Host "Atalho criado em: $shortcut"
Write-Host "Para desligar: .\scripts\install-autostart.ps1 -Remove"
