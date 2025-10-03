param(
    [string]$GraphPath = ".zero/artifacts/ZeroGraph.json",
    [string]$ReportPath = ".zero/artifacts/zero-health.md"
)

function Add-Error {
    param([string]$Message)
    $script:Errors += $Message
}

if (-not (Test-Path $GraphPath)) {
    Write-Error "ZeroGraph file not found at $GraphPath"
    exit 1
}

try {
    $json = Get-Content $GraphPath -Raw | ConvertFrom-Json -Depth 100
} catch {
    Write-Error "Failed to parse ZeroGraph.json: $_"
    exit 1
}

$Errors = @()
$warnings = @()
$allowedNodeTypes = @(
    "Project","DomainLayer","ApplicationLayer","InfrastructureLayer",
    "PresentationLayer","SharedCore","OrchestratorRuntime",
    "Agent","FrontendFeature","Dataset","Script"
)
$allowedRelTypes = @(
    "contains","depends_on","exposes","invokes","privilege_controls",
    "persists_to","renders","tests","generates"
)

if (-not $json.meta) { Add-Error "Missing meta section" }
if (-not $json.nodes) { Add-Error "Missing nodes array" }
if (-not $json.relationships) { Add-Error "Missing relationships array" }

$nodeIndex = @{}
$nodeTypeIndex = @{}
foreach ($node in $json.nodes) {
    if (-not $node.id) { Add-Error "Node without id"; continue }
    if ($nodeIndex.ContainsKey($node.id)) {
        Add-Error "Duplicate node id: $($node.id)"
        continue
    }
    $nodeIndex[$node.id] = $node
    if (-not $allowedNodeTypes.Contains($node.type)) {
        Add-Error "Node $($node.id) has invalid type $($node.type)"
    }
    $nodeTypeIndex[$node.id] = $node.type
    if (-not $node.properties) {
        Add-Error "Node $($node.id) missing properties block"
        continue
    }
    switch ($node.type) {
        "Project" {
            foreach ($prop in @("name","description","stack","status")) {
                if (-not $node.properties.$prop) { Add-Error "Project missing $prop" }
            }
        }
        "DomainLayer" {
            foreach ($prop in @("module_path","purpose")) {
                if (-not $node.properties.$prop) { Add-Error "Domain node $($node.id) missing $prop" }
            }
        }
        "ApplicationLayer" {
            foreach ($prop in @("module_path","responsibilities")) {
                if (-not $node.properties.$prop) { Add-Error "Application node $($node.id) missing $prop" }
            }
            if (-not $node.properties.depends_on) { Add-Error "Application node $($node.id) missing depends_on list" }
        }
        "InfrastructureLayer" {
            foreach ($prop in @("module_path","framework","exposes")) {
                if (-not $node.properties.$prop) { Add-Error "Infrastructure node $($node.id) missing $prop" }
            }
        }
        "PresentationLayer" {
            foreach ($prop in @("module_path","entrypoints")) {
                if (-not $node.properties.$prop) { Add-Error "Presentation node $($node.id) missing $prop" }
            }
        }
        "SharedCore" {
            foreach ($prop in @("module_path","utilities")) {
                if (-not $node.properties.$prop) { Add-Error "SharedCore node $($node.id) missing $prop" }
            }
        }
        "OrchestratorRuntime" {
            foreach ($prop in @("module_path","graph_role")) {
                if (-not $node.properties.$prop) { Add-Error "Orchestrator node $($node.id) missing $prop" }
            }
        }
        "Agent" {
            foreach ($prop in @("name","handler_path","privilege_level")) {
                if (-not $node.properties.$prop) { Add-Error "Agent node $($node.id) missing $prop" }
            }
        }
        "FrontendFeature" {
            foreach ($prop in @("route","description")) {
                if (-not $node.properties.$prop) { Add-Error "Frontend feature $($node.id) missing $prop" }
            }
        }
        "Dataset" {
            foreach ($prop in @("path","data_type","purpose")) {
                if (-not $node.properties.$prop) { Add-Error "Dataset $($node.id) missing $prop" }
            }
        }
        "Script" {
            foreach ($prop in @("path","scope","effects")) {
                if (-not $node.properties.$prop) { Add-Error "Script $($node.id) missing $prop" }
            }
        }
    }
}

$agentIds = $nodeIndex.Keys | Where-Object { $nodeTypeIndex[$_] -eq "Agent" }
$frontendIds = $nodeIndex.Keys | Where-Object { $nodeTypeIndex[$_] -eq "FrontendFeature" }

foreach ($rel in $json.relationships) {
    if (-not $rel.type) { Add-Error "Relationship missing type"; continue }
    if (-not $allowedRelTypes.Contains($rel.type)) {
        Add-Error "Relationship $($rel.type) is not allowed" }
    if (-not $rel.source -or -not $rel.target) {
        Add-Error "Relationship $($rel.type) missing source/target"; continue }
    if (-not $nodeIndex.ContainsKey($rel.source)) { Add-Error "Relationship source missing: $($rel.source)" }
    if (-not $nodeIndex.ContainsKey($rel.target)) { Add-Error "Relationship target missing: $($rel.target)" }
    if (-not $rel.properties) { Add-Error "Relationship $($rel.type) from $($rel.source) missing properties"; continue }
    switch ($rel.type) {
        "depends_on" {
            if (-not $rel.properties.reason) { Add-Error "depends_on missing reason ($($rel.source)->$($rel.target))" }
            $srcType = $nodeTypeIndex[$rel.source]
            $tgtType = $nodeTypeIndex[$rel.target]
            if ($srcType -eq "DomainLayer" -and $tgtType -like "Infrastructure*") {
                Add-Error "Violation: Domain layer $($rel.source) depends on infrastructure $($rel.target)"
            }
        }
        "exposes" {
            foreach ($prop in @("interface","method")) {
                if (-not $rel.properties.$prop) { Add-Error "exposes missing $prop ($($rel.source)->$($rel.target))" }
            }
        }
        "invokes" {
            foreach ($prop in @("trigger","path")) {
                if (-not $rel.properties.$prop) { Add-Error "invokes missing $prop ($($rel.source)->$($rel.target))" }
            }
        }
        "privilege_controls" {
            if (-not $rel.properties.policy) { Add-Error "privilege_controls missing policy ($($rel.source)->$($rel.target))" }
        }
        "persists_to" {
            foreach ($prop in @("operation","guard")) {
                if (-not $rel.properties.$prop) { Add-Error "persists_to missing $prop ($($rel.source)->$($rel.target))" }
            }
        }
        "renders" {
            foreach ($prop in @("channel","cadence")) {
                if (-not $rel.properties.$prop) { Add-Error "renders missing $prop ($($rel.source)->$($rel.target))" }
            }
        }
    }
}

foreach ($agent in $agentIds) {
    if (-not ($json.relationships | Where-Object { $_.type -eq "privilege_controls" -and $_.target -eq $agent })) {
        Add-Error "Agent $agent lacks privilege_controls relationship"
    }
}

foreach ($feature in $frontendIds) {
    if (-not ($json.relationships | Where-Object { $_.type -eq "renders" -and $_.source -eq $feature })) {
        Add-Error "Frontend feature $feature lacks renders relationship"
    }
}

$reportLines = @("# ZeroGraph Validation", "Generated: $(Get-Date -Format o)", "> Nota: Este archivo resume la validación estructural de ZeroGraph para confirmar que la topología del proyecto sigue coherente.")
if ($Errors.Count -eq 0) {
    $reportLines += "Resultado: ✅ Sin errores detectados"
    $exitCode = 0
} else {
    $reportLines += "Resultado: ❌ Se encontraron $($Errors.Count) errores"
    $reportLines += "## Errores"
    $reportLines += ($Errors | ForEach-Object { "- $_" })
    $exitCode = 1
}

Set-Content -Path $ReportPath -Value ($reportLines -join [Environment]::NewLine) -Encoding UTF8

if ($Errors.Count -eq 0) {
    Write-Host "ZeroGraph validado correctamente" -ForegroundColor Green
} else {
    foreach ($err in $Errors) { Write-Error $err }
}

exit $exitCode

