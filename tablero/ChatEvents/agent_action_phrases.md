# Frases por agente (alineadas a `shared_artifacts`)

## Capi DataB (`database_query`)
**Aliases**: `database_query`, `capi_datab`, `capidatab`
**Frase por defecto**: Interactuando con el core de datos
**Secuencia progresiva**:
- Generando SELECT parametrizado
- Ejecutando `operation.sql` (saldos_sucursal)
- Consolidando `summary_message`
**Frases contextuales**:
- `saldo`
  - Consultando saldo en `shared_artifacts.capi_datab.rows`
  - Comparando contra `planner_metadata`
  - Calculando saldo teórico (`summary_message`)
- `sucursal_objetivo`
  - Filtrando `saldos_sucursal` por sucursal (`planner_metadata.branch`)
  - Consultando fila correspondiente en `rows`
  - Resumiendo KPIs de la sucursal en `summary_message`
- `sucursal`
  - Normalizando identificador (`branch_descriptor`)
  - Filtrando registros en `rows`
  - Resumiendo dataset filtrado
- `total`
  - Agregando montos (`rows[*]`)
  - Calculando totales (`summary_message`)
  - Contrastando con `planner_metadata`
- `transaccion`
  - Listando transacciones (`response_metadata`)
  - Detectando outliers (`planner_metadata`)
  - Marcando revisión en `alerts`
- `export`
  - Serializando dataset (`export_file`)
  - Persistiendo export en workspace seguro
  - Publicando enlace de descarga
- `dispositivo`
  - Consultando estado POS/ATM (`rows`)
  - Analizando heartbeats (`metadata`)
  - Resumiendo alertas de dispositivos

## Capi El Cajas (`branch_operations`)
**Aliases**: `branch_operations`, `capi_elcajas`, `capielcajas`
**Frase por defecto**: Auditando flujo operativo de cajas
**Secuencia progresiva**:
- Generando análisis (`shared_artifacts.capi_elcajas.analysis`)
- Persistiendo alertas (`alerts_to_persist`)
- Creando recomendación (`recommendation_artifact`)
**Frases contextuales**:
- `saldo`
  - Leyendo `analysis[*].measured_total`
  - Comparando con `analysis[*].theoretical_total`
  - Alertando gap en `headline`
- `caja`
  - Evaluando canales (`analysis[*].channels`)
  - Registrando incidencias en `analysis`
  - Ajustando acciones (`recommendations`)
- `sucursal_objetivo`
  - Filtrando `analysis` por sucursal objetivo
  - Analizando flujo de la sucursal
  - Recomendando ajustes específicos (`recommendations`)
- `cierre`
  - Contabilizando cierre (`alerts_to_persist`)
  - Conciliando `datos_clave`
  - Preparando resumen de cierre
- `apertura`
  - Revisando estado inicial (`analysis`)
  - Validando fondos en `channels`
  - Notificando hallazgos en `recommendation`
- `transaccion`
  - Procesando `alert_operations`
  - Detectando anomalías (`analysis`)
  - Ajustando ledger (`alerts_to_persist`)

## Capi Desktop (`desktop_operation`)
**Aliases**: `desktop_operation`, `capi_desktop`, `capidesktop`
**Frase por defecto**: Gestionando entregables en workspace
**Secuencia progresiva**:
- Ensamblando contenido desde artefactos
- Formateando archivo según `filename`
- Guardando recurso con versionado
**Frases contextuales**:
- `excel`
  - Creando planilla con `rows`
  - Aplicando formato tabular
  - Guardando XLSX seguro
- `pdf`
  - Renderizando `summary_message`
  - Aplicando layout profesional
  - Exportando PDF final
- `reporte`
  - Estructurando `recommendation`
  - Insertando KPIs en el documento
  - Publicando reporte versionado
- `guardar`
  - Confirmando ruta `artifact_path`
  - Escribiendo archivo en disco
  - Validando hash de integridad
- `crear`
  - Inicializando documento base
  - Configurando formato estándar
  - Cargando contenido inicial

## Capi Noticias (`news_analysis`)
**Aliases**: `news_analysis`, `capi_noticias`, `capinoticias`
**Frase por defecto**: Analizando fuentes externas
**Secuencia progresiva**:
- Ingeriendo feeds (`shared_artifacts.news`)
- Filtrando notas relevantes
- Resumiendo hallazgos (`summary`)
**Frases contextuales**:
- `mercado`
  - Revisando notas de mercado
  - Evaluando tendencias (`analysis`)
  - Destacando impacto financiero
- `alerta`
  - Buscando alertas críticas
  - Cuantificando riesgo (`metadata`)
  - Recomendando seguimiento
- `liquidez`
  - Revisando reportes de liquidez
  - Analizando flujos (`analysis`)
  - Resumiendo implicancias

## Summary Agent (`summary_generation`)
**Aliases**: `summary_generation`, `summary`
**Frase por defecto**: Elaborando resumen ejecutivo
**Secuencia progresiva**:
- Reuniendo artefactos asociados
- Analizando métricas (`response_metadata`)
- Redactando `summary_message`
**Frases contextuales**:
- `diario`
  - Tomando datos del día (`rows`)
  - Comparando contra plan (`metadata`)
  - Resaltando highlights diarios
- `mensual`
  - Comparando mes previo (`analysis`)
  - Detectando variaciones relevantes
  - Sugiriendo próximos pasos
- `total`
  - Consolidando cifras globales
  - Priorizando indicadores críticos
  - Cierre ejecutivo del resumen

## Branch Agent (`branch_analysis`)
**Aliases**: `branch_analysis`, `branch`
**Frase por defecto**: Evaluando desempeño de sucursal
**Secuencia progresiva**:
- Ingeriendo `analysis` de sucursal
- Calculando KPIs (`metrics`)
- Presentando hallazgos clave
**Frases contextuales**:
- `rendimiento`
  - Midiendo contra objetivos
  - Detectando gaps relevantes
  - Proponiendo mejoras en el resumen
- `comparar`
  - Comparando con pares (`analysis`)
  - Ubicando ranking en `metadata`
  - Ajustando prioridades operativas
- `tendencia`
  - Analizando tendencias históricas
  - Proyectando escenarios futuros
  - Resumiendo patrones recurrentes

## Anomaly Agent (`anomaly_detection`)
**Aliases**: `anomaly_detection`, `anomaly`
**Frase por defecto**: Monitoreando anomalías operativas
**Secuencia progresiva**:
- Ejecutando modelos ML (`analysis`)
- Analizando patrones fuera de norma
- Reportando riesgos priorizados
**Frases contextuales**:
- `transaccion`
  - Escaneando transacciones (`analysis`)
  - Detectando montos fuera de rango
  - Marcando revisión en `alerts`
- `alerta`
  - Revisando alertas recientes
  - Clasificando severidad (`alerts`)
  - Recomendando mitigación
- `irregular`
  - Investigando desviaciones detectadas
  - Etiquetando severidad (`analysis`)
  - Notificando al orquestador central

## SmallTalk Agent (`conversation`)
**Aliases**: `conversation`, `smalltalk`
**Frase por defecto**: Procesando tu mensaje
**Secuencia progresiva**:
- Entendiendo intención del usuario
- Generando respuesta en lenguaje natural
**Frases contextuales**:
- `hola`
  - Preparando saludo cercano
  - Respondiendo con cordialidad
- `ayuda`
  - Detectando necesidad puntual
  - Ofreciendo alternativas útiles
- `gracias`
  - Reconociendo el agradecimiento
  - Contestando con cortesía

## Fallback genérico
Estas frases se usan cuando no hay coincidencias de contexto para un agente registrado:
- Procesando información recibida
- Analizando contexto disponible
- Compilando respuesta clara


## Ejemplo de respuesta esperada

Capi DataB
Generando SELECT parametrizado...
Ejecutando `operation.sql` (saldos_sucursal)...
Serializando dataset (`export_file`)...
Capi ElCajas
Comparando con `analysis[*].theoretical_total`
Alertando gap en `headline`
Capi DataB
Ejecutando `operation.sql` (saldos_sucursal)...
Capi Desktop
Guardando XLSX seguro...