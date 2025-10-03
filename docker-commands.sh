#!/bin/bash
# CapiAgentes - Comandos Docker Esenciales
# UN COMANDO POR CASO DE USO

if [ $# -eq 0 ]; then
    echo "❌ Uso: ./docker-commands.sh [start|stop|restart|rebuild|logs|status|clean]"
    exit 1
fi

COMPOSE_ARGS=("-f" "docker-compose.yml")
OBSERVABILITY_FILE="$(dirname "$0")/observability/docker-compose.elastic.yml"
if [ -f "$OBSERVABILITY_FILE" ]; then
    COMPOSE_ARGS+=("-f" "$OBSERVABILITY_FILE")
fi

invoke_compose() {
    docker compose "${COMPOSE_ARGS[@]}" "$@"
}

case $1 in
    start)
        echo "🚀 INICIANDO CapiAgentes (completo)..."
        invoke_compose up -d
        sleep 10
        echo "✅ ACCESO: Frontend http://localhost:3000 | Backend http://localhost:8000"
        ;;

    stop)
        echo "🛑 PARANDO CapiAgentes..."
        invoke_compose down
        echo "✅ DETENIDO: Todos los servicios parados"
        ;;

    restart)
        echo "🔄 REINICIANDO CapiAgentes..."
        invoke_compose down
        invoke_compose up -d
        sleep 10
        echo "✅ REINICIADO: http://localhost:3000"
        ;;

    rebuild)
        echo "🏗️ RECONSTRUYENDO CapiAgentes (desde cero)..."
        invoke_compose down
        invoke_compose build --no-cache
        invoke_compose up -d
        sleep 15
        echo "✅ RECONSTRUIDO: http://localhost:3000"
        ;;

    logs)
        echo "📋 MOSTRANDO logs en tiempo real..."
        invoke_compose logs -f
        ;;

    status)
        echo "📊 ESTADO de servicios:"
        invoke_compose ps
        echo ""
        echo "🔍 HEALTH CHECK:"
        curl -s http://localhost:8000/api/health || echo "❌ Backend no disponible"
        ;;

    clean)
        echo "🧹 LIMPIEZA COMPLETA (eliminando todo)..."
        invoke_compose down -v --remove-orphans
        docker system prune -f
        echo "✅ LIMPIO: Todo eliminado"
        ;;

    *)
        echo "❌ Comando inválido. Usa: start|stop|restart|rebuild|logs|status|clean"
        exit 1
        ;;
esac
