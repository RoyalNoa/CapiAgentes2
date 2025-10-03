<#
# @utility true
clean-experimental-scripts.ps1 - Detecta scripts no canónicos en `/.zero/scripts` y los mueve a `/.zero/dynamic/tools/experiments/<ts>/`.
NO BORRADO. Solo mueve.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptsDir = $PSScriptRoot
$root = Split-Path -Parent (Split-Path -Parent $scriptsDir)
$experiments = Join-Path $root '.zero/dynamic/tools/experiments'
if (-not (Test-Path -LiteralPath $experiments)) { New-Item -ItemType Directory -Path $experiments -Force | Out-Null }
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$target = Join-Path $experiments $ts
New-Item -ItemType Directory -Path $target -Force | Out-Null

$canonical = @('pipeline.ps1','estructura.ps1','conflictos-final.ps1','zerograh-validation.ps1','zero-circuit-validate.ps1','safe-move-to-papelera.ps1','clean-experimental-scripts.ps1')
$all = Get-ChildItem -LiteralPath $scriptsDir -Filter '*.ps1' -File -Force
$extra = $all | Where-Object { $canonical -notcontains $_.Name }

if (-not $extra) {
  Write-Host '[clean] No hay scripts experimentales para mover.'
  exit 0
}

Write-Host "[clean] A mover: $($extra.Name -join ', ')"
foreach ($s in $extra) {
  Move-Item -LiteralPath $s.FullName -Destination (Join-Path $target $s.Name) -Force
}

Write-Host "[clean] OK. Scripts movidos a: $target"
