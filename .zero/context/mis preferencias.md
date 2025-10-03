# CapiAgentes - Preferencias de Desarrollo

Propósito: plasmar estilo personal y decisiones por defecto en este repositorio. Úsalo como guía cuando exista ambigüedad.
Audiencia: desarrolladores y colaboradores IA de CapiAgentes.
Última actualización: 18/09/2025 (curado por humanos).

## Preferencias arquitectónicas
- Mantener límites hexagonales explícitos (domain -> application -> infrastructure/presentation).
- La lógica del orquestador vive en `Backend/src/infrastructure/langgraph/` y reutiliza contratos de `Backend/src/application/`.
- `Backend/ia_workspace/` permanece como runtime: agentes, adaptadores del orquestador, datos.
- Frontend es Next.js 14 con App Router; seguir los patrones en `Frontend/src/app/dashboard/`.

## Estilo de código backend (Python)
```python
# Logging: siempre usar helpers de logging estructurado
def run_agent(agent_name: str, payload: dict) -> AgentResult:
    logger = logging.getLogger("src.application.reasoning.run_agent")
    logger.info("agent_start", extra={"agent": agent_name})
    result = orchestrator.execute(agent_name, payload)
    logger.info("agent_end", extra={"agent": agent_name, "status": result.status})
    return result

# Usar typing + dataclasses para objetos de dominio
@dataclass
class BranchPerformance:
    branch_id: str
    revenue: Decimal
    expenses: Decimal
    anomalies: list[Anomaly]

# Inyección de dependencias vía parámetros o factorías ligeras
```
- Emplear `typing`, `pydantic` y `dataclasses` cuando aplique.
- Evitar estado global; preferir inyección de dependencias y objetos de contexto.
- Funciones cortas con retornos tempranos.
- Configuración desde `Backend/src/core/settings.py`; no leer variables de entorno inline.

## Estilo de código frontend (TypeScript/React)
```tsx
// Hooks para obtener datos
const { data, isLoading } = useAgentMetrics();

// Componentes con props tipadas
interface AlertPanelProps {
  alerts: AgentAlert[];
}

export function AlertPanel({ alerts }: AlertPanelProps) {
  if (!alerts.length) {
    return <EmptyState title="Sin alertas" description="Los agentes no reportan incidentes" />;
  }
  return (
    <section className="grid gap-3">
      {alerts.map((alert) => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </section>
  );
}
```
- Preferir componentes funcionales y hooks.
- Centralizar clientes API en `Frontend/src/app/services/`.
- Usar utilidades Tailwind junto con tokens de diseño.
- Las pruebas (cuando existan) viven junto a los componentes con Testing Library.

## Preferencias de pruebas
- Backend: `pytest -q` para ejecuciones rápidas; usar marcadores (`-m integration`) cuando sea necesario.
- Mockear dependencias externas con moderación; idealmente repositorios en memoria.
- Frontend: Jest/Testing Library (agregar cuando aplique).
- Regenerar `/.zero/artifacts/` tras cambios de estructura.

## Estándares de logging
- Siempre usar `logging` con extras estructurados.
- Prohibido `print()` en backend o código de agentes.
- Frontend debe loguear al console solo en desarrollo; proteger o eliminar en producción.

## Seguridad y cumplimiento
- Privilegio mínimo: agentes nuevos comienzan en `restricted` hasta revisión.
- Operaciones sobre documentos requieren confirmación explícita y respaldo.
- Sanitizar datos sensibles antes de responder o loguear.
- Seguir `/.zero/context/ARCHITECTURE.md` como guía de límites y controles.

## Preferencias de UX
- Dashboard enfocado en estado de agentes, severidad de anomalías y actividad reciente.
- Usar etiquetas claras en español; tooltips para explicar términos de negocio.
- Indicadores en tiempo real basados en WebSocket; agregar fallback con backoff exponencial.
- Mantener layouts densos pero legibles inspirados en terminales financieras.

## Watchlist de revisión de código
1. Violaciones a los límites hexagonales.
2. Pruebas faltantes para rutas del orquestador.
3. Logging omitido o inconsistente.
4. Tipos de frontend desalineados con DTOs backend.
5. Controles de privilegios ausentes o debilitados.

## Criterios de éxito
- Backend arranca en < 5 segundos con cachés calientes.
- Ejecución de agentes con mediana < 2 segundos.
- WebSocket del dashboard se reconecta automáticamente con backoff exponencial.
- Operaciones sobre documentos siempre crean un respaldo con timestamp.
- `./.zero/scripts/pipeline.ps1` corre limpio (sin duplicados inesperados ni artefactos faltantes).

---
Estas preferencias son obligatorias salvo indicación humana que las modifique.
