# MVP pendiente

## Resumen ejecutivo
Este documento explica el intento de extender la tarjeta de detalle del agente capi_noticias con controles para editar los segmentos destacados (diario/semanal/mensual). La implementación quedó incompleta y actualmente el frontend no compila por errores de sintaxis en los componentes nuevos. Se registran aquí: el plan inicial, las acciones realizadas, los problemas que surgieron y el trabajo pendiente para retomar la tarea cuando el código quede nuevamente estable.

## Contexto inicial
- Requerimiento: permitir que, al abrir el nodo capi_noticias dentro del panel de agentes del HUD, se pueda ajustar desde la UI los umbrales min_priority de los segmentos daily, weekly y monthly que persiste el agente.
- Situación previa: la página Frontend/src/app/pages/agentes/page.tsx ya mostraba un bloque CapiNoticiasInsights pero quedó obsoleto tras restaurar el código (no se mostraba nada en el overlay del grafo). El plan consistía en mover esa lógica al componente GraphPanel dentro de la tarjeta del agente seleccionado y reutilizar los estilos del HUD.

## Plan original
1. Extraer las constantes SEGMENT_KEYS, SEGMENT_LABELS y DEFAULT_SEGMENT_MIN_PRIORITY a un util compartido (@/app/utils/capiNoticiasSegments).
2. Crear un componente reutilizable (CapiNoticiasSegmentCard) que reciba la configuración actual y callbacks para editar/guardar/restablecer los umbrales.
3. Integrar esa tarjeta dentro del overlay del GraphPanel cuando el agente seleccionado sea capi_noticias, manteniendo la sección de overview general y la sección de eventos.
4. Ajustar los estilos en GraphPanel.module.css para la nueva tarjeta y el marcador de "Overview general".
5. Limpiar referencias antiguas (CapiNoticiasInsights), ejecutar 
pm run lint, corregir cualquier error y dejar el PR listo.

## Acciones realizadas
- **Paso 1 (completado):** se creó Frontend/src/app/utils/capiNoticiasSegments.ts con las constantes/exportaciones necesarias. Se actualizó page.tsx para consumirlas.
- **Paso 2 (parcial):** se creó Frontend/src/app/components/HUD/CapiNoticiasSegmentCard.tsx y se añadieron estilos complementarios en GraphPanel.module.css. Sin embargo, durante la edición surgieron varios reemplazos defectuosos (uso de ${...} dentro de interpolaciones, duplicados de span, etiquetas sin cerrar). El archivo quedó con errores de sintaxis.
- **Paso 3 (parcial):** se agregaron importaciones en GraphPanel.tsx y se insertó un marcador overviewMarker junto a un render condicional de CapiNoticiasSegmentCard. Se llegó a mover el bloque dentro del overlay, pero hubo múltiples reemplazos automáticos que insertaron secuencias \r\n literalmente y borraron parte del layout. Finalmente se volvió a **restaurar** GraphPanel.tsx al estado original porque la sección había quedado inconsistente.
- **Paso 4 (completado a medias):** se añadieron estilos .segmentCard* y .overviewMarker en GraphPanel.module.css. Los estilos existen, pero actualmente no se usan (porque GraphPanel.tsx restaurado ya no los referencia).
- **Paso 5 (no completado):** 
pm run lint se ejecutó varias veces y continúa fallando. Los errores importantes actuales:
  - CapiNoticiasSegmentCard.tsx:140:58 «Unterminated string literal» (causado por las interpolaciones mal cerradas).
  - El resto de los fallos listados son *warnings* preexistentes (hooks sin dependencias, <img> en HUDNavigator, etc.) que no se abordaron todavía.

## Estado actual del repositorio
- Frontend/src/app/utils/capiNoticiasSegments.ts: listo para usarse.
- Frontend/src/app/components/HUD/CapiNoticiasSegmentCard.tsx: **contiene errores de sintaxis** y necesita ser corregido o, si se decide posponer la funcionalidad, eliminado.
- Frontend/src/app/components/HUD/GraphPanel.tsx: restaurado al contenido original, **sin** la tarjeta nueva. Solo se añadió la importación, que se debería revertir o volver a usar cuando se retome la tarea.
- Frontend/src/app/components/HUD/GraphPanel.module.css: incluye nuevas clases (segmentCard*, overviewMarker). No se utilizan hoy, pero permanecen sin romper nada.
- Frontend/src/app/pages/agentes/page.tsx: mantiene las constantes extraídas y el paso de capiNoticiasControls hacia GraphPanel. Como GraphPanel volvió al estado anterior, ese prop no es consumido; produce un warning de tipo por props innecesarios, aunque no rompe la app.

## Problemas detectados
1. **Errores de plantilla en JSX:** al usar reemplazos masivos quedaron literales como ${cfg.lookback_days} sin template literal, duplicados de <span> y líneas cortadas. Esto causa los errores de lint y de compilación.
2. **Secuencias \r\n literales:** en un momento se introdujeron cadenas con barras invertidas dobles que se guardaron tal cual en el archivo. Se limpió, pero hay que revisar el bloque donde quedó la tarjeta para asegurar que no haya más artefactos.
3. **Importación sin uso en GraphPanel.tsx:** al restaurar el archivo, se mantuvo la importación de CapiNoticiasSegmentCard pero ya no se usa, lo que generará un warning.
4. **Warnings previos en hooks:** siguen pendientes (eran conocidos en el proyecto). No bloquean, pero conviene abordarlos al rehacer el trabajo.

## Trabajo pendiente recomendado
1. **Revertir o arreglar CapiNoticiasSegmentCard.tsx:**
   - Revisar cada interpolación y cerrar correctamente los template literals.
   - Verificar que el retorno tenga toda su jerarquía cerrada (cada <div> con su </div>).
   - Una vez estable, reutilizar este componente desde GraphPanel.tsx.
2. **Reaplicar la integración en GraphPanel.tsx:**
   - Reinsertar el bloque condicional {agent.name === 'capi_noticias' ...} dentro del overlay.
   - Añadir el marcador "Overview general" y verificar que no rompa el layout.
   - Asegurar que CapiNoticiasSegmentCard reciba las props solo cuando estén disponibles.
3. **Actualizar GraphPanel.module.css:**
   - Confirmar que la tarjeta nueva usa las clases agregadas.
   - Limpiar estilos sobrantes si se decide no usarlos.
4. **Corregir page.tsx si se pospone la tarjeta:**
   - Opcionalmente retirar el prop capiNoticiasControls para evitar advertencias hasta que el overlay lo soporte nuevamente.
5. **Ejecutar 
pm run lint y 
pm run build (o 
ext build)** una vez resuelto lo anterior, y ajustar cualquier error adicional.

## Observaciones finales
- No quedó ningún otro archivo modificado fuera de los listados. El resto del código se mantiene tal como estaba después de la restauración manual.
- Cuando el compañero que "reseteó" el estado de la app termine sus cambios, se recomienda sincronizar, volver a ejecutar 
pm install (si hay dependencias nuevas) y retomar la integración siguiendo el plan anterior, esta vez con modificaciones controladas y pruebas paso a paso.
- Para evitar que se repita la pérdida de trabajo, se sugiere trabajar en un branch dedicado y hacer commits intermedios antes de realizar transformaciones extensas automatizadas.
