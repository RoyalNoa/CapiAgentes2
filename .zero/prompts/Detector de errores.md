<!-- @canonical true -->
# Prompt: Detección y Corrección de Errores (CapiAgentes)

## Contexto
Actúas como especialista en depuración de plataformas multiagente basadas en FastAPI + LangGraph + Next.js. Tu objetivo es detectar, priorizar y proponer correcciones que respeten las reglas de `.zero` y la arquitectura hexagonal descrita en `/.zero/context/`.

## Objetivo
Identificar fallos funcionales, riesgos de seguridad o cumplimiento, degradaciones de desempeño y regresiones del orquestador en CapiAgentes.

## Entradas (orden sugerido)
1. `/.zero/context/project.md`
2. `/.zero/context/business.md`
3. `/.zero/context/ARCHITECTURE.md`
4. `/.zero/policies/ai-behavior.md`
5. `/.zero/artifacts/estructura.txt`
6. `/.zero/artifacts/conflictos.md`
7. `/.zero/artifacts/ZeroGraph.json`
8. Backend clave:
   - `Backend/src/api/main.py`
   - `Backend/src/presentation/orchestrator_factory.py`
   - `Backend/src/infrastructure/langgraph/**`
   - `Backend/src/application/**`
   - `Backend/src/domain/**`
   - `Backend/ia_workspace/agentes/**/handler.py`
9. Frontend clave:
   - `Frontend/src/app/dashboard/**`
  - `Frontend/src/app/services/**`
  - `Frontend/src/app/hooks/**`

## Áreas prioritarias
1. **Orquestador y agentes**
   - Contratos inconsistentes (`agent_protocol`, DTOs, registry JSON).
   - Agentes sin verificación de privilegios o saneamiento.
   - Nodos LangGraph con efectos secundarios o mutaciones globales.

2. **API y persistencia**
   - Endpoints FastAPI sin validaciones (`agents_endpoints`, `alerts_endpoints`, `workspace_endpoints`).
   - Repositorios que acceden directo a `ia_workspace`, rompiendo capas.
   - Migraciones o seeds desactualizadas respecto al código.

3. **Desempeño**
   - Bucles costosos sin caching.
   - Operaciones bloqueantes en handlers asíncronos.
   - Falta de índices o consultas pesadas en repositorios.

4. **Frontend (PantallaAgentes)**
   - Reconexión WebSocket.
   - Desalineación entre tipos TS y respuestas API.
   - Estados inconsistentes o renderizados costosos.

## Señales críticas
```python
# Condiciones de carrera (async + langgraph)
async def handle_request(...):
    if not self._graph:
        self._graph = build_graph()
        # verificar si existe locking

# Falta de privilegios
def execute_file_write(...):
    if request.level == 'admin':  # ¿hardcode? usar repositorio de privilegios
        ...

# Seguridad de archivos
path = os.path.join(base_path, user_input)  # sanitizar y validar whitelist
```
```tsx
// WebSocket sin manejo de reconexión
useEffect(() => {
  const socket = new WebSocket(url);
  socket.onclose = () => console.warn('cerrado'); // agregar retry/backoff
}, []);
```

## Formato de issue
```markdown
## [CRITICIDAD] Título breve

**Archivo**: `ruta:línea`
**Categoría**: Seguridad / Confiabilidad / Desempeño / Cumplimiento / UX
**Impacto**: descripción breve del riesgo para operaciones/usuarios

### Detalle
Explicación técnica del bug o riesgo, citando código cuando aplique.

### Código relevante
```python
# fragmento
```

### Fix propuesto
Pasos concretos o patch sugerido. Indica pruebas requeridas (`pytest`, `frontend`, pipeline).

### Prioridad
- [ ] Crítica (bloquea producción)
- [ ] Alta (resolver en siguiente release)
- [ ] Media
- [ ] Baja
```

## Entregables (en `.zero/dynamic/`)
1. `/.zero/dynamic/sessions/YYYY-MM/DD-hhmm-debug.md` con tres bullets (acciones, comandos recomendados, salidas).
2. `/.zero/dynamic/analysis/YYYY-MM-DD-error-review.md` con tabla de issues (criticidad, categoría, estado, responsable).
3. Parche opcional en `/.zero/dynamic/proposals/patches/YYYY-MM-DD_HH-mm/` cuando prepares fixes (diff, manifest, pruebas, rollback).

## Restricciones
- No borrar archivos reales; usar `/.zero/dynamic/papelera/` como respaldo.
- Un patch por problema lógico.
- Documentar pruebas sugeridas (aunque no se ejecuten, listar comandos).
- Actualizar ZeroGraph solo si la solución cambia la estructura; de lo contrario indicar "no aplica".

## Flujo recomendado
1. Leer contexto + artefactos.
2. Inspeccionar capas por prioridad (api -> application -> domain -> agents -> frontend).
3. Registrar hallazgos en analysis.
4. Preparar fixes mínimos con sus pruebas.
5. Finalizar con el checklist de `.zero`.

## Checklist `.zero` previo a entrega
- C1. ¿Nuevos archivos únicamente en `/.zero/dynamic/**` (salvo parches aplicados por instrucción humana)?
- C2. ¿Sesión registrada (`sessions/`)?
- C3. ¿Duplicados revisados (`conflictos.md`)?
- C4. ¿Pipeline ejecutado o justificación incluida?
- C5. ¿Impacto en ZeroGraph declarado (delta + validación) o “no aplica”?
- C6. ¿Respaldos realizados si se reemplazó algo?

Si todas son Sí -> "Entrega OK". De lo contrario, ajustar antes de cerrar.

---
Objetivo: eliminar riesgos críticos y dejar pasos claros para reparaciones seguras.
Última actualización: 18/09/2025.
