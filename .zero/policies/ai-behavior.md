<!-- @canonical true -->
# Política de Comportamiento IA (.zero)

## Propósito del documento
- Define reglas realistas para que la IA colabore con personas y scripts sin bloquear entregas.
- Alinea a la IA con los objetivos de .zero: documentar contexto, evitar duplicados y mantener artefactos confiables.
- Sustituye versiones anteriores de `ai-behavior`.

## Principios base
- Priorizar siempre las instrucciones del usuario humano y las políticas de la organización.
- Transparencia: describir de forma concisa cada acción relevante en la respuesta o en los registros solicitados.
- Conservación: no eliminar ni sobrescribir información crítica sin copia previa.
- Iteración responsable: preferir cambios pequeños y verificables, comunicando riesgos.

## Flujo operativo recomendado
1. Comprender la solicitud revisando archivos relevantes (código, docs, `.zero/context`).
2. Identificar riesgos: duplicados potenciales, dependencias, permisos o sandbox.
3. Ejecutar el trabajo (análisis, edición de código, generación de parches) respetando las reglas de esta política.
4. Validar con pruebas, comandos o inspecciones cuando sea posible.
5. Reportar resultado, hallazgos y pasos siguientes.

## Modificación de código y archivos del proyecto
- Se permite editar cualquier archivo solicitado por el usuario, manteniendo coherencia con la base existente.
- Antes de crear un archivo nuevo, ejecutar una búsqueda por nombre (`Get-ChildItem -Recurse -File` o `rg --files`) para evitar duplicados.
- Si se detecta conflicto, explicar la colisión y proponer alternativas antes de continuar.
- Conservar formato y estilo del lenguaje (indentación, nombres, comentarios).
- Cuando el cambio sea amplio, considerar proponer parches (`git diff` o archivos `.patch`) y documentar pruebas sugeridas.

## Uso de `.zero/dynamic`
- `/.zero/dynamic/analysis/`: análisis, planes, bitácoras extendidas.
- `/.zero/dynamic/proposals/`: parches, manifiestos o pruebas para flujos controlados.
- `/.zero/dynamic/papelera/`: históricos opcionales; usar solo para resguardar archivos reemplazados.
- No es obligatorio escribir en `dynamic` si el usuario quiere resultados directos en la conversación.

## Prevención de duplicados
- Verificar nombres antes de crear componentes, scripts o documentos.
- Reutilizar archivos existentes cuando cubran el mismo propósito; documentar excepciones.
- Para mover o renombrar, preferir `Move-Item`/`git mv` para preservar historial.

## Registro de actividad
- Mantener la respuesta al usuario como fuente primaria: incluir qué se hizo, comandos relevantes y ubicación de cambios.
- Si el usuario lo exige, crear una nota de sesión en `/.zero/dynamic/sessions/YYYY-MM/DD-hhmm-descripcion.md` con tres secciones mínimas: acciones, comandos y salidas.

## Integración con ZeroGraph y artefactos
- Ejecutar `./.zero/scripts/zerograh-validation.ps1` o el pipeline solo cuando sea necesario actualizar `ZeroGraph.json` o auditar conflictos.
- Si se genera un delta de ZeroGraph, crear respaldo antes de aplicar cambios y documentar el procedimiento.
- Mantener `/.zero/artifacts/` como salidas automatizadas; no editarlas manualmente salvo instrucción explícita.

## Mecanismos de seguridad
- Detener la tarea si el sandbox o la política de aprobaciones impide un comando clave; pedir claridad al usuario.
- Señalar impactos potenciales en seguridad, rendimiento o UX antes de aplicar cambios de alto riesgo.
- Registrar cualquier limitación que impida completar pruebas locales.

## Reglas finales
- Esta política es obligatoria para asistentes y agentes que operen en este repositorio.
- Las actualizaciones deben conservar la cabecera `@canonical` y explicar en la respuesta los motivos del cambio.
- Si surge conflicto entre esta política y una instrucción directa del usuario, confirmar o priorizar la indicación humana.
