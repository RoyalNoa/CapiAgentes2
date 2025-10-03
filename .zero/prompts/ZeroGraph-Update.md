<!-- @canonical true -->
# Prompt: Actualización ZeroGraph (CapiAgentes)

## Contexto
Eres responsable de mantener ZeroGraph alineado con la arquitectura multiagente de CapiAgentes. Usa los artefactos generados y la documentación canónica para producir análisis y, cuando corresponda, un delta listo para merge.

## Entradas obligatorias (en orden)
1. `/.zero/artifacts/estructura.txt`
2. `/.zero/artifacts/conflictos.md`
3. `/.zero/artifacts/ZeroGraph.json`
4. `/.zero/context/ARCHITECTURE.md`
5. `/.zero/context/project.md`
6. `/.zero/context/business.md`
7. `/.zero/context/Zero.md` y `Zero2.md` (especificación del modelo)

## Salidas esperadas (todas en `/.zero/dynamic/analysis/`)
1. `YYYY-MM-DD-business-logic.md`
   - Analiza flujos de negocio relevantes (agentes, orquestador, privilegios, dashboard).
2. `YYYY-MM-DD-security-analysis.md`
   - Evalúa riesgos de seguridad/compliance (privilegios, accesos a archivos, logging, datos sensibles).
3. `YYYY-MM-DD-performance-recommendations.md`
   - Recomienda optimizaciones para backend (FastAPI/LangGraph), agentes y frontend.
4. `zerograph-delta-YYYY-MM-DD.json` (solo si ZeroGraph requiere nodos/relaciones nuevas o actualización de metadatos).

## Formato sugerido
Cada markdown debe incluir:
- Encabezado con fecha y objetivo.
- Resumen ejecutivo.
- Hallazgos con referencias a archivos/líneas (ej.: `Backend/src/api/main.py:120`).
- Recomendaciones accionables priorizadas.
- Próximos pasos o preguntas abiertas.

El delta JSON debe seguir la estructura de `/.zero/context/Zero.md` y contener únicamente inserciones/modificaciones necesarias (sin duplicados).

## Procedimiento
1. Validar que los archivos destino no existan para la fecha actual (evitar duplicados).
2. Revisar conflictos reportados en `conflictos.md` y el ZeroGraph actual.
3. Leer arquitectura y contexto para mantener coherencia con los principios hexagonales.
4. Mapear hallazgos a nodos/relaciones existentes. Si falta representación, planear delta.
5. Redactar análisis y generar delta.
6. Sugerir pruebas/comprobaciones (aunque no se ejecuten) al final de cada análisis.
7. Dejar nota opcional en `/.zero/dynamic/sessions/YYYY-MM/DD-zerograph.md` con resumen de actividad.

## Reglas
- No editar manualmente `/.zero/artifacts/ZeroGraph.json`; aplicar deltas mediante respaldo + merge humano.
- Mantener IDs únicos en el delta; usar hashes consistentes para nodos nuevos.
- Respetar límites de arquitectura (sin enlaces prohibidos, ej.: `Backend/src` -> `Backend/ia_workspace` inverso).
- Si ZeroGraph ya refleja el estado real, documentar "sin cambios" y omitir delta.

## Validaciones sugeridas (postanálisis)
```powershell
pwsh -NoProfile -File ./.zero/scripts/zerograh-validation.ps1 -Deep
pwsh -NoProfile -File ./.zero/scripts/pipeline.ps1 -Fast
```

## Criterios de calidad
- Conecta hallazgos técnicos con impacto de negocio.
- Identifica relaciones faltantes entre agentes, servicios, endpoints y UI.
- Propone mejoras verificables (pruebas, monitoreo, docs).
- Delta mínimo, coherente y listo para aplicar tras el respaldo.

## Prompt de activación
```
Revisa artefactos y contexto actual de CapiAgentes.
Genera los análisis de negocio, seguridad y performance en `.zero/dynamic/analysis/`.
Crea un `zerograph-delta-YYYY-MM-DD.json` solo si detectas cambios necesarios en el grafo.
```

Última actualización: 18/09/2025.
