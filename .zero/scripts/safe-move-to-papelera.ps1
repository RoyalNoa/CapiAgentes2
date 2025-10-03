<#
# @utility true
safe-move-to-papelera.ps1 - Mueve (NO BORRA) archivos/carpeta a `.zero/dynamic/papelera/<timestamp>/`
Uso:
  pwsh ./.zero/scripts/safe-move-to-papelera.ps1 -Path '.zero/scripts/conflictos-simple.ps1'
#>
param(
  [Parameter(Mandatory=$true)] [string]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Path)) { throw "No existe: $Path" }
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$trashRoot = Join-Path $root '.zero/dynamic/papelera'
if (-not (Test-Path -LiteralPath $trashRoot)) { New-Item -ItemType Directory -Path $trashRoot -Force | Out-Null }
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$destDir = Join-Path $trashRoot $ts
New-Item -ItemType Directory -Path $destDir -Force | Out-Null

Write-Host "[safe-move] Moviendo a papelera: $Path -> $destDir"
Move-Item -LiteralPath $Path -Destination $destDir -Force
Write-Host "[safe-move] OK"
