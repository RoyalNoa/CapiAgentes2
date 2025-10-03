# Task 01 - Normalizar contratos de grafo y catalogos

## Objetivo
Definir los DTOs/Modelos necesarios para compartir grafos de agentes entre Backend (FastAPI/LangGraph) y Frontend (Next.js), alineados con lo documentado en `docs/Nuevas Funcionalidades/grafo_n8n_blueprint.md` y el modelo de `WorkflowEntity` de n8n.

## Alcance
- Contratos HTTP (`AgentWorkflowDto`, `AgentCanvasNodeData`, `AgentCanvasConnectionData`, `AgentPushMessage`).
- Serializadores/adaptadores en `Backend/src/infrastructure/langgraph/state_schema.py` y servicios relacionados.
- Catalogo de nodos/credenciales expuesto via API (`GET /agents/graph/catalog`).

## Pasos sugeridos
1. Auditar el estado actual de `GraphState.to_frontend_format()` y mapearlo contra los campos requeridos por el canvas tipo n8n.
2. Disenar los modelos Pydantic en un nuevo modulo `Backend/src/presentation/schemas/graph.py`.
3. Extender `state_schema.py` y los orquestadores para poblar `meta` (viewport, node_positions) y `pin_data` cuando aplique.
4. Exponer endpoints REST + contrato OpenAPI: `GET /agents/workflows/{id}`, `PATCH /agents/workflows/{id}`, `POST /agents/workflows/run`, `GET /agents/graph/catalog`.
5. Documentar la forma de los eventos push (`executionStarted`, `nodeExecuteAfterData`, etc.) tomando como referencia `packages/@n8n/api-types/src/push/execution.ts`.

## Criterios de aceptacion
- Nuevos DTOs con tipado estricto, pruebas unitarias/minimales en `Backend/tests` que validen serializacion/deserializacion.
- Endpoints registrados en FastAPI y visibles en `GET /openapi.json`.
- Documentacion actualizada en `docs/Nuevas Funcionalidades` describiendo los contratos.
