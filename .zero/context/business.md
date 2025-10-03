# Plataforma Multiagente CAPI - Contexto de Negocio

## Entorno de mercado
CapiAgentes opera dentro de instituciones financieras que manejan grandes volúmenes de datos transaccionales, métricas de desempeño por sucursal y obligaciones de cumplimiento. Los equipos confían en análisis automatizados mientras mantienen supervisión estricta, trazabilidad y segregación de funciones.

## Propuesta de valor
- Insights consolidados provenientes de múltiples agentes especializados (resumen, sucursales, anomalías, documentos).
- Recomendaciones automatizadas con validación humana y controles de privilegios.
- Monitoreo en tiempo real mediante el dashboard PantallaAgentes y métricas por WebSocket.
- Operaciones documentales seguras (CSV, Excel, Word) con salvaguardas de seguridad y respaldos.
- Arquitectura extensible que permite sumar nuevos agentes analíticos sin reescribir los sistemas centrales.

## Flujos asistidos
1. **Revisión de desempeño por sucursal**
   - Usuario: gerente regional de operaciones.
   - Flujo: solicita insights de sucursal -> el orquestador enruta al agente Branch -> resultados alimentan dashboards y alertas.
   - Resultado: ranking accionable de sucursales con contexto sobre desvíos.

2. **Detección de anomalías financieras**
   - Usuario: analista de riesgo.
   - Flujo: programa escaneos de anomalías -> el agente Anomaly analiza datos -> notificaciones aparecen en dashboard + API -> tareas de seguimiento registradas.
   - Resultado: anomalías críticas detectadas en minutos, con severidad y recomendaciones.

3. **Generación de resumen ejecutivo**
   - Usuario: líder financiero preparando reportes.
   - Flujo: invoca al agente Summary -> agrega métricas + narrativa -> puede alimentar al generador de documentos.
   - Resultado: una solicitud devuelve distribución por producto, sucursal y periodo.

4. **Operaciones de documentos seguras**
   - Usuario: especialista en documentos.
   - Flujo: envía petición al Capi Desktop -> el agente realiza lecturas/escrituras validadas en carpetas aprobadas -> devuelve un resumen y el registro de auditoría.
   - Resultado: cero accesos no autorizados y respaldos automáticos en `workspace/data/backups/`.

## Stakeholders
- **Operaciones**: garantizan disponibilidad, gestionan privilegios de agentes, responden a alertas.
- **Riesgo & Compliance**: validan logs de auditoría, escalaciones de privilegios y políticas de retención.
- **Ingeniería**: mantienen orquestador, agentes, pipelines, pruebas y documentación.
- **Patrocinadores ejecutivos**: monitorean KPIs y adopción a través de dashboards y reportes.

## Paisaje de datos
- Datos financieros estructurados (CSV, vistas de base) ingeridos via capa de persistencia (`Backend/src/infrastructure/persistence`).
- Archivos JSON de configuración bajo `Backend/ia_workspace/data/` que controlan capacidades, ruteo y privilegios de agentes.
- Esquema PostgreSQL (`Backend/database/`) con tablas para agentes, privilegios, cargas y registros históricos.
- Logs en `Backend/logs/` con políticas de rotación definidas en `Backend/src/core/logging_config.json`.

## Guardrails de cumplimiento
- Toda operación de escritura valida privilegios antes de ejecutarse.
- No se permiten llamadas de red directas desde agentes; las integraciones pasan por servicios controlados.
- Información sensible se anonimiza en logs; solo métricas agregadas o hasheadas.
- Operaciones documentales mantienen respaldos con marcas de tiempo en `workspace/data/backups/`.
- Cada ejecución de agente incorpora metadatos de trazabilidad para auditoría.

## Métricas clave de negocio
- Tasa diaria de éxitos vs. fallos por agente.
- Tiempo medio para detectar anomalías tras la ingesta de datos.
- Volumen de acciones privilegiadas (escritura de documentos, operaciones admin).
- Número de sesiones de dashboard y tiempo de respuesta de actualizaciones WebSocket.
- Cumplimiento de SLA para disponibilidad backend y tasas de error API.

## Diferenciadores competitivos
- Integración profunda entre orquestador, agentes y visualizaciones de PantallaAgentes.
- Playbooks predefinidos para incorporar agentes, flujos y componentes UI.
- Modelo de seguridad basado en privilegios dinámicos en lugar de roles estáticos.
- Documentación integral en `AI/` y `.zero/` que facilita onboarding asistido por IA.

Última actualización: 18/09/2025 (curado por humanos).
