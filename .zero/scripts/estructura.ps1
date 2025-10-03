
<#
# @canonical true
# estructura.ps1 - Genera artifacts de estructura y conflictos para CapiAgentes
# NO-BORRADO: solo escribe en /.zero/artifacts/
#>
param(
    [switch]$Deep
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$zeroDir = Split-Path -Parent $PSScriptRoot
$project = Split-Path -Parent $zeroDir
$artifactsDir = Join-Path $zeroDir 'artifacts'
if (-not (Test-Path -LiteralPath $artifactsDir)) {
    New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null
}

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

$carpetasExcluirNormalized = $carpetasExcluir | ForEach-Object { ($_ -replace '\\','/').TrimEnd('/') }

function Get-RelativePath([string]$fullPath) {
    return $fullPath.Substring($project.Length + 1).Replace("\", "/")
}

# NOTA: No permitir que artefactos incluyan carpetas de dependencias o builds. Mantener esta lista sincronizada con pipeline.ps1.
function ShouldSkip {
    param([string]$relativePath,[bool]$isDirectory)
    $normalized = $relativePath.Replace('\\','/').Trim()
    if ($isDirectory -and $normalized -notlike '*/') { $normalized += '/' }
    $trimmed = $normalized.TrimEnd('/')
    if (-not $trimmed) { return $false }
    foreach ($dir in $carpetasExcluirNormalized) {
        $pattern = '(^|/)' + [regex]::Escape($dir) + '(/|$)'
        if ($trimmed -match $pattern) { return $true }
    }
    if (-not $isDirectory) {
        $ext = [System.IO.Path]::GetExtension($trimmed).ToLowerInvariant()
        if ($ext -and ($extensionesExcluir -contains $ext)) { return $true }
    }
    if ($trimmed -like '**/~$*' -or $trimmed -like '*nul') { return $true }
    return $false
}

$allFiles = New-Object System.Collections.Generic.List[string]
$archivosPorNombre = @{}
$archivosPorHash = @{}
$erroresHash = @()
$maxHashMB = 50
$maxHashBytes = $maxHashMB * 1MB

function Collect-ProjectItems {
    param([string]$rootPath)
    $stack = New-Object System.Collections.Generic.Stack[System.IO.DirectoryInfo]
    $stack.Push((Get-Item -LiteralPath $rootPath))
    while ($stack.Count -gt 0) {
        $dir = $stack.Pop()
        $children = Get-ChildItem -LiteralPath $dir.FullName -Force | Sort-Object { !$_.PSIsContainer }, Name
        foreach ($item in $children) {
            $relative = Get-RelativePath -fullPath $item.FullName
            if (ShouldSkip -relativePath $relative -isDirectory:$item.PSIsContainer) { continue }
            if ($item.PSIsContainer) {
                $stack.Push($item)
            } else {
                $allFiles.Add($relative) | Out-Null
                if ($archivosPorNombre.ContainsKey($item.Name)) {
                    $archivosPorNombre[$item.Name] += @($relative)
                } else {
                    $archivosPorNombre[$item.Name] = @($relative)
                }
                try {
                    if ($item.Length -le $maxHashBytes) {
                        $hash = (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256 -ErrorAction Stop).Hash
                        if ($archivosPorHash.ContainsKey($hash)) {
                            $archivosPorHash[$hash] += @($relative)
                        } else {
                            $archivosPorHash[$hash] = @($relative)
                        }
                    } else {
                        $erroresHash += "Omitido por tamaño (> $maxHashMB MB): $relative"
                    }
                } catch {
                    $erroresHash += "Error hash en ${relative}: $($_.Exception.Message)"
                }
            }
        }
    }
}

function Write-Tree {
    param([string]$rootPath,[string]$outputPath)
    $writer = New-Object System.Text.StringBuilder
    [void]$writer.AppendLine('# Árbol de CapiAgentes (excluye dependencias y builds)')
    function RecurseTree {
        param([string]$currentPath,[int]$depth)
        $children = Get-ChildItem -LiteralPath $currentPath -Force | Sort-Object { !$_.PSIsContainer }, Name
        foreach ($child in $children) {
            $rel = Get-RelativePath -fullPath $child.FullName
            if (ShouldSkip -relativePath $rel -isDirectory:$child.PSIsContainer) { continue }
            $indent = '|' + ('   |' * $depth)
            if ($child.PSIsContainer) {
                [void]$writer.AppendLine("$indent-- $($child.Name)/")
                RecurseTree -currentPath $child.FullName -depth ($depth + 1)
            } else {
                [void]$writer.AppendLine("$indent-- $($child.Name)")
            }
        }
    }
    [void]$writer.AppendLine("$((Split-Path -Leaf $rootPath))/")
    RecurseTree -currentPath $rootPath -depth 0
    $writer.ToString() | Out-File -LiteralPath $outputPath -Encoding UTF8 -Force
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

function Get-StringHashSHA256 {
    param([string]$Text)
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
$out = Join-Path $artifactsDir 'estructura.txt'

Collect-ProjectItems -rootPath $project

if (-not $Deep) {
    Write-Tree -rootPath $project -outputPath $out
    Write-Host "[estructura] generado: $out"
    return
}

Write-Tree -rootPath $project -outputPath $out
Write-Host "[estructura] generado: $out"

$archivoConflictos = Join-Path $artifactsDir 'conflictos.md'
$fecha = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"# Posibles conflictos" | Out-File $archivoConflictos -Force -Encoding UTF8`n"> Nota: Usa este resumen para identificar duplicados o definiciones repetidas antes de depurar manualmente." | Out-File $archivoConflictos -Append -Encoding UTF8`n"" | Out-File $archivoConflictos -Append -Encoding UTF8
"Generado: $fecha" | Out-File $archivoConflictos -Append -Encoding UTF8
"Raíz: $project" | Out-File $archivoConflictos -Append -Encoding UTF8
"" | Out-File $archivoConflictos -Append -Encoding UTF8

$tsFiles = $allFiles | Where-Object { $_ -match '\.(js|mjs|cjs|ts|tsx|jsx)$' } | ForEach-Object { Join-Path $project $_ }
$pyFiles = $allFiles | Where-Object { $_ -like '*.py' } | ForEach-Object { Join-Path $project $_ }
$funcs = @()
foreach ($f in $tsFiles) { $funcs += Extract-TypeScriptFunctions -FilePath $f }
foreach ($f in $pyFiles) { $funcs += Extract-PythonFunctions -FilePath $f }

$byName = $funcs | Group-Object -Property Name | Where-Object { $_.Count -gt 1 }
$byName = if ($byName) { @($byName) } else { @() }
"## Colisiones de nombres de función (Python/TypeScript)" | Out-File $archivoConflictos -Append -Encoding UTF8
"Total: $($byName.Count)" | Out-File $archivoConflictos -Append -Encoding UTF8
"" | Out-File $archivoConflictos -Append -Encoding UTF8
foreach ($g in $byName | Sort-Object Name) {
    "### $($g.Name)" | Out-File $archivoConflictos -Append -Encoding UTF8
    foreach ($it in ($g.Group | Sort-Object Language, File, Line)) {
        $rel = Get-RelativePath -fullPath $it.File
        "- [$($it.Language)] $rel : línea $($it.Line)" | Out-File $archivoConflictos -Append -Encoding UTF8
    }
    "" | Out-File $archivoConflictos -Append -Encoding UTF8
}

$byHash = $funcs | Group-Object -Property Hash | Where-Object { $_.Count -gt 1 }
$byHash = if ($byHash) { @($byHash) } else { @() }
$byHashDifferentName = @()
foreach ($grp in $byHash) {
    $names = ($grp.Group | Select-Object -ExpandProperty Name | Sort-Object -Unique)
    if ($names.Count -gt 1) { $byHashDifferentName += $grp }
}
"## Implementaciones idénticas con distinto nombre" | Out-File $archivoConflictos -Append -Encoding UTF8
"Total: $($byHashDifferentName.Count)" | Out-File $archivoConflictos -Append -Encoding UTF8
"" | Out-File $archivoConflictos -Append -Encoding UTF8
foreach ($grp in $byHashDifferentName) {
    "### Hash: $($grp.Name)" | Out-File $archivoConflictos -Append -Encoding UTF8
    foreach ($it in ($grp.Group | Sort-Object Name, File, Line)) {
        $rel = Get-RelativePath -fullPath $it.File
        "- [$($it.Language)] $($it.Name) @ $rel : línea $($it.Line)" | Out-File $archivoConflictos -Append -Encoding UTF8
    }
    "" | Out-File $archivoConflictos -Append -Encoding UTF8
}

$markupFiles = $allFiles | Where-Object { $_ -match '\.(html|htm|tsx|jsx)$' } | ForEach-Object { Join-Path $project $_ }
$ids = @(); foreach ($f in $markupFiles) { $ids += Extract-MarkupIds -FilePath $f }
$byId = $ids | Group-Object -Property Id | Where-Object { $_.Count -gt 1 }
$byId = if ($byId) { @($byId) } else { @() }
"## IDs de DOM duplicados" | Out-File $archivoConflictos -Append -Encoding UTF8
"Total: $($byId.Count)" | Out-File $archivoConflictos -Append -Encoding UTF8
"" | Out-File $archivoConflictos -Append -Encoding UTF8
foreach ($g in $byId | Sort-Object Name) {
    "### id: $($g.Name)" | Out-File $archivoConflictos -Append -Encoding UTF8
    foreach ($it in ($g.Group | Sort-Object File, Line)) {
        $rel = Get-RelativePath -fullPath $it.File
        "- $rel : línea $($it.Line)" | Out-File $archivoConflictos -Append -Encoding UTF8
    }
    "" | Out-File $archivoConflictos -Append -Encoding UTF8
}

$routeFiles = $pyFiles | Where-Object { $_ -match 'Backend\\src\\api' -or $_ -match 'Backend\\src\\presentation' }
$routes = @(); foreach ($f in $routeFiles) { $routes += Extract-FastApiRoutes -FilePath $f }
$routeGroups = $routes | Group-Object { "{0} {1}" -f $_.Verb, $_.Path } | Where-Object { $_.Count -gt 1 }
$routeGroups = if ($routeGroups) { @($routeGroups) } else { @() }
"## Rutas FastAPI duplicadas" | Out-File $archivoConflictos -Append -Encoding UTF8
"Total: $($routeGroups.Count)" | Out-File $archivoConflictos -Append -Encoding UTF8
"" | Out-File $archivoConflictos -Append -Encoding UTF8
foreach ($grp in $routeGroups | Sort-Object Name) {
    "### $($grp.Name)" | Out-File $archivoConflictos -Append -Encoding UTF8
    foreach ($loc in ($grp.Group | Sort-Object File, Line)) {
        $rel = Get-RelativePath -fullPath $loc.File
        "- $rel : línea $($loc.Line)" | Out-File $archivoConflictos -Append -Encoding UTF8
    }
    "" | Out-File $archivoConflictos -Append -Encoding UTF8
}

if ($erroresHash.Count -gt 0) {
    "## Notas" | Out-File $archivoConflictos -Append -Encoding UTF8
    foreach ($e in $erroresHash) { "- $e" | Out-File $archivoConflictos -Append -Encoding UTF8 }
    "" | Out-File $archivoConflictos -Append -Encoding UTF8
}

Write-Host "[estructura] conflictos guardados en: $archivoConflictos"

# Construcción de ZeroGraph
function Add-Node {
    param($collection,[string]$id,[string]$type,[hashtable]$properties)
    $collection.Add([ordered]@{ id = $id; type = $type; properties = $properties }) | Out-Null
}
function Add-Rel {
    param($collection,[string]$source,[string]$target,[string]$type,[hashtable]$properties)
    $collection.Add([ordered]@{ id = 'rel-' + ([guid]::NewGuid().ToString('N')); source = $source; target = $target; type = $type; properties = $properties }) | Out-Null
}

$nodes = New-Object System.Collections.ArrayList
$relationships = New-Object System.Collections.ArrayList

Add-Node $nodes 'project:capiagentes' 'Project' ([ordered]@{
    name = 'CapiAgentes'
    description = 'Multi-agent financial intelligence and orchestration platform'
    stack = @('python-fastapi','langgraph','next.js')
    status = 'production_ready'
})
function Get-DirStats([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return @{ files = 0 } }
    $files = Get-ChildItem -LiteralPath $path -Recurse -File -Force | Where-Object {
        -not (ShouldSkip -relativePath (Get-RelativePath -fullPath $_.FullName) -isDirectory:$false)
    }
    return @{ files = $files.Count }
}

$layers = @(
    @{ Id='layer:domain'; Type='DomainLayer'; Path='Backend/src/domain'; Purpose='Domain entities, contracts and pure business rules' },
    @{ Id='layer:application'; Type='ApplicationLayer'; Path='Backend/src/application'; Purpose='Use cases, reasoning services and orchestrator helpers' },
    @{ Id='layer:infrastructure'; Type='InfrastructureLayer'; Path='Backend/src/infrastructure'; Purpose='Adapters for LangGraph, persistence, messaging and integrations' },
    @{ Id='layer:presentation'; Type='PresentationLayer'; Path='Backend/src/presentation'; Purpose='FastAPI routers, WebSocket presenters and orchestrator factory' },
    @{ Id='layer:shared'; Type='SharedCore'; Path='Backend/src/shared'; Purpose='Shared utilities and repositories' },
    @{ Id='layer:core'; Type='SharedCore'; Path='Backend/src/core'; Purpose='Configuration and logging' },
    @{ Id='layer:frontend'; Type='FrontendFeature'; Path='Frontend/src'; Purpose='PantallaAgentes dashboard (Next.js)' }
)
foreach ($layer in $layers) {
    $stats = Get-DirStats -path (Join-Path $project $layer.Path)
    Add-Node $nodes $layer.Id $layer.Type ([ordered]@{
        module_path = $layer.Path
        files = $stats.files
        purpose = $layer.Purpose
    })
    Add-Rel $relationships 'project:capiagentes' $layer.Id 'contains' ([ordered]@{ description = 'Partición de capa del proyecto' })
}

$domainSubdirs = @('entities','contracts','services')
foreach ($sub in $domainSubdirs) {
    $path = "Backend/src/domain/$sub"
    $abs = Join-Path $project $path
    if (Test-Path -LiteralPath $abs) {
        $stats = Get-DirStats -path $abs
        Add-Node $nodes "domain:$sub" 'DomainLayer' ([ordered]@{
            module_path = $path
            purpose = "Domain $sub"
            files = $stats.files
        })
        Add-Rel $relationships 'layer:domain' "domain:$sub" 'contains' ([ordered]@{ description = 'Domain submodule' })
    }
}

$applicationSubdirs = @(
    @{ Name='analysis'; Purpose='Financial analysis orchestrations' },
    @{ Name='alerts'; Purpose='Alert pipelines and smart recommendations' },
    @{ Name='conversation'; Purpose='Conversation state management' },
    @{ Name='document_generation'; Purpose='Document generation and LLM enhancements' },
    @{ Name='nlp'; Purpose='NLP utilities and intent classifiers' },
    @{ Name='reasoning'; Purpose='LangGraph reasoning helpers' },
    @{ Name='services'; Purpose='Application service layer' },
    @{ Name='use_cases'; Purpose='Financial analysis use cases' }
)
foreach ($sub in $applicationSubdirs) {
    $path = "Backend/src/application/$($sub.Name)"
    $abs = Join-Path $project $path
    if (Test-Path -LiteralPath $abs) {
        $stats = Get-DirStats -path $abs
        Add-Node $nodes "application:$($sub.Name)" 'ApplicationLayer' ([ordered]@{
            module_path = $path
            responsibilities = $sub.Purpose
            files = $stats.files
            depends_on = @('layer:domain')
        })
        Add-Rel $relationships 'layer:application' "application:$($sub.Name)" 'contains' ([ordered]@{ description = 'Application module' })
        Add-Rel $relationships "application:$($sub.Name)" 'layer:domain' 'depends_on' ([ordered]@{ reason = 'uses domain contracts' })
    }
}

$infraSubdirs = @(
    @{ Name='langgraph'; Purpose='LangGraph runtime and nodes'; Framework='LangGraph' },
    @{ Name='persistence'; Purpose='Persistence adapters and repositories'; Framework='PostgreSQL' },
    @{ Name='websocket'; Purpose='WebSocket event broadcaster'; Framework='FastAPI' }
)
foreach ($sub in $infraSubdirs) {
    $path = "Backend/src/infrastructure/$($sub.Name)"
    $abs = Join-Path $project $path
    if (Test-Path -LiteralPath $abs) {
        $stats = Get-DirStats -path $abs
        Add-Node $nodes "infrastructure:$($sub.Name)" 'InfrastructureLayer' ([ordered]@{
            module_path = $path
            framework = $sub.Framework
            exposes = $sub.Purpose
            files = $stats.files
        })
        Add-Rel $relationships 'layer:infrastructure' "infrastructure:$($sub.Name)" 'contains' ([ordered]@{ description = 'Infrastructure module' })
        Add-Rel $relationships "infrastructure:$($sub.Name)" 'layer:application' 'depends_on' ([ordered]@{ reason = 'invokes application services' })
    }
}

$presentationMap = @(
    @{ Id='presentation:api'; Path='Backend/src/api'; Purpose='FastAPI routers and middleware'; Entrypoints=@('REST:/api/agents','REST:/api/alerts','REST:/api/workspace','REST:/api/health','WebSocket:/ws/agents') },
    @{ Id='presentation:websocket'; Path='Backend/src/presentation/websocket_langgraph.py'; Purpose='WebSocket orchestrator for LangGraph'; Entrypoints=@('WebSocket:/ws/langgraph') },
    @{ Id='presentation:orchestrator'; Path='Backend/src/presentation/orchestrator_factory.py'; Purpose='Factory wiring LangGraph orchestrators'; Entrypoints=@() }
)
foreach ($item in $presentationMap) {
    $abs = Join-Path $project $item.Path
    if (Test-Path -LiteralPath $abs) {
        $stats = Get-DirStats -path (Split-Path -Parent $abs)
        Add-Node $nodes $item.Id 'PresentationLayer' ([ordered]@{
            module_path = $item.Path
            entrypoints = $item.Entrypoints
            description = $item.Purpose
            files = $stats.files
        })
        Add-Rel $relationships 'layer:presentation' $item.Id 'contains' ([ordered]@{ description = 'Presentation component' })
        Add-Rel $relationships $item.Id 'layer:application' 'depends_on' ([ordered]@{ reason = 'calls application services' })
        foreach ($entry in $item.Entrypoints) {
            $parts = $entry.Split(':')
            Add-Rel $relationships $item.Id 'layer:application' 'exposes' ([ordered]@{ interface = $entry; method = $parts[0] })
        }
    }
}

$orchestratorDir = Join-Path $project 'Backend/ia_workspace/orchestrator'
if (Test-Path -LiteralPath $orchestratorDir) {
    $stats = Get-DirStats -path $orchestratorDir
    Add-Node $nodes 'orchestrator:workspace' 'OrchestratorRuntime' ([ordered]@{
        module_path = 'Backend/ia_workspace/orchestrator'
        graph_role = 'runtime_extensions'
        files = $stats.files
    })
    Add-Rel $relationships 'project:capiagentes' 'orchestrator:workspace' 'contains' ([ordered]@{ description = 'Orchestrator runtime assets' })
    Add-Rel $relationships 'orchestrator:workspace' 'infrastructure:langgraph' 'depends_on' ([ordered]@{ reason = 'extends LangGraph runtime' })
}

$agentsDir = Join-Path $project 'Backend/ia_workspace/agentes'
$agentsRegistryPath = Join-Path $project 'Backend/ia_workspace/data/agents_registry.json'
$agentPrivilegesPath = Join-Path $project 'Backend/ia_workspace/data/agent_privileges.json'
$agentsRegistry = @{}
if (Test-Path -LiteralPath $agentsRegistryPath) {
    $agentsRegistry = Get-Content -LiteralPath $agentsRegistryPath -Raw | ConvertFrom-Json
}
$agentPrivileges = @{}
if (Test-Path -LiteralPath $agentPrivilegesPath) {
    $agentPrivileges = (Get-Content -LiteralPath $agentPrivilegesPath -Raw | ConvertFrom-Json).agent_assignments
}
if (Test-Path -LiteralPath $agentsDir) {
    $agentDirs = Get-ChildItem -LiteralPath $agentsDir -Directory -Force
    foreach ($agentDir in $agentDirs) {
        $agentName = $agentDir.Name
        $registry = $agentsRegistry.$agentName
        $privConf = $agentPrivileges.$agentName
        if (-not $privConf -and $agentName -like '*_fallback') {
            $fallback = $agentName -replace '_fallback',''
            $privConf = $agentPrivileges.$fallback
        }
        $priv = if ($privConf) { $privConf.privilege_level } else { 'standard' }
        $display = if ($registry) { $registry.display_name } else { ($agentName -replace '_',' ') }
        $handlerPath = "Backend/ia_workspace/agentes/$agentName/handler.py"
        Add-Node $nodes "agent:$agentName" 'Agent' ([ordered]@{
            name = $agentName
            display_name = $display
            handler_path = $handlerPath
            privilege_level = $priv
            capabilities = if ($registry) { $registry.capabilities } else { @{} }
        })
        Add-Rel $relationships 'project:capiagentes' "agent:$agentName" 'contains' ([ordered]@{ description = 'Agente registrado en workspace' })
        Add-Rel $relationships "agent:$agentName" 'infrastructure:langgraph' 'depends_on' ([ordered]@{ reason = 'executed via LangGraph nodes' })
        Add-Rel $relationships 'presentation:api' "agent:$agentName" 'privilege_controls' ([ordered]@{ enforced = $true })
        Add-Rel $relationships 'orchestrator:workspace' "agent:$agentName" 'invokes' ([ordered]@{ trigger = 'intent'; path = $handlerPath })
    }
}

$datasets = @(
    @{ Id='dataset:agents_config'; Path='Backend/ia_workspace/data/agents_config.json'; Purpose='Habilitación de agentes'; Type='json' },
    @{ Id='dataset:agent_privileges'; Path='Backend/ia_workspace/data/agent_privileges.json'; Purpose='Mapa de privilegios de agentes'; Type='json' },
    @{ Id='dataset:schema'; Path='Backend/database/schema.sql'; Purpose='Esquema PostgreSQL'; Type='sql' },
    @{ Id='dataset:seed'; Path='Backend/database/seed_data.sql'; Purpose='Datos seed de referencia'; Type='sql' }
)
foreach ($dataset in $datasets) {
    $abs = Join-Path $project $dataset.Path
    if (Test-Path -LiteralPath $abs) {
        Add-Node $nodes $dataset.Id 'Dataset' ([ordered]@{
            path = $dataset.Path
            type = $dataset.Type
            purpose = $dataset.Purpose
        })
        Add-Rel $relationships 'project:capiagentes' $dataset.Id 'contains' ([ordered]@{ description = 'Dataset operativo' })
    }
}

$frontendFeatures = @(
    @{ Id='frontend:dashboard'; Path='Frontend/src/app/dashboard'; Route='/dashboard'; Description='Pantalla principal con métricas de agentes'; Api=@('REST:/api/agents','WebSocket:/ws/agents') },
    @{ Id='frontend:workspace'; Path='Frontend/src/app/workspace'; Route='/workspace'; Description='Gestión de archivos y agentes'; Api=@('REST:/api/workspace') },
    @{ Id='frontend:health'; Path='Frontend/src/app/health'; Route='/health'; Description='Estado general de la plataforma'; Api=@('REST:/api/health') }
)
foreach ($feature in $frontendFeatures) {
    $abs = Join-Path $project $feature.Path
    if (Test-Path -LiteralPath $abs) {
        $stats = Get-DirStats -path $abs
        Add-Node $nodes $feature.Id 'FrontendFeature' ([ordered]@{
            route = $feature.Route
            description = $feature.Description
            consumes_api = $feature.Api
            files = $stats.files
        })
        Add-Rel $relationships 'layer:frontend' $feature.Id 'contains' ([ordered]@{ description = 'Frontend feature' })
        foreach ($api in $feature.Api) {
            Add-Rel $relationships $feature.Id 'presentation:api' 'renders' ([ordered]@{
                channel = (if ($api -like 'WebSocket*') { 'WebSocket' } else { 'REST' })
                cadence = (if ($api -like 'WebSocket*') { 'live' } else { 'request' })
            })
        }
    }
}

$scriptMap = @(
    @{ Id='script:zero-pipeline'; Path='.zero/scripts/pipeline.ps1'; Scope='pipeline'; Effects='Regenera artifacts de .zero' },
    @{ Id='script:docker-ps1'; Path='docker-commands.ps1'; Scope='devops'; Effects='Gestiona stack Docker (Windows)' },
    @{ Id='script:docker-sh'; Path='docker-commands.sh'; Scope='devops'; Effects='Gestiona stack Docker (Linux/Mac)' }
)
foreach ($script in $scriptMap) {
    $abs = Join-Path $project $script.Path
    if (Test-Path -LiteralPath $abs) {
        Add-Node $nodes $script.Id 'Script' ([ordered]@{
            path = $script.Path
            scope = $script.Scope
            effects = $script.Effects
        })
        Add-Rel $relationships 'project:capiagentes' $script.Id 'contains' ([ordered]@{ description = 'Script operativo' })
    }
}

Add-Rel $relationships 'application:analysis' 'dataset:schema' 'persists_to' ([ordered]@{ operation = 'read'; guard = 'schema_validation' })
Add-Rel $relationships 'application:alerts' 'dataset:agent_privileges' 'persists_to' ([ordered]@{ operation = 'read'; guard = 'privilege_check' })
Add-Rel $relationships 'application:services' 'dataset:agents_config' 'persists_to' ([ordered]@{ operation = 'read'; guard = 'privilege_check' })
$nodeTypeCounts = @{}
foreach ($n in $nodes) { $nodeTypeCounts[$n.type] = ($nodeTypeCounts[$n.type] + 1) }
$relTypeCounts = @{}
foreach ($r in $relationships) { $relTypeCounts[$r.type] = ($relTypeCounts[$r.type] + 1) }

$zerograph = [ordered]@{
    meta = [ordered]@{
        version = '1.0'
        Generado = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
        project = 'CapiAgentes'
        environment = 'development'
        description = 'Graph view of CapiAgentes multi-agent architecture'
    }
    nodes = $nodes
    relationships = $relationships
    statistics = [ordered]@{
        total_files = $allFiles.Count
        function_collisions = $byName.Count
        identical_function_hashes = $byHashDifferentName.Count
        duplicate_dom_ids = $byId.Count
        duplicate_routes = $routeGroups.Count
    }
    graph_metrics = [ordered]@{
        total_nodes = $nodes.Count
        total_relationships = $relationships.Count
        node_types_distribution = $nodeTypeCounts
        relationship_types_distribution = $relTypeCounts
    }
}

$estructuraJson = Join-Path $artifactsDir 'estructura.json'
$estructuraData = [ordered]@{
    metadata = [ordered]@{
        timestamp = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
        project_root = Split-Path -Leaf $project
        analysis_type = 'automated_structure'
    }
    statistics = $zerograph.statistics
    tree_file = 'estructura.txt'
    conflicts_file = 'conflictos.md'
}
$estructuraData | ConvertTo-Json -Depth 10 | Out-File $estructuraJson -Encoding UTF8

$zerograph | ConvertTo-Json -Depth 10 | Out-File (Join-Path $artifactsDir 'ZeroGraph.json') -Encoding UTF8
Write-Host '[estructura] generado estructura.json and ZeroGraph.json'



