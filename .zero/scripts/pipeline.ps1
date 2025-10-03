<#
# @canonical true
pipeline.ps1 - Orquestación principal de .zero para regenerar artifacts
Genera:
  - /.zero/artifacts/estructura.txt
  - /.zero/artifacts/conflictos.md
  - /.zero/artifacts/scripts-health.md
  - /.zero/artifacts/prompts-health.md (si existen prompts)
  - /.zero/artifacts/catalog.md
  - /.zero/artifacts/health.md (resumen unificado)
  - /.zero/artifacts/zero-health.md (solo si corre preflight)
Política NO-BORRADO: solo escribe archivos dentro de /.zero/artifacts/.
Uso recomendado:
  - Rápido (por defecto):  pwsh -NoProfile -ExecutionPolicy Bypass -File ./.zero/scripts/pipeline.ps1 -Fast
  - Profundo:         pwsh -NoProfile -ExecutionPolicy Bypass -File ./.zero/scripts/pipeline.ps1 -Deep
  - Timeout por paso: -StepTimeoutSec 60
  - Abort controlado: crear /.zero/dynamic/.stop-pipeline durante la ejecución
#>
param(
  [switch]$Fast,
  [switch]$Deep,
  [int]$StepTimeoutSec = 60
)

function Set-HeadlineNote {
  param([string]$Path, [string]$NoteLine)
  if (-not (Test-Path -LiteralPath $Path)) { return }
  $lines = Get-Content -LiteralPath $Path
  if (-not $lines -or $lines.Count -eq 0) { return }
  if ($lines.Count -gt 1 -and $lines[1] -eq $NoteLine) { return }
  $new = @()
  $new += $lines[0]
  $new += $NoteLine
  if ($lines.Count -gt 1) { $new += $lines[1..($lines.Count-1)] }
  Set-Content -LiteralPath $Path -Value $new -Encoding UTF8 -Force
}

$zeroDir = Split-Path -Parent $PSScriptRoot
$project = Split-Path -Parent $zeroDir
$artifactsDir = Join-Path $zeroDir 'artifacts'
if (-not (Test-Path -LiteralPath $artifactsDir)) {
  New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
}
$stopFile = Join-Path $zeroDir 'dynamic/.stop-pipeline'

Write-Host "[pipeline] Proyecto: $project"
$mode = if ($Deep) { 'Profundo' } elseif ($Fast) { 'Rápido' } else { 'Rápido (por defecto)' }
Write-Host "[pipeline] Modo: $mode"

function Check-Stop {
  if (Test-Path -LiteralPath $stopFile) {
    Write-Warning "[pipeline] stop file detectado: $stopFile - abortando"
    exit 2
  }
}

function Invoke-WithTimeout {
  param(
    [scriptblock]$Script,
    [int]$TimeoutSec,
    [string]$Name
  )
  $job = Start-Job -ScriptBlock $Script
  if (-not (Wait-Job -Job $job -Timeout $TimeoutSec)) {
    Write-Warning "[pipeline] $Name excedió ${TimeoutSec}s - cancelando y usando alternativa"
    try { Stop-Job -Job $job -Force -ErrorAction SilentlyContinue } catch {}
    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
    return $false
  }
  Receive-Job -Job $job -Keep | ForEach-Object { if ($_){ Write-Host $_ } }
  Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
  return $true
}

function Test-IsExcludedPath {
  param([string]$relative,[string[]]$excludedPaths)
  $normalized = $relative.Replace('\','/').Trim()
  if (-not $normalized) { return $false }
  foreach ($dir in $excludedPaths) {
    $pattern = '(^|/)' + [regex]::Escape($dir) + '(/|$)'
    if ($normalized -match $pattern) { return $true }
  }
  return $false
}


$canonicalScripts = @('pipeline.ps1','estructura.ps1','conflictos-final.ps1','zerograh-validation.ps1','zero-circuit-validate.ps1','safe-move-to-papelera.ps1','clean-experimental-scripts.ps1')

# ===== Paso: estructura =====
$estructuraScript = Join-Path $PSScriptRoot 'estructura.ps1'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host "[pipeline] Paso: estructura"
if (Test-Path -LiteralPath $estructuraScript) {
  if ($Deep) { & $estructuraScript -Deep } else { & $estructuraScript }
} else {
  $out = Join-Path $artifactsDir 'estructura.txt'
  "# Estructura del proyecto`nRaíz: $project`n" | Out-File -LiteralPath $out -Encoding UTF8 -Force
  Get-ChildItem -LiteralPath $project -Recurse -Force -File | ForEach-Object {
    $_.FullName.Substring($project.Length + 1).Replace('\','/')
  } | Sort-Object | Out-File -LiteralPath $out -Encoding UTF8 -Append
}
Set-HeadlineNote -Path (Join-Path $artifactsDir 'estructura.txt') -NoteLine '# Nota: Usa esta salida para obtener un mapa rápido del repositorio antes de profundizar en módulos específicos.'
Write-Host ("[pipeline] estructura completado en {0:N1}s" -f $sw.Elapsed.TotalSeconds)

# ===== Paso: conflictos =====
Write-Host "[pipeline] Paso: conflictos"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Check-Stop
if ($Deep) {
  $confFinal = Join-Path $PSScriptRoot 'conflictos-final.ps1'
  if (Test-Path -LiteralPath $confFinal) {
    $ok = Invoke-WithTimeout -Script { & $using:confFinal } -TimeoutSec $StepTimeoutSec -Name 'conflictos-final'
    if (-not $ok) { $Deep = $false }
  } else {
    Write-Warning "[pipeline] conflictos-final.ps1 no encontrado - usando modo rápido"
    $Deep = $false
  }
}
if (-not $Deep) {
  $salida = Join-Path $artifactsDir 'conflictos.md'
  "# Conflictos (rápido)" | Out-File -LiteralPath $salida -Encoding UTF8 -Force
  "Generado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -LiteralPath $salida -Append -Encoding UTF8
  "" | Out-File -LiteralPath $salida -Append -Encoding UTF8
  # NOTA: Mantener estas exclusiones sincronizadas con estructura.ps1 para evitar basura en artefactos.
  $excludeDirs = @('.git','.vscode','.idea','.vs','node_modules','dist','build','coverage','tmp','logs','bin','obj','Debug','Release','x64','win-x64','.sass-cache','.parcel-cache','.next','.nuxt','.cache','.storybook','.zero/dynamic','.zero/artifacts','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.venv','env','envs','artifacts','build_output')
  $excludeDirsNormalized = $excludeDirs | ForEach-Object { ($_ -replace '\\','/').TrimEnd('/') }
  $dups = Get-ChildItem -LiteralPath $project -Recurse -Force -File |
    Where-Object {
      $rel = $_.FullName.Substring($project.Length + 1).Replace('\','/')
      if (Test-IsExcludedPath -relative $rel -excludedPaths $excludeDirsNormalized) { return $false }
      return $true
    } |
    Group-Object Name | Where-Object { $_.Count -gt 1 }
  "## Duplicados por nombre de archivo" | Out-File -LiteralPath $salida -Append -Encoding UTF8
  "Total: $($dups.Count)" | Out-File -LiteralPath $salida -Append -Encoding UTF8
  foreach ($g in $dups | Sort-Object Count -Descending) {
    "### $($g.Name)" | Out-File -LiteralPath $salida -Append -Encoding UTF8
    $g.Group | ForEach-Object {
      "- $($_.FullName.Substring($project.Length + 1).Replace('\','/'))" | Out-File -LiteralPath $salida -Append -Encoding UTF8
    }
    "" | Out-File -LiteralPath $salida -Append -Encoding UTF8
  }
}
Set-HeadlineNote -Path (Join-Path $artifactsDir 'conflictos.md') -NoteLine '> Nota: Este reporte enumera duplicados detectados automáticamente; úsalo como punto de partida antes de depurar manualmente.'
Write-Host ("[pipeline] conflictos completado en {0:N1}s" -f $sw.Elapsed.TotalSeconds)

# ===== Paso: scripts-health =====
Write-Host "[pipeline] Paso: scripts-health"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Check-Stop
$scriptsHealth = Join-Path $artifactsDir 'scripts-health.md'
"# Reporte de salud de scripts" | Out-File -LiteralPath $scriptsHealth -Encoding UTF8 -Force
"Generado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8

$scripts = Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' -File -Force | Sort-Object Name
"## Lista de scripts" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8
foreach ($s in $scripts) {
  $name = $s.Name
  $isCanonical = $canonicalScripts -contains $name
  $mark = if ($isCanonical) { '✔ canonical' } else { '⚠ extra' }
  "- $name - $mark" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8
}

$groups = $scripts | Group-Object { $_.BaseName.Split('-')[0] }
"`n## Familias (para inspección)" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8
foreach ($g in ($groups | Sort-Object Count -Descending)) {
  if ($g.Count -gt 1) {
    "### $($g.Name) (total: $($g.Count))" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8
    $g.Group | ForEach-Object { "  - $($_.Name)" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8 }
  }
}

"`n## Recomendaciones" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8
"- Mantener solo los canónicos: $($canonicalScripts -join ', ')" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8
"- Scripts experimentales → /.zero/dynamic/tools/experiments/<timestamp>/" | Out-File -LiteralPath $scriptsHealth -Append -Encoding UTF8
Set-HeadlineNote -Path (Join-Path $artifactsDir 'scripts-health.md') -NoteLine '> Nota: Este inventario describe los scripts disponibles en /.zero/scripts y su status para guiar automatizaciones.'
Write-Host ("[pipeline] scripts-health completado en {0:N1}s" -f $sw.Elapsed.TotalSeconds)

# ===== Paso: prompts-health =====
$promptsDir = Join-Path $zeroDir 'prompts'
if (Test-Path -LiteralPath $promptsDir) {
  Write-Host "[pipeline] Paso: prompts-health"
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $promptsHealth = Join-Path $artifactsDir 'prompts-health.md'
  "# Reporte de salud de prompts" | Out-File -LiteralPath $promptsHealth -Encoding UTF8 -Force
  "Generado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" | Out-File -LiteralPath $promptsHealth -Append -Encoding UTF8

  $promptFiles = Get-ChildItem -LiteralPath $promptsDir -Filter '*.md' -File -Force | Sort-Object Name
  $promptInfos = @()
  "## Lista de prompts" | Out-File -LiteralPath $promptsHealth -Append -Encoding UTF8
  foreach ($pf in $promptFiles) {
    $head = (Get-Content -LiteralPath $pf.FullName -TotalCount 5 -ErrorAction SilentlyContinue) -join "`n"
    $isCanonical = $false
    if ($head -match '<!--\s*@canonical\s+true\s*-->') { $isCanonical = $true }
    $mark = if ($isCanonical) { '✔ canonical' } else { '⚠ extra' }
    "- $($pf.Name) - $mark" | Out-File -LiteralPath $promptsHealth -Append -Encoding UTF8
    $promptInfos += [pscustomobject]@{ Name=$pf.Name; BaseName=$pf.BaseName; Canonical=$isCanonical }
  }

  function Get-Family([string]$base) {
    $b = $base -replace '\s+', ' '
    $parts = $b -split '[- ]'
    if ($parts.Count -gt 0) { return $parts[0].ToLowerInvariant() } else { return $b.ToLowerInvariant() }
  }

  "`n## Familias (posibles duplicados)" | Out-File -LiteralPath $promptsHealth -Append -Encoding UTF8
  $promptInfos | ForEach-Object { $_ | Add-Member -NotePropertyName Family -NotePropertyValue (Get-Family $_.BaseName) }
  $famGroups = $promptInfos | Group-Object Family | Sort-Object Count -Descending
  foreach ($fg in $famGroups) {
    if ($fg.Count -gt 1) {
      "### $($fg.Name) (total: $($fg.Count))" | Out-File -LiteralPath $promptsHealth -Append -Encoding UTF8
      foreach ($item in $fg.Group) {
        "  - $($item.Name) - $(if ($item.Canonical) { '✔' } else { '⚠' })" | Out-File -LiteralPath $promptsHealth -Append -Encoding UTF8
      }
    }
  }
  Set-HeadlineNote -Path (Join-Path $artifactsDir 'prompts-health.md') -NoteLine '> Nota: Resume los prompts disponibles y resalta cuáles son canónicos para facilitar la colaboración entre equipos.'
Write-Host ("[pipeline] prompts-health completado en {0:N1}s" -f $sw.Elapsed.TotalSeconds)
}

# ===== Catálogo =====
Write-Host "[pipeline] Paso: catálogo"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$catalog = Join-Path $artifactsDir 'catalog.md'
"# Catálogo .zero" | Out-File -LiteralPath $catalog -Encoding UTF8 -Force
"Generado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" | Out-File -LiteralPath $catalog -Append -Encoding UTF8
"## Scripts" | Out-File -LiteralPath $catalog -Append -Encoding UTF8
foreach ($s in $scripts) {
  $name = $s.Name
  $mark = if ($canonicalScripts -contains $name) { '✔ canonical' } else { '⚠ extra' }
  "- $name - $mark" | Out-File -LiteralPath $catalog -Append -Encoding UTF8
}
if ($promptInfos) {
  "`n## Prompts" | Out-File -LiteralPath $catalog -Append -Encoding UTF8
  foreach ($pi in $promptInfos | Sort-Object Name) {
    $mark = if ($pi.Canonical) { '✔ canonical' } else { '⚠ extra' }
    "- $($pi.Name) - $mark" | Out-File -LiteralPath $catalog -Append -Encoding UTF8
  }
}
Set-HeadlineNote -Path (Join-Path $artifactsDir 'catalog.md') -NoteLine '> Nota: Catálogo maestro de scripts y prompts .zero para que cualquiera identifique puntos de entrada rápidamente.'
Write-Host ("[pipeline] catálogo completado en {0:N1}s" -f $sw.Elapsed.TotalSeconds)

Write-Host "[pipeline] Artefactos actualizados en: $artifactsDir"

# ===== ZeroGraph Validation =====
if (-not $Fast) {
  $validation = Join-Path $PSScriptRoot 'zerograh-validation.ps1'
  if (Test-Path -LiteralPath $validation) {
    Write-Host "[pipeline] Paso: validación de ZeroGraph"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
      $validationResult = & $validation -AutoFix:$Deep -Quiet:$Fast
      if (-not $validationResult) {
        Write-Warning "[pipeline] ZeroGraph requiere revisión manual"
      }
    } catch {
      Write-Warning "[pipeline] Error en la validación de ZeroGraph: $($_.Exception.Message)"
    }
    Write-Host ("[pipeline] validación de ZeroGraph completada en {0:N1}s" -f $sw.Elapsed.TotalSeconds)
  }
}

# ===== Preflight opcional =====
if (-not $Fast) {
  $preflight = Join-Path $PSScriptRoot 'preflight-linter.ps1'
  if (Test-Path -LiteralPath $preflight) {
    Write-Host "[pipeline] Paso: preflight-linter"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $ok = Invoke-WithTimeout -Script { & $using:preflight } -TimeoutSec $StepTimeoutSec -Name 'preflight-linter'
    if (-not $ok) { Write-Warning "[pipeline] preflight-linter omitido por timeout" }
    Write-Host ("[pipeline] preflight-linter completado en {0:N1}s" -f $sw.Elapsed.TotalSeconds)
  }
}

# ===== Health consolidado =====
Write-Host "[pipeline] Paso: salud"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$healthUnified = Join-Path $artifactsDir 'health.md'
"# Salud .zero" | Out-File -LiteralPath $healthUnified -Encoding UTF8 -Force
"Generado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n" | Out-File -LiteralPath $healthUnified -Append -Encoding UTF8

function Add-Section($title, $file) {
  if (Test-Path -LiteralPath $file) {
    "## $title" | Out-File -LiteralPath $healthUnified -Append -Encoding UTF8
    "" | Out-File -LiteralPath $healthUnified -Append -Encoding UTF8
    Get-Content -LiteralPath $file -Raw | Out-File -LiteralPath $healthUnified -Append -Encoding UTF8
    "`n" | Out-File -LiteralPath $healthUnified -Append -Encoding UTF8
  }
}

Add-Section -title 'Conflictos' -file (Join-Path $artifactsDir 'conflictos.md')
Add-Section -title 'Salud de scripts' -file (Join-Path $artifactsDir 'scripts-health.md')
Add-Section -title 'Salud de prompts' -file (Join-Path $artifactsDir 'prompts-health.md')
Add-Section -title 'ZeroGraph' -file (Join-Path $artifactsDir 'ZeroGraph.json')
Add-Section -title 'Catálogo .zero' -file (Join-Path $artifactsDir 'catalog.md')
if (Test-Path -LiteralPath (Join-Path $artifactsDir 'zero-health.md')) {
  Add-Section -title 'Zero Health' -file (Join-Path $artifactsDir 'zero-health.md')
}
Set-HeadlineNote -Path (Join-Path $artifactsDir 'health.md') -NoteLine '> Nota: Consolida los reportes automáticos para obtener un estado general de CapiAgentes sin revisar cada archivo individual.'
Write-Host ("[pipeline] health generado en {0:N1}s" -f $sw.Elapsed.TotalSeconds)

Set-HeadlineNote -Path (Join-Path $artifactsDir 'zero-circuit-report.md') -NoteLine '> Nota: Informe integral del circuito .zero; combina frescura de artifacts, validaciones y ZeroGraph para decidir si es seguro avanzar.'
Write-Host "[pipeline] OK Completado"






























