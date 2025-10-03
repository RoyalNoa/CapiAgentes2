
<#
# @canonical true
# conflictos-final.ps1 - Análisis experto de duplicados y colisiones para CapiAgentes
# NO-BORRADO: solo lectura; escribe reporte en /.zero/artifacts/conflictos.md
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$artifactsDir = Join-Path $root '.zero/artifacts'
if (-not (Test-Path -LiteralPath $artifactsDir)) {
    New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
}
$salida = Join-Path $artifactsDir 'conflictos.md'

Write-Host "[conflictos] Inicio del análisis experto"

$carpetasExcluir = @(
    '.git','.vscode','.idea','.vs','node_modules','dist','build','coverage','tmp','logs','bin','obj','Debug','Release','x64','win-x64',
    '.sass-cache','.parcel-cache','.next','.nuxt','.cache','.storybook','.zero/dynamic','.zero/artifacts','__pycache__','.pytest_cache',
    '.mypy_cache','.ruff_cache','.venv','env','envs','artifacts','build_output'
)

$extensionesExcluir = @(
    '.env','.log','.ds_store','Thumbs.db','.lock','.swp','.bak','.tmp','.exe','.dll','.pdb','.iso','.msi',
    '.zip','.7z','.rar','.gz','.tar','.xz','.asar','.png','.jpg','.jpeg','.gif','.bmp','.ico','.svg',
    '.mp3','.wav','.mp4','.mov','.avi','.pdf','.sqlite','.db'
)

function Get-RelativePath([string]$fullPath) {
    return $fullPath.Substring($root.Length + 1).Replace("\", "/")
}

function DebeExcluir {
    param([string]$ruta)
    $rutaNorm = $ruta.Replace("\", "/")
    $base = [System.IO.Path]::GetFileName($rutaNorm)
    $ext = [System.IO.Path]::GetExtension($rutaNorm).ToLowerInvariant()
    foreach ($carpeta in $carpetasExcluir) {
        if ($rutaNorm -match "^$carpeta(/|$)") { return $true }
    }
    if ($base -like "~$*") { return $true }
    if ($base -ieq 'nul') { return $true }
    if ($ext -and ($extensionesExcluir -contains $ext)) { return $true }
    return $false
}

function Get-ProjectFiles {
    param([string[]]$Extensions)
    $files = @()
    Get-ChildItem -LiteralPath $root -Recurse -File -Force | ForEach-Object {
        $rel = Get-RelativePath -fullPath $_.FullName
        if (-not (DebeExcluir -ruta $rel)) {
            $ext = [System.IO.Path]::GetExtension($_.Name).ToLowerInvariant()
            if ($Extensions -contains $ext) { $files += $_.FullName }
        }
    }
    return $files
}

function Normalize-Code {
    param([string]$Text,[string]$Language)
    $norm = $Text
    switch ($Language) {
        'python' { $norm = [regex]::Replace($norm, '(?m)^\s*#.*$', '') }
        default {
            $norm = [regex]::Replace($norm, '/\*.*?\*/', '', 'Singleline')
            $norm = [regex]::Replace($norm, '(?m)//.*$', '')
        }
    }
    $norm = [regex]::Replace($norm, '\s+', ' ')
    return $norm.Trim()
}

function Get-StringHashSHA256 { param([string]$Text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $hashBytes = $sha.ComputeHash($bytes) } finally { $sha.Dispose() }
    return ([System.BitConverter]::ToString($hashBytes)).Replace('-', '')
}
function Extract-TypeScriptFunctions {
    param([string]$FilePath)
    $text = Get-Content -LiteralPath $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $text) { return @() }
    $results = @()
    $patterns = @(
        @{ Regex = '(?m)(?:export\s+)?function\s+([A-Za-z_$][\w$]*)\s*\([^\)]*\)\s*\{'; Kind = 'decl' },
        @{ Regex = '(?m)(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*function\s*\([^\)]*\)\s*\{'; Kind = 'expr' },
        @{ Regex = '(?m)(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*[^=]*=>\s*'; Kind = 'arrow' }
    )
    foreach ($p in $patterns) {
        $rx = [regex]::new($p.Regex)
        foreach ($m in $rx.Matches($text)) {
            $name = $m.Groups[1].Value
            $start = $m.Index
            $body = ''
            $braceIdx = $text.IndexOf('{', $m.Index)
            if ($braceIdx -ge 0 -and $braceIdx -lt ($m.Index + 400)) {
                $depth = 0
                for ($i = $braceIdx; $i -lt $text.Length; $i++) {
                    $ch = $text[$i]
                    if ($ch -eq '{') { $depth++ }
                    elseif ($ch -eq '}') {
                        $depth--
                        if ($depth -eq 0) { $body = $text.Substring($braceIdx, $i - $braceIdx + 1); break }
                    }
                }
            }
            if (-not $body -and $p.Kind -eq 'arrow') {
                $semi = $text.IndexOf(';', $m.Index)
                if ($semi -gt $m.Index) { $body = $text.Substring($m.Index, $semi - $m.Index + 1) }
            }
            if ($body) {
                $norm = Normalize-Code -Text $body -Language 'ts'
                $hash = Get-StringHashSHA256 -Text $norm
                $prefix = if ($start -gt 0) { $text.Substring(0, $start) } else { '' }
                $line = ($prefix -split "`n").Count
                $results += [pscustomobject]@{ File = $FilePath; Name = $name; Line = $line; Hash = $hash; Language = 'ts' }
            }
        }
    }
    return $results
}

function Extract-PythonFunctions {
    param([string]$FilePath)
    $text = Get-Content -LiteralPath $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $text) { return @() }
    $lines = $text -split "`n"
    $results = @()
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        if ($line -match '^(\s*)def\s+([A-Za-z_][\w]*)\s*\(') {
            $indent = $matches[1]
            $name = $matches[2]
            $bodyLines = @($line)
            for ($j = $i + 1; $j -lt $lines.Length; $j++) {
                $next = $lines[$j]
                if ([string]::IsNullOrWhiteSpace($next)) {
                    $bodyLines += $next
                    continue
                }
                $trimmed = $next.TrimStart()
                $currentIndent = $next.Substring(0, $next.Length - $trimmed.Length)
                if ($currentIndent.Length -le $indent.Length) { break }
                $bodyLines += $next
            }
            $body = [string]::Join("`n", $bodyLines)
            $norm = Normalize-Code -Text $body -Language 'python'
            $hash = Get-StringHashSHA256 -Text $norm
            $results += [pscustomobject]@{ File = $FilePath; Name = $name; Line = $i + 1; Hash = $hash; Language = 'python' }
        }
    }
    return $results
}

function Extract-MarkupIds {
    param([string]$FilePath)
    $text = Get-Content -LiteralPath $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $text) { return @() }
    $rx = [regex]::new('id\s*=\s*["''`]([^"''`]+)["''`]')
    $results = @()
    foreach ($m in $rx.Matches($text)) {
        $id = $m.Groups[1].Value
        $line = (($text.Substring(0, $m.Index)) -split "`n").Count
        $results += [pscustomobject]@{ File = $FilePath; Id = $id; Line = $line }
    }
    return $results
}

function Extract-FastApiRoutes {
    param([string]$FilePath)
    $text = Get-Content -LiteralPath $FilePath -Raw -ErrorAction SilentlyContinue
    if (-not $text) { return @() }
    $lines = $text -split "`n"
    $results = @()
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        if ($line -match '@[\w\.]*router\.(get|post|put|patch|delete)\s*\(\s*"([^"]+)"') {
            $verb = $matches[1].ToUpperInvariant()
            $path = $matches[2]
            $results += [pscustomobject]@{ File = $FilePath; Line = $i + 1; Verb = $verb; Path = $path }
        }
        elseif ($line -match '@app\.(get|post|put|patch|delete)\s*\(\s*"([^"]+)"') {
            $verb = $matches[1].ToUpperInvariant()
            $path = $matches[2]
            $results += [pscustomobject]@{ File = $FilePath; Line = $i + 1; Verb = $verb; Path = $path }
        }
    }
    return $results
}
try {
    $fecha = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "# Análisis Experto de Conflictos - CapiAgentes" | Out-File $salida -Force -Encoding UTF8
    "" | Out-File $salida -Append -Encoding UTF8
    "Generado: $fecha" | Out-File $salida -Append -Encoding UTF8
    "Proyecto: $root" | Out-File $salida -Append -Encoding UTF8
    "" | Out-File $salida -Append -Encoding UTF8

    $tsFiles = Get-ProjectFiles -Extensions @('.js','.mjs','.cjs','.ts','.tsx','.jsx')
    $pyFiles = Get-ProjectFiles -Extensions @('.py')
    $funcs = @()
    foreach ($f in $tsFiles) { $funcs += Extract-TypeScriptFunctions -FilePath $f }
    foreach ($f in $pyFiles) { $funcs += Extract-PythonFunctions -FilePath $f }

    $byName = $funcs | Group-Object -Property Name | Where-Object { $_.Count -gt 1 }
    "## Colisiones de nombres de función (Python/TypeScript)" | Out-File $salida -Append -Encoding UTF8
    "Total: $($byName.Count)" | Out-File $salida -Append -Encoding UTF8
    "" | Out-File $salida -Append -Encoding UTF8
    foreach ($g in $byName | Sort-Object Name) {
        "### $($g.Name)" | Out-File $salida -Append -Encoding UTF8
        foreach ($it in ($g.Group | Sort-Object Language, File, Line)) {
            $lang = $it.Language
            "- [$lang] $((Get-RelativePath -fullPath $it.File)) : línea $($it.Line)" | Out-File $salida -Append -Encoding UTF8
        }
        "" | Out-File $salida -Append -Encoding UTF8
    }

    $byHash = $funcs | Group-Object -Property Hash | Where-Object { $_.Count -gt 1 }
    $byHashDifferentName = @()
    foreach ($grp in $byHash) {
        $names = ($grp.Group | Select-Object -ExpandProperty Name | Sort-Object -Unique)
        if ($names.Count -gt 1) { $byHashDifferentName += $grp }
    }
    "## Implementaciones idénticas con distinto nombre" | Out-File $salida -Append -Encoding UTF8
    "Total: $($byHashDifferentName.Count)" | Out-File $salida -Append -Encoding UTF8
    "" | Out-File $salida -Append -Encoding UTF8
    foreach ($grp in $byHashDifferentName) {
        "### Hash: $($grp.Name)" | Out-File $salida -Append -Encoding UTF8
        foreach ($it in ($grp.Group | Sort-Object Name, File, Line)) {
            "- [$($it.Language)] $($it.Name) @ $((Get-RelativePath -fullPath $it.File)) : línea $($it.Line)" | Out-File $salida -Append -Encoding UTF8
        }
        "" | Out-File $salida -Append -Encoding UTF8
    }

    $markupFiles = Get-ProjectFiles -Extensions @('.html','.htm','.tsx','.jsx')
    $idsDom = @(); foreach ($f in $markupFiles) { $idsDom += Extract-MarkupIds -FilePath $f }
    $byId = $idsDom | Group-Object -Property Id | Where-Object { $_.Count -gt 1 }
    "## IDs de DOM duplicados" | Out-File $salida -Append -Encoding UTF8
    "Total: $($byId.Count)" | Out-File $salida -Append -Encoding UTF8
    "" | Out-File $salida -Append -Encoding UTF8
    foreach ($g in $byId | Sort-Object Name) {
        "### id: $($g.Name)" | Out-File $salida -Append -Encoding UTF8
        foreach ($loc in ($g.Group | Sort-Object File, Line)) {
            "- $((Get-RelativePath -fullPath $loc.File)) : línea $($loc.Line)" | Out-File $salida -Append -Encoding UTF8
        }
        "" | Out-File $salida -Append -Encoding UTF8
    }

    $routeFiles = $pyFiles | Where-Object { $_ -match 'Backend\\src\\api' -or $_ -match 'Backend\\src\\presentation' }
    $routes = @(); foreach ($f in $routeFiles) { $routes += Extract-FastApiRoutes -FilePath $f }
    $routeGroups = $routes | Group-Object { "{0} {1}" -f $_.Verb, $_.Path } | Where-Object { $_.Count -gt 1 }
    "## Duplicados de rutas FastAPI" | Out-File $salida -Append -Encoding UTF8
    "Total: $($routeGroups.Count)" | Out-File $salida -Append -Encoding UTF8
    "" | Out-File $salida -Append -Encoding UTF8
    foreach ($grp in $routeGroups | Sort-Object Name) {
        "### $($grp.Name)" | Out-File $salida -Append -Encoding UTF8
        foreach ($loc in ($grp.Group | Sort-Object File, Line)) {
            "- $((Get-RelativePath -fullPath $loc.File)) : línea $($loc.Line)" | Out-File $salida -Append -Encoding UTF8
        }
        "" | Out-File $salida -Append -Encoding UTF8
    }

    if ($erroresHash.Count -gt 0) {
        "## Notas" | Out-File $salida -Append -Encoding UTF8
        foreach ($e in $erroresHash) { "- $e" | Out-File $salida -Append -Encoding UTF8 }
        "" | Out-File $salida -Append -Encoding UTF8
    }

    # ================= Agentes & Config =================
    $agentsConfigPath = Join-Path $root 'Backend/ia_workspace/data/agents_config.json'
    $agentsRegistryPath = Join-Path $root 'Backend/ia_workspace/data/agents_registry.json'
    $agentPrivilegesPath = Join-Path $root 'Backend/ia_workspace/data/agent_privileges.json'

    "## Configuración de agentes" | Out-File $salida -Append -Encoding UTF8
    if (Test-Path -LiteralPath $agentsConfigPath) {
        $config = Get-Content -LiteralPath $agentsConfigPath -Raw | ConvertFrom-Json
        $disabled = $config.PSObject.Properties | Where-Object { -not $_.Value } | ForEach-Object { $_.Name }
        "- Archivo: Backend/ia_workspace/data/agents_config.json" | Out-File $salida -Append -Encoding UTF8
        "- Agentes deshabilitados: $((if ($disabled) { $disabled -join ', ' } else { 'ninguno' }))" | Out-File $salida -Append -Encoding UTF8
    } else {
        "- agents_config.json no encontrado" | Out-File $salida -Append -Encoding UTF8
    }

    if (Test-Path -LiteralPath $agentsRegistryPath) {
        $registry = Get-Content -LiteralPath $agentsRegistryPath -Raw | ConvertFrom-Json
        $duplicateNames = $registry.PSObject.Properties | Group-Object Name | Where-Object { $_.Count -gt 1 }
        $missingHandlers = @()
        foreach ($agent in $registry.PSObject.Properties) {
            $handlerPath = $agent.Value.metadata.agent_class_path
            if (-not $handlerPath) { $missingHandlers += $agent.Name }
        }
        "- Duplicados en registry: $((if ($duplicateNames){$duplicateNames.Count}else{0}))" | Out-File $salida -Append -Encoding UTF8
        if ($missingHandlers.Count -gt 0) {
            "- Agentes sin handler declarado: $($missingHandlers -join ', ')" | Out-File $salida -Append -Encoding UTF8
        }
    } else {
        "- agents_registry.json no encontrado" | Out-File $salida -Append -Encoding UTF8
    }

    if (Test-Path -LiteralPath $agentPrivilegesPath) {
        $privileges = Get-Content -LiteralPath $agentPrivilegesPath -Raw | ConvertFrom-Json
        $missingAssignments = @()
        $agentsDir = Join-Path $root 'Backend/ia_workspace/agentes'
        if (Test-Path -LiteralPath $agentsDir) {
            $agentDirs = Get-ChildItem -LiteralPath $agentsDir -Directory -Force
            foreach ($dir in $agentDirs) {
                if (-not $privileges.agent_assignments.PSObject.Properties.Name.Contains($dir.Name)) {
                    $missingAssignments += $dir.Name
                }
            }
        }
        "- Asignaciones de privilegios faltantes: $((if ($missingAssignments){$missingAssignments -join ', ' } else { 'ninguna' }))" | Out-File $salida -Append -Encoding UTF8
    }

    "" | Out-File $salida -Append -Encoding UTF8
    "## Resumen" | Out-File $salida -Append -Encoding UTF8
    "- Colisiones de funciones: $($byName.Count)" | Out-File $salida -Append -Encoding UTF8
    "- Implementaciones idénticas: $($byHashDifferentName.Count)" | Out-File $salida -Append -Encoding UTF8
    "- IDs DOM duplicados: $($byId.Count)" | Out-File $salida -Append -Encoding UTF8
    "- Rutas duplicadas: $($routeGroups.Count)" | Out-File $salida -Append -Encoding UTF8

    Write-Host "[conflictos] reporte generado en: $salida"

} catch {
    Write-Host "[conflictos] Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}


