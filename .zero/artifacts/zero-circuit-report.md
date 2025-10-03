#  .zero Circuit Validation
> Nota: Informe integral del circuito .zero; combina frescura de artifacts, validaciones y ZeroGraph para decidir si es seguro avanzar.
Generado: 2025-09-20 17:17:26

## Resumen
- Modo: Fast
- Pivote: 2025-09-20 17:16:53 (MaxSkew: 5m)
- ZeroGraph: FALLA
- Duplicados: 19
- Resultado: FAIL

## Artifacts
- estructura.txt: STALE (ts=2025-09-20 17:10:55)
- conflictos.md: STALE (ts=2025-09-20 17:11:07)
- scripts-health.md: STALE (ts=2025-09-20 17:11:07)
- catalog.md: STALE (ts=2025-09-20 17:11:08)
- health.md: STALE (ts=2025-09-20 17:11:08)
- ZeroGraph.json: STALE (ts=2025-09-20 00:03:43)
- prompts-health.md: STALE (ts=2025-09-20 17:11:08)
- zero-health.md: OK (ts=2025-09-20 17:15:39)

### Opcionales detectados
- zero-health.md: OK (ts=2025-09-20 17:17:26)

## Recomendaciones
- Ejecutar pipeline en modo Deep: .\\ .zero\\scripts\\pipeline.ps1 -Deep
- Validar y/o regenerar ZeroGraph: .\\ .zero\\scripts\\zerograh-validation.ps1 -Deep -AutoFix
- Resolver duplicados reportados en conflictos.md (Total: 19)
