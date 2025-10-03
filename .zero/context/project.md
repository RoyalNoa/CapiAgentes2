# Plataforma Multiagente CAPI - Definición del Proyecto

## Visión
Entregar una plataforma financiera multiagente lista para producción que automatice insights de portafolio, analice sucursales y anomalías, y asista en manejo seguro de documentos. Cada interfaz debe reforzar la idea de agentes coordinados apoyando a equipos financieros en tiempo real.

## Objetivos de negocio
1. Proveer un backend FastAPI confiable que orqueste agentes, flujos y datos.
2. Ofrecer un dashboard Next.js responsivo (PantallaAgentes) para monitorear actividad, métricas y alertas.
3. Mantener interacciones auditables mediante controles de privilegios y logging centralizado.
4. Habilitar manipulación segura de documentos a través del flujo Capi Desktop.
5. Mantener la plataforma modular para añadir agentes y etapas de orquestación con baja fricción.

## Dominio del problema
- Razonamiento multiagente sobre datasets financieros normalizados (branch, summary, anomaly).
- Orquestación coordinada con pipelines LangGraph dentro del backend.
- Servicios reutilizables para estado conversacional, NLP, alertas y generación documental.
- Restricciones enterprise: sin llamadas de red externas en runtime, manejo privilegiado de datos, auditoría por diseño.

## Usuarios objetivo
- Analistas financieros que requieren insights consolidados por sucursal o línea de producto.
- Equipos de operaciones responsables de supervisar agentes y sus privilegios.
- Revisores de riesgo y compliance que auditan logs, trazas y controles de seguridad.
- Ingenieros de IA que extienden el orquestador con nuevos nodos, prompts o agentes.

## Métricas de éxito
- Disponibilidad backend >= 99% en horarios críticos.
- Mediana de ejecución de agentes < 300 ms con caché y < 2 s para análisis pesados.
- Frescura de datos en dashboard < 5 s (actualizaciones WebSocket).
- Cero incidentes críticos de seguridad vinculados a escalaciones de privilegios.
- Tiempo de onboarding de un agente nuevo <= 1 día hábil (código + docs + pruebas).

## Restricciones operativas
- Python 3.10+ con dependencias en `Backend/requirements.txt`.
- Frontend construido con Next.js 14 + React, TypeScript, Tailwind.
- Despliegue local vía `docker-commands.(ps1|sh)`.
- Base de datos: PostgreSQL con esquema en `Backend/database/` (schema.sql + seed_data.sql).
- Logging a través de `Backend/src/core/logging_config.json` escribiendo en `Backend/logs/`.
- Los agentes leen desde `Backend/ia_workspace/data/` y no introducen código ejecutable en esa carpeta.

## Flujo de información (alto nivel)
```
Fuentes de datos (CSV/DB) --> Adaptadores de ingesta backend --> Servicios de dominio -->
Orquestador LangGraph --> Agentes --> Respuestas (API) --> Dashboard frontend
                                           \--> Generación de documentos
```

## Principios arquitectónicos
1. Preservar el layering hexagonal en `Backend/src/` (domain -> application -> infrastructure/presentation).
2. Mantener la lógica de orquestación en infrastructure/langgraph y exponer solo contratos a agentes.
3. Tratar `Backend/ia_workspace/` como espacio dinámico: agentes + datos, sin lógica compartida.
4. Frontend consume APIs del backend; nunca acoplarse a internals de agentes.
5. Cada cambio debe ser trazable mediante logging, pruebas y documentación actualizada.

## Notas de estado
- El proyecto ya cuenta con pruebas de nivel producción en `Backend/tests/` cubriendo orquestador, agentes y servicios.
- La documentación de PantallaAgentes vive en `AI/Tablero/PantallaAgentes/` y debe consultarse para trabajo UI.
- Los artefactos `.zero` son la referencia de estructura, conflictos y ZeroGraph.

Última actualización: 18/09/2025 (curado por humanos).
