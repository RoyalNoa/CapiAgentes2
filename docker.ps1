<#
.SYNOPSIS
    Docker management script for CapiAgentes - Professional deployment automation

.DESCRIPTION
    Advanced Docker orchestration with multi-environment support, health monitoring,
    performance optimization, and comprehensive logging for production deployments.

.PARAMETER Action
    Operations: up|down|restart|install|rebuild|ps|logs|health|dev|test|prod|monitor|clean|backup

.PARAMETER Environment
    Target environment: production|development|testing|staging

.PARAMETER Profile
    Service profiles: redis|monitoring|all

.EXAMPLE
    ./docker.ps1 -Action prod -Profile all
    Deploys full production stack with monitoring

.EXAMPLE
    ./docker.ps1 -Action dev -Follow
    Starts development environment with live logs
#>
[CmdletBinding()]
param(
  [ValidateSet('up','down','restart','install','rebuild','ps','logs','health','dev','test','prod','monitor','clean','backup','exec')]
  [string]$Action = 'up',

  [ValidateSet('production','development','testing','staging')]
  [string]$Environment = 'production',

  [ValidateSet('redis','monitoring','all','none')]
  [string]$Profile = 'none',

  [ValidateSet('backend','frontend','both')]
  [string]$Service = 'both',

  [switch]$NoCache,
  [switch]$Prune,
  [switch]$ForceRancher,
  [switch]$Follow,
  [switch]$Detached,
  [switch]$Watch,

  [string]$Container,
  [string]$Command = 'bash'
)
# Enhanced logging with levels
function Log {
  param(
    [string]$Message,
    [ConsoleColor]$Color='Gray',
    [ValidateSet('INFO','WARN','ERROR','SUCCESS','DEBUG')]
    [string]$Level='INFO'
  )
  $timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  $prefix = "[$timestamp] [$Level]"
  Write-Host "$prefix $Message" -ForegroundColor $Color
}

function Show-Banner {
  Write-Host "`n" -NoNewline
  Write-Host "  ╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
  Write-Host "  ║               " -ForegroundColor Cyan -NoNewline
  Write-Host "CAPI AGENTES DOCKER MANAGER" -ForegroundColor White -NoNewline
  Write-Host "               ║" -ForegroundColor Cyan
  Write-Host "  ║          Professional Multi-Agent Financial Platform      ║" -ForegroundColor Cyan
  Write-Host "  ╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
  Write-Host "`n" -NoNewline
}
# Paths
$repoRoot  = Split-Path -Parent $MyInvocation.MyCommand.Path
$compose   = Join-Path $repoRoot 'docker-compose.yml'
if(-not (Test-Path $compose)){ throw "No se encontró docker-compose.yml en $repoRoot" }
# CLI detection
function Select-CLI {
  param([switch]$ForceRancher)
  $dockerOk=$false; if(Get-Command docker -ErrorAction SilentlyContinue){ docker version > $null 2>&1; if($LASTEXITCODE -eq 0){ $dockerOk=$true } }
  $nerdctlOk=$false; if(Get-Command nerdctl -ErrorAction SilentlyContinue){ nerdctl version > $null 2>&1; if($LASTEXITCODE -eq 0){ $nerdctlOk=$true } }
  if($ForceRancher){ if($nerdctlOk){ return 'nerdctl' } if($dockerOk){ Log 'Forzado Rancher pero nerdctl no disponible, usando docker' DarkYellow; return 'docker' } return $null }
  if($dockerOk){ return 'docker' }
  if($nerdctlOk){ return 'nerdctl' }
  return $null
}
$CLI = Select-CLI -ForceRancher:$ForceRancher
if(-not $CLI){ throw 'No se detectó runtime (docker/nerdctl). Abre Docker Desktop o Rancher y reintenta.' }
Log "CLI: $CLI | compose: $compose" DarkGray

# Ajuste de variables de entorno para rutas host usadas en docker-compose (volúmenes)
function Convert-ToWSLPath {
  param([string]$WinPath)
  if(-not $WinPath){ return $null }
  if($WinPath -match '^[A-Za-z]:\\'){ # C:\Users\...
    $drive = $WinPath.Substring(0,1).ToLower()
    $rest  = $WinPath.Substring(2).Replace('\\','/')
    return "/mnt/$drive/$rest"
  }
  if($WinPath -match '^[A-Za-z]:/'){ # C:/Users/...
    $drive = $WinPath.Substring(0,1).ToLower()
    $rest  = $WinPath.Substring(2)
    return "/mnt/$drive/$rest"
  }
  return $WinPath
}

# Configurar envs de rutas para compose según runtime
function Set-ComposeHostPathEnv {
  param([string]$RepoRoot,[string]$CLIName)
  $defaultBackendSrc = Join-Path $RepoRoot 'Backend/src'
  # Ensure ia_workspace is always under Backend to avoid root-level folder creation
  $defaultIaWs       = Join-Path $RepoRoot 'Backend/ia_workspace'
  if(-not $env:CAPI_BACKEND_SRC -or [string]::IsNullOrWhiteSpace($env:CAPI_BACKEND_SRC)){ $env:CAPI_BACKEND_SRC = $defaultBackendSrc }
  if(-not $env:CAPI_IA_WORKSPACE -or [string]::IsNullOrWhiteSpace($env:CAPI_IA_WORKSPACE)){ $env:CAPI_IA_WORKSPACE = $defaultIaWs }
  if($CLIName -eq 'nerdctl'){
    $env:CAPI_BACKEND_SRC   = Convert-ToWSLPath $env:CAPI_BACKEND_SRC
    $env:CAPI_IA_WORKSPACE  = Convert-ToWSLPath $env:CAPI_IA_WORKSPACE
  }
  Log "CAPI_BACKEND_SRC=$($env:CAPI_BACKEND_SRC) | CAPI_IA_WORKSPACE=$($env:CAPI_IA_WORKSPACE)" DarkGray
}

Set-ComposeHostPathEnv -RepoRoot $repoRoot -CLIName $CLI

# Performance and security validation
function Test-SystemRequirements {
  Log 'Validating system requirements...' 'Yellow' 'INFO'

  # Check available memory
  $memory = (Get-WmiObject -Class Win32_OperatingSystem).TotalVisibleMemorySize / 1MB
  if($memory -lt 4) {
    Log "Warning: Low memory detected $([math]::Round($memory, 1))GB. Recommend 4GB+" 'Yellow' 'WARN'
  }

  # Check disk space
  $disk = Get-WmiObject -Class Win32_LogicalDisk | Where-Object {$_.DeviceID -eq 'C:'}
  $freeSpaceGB = $disk.FreeSpace / 1GB
  if($freeSpaceGB -lt 5) {
    Log "Warning: Low disk space $([math]::Round($freeSpaceGB, 1))GB free. Recommend 5GB+" 'Yellow' 'WARN'
  }

  Log 'System validation completed' 'Green' 'SUCCESS'
}

Test-SystemRequirements
function Invoke-Compose { param([string[]]$ComposeArgs)
  $argsList = @('-f', $compose) + $ComposeArgs
  if($CLI -eq 'docker'){ & docker compose @argsList } else { & nerdctl compose @argsList }
  if($LASTEXITCODE -ne 0){ throw "Fallo compose: $($ComposeArgs -join ' ')" }
}
function Invoke-CLI { param([string]$Sub,[string[]]$CliArgs)
  if($CLI -eq 'docker'){ & docker $Sub @CliArgs } else { & nerdctl $Sub @CliArgs }
}
function Get-Services {
  switch($Service) {
    'frontend' { return @('frontend') }
    'backend' { return @('backend') }
    'both' { return @('backend','frontend') }
    default { return @('backend','frontend') }
  }
}

function Get-ProfileServices {
  param([string]$ProfileName)
  $baseServices = Get-Services
  switch($ProfileName) {
    'redis' { return $baseServices + @('redis') }
    'monitoring' { return $baseServices + @('prometheus') }
    'all' { return $baseServices + @('redis','prometheus') }
    default { return $baseServices }
  }
}

function Get-EnvironmentServices {
  param([string]$EnvType)
  switch($EnvType) {
    'development' { return @('backend-dev','frontend') }
    'testing' { return @('backend-test') }
    'staging' { return @('backend','frontend') }
    default { return Get-ProfileServices -ProfileName $Profile }
  }
}
function Stop-Stack {
  Log 'Stopping stack...' 'Yellow' 'INFO'
  try {
    Invoke-Compose -ComposeArgs @('down','--remove-orphans','--timeout','30')
    Log 'Stack stopped successfully' 'Green' 'SUCCESS'
  } catch {
    Log 'Nothing to stop or controlled error' 'Gray' 'WARN'
  }
}
function Build-Stack {
  param([string[]]$Services,[switch]$NoCache,[switch]$Pull)
  Log "Building services: $($Services -join ', ')" 'Cyan' 'INFO'

  $buildArgs = @('build')
  if($NoCache) {
    $buildArgs += '--no-cache'
    Log 'Using no-cache build' 'Yellow' 'INFO'
  }
  if($Pull -and $CLI -eq 'docker') {
    $buildArgs += '--pull'
    Log 'Pulling latest base images' 'Blue' 'INFO'
  }

  # Parallel build if multiple services
  if($Services.Count -gt 1) {
    $buildArgs += '--parallel'
    Log 'Building services in parallel' 'Blue' 'INFO'
  }

  $buildArgs += $Services
  Invoke-Compose -ComposeArgs $buildArgs

  Log 'Build completed successfully' 'Green' 'SUCCESS'
}
function Start-Stack {
  param([string[]]$Services)
  Log "Starting services: $($Services -join ', ')" 'Cyan' 'INFO'

  $upArgs = @('up')
  if($Detached -or $Action -ne 'dev') { $upArgs += '-d' }
  $upArgs += $Services

  Invoke-Compose -ComposeArgs $upArgs

  if($Detached -or $Action -ne 'dev') {
    Start-Sleep -Seconds 3
    Log 'Current status:' 'Green' 'INFO'
    Invoke-Compose -ComposeArgs @('ps','--format','table')
  }

  if($Watch -and ($Detached -or $Action -ne 'dev')) {
    Log 'Monitoring logs... (Ctrl+C to stop)' 'Yellow' 'INFO'
    Invoke-Compose -ComposeArgs (@('logs','-f','--tail=50') + $Services)
  }
}
function Invoke-Prune {
  Log 'Cleaning images and cache...' 'Yellow' 'INFO'
  try {
    Invoke-CLI image @('prune','-f')
    Log 'Images cleaned' 'Green' 'SUCCESS'
  } catch {
    Log 'Image cleanup failed' 'Yellow' 'WARN'
  }
  try {
    Invoke-CLI builder @('prune','-f')
    Log 'Build cache cleaned' 'Green' 'SUCCESS'
  } catch {
    Log 'Builder cache cleanup failed' 'Yellow' 'WARN'
  }
}
function Test-StackHealth {
  Log 'Performing comprehensive health check...' 'Cyan' 'INFO'

  $healthResults = @{}

  # Backend health check
  try {
    $backendResponse = & curl.exe -sS -w "%{http_code}" http://localhost:8000/health 2>$null
    if($backendResponse -match '200$') {
      Log 'Backend: Healthy (200)' 'Green' 'SUCCESS'
      $healthResults.Backend = 'Healthy'
    } else {
      Log "Backend: Unhealthy ($backendResponse)" 'Red' 'ERROR'
      $healthResults.Backend = 'Unhealthy'
    }
  } catch {
    Log 'Backend: Unavailable' 'Red' 'ERROR'
    $healthResults.Backend = 'Unavailable'
  }

  # Frontend health check
  try {
    $frontendResponse = & curl.exe -sS -I http://localhost:3000 2>$null | Select-String 'HTTP.*200'
    if($frontendResponse) {
      Log 'Frontend: Healthy (200)' 'Green' 'SUCCESS'
      $healthResults.Frontend = 'Healthy'
    } else {
      Log 'Frontend: Unhealthy' 'Red' 'ERROR'
      $healthResults.Frontend = 'Unhealthy'
    }
  } catch {
    Log 'Frontend: Unavailable' 'Red' 'ERROR'
    $healthResults.Frontend = 'Unavailable'
  }

  # Container status check
  Log 'Container status:' 'Yellow' 'INFO'
  try {
    Invoke-Compose -ComposeArgs @('ps','--format','table')
  } catch {
    Log 'Could not retrieve container status' 'Red' 'WARN'
  }

  return $healthResults
}
# Main execution logic
Show-Banner
Log "Environment: $Environment | Profile: $Profile | Service: $Service" 'Cyan' 'INFO'

$services = Get-EnvironmentServices -EnvType $Environment

switch ($Action) {
  'down' {
    Log 'Shutting down stack...' 'Yellow' 'INFO'
    Stop-Stack
  }

  'up' {
    Log "Starting services: $($services -join ', ')" 'Green' 'INFO'
    Start-Stack -Services $services
  }

  'restart' {
    Log 'Restarting stack...' 'Yellow' 'INFO'
    Stop-Stack
    Start-Sleep -Seconds 2
    Start-Stack -Services $services
  }

  'install' {
    Log 'Installing fresh stack...' 'Cyan' 'INFO'
    if($Prune) { Invoke-Prune }
    Build-Stack -Services $services -NoCache:$NoCache -Pull
    Start-Stack -Services $services
    Start-Sleep -Seconds 5
    Test-StackHealth
  }

  'rebuild' {
    Log 'Rebuilding stack...' 'Cyan' 'INFO'
    Stop-Stack
    if($Prune) { Invoke-Prune }
    Build-Stack -Services $services -NoCache:$NoCache -Pull
    Start-Stack -Services $services
  }

  'dev' {
    Log 'Starting development environment...' 'Magenta' 'INFO'
    Stop-Stack
    $profiles = @('--profile','dev')
    if($Profile -eq 'redis') { $profiles += @('--profile','redis') }
    if($Profile -eq 'monitoring') { $profiles += @('--profile','monitoring') }
    if($Profile -eq 'all') { $profiles += @('--profile','redis','--profile','monitoring') }

    $devServices = @('backend-dev','frontend')
    if($Profile -eq 'redis' -or $Profile -eq 'all') { $devServices += 'redis' }
    if($Profile -eq 'monitoring' -or $Profile -eq 'all') { $devServices += 'prometheus' }

    Invoke-Compose -ComposeArgs ($profiles + @('up','-d') + $devServices)
    if($Follow) {
      Log 'Following logs... (Ctrl+C to stop)' 'Yellow' 'INFO'
      Invoke-Compose -ComposeArgs ($profiles + @('logs','-f') + $devServices)
    }
  }

  'test' {
    Log 'Running test suite...' 'Magenta' 'INFO'
    Invoke-Compose -ComposeArgs @('--profile','test','up','--abort-on-container-exit','backend-test')
  }

  'prod' {
    Log 'Deploying production stack...' 'Green' 'INFO'
    Stop-Stack
    Build-Stack -Services $services -NoCache:$false -Pull
    $prodServices = Get-ProfileServices -ProfileName $Profile
    Start-Stack -Services $prodServices
    Start-Sleep -Seconds 10
    $health = Test-StackHealth
    if($health.Backend -eq 'Healthy' -and $health.Frontend -eq 'Healthy') {
      Log 'Production deployment successful!' 'Green' 'SUCCESS'
    } else {
      Log 'Production deployment has health issues!' 'Red' 'ERROR'
    }
  }

  'monitor' {
    Log 'Starting monitoring stack...' 'Blue' 'INFO'
    $monitorServices = Get-Services + @('prometheus')
    Invoke-Compose -ComposeArgs @('--profile','monitoring','up','-d') + $monitorServices
    Log 'Prometheus available at http://localhost:9090' 'Green' 'SUCCESS'
  }

  'clean' {
    Log 'Performing deep cleanup...' 'Yellow' 'WARN'
    Stop-Stack
    Invoke-Prune
    try {
      Invoke-CLI system @('prune','-a','-f','--volumes')
      Log 'System cleanup completed' 'Green' 'SUCCESS'
    } catch {
      Log 'Cleanup completed with warnings' 'Yellow' 'WARN'
    }
  }

  'backup' {
    Log 'Creating data backup...' 'Cyan' 'INFO'
    $timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
    $backupDir = "./backups/backup_$timestamp"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

    # Backup volumes
    try {
      Invoke-CLI run @('--rm','-v','capi_backend_data:/data','-v',"$($PWD.Path)${backupDir}:/backup",'alpine','tar','czf','/backup/backend_data.tar.gz','-C','/data','.')
      Log "Backup created: $backupDir" 'Green' 'SUCCESS'
    } catch {
      Log 'Backup failed' 'Red' 'ERROR'
    }
  }

  'exec' {
    if(-not $Container) {
      Log 'Container name required for exec. Use -Container parameter' 'Red' 'ERROR'
      exit 1
    }
    Log "Executing command in container: $Container" 'Cyan' 'INFO'
    Invoke-CLI exec @('-it',$Container,$Command)
  }

  'ps' {
    Log 'Container status:' 'Cyan' 'INFO'
    Invoke-Compose -ComposeArgs @('ps','--format','table')
  }

  'logs' {
    $logArgs = @('logs')
    if($Follow) { $logArgs += '-f' }
    if(-not $Follow) { $logArgs += '--tail=100' }
    Log "Showing logs for: $($services -join ', ')" 'Cyan' 'INFO'
    Invoke-Compose -ComposeArgs ($logArgs + $services)
  }

  'health' {
    Test-StackHealth | Out-Null
  }

  default {
    Log "Unknown action: $Action" 'Red' 'ERROR'
    exit 1
  }
}

Log 'Operation completed successfully!' 'Green' 'SUCCESS'
