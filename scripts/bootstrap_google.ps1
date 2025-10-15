<#
.SYNOPSIS
Bootstrapa credenciales OAuth para Agente G usando las variables definidas en .env.
#>

param(
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Ir a la raíz del repositorio (carpeta padre de scripts)
Set-Location (Split-Path -Parent $PSScriptRoot)

$envFile = ".env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env no encontrado en $(Get-Location)"
    exit 1
}

# Cargar variables requeridas desde .env
$required = @("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_SCOPES", "GOOGLE_TOKEN_STORE")
$loaded = @{}

Get-Content $envFile | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*([^#=]+)\s*=\s*(.+)\s*$") {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($required -contains $name) {
            Set-Item -Path "Env:$name" -Value $value
            $loaded[$name] = $value
        }
    }
}

foreach ($key in $required) {
    if (-not $loaded.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($loaded[$key])) {
        Write-Error "La variable $key debe estar definida en .env"
        exit 1
    }
}

# Ejecutar bootstrap con o sin navegador
$args = @("scripts\bootstrap_google_oauth.py")
if ($NoBrowser) {
    $args += "--no-browser"
}

Write-Host "Ejecutando bootstrap con GOOGLE_CLIENT_ID=$($loaded['GOOGLE_CLIENT_ID'])"
python @args
