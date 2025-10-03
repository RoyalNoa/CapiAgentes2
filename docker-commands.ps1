# CapiAgentes - Comandos Docker Esenciales
# UN COMANDO POR CASO DE USO - SIN EDITAR

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "rebuild", "logs", "status", "clean")]
    [string]$Action
)

$composeArgs = @('-f', 'docker-compose.yml')
$observabilityFile = Join-Path $PSScriptRoot 'observability\docker-compose.elastic.yml'
if (Test-Path $observabilityFile) {
    $composeArgs += @('-f', $observabilityFile)
}

function Invoke-DockerCompose {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$AdditionalArgs
    )
    docker compose @composeArgs @AdditionalArgs
}

switch ($Action) {
    "start" {
        Write-Host "🚀 INICIANDO CapiAgentes (completo)..." -ForegroundColor Green
        Invoke-DockerCompose -AdditionalArgs @('up', '-d')
        Start-Sleep 10
        Write-Host "✅ ACCESO: Frontend http://localhost:3000 | Backend http://localhost:8000" -ForegroundColor Green
    }

    "stop" {
        Write-Host "🛑 PARANDO CapiAgentes..." -ForegroundColor Yellow
        Invoke-DockerCompose -AdditionalArgs @('down')
        Write-Host "✅ DETENIDO: Todos los servicios parados" -ForegroundColor Green
    }

    "restart" {
        Write-Host "🔄 REINICIANDO CapiAgentes..." -ForegroundColor Blue
        Invoke-DockerCompose -AdditionalArgs @('down')
        Invoke-DockerCompose -AdditionalArgs @('up', '-d')
        Start-Sleep 10
        Write-Host "✅ REINICIADO: http://localhost:3000" -ForegroundColor Green
    }

    "rebuild" {
        Write-Host "🏗️ RECONSTRUYENDO CapiAgentes (desde cero)..." -ForegroundColor Magenta
        Invoke-DockerCompose -AdditionalArgs @('down')
        Invoke-DockerCompose -AdditionalArgs @('build', '--no-cache')
        Invoke-DockerCompose -AdditionalArgs @('up', '-d')
        Start-Sleep 15
        Write-Host "✅ RECONSTRUIDO: http://localhost:3000" -ForegroundColor Green
    }

    "logs" {
        Write-Host "📋 MOSTRANDO logs en tiempo real..." -ForegroundColor Blue
        Invoke-DockerCompose -AdditionalArgs @('logs', '-f')
    }

    "status" {
        Write-Host "📊 ESTADO de servicios:" -ForegroundColor Blue
        Invoke-DockerCompose -AdditionalArgs @('ps')
        Write-Host "`n🔍 HEALTH CHECK:" -ForegroundColor Blue
        $health = try { curl -s http://localhost:8000/api/health } catch { $null }
        if (-not $health) {
            Write-Host "❌ Backend no disponible" -ForegroundColor Red
        } else {
            Write-Host $health
        }
    }

    "clean" {
        Write-Host "🧹 LIMPIEZA COMPLETA (eliminando todo)..." -ForegroundColor Red
        Invoke-DockerCompose -AdditionalArgs @('down', '-v', '--remove-orphans')
        docker system prune -f
        Write-Host "✅ LIMPIO: Todo eliminado" -ForegroundColor Green
    }
}
