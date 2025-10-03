# Planificador NL->SQL propuesto

## Objetivo
Traducir consultas naturales sobre saldos y otras metricas financieras a planes SQL seguros sin depender de regex. Debe convivir con `prepare_operation` y convertirse en el camino principal del agente.

## Componentes clave
- **NLQueryPlanner (nuevo modulo interno)**: encapsula el uso de `LLMReasoner` para devolver un JSON estructurado con la consulta interpretada.
- **SchemaCatalog**: describe tablas, columnas y joins permitidos (por ahora derivado de constantes; luego puede leerse de metadata). Incluir alias de sucursales y campos disponibles (`saldo_total`, `fecha_corte`, etc.).
- **PlanValidator**: normaliza el JSON del planner, aplica `validate_table`, usa `BranchIdentifier` para convertir nombres libres y asegura limites (`limit`, `order_by`, `filters`).
- **SqlBuilder extension**: agregar soporte para agregaciones (`SUM`, `AVG`, `COUNT`), `GROUP BY`, `HAVING`, comparadores (`>`, `<`, `BETWEEN`, `ILIKE`), y filtros por fechas.

## Flujo propuesto en `prepare_operation`
1. Detectar formato deseado (`json/csv/txt`) igual que hoy.
2. Intentar parseo JSON estructurado (compatibilidad).
3. Enviar la instruccion completa + contexto (posible `format_hint`, historial) al `NLQueryPlanner`.
   - Prompt incluir:
     - Objetivo del agente.
     - Catalogo de tablas autorizadas con descripcion breve.
     - Campos numericos y de fecha disponibles.
     - Esquema de salida obligatorio (ver mas abajo).
     - Ejemplos positivos (saldo de Villa Crespo, top 5 sucursales con mayores saldos) y negativos (SQL directo, acciones no permitidas).
4. Si el planner responde con confianza >= umbral (p.ej. 0.6) devolver `DbOperation` derivado del plan validado.
5. Si el planner falla o retorna intent `other`, caer en heuristicas actuales (regex) para no romper casos conocidos.

## Especificacion del JSON de plan
```json
{
  "operation": "select",
  "table": "public.saldos_sucursal",
  "columns": ["sucursal_id", "saldo_total"],
  "aggregations": [{"column": "saldo_total", "func": "sum", "alias": "saldo"}],
  "filters": [
    {"column": "sucursal_nombre", "op": "ilike", "value": "%Villa Crespo%"},
    {"column": "fecha", "op": "between", "value": ["2024-01-01", "2024-01-31"]}
  ],
  "group_by": ["sucursal_id"],
  "order_by": [{"column": "saldo", "direction": "desc"}],
  "limit": 10,
  "needs_branch_lookup": true,
  "output_format": "json",
  "confidence": 0.82,
  "reasoning": "Se busco saldo total por sucursal con filtro Villa Crespo"
}
```
Notas:
- `needs_branch_lookup` obliga a pasar por `BranchIdentifier` cuando el planner devuelva `branch` textual.
- Si `aggregations` existe debe mapearse a `SqlBuilder` generando `SUM(col) AS alias`.

## Validaciones necesarias
- `operation` restringido a `select` (otras operaciones mantienen flujo actual con aprobacion).
- Verificar columnas contra catalogo y sanitizarlas.
- Convertir filtros a parametros posicionados. Soportar valores escalares, listas (`IN`), rangos (`between`).
- Aplicar limites por defecto (ej. `limit` maximo 100) si el planner no devuelve ninguno.
- Para branch: usar `BranchIdentifier` con alias conocidos (Villa Crespo -> `branch_id` o `sucursal_nombre ilike`).

## Integracion con router
- Ajustar `SemanticIntentService` para etiquetar consultas con entidades de sucursal/saldo como `db_operation`. Anadir plantillas al fallback semantico para detectar palabras clave ("saldo", "movimientos", "monto", nombres de sucursal).
- Registrar en `response_metadata` un campo `semantic_plan` con el JSON final para facilitar auditoria.

## Observabilidad y metricas
- Contar decisiones del planner (`planner_confidence`, `planner_source`), distinguir fallback vs plan valido.
- Loggear prompt/respuesta anonimizada en debug cuando se active flag `LOG_NL_PLANNER_DEBUG`.
- Anadir `processing_metrics.nl_query_planner_ms` con tiempo de razonamiento.

## Testing sugerido
- Pytest con fixtures que simulan razonador devolviendo JSON conocido.
- Casos: "saldo de la sucursal de Villa Crespo", "top 3 sucursales por saldo", "saldo promedio entre marzo y abril".
- Negativos: sucursal inexistente, intento de tabla no autorizada, consultas con lenguaje ambiguo.

## Riesgos y mitigaciones
- **Hallucination de columnas**: recortar catalogo y responder con error orientado.
- **Coste LLM**: cachear planes por `(branch, metric, rango)` en memoria a corto plazo.
- **Operaciones no SELECT**: mantener heuristicas actuales + aprobacion humana, registrar tarea para futura expansion.
