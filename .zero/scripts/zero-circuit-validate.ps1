<#
=================================
zero-circuit-validate.ps1 — Verifica si el circuito completo de  .zero fue aplicado

Qué hace:
- (Opcional) Ejecuta el pipeline  .zero (rápido o profundo)
- Verifica existencia y frescura de artifacts (vs último cambio de código o -Since)
- Ejecuta validación de ZeroGraph y parsea conflictos
- Genera reporte unificado en / .zero/artifacts/zero-circuit-report.md
- Devuelve código de salida 0 (OK) / 1 (FALLA)

Uso rápido:
  pwsh -NoProfile -ExecutionPolicy Bypass -File " .zero/scripts/zero-circuit-validate.ps1"

Parámetros útiles:
  -Deep            Validación profunda (y pipeline profundo)
  -AutoFix         Permite autocorrección en ZeroGraph (si aplica)
  -NoRunPipeline   No ejecutar pipeline (solo validar artifacts existentes)
  -Since <DateTime>Forzar fecha pivote de comparación
  -MaxSkewMinutes N Tolerancia de desfase al comparar timestamps (por defecto 5)
  -ChangeTag "XYZ" Tag para buscar en sesiones/analysis (opcional)
  -Quiet           Salida mínima
=================================
#>

param(
  [switch]$Deep,
  [switch]$AutoFix,
  [switch]$NoRunPipeline,
  [datetime]$Since,
  [int]$MaxSkewMinutes = 5,
  [string]$ChangeTag,
  [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$zeroDir = Split-Path -Parent $PSScriptRoot
$project = Split-Path -Parent $zeroDir
$artifactsDir = Join-Path $zeroDir 'artifacts'
if (-not (Test-Path -LiteralPath $artifactsDir)) { New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null }
$reportFile = Join-Path $artifactsDir 'zero-circuit-report.md'

function Write-Info($msg){ if (-not $Quiet) { Write-Host $msg -ForegroundColor Cyan } }
function Write-Ok($msg){ if (-not $Quiet) { Write-Host $msg -ForegroundColor Green } }
function Write-Warn($msg){ if (-not $Quiet) { Write-Warning $msg } }
function Write-Err($msg){ if (-not $Quiet) { Write-Host $msg -ForegroundColor Red } }

Write-Info "[zero-circuit] Inicio de validación del circuito  .zero"

# 1) Determinar fecha pivote de comparación
Write-Info "[zero-circuit] Resolviendo fecha pivote para frescura"
if ($Since) {
  $pivotTime = $Since
  Write-Info "[zero-circuit] Usando -Since: $($pivotTime.ToString('yyyy-MM-dd HH:mm:ss'))"
} else {
  # Buscar cambios de código relevantes (excluyendo dinámicos y artifacts)
  $codeFiles = Get-ChildItem -LiteralPath $project -Recurse -File -Force |
    Where-Object {
      $_.Extension.ToLowerInvariant() -in @('.js','.ts','.tsx','.jsx','.py','.json','.md','.ps1','.yml','.yaml','.html') -and
      $_.FullName -notmatch "\\\\ .zero\\\\(dynamic|artifacts)" -and
      $_.FullName -notmatch "node_modules" -and
      $_.FullName -notmatch "\\\\build\\\\" -and
      $_.FullName -notmatch "\\\\dist\\\\"
    }
  if ($codeFiles.Count -gt 0) {
    $pivotTime = ($codeFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime
  } else {
    $pivotTime = Get-Date
    Write-Warn "[zero-circuit] No se hallaron archivos de código; usando ahora() como pivote"
  }
  Write-Info ("[zero-circuit] Último cambio de código: {0}" -f $pivotTime.ToString('yyyy-MM-dd HH:mm:ss'))
}

# 2) (Opcional) Ejecutar pipeline
if (-not $NoRunPipeline) {
  $pipeline = Join-Path $PSScriptRoot 'pipeline.ps1'
  if (Test-Path -LiteralPath $pipeline) {
    try {
      Write-Info "[zero-circuit] Ejecutando pipeline ($([string]::Copy((if($Deep){'Deep'}else{'Fast'}))))"
      if ($Deep) {
        & $pipeline -Deep -StepTimeoutSec 60 | Out-Null
      } else {
        & $pipeline -Fast | Out-Null
      }
      Write-Ok "[zero-circuit] Pipeline ejecutado"
    } catch {
      Write-Warn "[zero-circuit] Error ejecutando pipeline: $($_.Exception.Message)"
    }
  } else {
    Write-Warn "[zero-circuit] pipeline.ps1 no encontrado; se continúa con validación de artifacts"
  }
}

# 3) Verificar artifacts requeridos
$required = @(
  'estructura.txt',
  'conflictos.md',
  'scripts-health.md',
  'catalog.md',
  'health.md',
  'ZeroGraph.json'
)

# prompts-health.md es requerido solo si existe carpeta prompts
$promptsDir = Join-Path $zeroDir 'prompts'
if (Test-Path -LiteralPath $promptsDir) { $required += 'prompts-health.md' }

# zero-health.md es opcional (si corre preflight-linter en modo Deep)
$optional = @('zero-health.md')

$results = @()
$failed = $false
$skew = [TimeSpan]::FromMinutes($MaxSkewMinutes)

foreach ($name in $required) {
  $path = Join-Path $artifactsDir $name
  $exists = Test-Path -LiteralPath $path
  $fresh = $false
  $ageInfo = ''
  if ($exists) {
    $t = (Get-Item -LiteralPath $path).LastWriteTime
    $fresh = ($t + $skew) -ge $pivotTime
    $ageInfo = ('{0:yyyy-MM-dd HH:mm:ss}' -f $t)
  }
  if (-not $exists -or -not $fresh) { $failed = $true }
  $results += [pscustomobject]@{ Name=$name; Path=$path; Exists=$exists; Fresh=$fresh; Time=$ageInfo }
}

foreach ($name in $optional) {
  $path = Join-Path $artifactsDir $name
  if (Test-Path -LiteralPath $path) {
    $t = (Get-Item -LiteralPath $path).LastWriteTime
    $fresh = ($t + $skew) -ge $pivotTime
    $results += [pscustomobject]@{ Name=$name; Path=$path; Exists=$true; Fresh=$fresh; Time=("{0:yyyy-MM-dd HH:mm:ss}" -f $t) }
  }
}

# 4) Validación de ZeroGraph
$zerograh = Join-Path $PSScriptRoot 'zerograh-validation.ps1'
$zerograhOk = $false
if (Test-Path -LiteralPath $zerograh) {
  try {
    $zerograhOk = & $zerograh -Deep:$Deep -AutoFix:$AutoFix -Quiet:$Quiet
    if (-not $zerograhOk) { $failed = $true }
  } catch {
    $failed = $true
    Write-Warn "[zero-circuit] Error ejecutando zerograh-validation: $($_.Exception.Message)"
  }
} else {
  Write-Warn "[zero-circuit] zerograh-validation.ps1 no encontrado"
}

# 5) Parsear conflictos.md para duplicados
$confPath = Join-Path $artifactsDir 'conflictos.md'
$dupCount = $null
if (Test-Path -LiteralPath $confPath) {
  try {
    $content = Get-Content -LiteralPath $confPath -Raw
    # Buscar línea "Total: X" (formato de pipeline rápido)
    $m = [regex]::Match($content, "(?mi)^Total:\s*(\d+)")
    if ($m.Success) {
      $dupCount = [int]$m.Groups[1].Value
      if ($dupCount -gt 0) { $failed = $true }
    } else {
      # Si no hay línea Total, no forzar fallo pero dejar aviso
      Write-Warn "[zero-circuit] No se encontró 'Total:' en conflictos.md; no se evaluará duplicados"
    }
  } catch {
    Write-Warn "[zero-circuit] No se pudo parsear conflictos.md: $($_.Exception.Message)"
  }
}

# 6) Chequeo de sesiones/analysis con ChangeTag (opcional)
$sessionsOk = $true
if ($ChangeTag) {
  $dynamicDir = Join-Path $zeroDir 'dynamic'
  $sinceTime = $pivotTime
  $hits = @()
  if (Test-Path -LiteralPath $dynamicDir) {
    $hits = Get-ChildItem -LiteralPath $dynamicDir -Recurse -File -Force |
      Where-Object { $_.LastWriteTime -ge $sinceTime } |
      Where-Object { try { Select-String -LiteralPath $_.FullName -Pattern $ChangeTag -Quiet -ErrorAction Stop } catch { $false } }
  }
  if ($hits.Count -lt 1) {
    $sessionsOk = $false
    # No marca fallo duro, pero sí advertencia (según políticas dinámicas no-obligatorio)
  }
  # (Opcional) hint de sesiones omitido en reporte para mantener salida mínima
}

# 7) Generar reporte
"#  .zero Circuit Validation" | Out-File -LiteralPath $reportFile -Encoding UTF8 -Force
('Generado: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
"" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
"## Resumen" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
if ($Deep) { $modeText = 'Deep' } else { $modeText = 'Fast' }
('- Modo: {0}' -f $modeText) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
('- Pivote: {0} (MaxSkew: {1}m)' -f ($pivotTime.ToString('yyyy-MM-dd HH:mm:ss')), $MaxSkewMinutes) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
if ($ChangeTag) { ('- ChangeTag: {0}' -f $ChangeTag) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8 }
if ($zerograhOk) { $zgText = 'OK' } else { $zgText = 'FALLA' }
('- ZeroGraph: {0}' -f $zgText) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
if ($null -ne $dupCount) { ('- Duplicados: {0}' -f $dupCount) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8 }
if ($ChangeTag) {
  $sessStatus = if ($sessionsOk) { 'sugerido presente / OK' } else { 'sin evidencia con tag' }
  ('- Sesiones/Analysis: {0}' -f $sessStatus) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
}
if (-not $failed) { $resultText = 'PASS' } else { $resultText = 'FAIL' }
('- Resultado: {0}' -f $resultText) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8

"`n## Artifacts" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
foreach ($r in $results) {
  if (-not $r.Exists) { $status = 'NO-EXISTE' }
  elseif (-not $r.Fresh) { $status = 'STALE' }
  else { $status = 'OK' }
  ('- {0}: {1} (ts={2})' -f $r.Name, $status, $r.Time) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
}

if ($optional.Count -gt 0) {
  "`n### Opcionales detectados" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
  foreach ($name in $optional) {
    $path = Join-Path $artifactsDir $name
    if (Test-Path -LiteralPath $path) {
      $t = (Get-Item -LiteralPath $path).LastWriteTime
  $fresh = ($t + $skew) -ge $pivotTime
  if ($fresh) { $status = 'OK' } else { $status = 'STALE' }
      $ts = Get-Date -Date $t -Format 'yyyy-MM-dd HH:mm:ss'
      ('- {0}: {1} (ts={2})' -f $name, $status, $ts) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
    } else {
      ('- {0}: no generado' -f $name) | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
    }
  }
}

"`n## Recomendaciones" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
if ($failed) {
  "- Ejecutar pipeline en modo Deep: .\\ .zero\\scripts\\pipeline.ps1 -Deep" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
  "- Validar y/o regenerar ZeroGraph: .\\ .zero\\scripts\\zerograh-validation.ps1 -Deep -AutoFix" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
  if ($dupCount -gt 0) { "- Resolver duplicados reportados en conflictos.md (Total: $dupCount)" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8 }
  if ($ChangeTag -and -not $sessionsOk) { "- Registrar sesión/analysis con tag '$ChangeTag' en / .zero/dynamic/**" | Out-File -LiteralPath $reportFile -Append -Encoding UTF8 }
} else {
  "- Circuito  .zero aplicado correctamente. Mantener rutina post-cambio: pipeline Deep + validación." | Out-File -LiteralPath $reportFile -Append -Encoding UTF8
}

Write-Info "[zero-circuit] Reporte: $reportFile"

if ($failed) { exit 1 } else { exit 0 }


