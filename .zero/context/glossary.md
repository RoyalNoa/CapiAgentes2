# CapiAgentes - Glosario

## Operaciones financieras
**PRIVILEGIO DE AGENTE** - Nivel de permiso que define qué puede ejecutar cada agente (restricted/standard/elevated/privileged/admin).
**DESEMPEÑO DE SUCURSAL** - KPIs que miden ingresos, costos y anomalías por sucursal.
**RESUMEN FINANCIERO** - Métricas agregadas (netos, distribuciones, varianza) generadas por el agente Summary.
**ESCANEO DE ANOMALÍAS** - Detección automática de outliers o transacciones sospechosas.
**PANTALLAAGENTES** - Dashboard que muestra ejecuciones, métricas y alertas para operadores.

## Conceptos de plataforma
**ORQUESTADOR LANGGRAPH** - Motor basado en grafos que coordina los caminos de ejecución de los agentes.
**REGISTRO DE AGENTES** - Conjunto de JSON + base de datos que mapea agentes con capacidades y privilegios.
**DATOS DE WORKSPACE** - Archivos CSV/JSON bajo `Backend/ia_workspace/data/` usados como conjunto de trabajo por los agentes.
**FACTORÍA DE ORQUESTADOR** - Componente que arma los pipelines de LangGraph según configuración.
**LOG DE SESIÓN** - Traza de interacciones entre usuarios, orquestador y agentes guardada para auditoría.

## Vocabulario backend
**APLICACIÓN FASTAPI** - Punto de entrada en `Backend/src/api/main.py` que expone REST y WebSocket.
**CAPA PRESENTATION** - Adaptadores que traducen solicitudes HTTP/WebSocket en tareas del orquestador.
**SERVICIO APPLICATION** - Lógica de negocio orquestada ubicada en `Backend/src/application/`.
**ENTIDAD DE DOMINIO** - Objeto de negocio definido en `Backend/src/domain/` (Python puro, sin frameworks).
**UTILIDAD SHARED** - Helper reutilizable dentro de `Backend/src/shared/` (file_manager, memory_manager, task_scheduler).

## Vocabulario frontend
**APP ROUTER** - Enrutador de Next.js 14 usado en `Frontend/src/app/`.
**WIDGET DE DASHBOARD** - Componente visual que muestra KPIs o estado de agentes.
**CLIENTE WEBSOCKET** - Listener para eventos (`api.log`) que actualiza PantallaAgentes en tiempo real.
**TOKENS DE ESTILO** - Constantes de diseño definidas en `AI/Tablero/PantallaAgentes/STYLE_TOKENS.md`.

## Datos y persistencia
**SCHEMA.SQL** - Esquema de PostgreSQL en `Backend/database/schema.sql`.
**SEED DATA** - Inserts de referencia para demos (`Backend/database/seed_data.sql`).
**DIRECTORIO DE RESPALDOS** - Ubicación dentro de `ia_workspace/data/backups/` con copias timestamped.
**TABLA DE PRIVILEGIOS DE AGENTES** - Tabla `public.agentes` que controla la escalera de privilegios.

## Observabilidad
**CONFIGURACIÓN DE LOGGING** - JSON en `Backend/src/core/logging_config.json` con handlers y rotación.
**APP.LOG** - Logs INFO del backend.
**ERRORS.LOG** - Logs ERROR para excepciones.
**API.LOG** - Logs específicos de API y WebSocket.
**REPORTE DE SALUD** - `/.zero/artifacts/health.md` con el estado más reciente del pipeline.

## Sistema de documentación
**ZERO CONTEXT** - Documentos canónicos dentro de `/.zero/context/*`.
**ZERO ARTIFACTS** - Salidas generadas por `/.zero/scripts/` (estructura, conflictos, ZeroGraph).
**ZERO DYNAMIC** - Área escribible para colaboración IA/humana (analysis, sessions, proposals).
**ZEROGRAPH** - Representación JSON de nodos, relaciones y métricas del proyecto.

---
Última actualización: 18/09/2025 (curado por humanos).
