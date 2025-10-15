# Frases de Morphing Text para Nodos del Orquestador

## Secuencia Principal del Orquestador
Orden específico para la animación inicial:
1. **Identificando objetivo...**
2. **Evaluando contexto...**
3. **Razonando...**
4. **Diseñando estrategia...**
5. **Coordinando agentes...**

## Frases Completas por Nodo

### StartNode (Inicio)
- "Iniciando sistema..."
- "Conectando servicios..."
- "Preparando entorno..."
- "Verificando recursos..."
- "Activando módulos..."

### IntentNode (Clasificación de Intención)
- "Identificando objetivo..."
- "Clasificando consulta..."
- "Analizando intención..."
- "Detectando propósito..."
- "Interpretando solicitud..."
- "Decodificando mensaje..."
- "Reconociendo patrón..."

### ReActNode (Razonamiento + Acción)
- "Evaluando contexto..."
- "Recopilando métricas..."
- "Inspeccionando datos..."
- "Procesando información..."
- "Analizando variables..."
- "Examinando parámetros..."
- "Verificando condiciones..."

### ReasoningNode (Razonamiento Avanzado)
- "Razonando..."
- "Planificando pasos..."
- "Diseñando estrategia..."
- "Formulando respuesta..."
- "Construyendo lógica..."
- "Elaborando solución..."
- "Generando hipótesis..."

### SupervisorNode (Supervisión)
- "Supervisando flujo..."
- "Coordinando agentes..."
- "Asignando tareas..."
- "Verificando recursos..."
- "Distribuyendo carga..."
- "Sincronizando procesos..."
- "Monitoreando estado..."

### RouterNode (Enrutamiento)
- "Enrutando consulta..."
- "Seleccionando agente..."
- "Dirigiendo petición..."
- "Optimizando ruta..."
- "Determinando destino..."
- "Estableciendo conexión..."
- "Priorizando canal..."

### HumanGateNode (Validación Humana)
- "Validando respuesta..."
- "Verificando calidad..."
- "Revisando resultados..."
- "Confirmando precisión..."
- "Evaluando coherencia..."
- "Comprobando integridad..."

### AssembleNode (Ensamblado)
- "Ensamblando respuesta..."
- "Consolidando datos..."
- "Integrando resultados..."
- "Unificando información..."
- "Estructurando salida..."
- "Combinando elementos..."
- "Organizando contenido..."

### FinalizeNode (Finalización)
- "Finalizando proceso..."
- "Completando operación..."
- "Preparando entrega..."
- "Cerrando transacción..."
- "Confirmando éxito..."
- "Liberando recursos..."

## Frases para Agentes Especializados

### Capi DataB (Base de Datos)
- "Consultando base de datos..."
- "Ejecutando query..."
- "Recuperando registros..."
- "Accediendo a tablas..."
- "Filtrando resultados..."

### El Cajas (Operaciones de Sucursal)
- "Verificando cajas..."
- "Calculando saldos..."
- "Analizando sucursal..."
- "Procesando transacciones..."
- "Validando operaciones..."

### Capi Desktop (Operaciones de Escritorio)
- "Accediendo a archivos..."
- "Generando documento..."
- "Preparando exportación..."
- "Creando reporte..."
- "Guardando resultados..."

### Capi Noticias (Análisis de Noticias)
- "Buscando noticias..."
- "Analizando contenido..."
- "Extrayendo información..."
- "Evaluando relevancia..."
- "Procesando artículos..."

### Summary Agent (Resumen)
- "Generando resumen..."
- "Sintetizando datos..."
- "Compilando métricas..."
- "Calculando totales..."
- "Preparando vista general..."

### Branch Agent (Análisis de Sucursal)
- "Analizando sucursal..."
- "Evaluando rendimiento..."
- "Comparando métricas..."
- "Identificando tendencias..."
- "Calculando indicadores..."

### Anomaly Agent (Detección de Anomalías)
- "Detectando anomalías..."
- "Buscando irregularidades..."
- "Analizando patrones..."
- "Identificando outliers..."
- "Evaluando desviaciones..."

<<<<<<< HEAD
### SmallTalk Agent (Conversación)
=======
### Capi Gus (Conversación)
>>>>>>> origin/develop
- "Procesando saludo..."
- "Generando respuesta..."
- "Preparando mensaje..."
- "Construyendo diálogo..."
- "Formulando cortesía..."

## Animaciones y Tiempos

### Configuración de Animación Principal
- **Duración por palabra**: 1 segundo
- **Shimmer (brillo blanco)**: 2 pasadas antes del morphing
- **Dirección del shimmer**: Siempre de izquierda a derecha
- **Color inicial**: Naranja (#ff9a00)
- **Color final**: Cian (#00e5ff)
- **Transición**: El último mensaje queda en cian cuando termina el batch

### Configuración para Eventos de Agentes
- **Shimmer inicial**: 2 animaciones antes de cambiar
- **Espaciado**: Mínimo entre eventos (2px margin)
- **Color procesando**: Naranja con shimmer blanco
- **Color completado**: Cian sin animación
- **Tiempo entre eventos**: 300ms (simulado)