# Task 04 - Quality, pruebas y adopcion gradual

## Objetivo irrenunciable
Garantizar que el nuevo graph canvas se habilite sin riesgos: feature flag controlado, migracion de datos vieja -> nueva estructura, pipeline CI con cobertura, guia de uso y plan de rollback.

## Referencias obligatorias
- Blueprint `docs/Nuevas Funcionalidades/grafo_n8n_blueprint.md` (seccion "Proximos pasos sugeridos").
- Contratos Task 01 y servicios Task 02/03.
- Flujos de QA en n8n: revisar `packages/frontend/editor-ui/src/components/canvas/__tests__`, `packages/frontend/editor-ui/e2e` (si aplica), `workflow-execution.service.ts` tests.
- Observabilidad actual CAPI (`observability/`, `logs/`, `docker-compose.yml`).

## Entregables concretos
1. Feature flag `graphCanvasV2` en backend y frontend:
   - Backend: leer de `GraphState.config` o `.env`, exponer en `GET /agents/graph/status`.
   - Frontend: hook `useFeatureFlags` (nuevo) que consulte endpoint y habilite canvas solo si flag true.
2. Script de migracion:
   - `scripts/migrate_graph_meta.py` que tome workflows existentes (contrato anterior) y construya `AgentWorkflowMeta` + `node_positions`.
   - Reporte en consola (cuenta de nodos migrados, warnings si faltan posiciones).
3. Plan de QA automatizado:
   - Backend: ampliar `pytest Backend/tests -q` con suites Task 01/02.
   - Frontend: agregar `npm test -- --runTestsByPath src/app/workspace/canvas/__tests__/*` y listar en pipeline.
   - Opcional: Playwright e2e `npm run test:e2e` (documentar si se posterga).
4. Observabilidad y alertas:
   - Dashboards Kibana/Elastic (ver `kibana_seed.json`) actualizados con logs `graph_canvas`.
   - Alertas (Slack/email) cuando una ejecucion termina en error > N veces.
5. Documentacion:
   - `docs/Nuevas Funcionalidades/graph_canvas_rollout.md` con plan por entornos (dev -> staging -> prod), checklist, owners.
   - Manual para usuarios finales (capturas, pasos para ejecutar workflows, como leer estados).
6. Roadmap y backlog:
   - Crear issues/tareas para funcionalidades pendientes (auto-layout, colaboracion simultanea, versionado) citando blueprint.

## Pasos detallados
1. **Feature flag end-to-end**
   - Backend: introducir config en `Backend/.env.example` (`GRAPH_CANVAS_V2_ENABLED=true`). Leerla en `Backend/src/config/...` y exponer en `GraphState.config`.
   - Ajustar `GET /agents/graph/status` para incluir `{ "graph_canvas_v2": bool }`.
   - Frontend: crear `Frontend/src/app/hooks/useFeatureFlags.ts` que llame a `/agents/graph/status` y almacene flags en contexto.
   - En `WorkspaceTab` mostrar toggle (solo visible para admin) que permita habilitar/deshabilitar localmente (guardar preferencia en localStorage por usuario).
2. **Migracion de layouts antiguos**
   - Analizar `Backend/src/infrastructure/langgraph/state_schema.py` actual para identificar donde se guardan posiciones previas (`node_positions`).
   - Script `scripts/migrate_graph_meta.py` debe:
     - Leer workflows desde DB o API (usar `ExecutionService`/`AgentRegistryService`).
     - Para cada workflow: si `meta` vacio, construir `AgentWorkflowMeta` con viewport default y mapear `node_positions` existentes.
     - Escribir reporte JSON `logs/graph_migration_{timestamp}.json` con resultados.
   - Proveer modo dry-run vs apply.
3. **QA backend**
   - Añadir `pytest` stage a pipeline (GitHub Actions / CI). Incluir coverage minimal 80% en nuevos modulos.
   - Simular ejecuciones fallidas y asegurarse que logs contengan `execution_finished status=error` (para alertas).
4. **QA frontend**
   - Crear `jest.config.canvas.json` si se requiere aislar tests.
   - Escribir mocks de WebSocket y API en `__tests__/AgentCanvasPush.test.tsx`.
   - Documentar pasos manuales: arrastrar nodo, conectar, ejecutar, verificar overlays.
   - Preparar script Playwright (si se habilita) que cree workflow demo, ejecute y valide UI.
5. **Observabilidad**
   - En backend, usar logger estructurado (`get_logger`) con `extra={'component': 'graph_canvas', 'execution_id': ...}`.
   - Exportar metricas Prometheus (si aplica) para conteo de ejecuciones, errores, latencia media.
   - Actualizar `kibana_seed.json` con panel "Graph Canvas" (mismas dimensiones que paneles existentes).
6. **Plan de rollout**
   - Definir fases:
     1. Dev interno (flag manual, base de datos de pruebas).
     2. Staging (subset usuarios, recopilar feedback, habilitar telemetria).
     3. Produccion (feature flag default true tras validacion).
   - Documentar criterios de salida para cada fase (ej. 0 errores bloqueantes en 1 semana, latencia < X ms).
   - Redactar rollback (deshabilitar flag, revertir meta a version anterior, limpiar pushes activos).
7. **Manual de usuario**
   - Explicar jerarquia de estados (colores, badges, paneles) reutilizando blueprint.
   - Incluir troubleshooting: que hacer si WS cae, si nodo queda en rojo, etc.
   - Añadir seccion "Diferencias vs editor anterior".
8. **Backlog futuro**
   - Enumerar features a abordar despues (auto-layout, colaboracion, versionado historico, plantillas) con referencias a blueprint.
   - Crear issues en tracker con etiquetas (GraphCanvas, FollowUp).

## Validaciones
- Checklist final debe ser firmado por responsable backend y frontend.
- Ejecutar script de migracion en modo dry-run y adjuntar reporte a docs.
- CI debe fallar si flag no seteado o pruebas faltantes.

## Riesgos
- Flag mal configurada -> bloquear canvas viejo. Mitigacion: default false y fallback a UI anterior hasta validacion.
- Migracion incompleta -> nodos sin posicion. Mitigacion: script con reporte y verificacion manual.
- Tests inestables -> pipeline ruidoso. Mitigacion: aislar WebSocket tests y usar retries limitados.

## Definicion de hecho
- Feature flag controlado por configuracion y toggle.
- Script de migracion ejecutado en dev con reporte.
- Documentacion y plan de rollout entregados.
- QA automatizado integrado en CI.
