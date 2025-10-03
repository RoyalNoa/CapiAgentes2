param(
    [string]$Date = (Get-Date).ToString('yyyy-MM-dd')
)

# Registro de cambios para .zero/dynamic
# - Clasifica ALTAS (creados hoy), MODIFICACIONES (modificados hoy) y BAJAS (movidos a papelera hoy) (creados hoy), MODIFICACIONES (modificados hoy), BAJAS (movidos a papelera hoy)
# - Extrae scripts/comandos de sesiones del día
# - Genera:
#   1) .zero/dynamic/sessions/YYYY-MM/DD-change-log.md
#   2) .zero/dynamic/analysis/zerograph-delta-YYYY-MM-DD.json

$ErrorActionPreference = 'Stop'

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

# Directorios base
$root = (Get-Location).Path
$dynamicRoot = Join-Path $root '.zero/dynamic'
$papeleraDir = Join-Path $dynamicRoot 'papelera'
$analysisDir = Join-Path $dynamicRoot 'analysis'
$toolsDir = Join-Path $dynamicRoot 'tools'
$proposalsDir = Join-Path $dynamicRoot 'proposals'

# Fecha y rangos
try {
    $start = Get-Date ("$Date 00:00:00")
} catch {
    throw "Fecha inválida. Use formato yyyy-MM-dd. Valor: '$Date'"
}
$end = $start.AddDays(1)
$year = $start.ToString('yyyy')
$month = $start.ToString('MM')
$day = $start.ToString('dd')

# Sesiones destino
$sessionsMonthDir = Join-Path $dynamicRoot (Join-Path 'sessions' ("$year-$month"))
$changeLogPath = Join-Path $sessionsMonthDir ("$day-change-log.md")

# Asegurar carpetas
Ensure-Directory $dynamicRoot
Ensure-Directory $papeleraDir
Ensure-Directory $analysisDir
Ensure-Directory $toolsDir
Ensure-Directory $proposalsDir
Ensure-Directory $sessionsMonthDir

Write-Host "[change-logger] Escaneando cambios para $Date" -ForegroundColor Cyan

# Helper: obtener ruta relativa desde repo root
function To-Relative([string]$path) {
    $p = [System.IO.Path]::GetFullPath($path)
    $r = [System.IO.Path]::GetFullPath($root)
    if ($p.StartsWith($r)) { return $p.Substring($r.Length).TrimStart('\','/') } else { return $path }
}

# 1) Altas (creados hoy) en dynamic
$altas = Get-ChildItem -LiteralPath $dynamicRoot -Recurse -File -Force |
    Where-Object { $_.CreationTime -ge $start -and $_.CreationTime -lt $end } |
    Sort-Object FullName |
    ForEach-Object { To-Relative $_.FullName }

# 2) Modificaciones (modificados hoy, pero creados antes de hoy)
$mods = Get-ChildItem -LiteralPath $dynamicRoot -Recurse -File -Force |
    Where-Object { $_.LastWriteTime -ge $start -and $_.LastWriteTime -lt $end -and $_.CreationTime -lt $start } |
    Sort-Object FullName |
    ForEach-Object { To-Relative $_.FullName }

# 3) Bajas (movidos a papelera hoy): tomamos entradas bajo papelera creadas hoy
$bajas = @()
if (Test-Path -LiteralPath $papeleraDir) {
    $bajas = Get-ChildItem -LiteralPath $papeleraDir -Force |
        Where-Object { $_.CreationTime -ge $start -and $_.CreationTime -lt $end } |
        Sort-Object FullName |
        ForEach-Object { To-Relative $_.FullName }
}

# 4) Scripts ejecutados (sesiones del día): buscar .ps1 y comandos pwsh en sesiones YYYY-MM/DD-*.md
$scripts = @()
$cmds = @()
$sessionFiles = Get-ChildItem -LiteralPath $sessionsMonthDir -File -Filter ("$day-*.md") -ErrorAction SilentlyContinue
foreach ($sf in $sessionFiles) {
    $lines = Get-Content -LiteralPath $sf.FullName -ErrorAction SilentlyContinue
    foreach ($ln in $lines) {
        if ($ln -match '\\w+\.ps1\b') { $scripts += ($ln | Select-String -Pattern '\\w+\.ps1\b' -AllMatches).Matches.Value }
        if ($ln -match '^```pwsh' -or $ln -match '^pwsh ' -or $ln -match '^Set-Location ' -or $ln -match '\\pipeline\.ps1' ) { $cmds += $ln }
    }
}
$scripts = $scripts | Sort-Object -Unique
$cmds = $cmds | Sort-Object -Unique

# 5) Propuestas de parches (creadas o modificadas hoy)
$patchesInfo = @()
$patchRoot = Join-Path $proposalsDir 'patches'
if (Test-Path -LiteralPath $patchRoot) {
    $patchFiles = Get-ChildItem -LiteralPath $patchRoot -Recurse -File -Filter '*.patch' -Force -ErrorAction SilentlyContinue |
        Where-Object { ($_.CreationTime -ge $start -and $_.CreationTime -lt $end) -or ($_.LastWriteTime -ge $start -and $_.LastWriteTime -lt $end) } |
        Sort-Object FullName

    foreach ($pf in $patchFiles) {
        $content = Get-Content -LiteralPath $pf.FullName -ErrorAction SilentlyContinue
        $adds = 0; $dels = 0
        foreach ($line in $content) {
            if ($line -match '^\+[^\+]' ) { $adds++ }
            if ($line -match '^-[^-]' ) { $dels++ }
        }
        $pdir = Split-Path -Parent $pf.FullName
        $manifest = Join-Path $pdir 'manifest.json'
        $tests = Join-Path $pdir 'tests.md'
        $rollback = Join-Path $pdir 'rollback.md'
        $item = [ordered]@{
            patch = (To-Relative $pf.FullName)
            created = $pf.CreationTime.ToString('s')
            modified = $pf.LastWriteTime.ToString('s')
            addedLines = $adds
            removedLines = $dels
            manifest = (if (Test-Path -LiteralPath $manifest) { To-Relative $manifest } else { $null })
            tests = (if (Test-Path -LiteralPath $tests) { To-Relative $tests } else { $null })
            rollback = (if (Test-Path -LiteralPath $rollback) { To-Relative $rollback } else { $null })
        }
        $patchesInfo += [pscustomobject]$item
    }
}

# 6) Construir ZeroGraph delta mínimo
$delta = [ordered]@{
    date = $Date
    filesAdded = $altas
    filesModified = $mods
    filesRemoved = $bajas
    scripts = $scripts
    commands = $cmds
    patches = $patchesInfo
}

$deltaPath = Join-Path $analysisDir ("zerograph-delta-$Date.json")
$delta | ConvertTo-Json -Depth 6 | Out-File -FilePath $deltaPath -Encoding UTF8

# 6) Generar Change Log Markdown
$sb = New-Object System.Text.StringBuilder
$null = $sb.AppendLine("# Registro de Cambios IA - $Date")
$null = $sb.AppendLine()
$null = $sb.AppendLine("Generado por .zero/dynamic/tools/change-logger.ps1")
$null = $sb.AppendLine()
$null = $sb.AppendLine("## Resumen")
$null = $sb.AppendLine("- Altas: " + ($altas.Count))
$null = $sb.AppendLine("- Modificaciones: " + ($mods.Count))
$null = $sb.AppendLine("- Bajas (papelera): " + ($bajas.Count))
$null = $sb.AppendLine()
$null = $sb.AppendLine("## Altas (creados hoy)")
if ($altas.Count -eq 0) {
    $null = $sb.AppendLine("- (ninguna)")
} else {
    $altas | ForEach-Object {
        $null = $sb.AppendLine("- $($_)")
    }
}
$null = $sb.AppendLine()
$null = $sb.AppendLine("## Modificaciones (modificados hoy)")
if ($mods.Count -eq 0) {
    $null = $sb.AppendLine("- (ninguna)")
} else {
    $mods | ForEach-Object {
        $null = $sb.AppendLine("- $($_)")
    }
}
$null = $sb.AppendLine()
$null = $sb.AppendLine("## Bajas (movidos a papelera hoy)")
if ($bajas.Count -eq 0) {
    $null = $sb.AppendLine("- (ninguna)")
} else {
    $bajas | ForEach-Object {
        $null = $sb.AppendLine("- $($_)")
    }
}
$null = $sb.AppendLine()
$null = $sb.AppendLine("## Scripts ejecutados (detectados en sesiones)")
if ($scripts.Count -eq 0) {
    $null = $sb.AppendLine("- (no detectados)")
} else {
    $scripts | ForEach-Object {
        $null = $sb.AppendLine("- $($_)")
    }
}
$null = $sb.AppendLine()
$null = $sb.AppendLine("## Comandos capturados")
if ($cmds.Count -eq 0) {
    $null = $sb.AppendLine("```")
    $null = $sb.AppendLine("(no detectados)")
    $null = $sb.AppendLine("```")
} else {
    $null = $sb.AppendLine("```pwsh")
    $cmds | ForEach-Object { $null = $sb.AppendLine($_) }
    $null = $sb.AppendLine("```")
}
$null = $sb.AppendLine()
    $null = $sb.AppendLine("## Propuestas de parches (hoy)")
    if ($patchesInfo.Count -eq 0) {
        $null = $sb.AppendLine("- (ninguna)")
    } else {
        foreach ($p in $patchesInfo) {
            $null = $sb.AppendLine("- ``$($p.patch)`` (+$($p.addedLines) / -$($p.removedLines))")
            if ($p.manifest -or $p.tests -or $p.rollback) {
                $null = $sb.AppendLine("  - manifest: ``$($p.manifest)``")
                $null = $sb.AppendLine("  - tests: ``$($p.tests)``")
                $null = $sb.AppendLine("  - rollback: ``$($p.rollback)``")
            }
        }
    }
    $null = $sb.AppendLine()
$null = $sb.AppendLine("## Próximos pasos (ZeroGraph)")
$null = $sb.AppendLine("- Revisar `/.zero/artifacts/ZeroGraph.json` y aplicar delta en `/.zero/dynamic/analysis/zerograph-delta-$Date.json`.\n- Si hay cambios estructurales de código, preparar parches en `/.zero/dynamic/proposals/patches/`.\n- Validar duplicados/colisiones en `/.zero/artifacts/conflictos.md`.\n")

$sb.ToString() | Out-File -FilePath $changeLogPath -Encoding UTF8

Write-Host "[change-logger] Log generado:" (To-Relative $changeLogPath) -ForegroundColor Green
Write-Host "[change-logger] Delta ZeroGraph:" (To-Relative $deltaPath) -ForegroundColor Green

