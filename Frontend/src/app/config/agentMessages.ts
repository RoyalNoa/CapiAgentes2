/**
 * Sistema de mensajes ultra-descriptivos para agentes CAPI
 * Diseñado para usuarios no técnicos con feedback rico y contextual
 */

export interface AgentMessage {
  default: string;
  contextual: {
    [keyword: string]: string[];
  };
  progressive?: string[]; // Mensajes que se muestran secuencialmente
}

// Mapeo de action types a mensajes descriptivos
export const AGENT_MESSAGES: Record<string, AgentMessage> = {
  // Capi DataB - Base de datos (múltiples variantes del nombre)
  'database_query': {
    default: 'Accediendo al sistema financiero...',
    contextual: {
      'saldo': [
        'Conectando con sistema financiero central...',
        'Accediendo a registros de saldos...',
        'Calculando totales disponibles...'
      ],
      'palermo': [
        'Localizando sucursal Palermo (SUC-404)...',
        'Accediendo a base de datos de Palermo...',
        'Recuperando información actualizada...'
      ],
      'sucursal': [
        'Buscando información de sucursales...',
        'Filtrando registros por ubicación...',
        'Procesando datos encontrados...'
      ],
      'total': [
        'Sumando valores registrados...',
        'Calculando montos totales...',
        'Consolidando información financiera...'
      ],
      'transaccion': [
        'Buscando movimientos recientes...',
        'Analizando historial de transacciones...',
        'Verificando operaciones del día...'
      ],
      'export': [
        'Preparando datos para exportación...',
        'Formateando información solicitada...',
        'Generando archivo de datos...'
      ],
      'dispositivo': [
        'Consultando estado de dispositivos...',
        'Verificando terminales activas...',
        'Recopilando información de equipos...'
      ]
    },
    progressive: [
      'Estableciendo conexión segura...',
      'Autenticando credenciales...',
      'Ejecutando consulta...'
    ]
  },

  // El Cajas - Operaciones de sucursal
  'branch_operations': {
    default: 'Verificando operaciones de sucursal...',
    contextual: {
      'saldo': [
        'Conectando con terminal de cajas...',
        'Verificando efectivo disponible...',
        'Sumando denominaciones de billetes...'
      ],
      'caja': [
        'Accediendo a sistema de cajas...',
        'Verificando cajas operativas...',
        'Contabilizando efectivo por caja...'
      ],
      'palermo': [
        'Conectando con sucursal Palermo...',
        'Verificando 5 cajas registradas...',
        'Procesando información de cajas...'
      ],
      'cierre': [
        'Iniciando proceso de cierre...',
        'Contabilizando operaciones del día...',
        'Generando resumen de cierre...'
      ],
      'apertura': [
        'Verificando condiciones de apertura...',
        'Validando montos iniciales...',
        'Habilitando cajas para operación...'
      ],
      'transaccion': [
        'Revisando transacciones pendientes...',
        'Validando operaciones en curso...',
        'Actualizando registros de caja...'
      ]
    },
    progressive: [
      'Sincronizando con sucursal...',
      'Validando información...',
      'Procesando datos de cajas...'
    ]
  },

  // Capi Desktop - Operaciones de escritorio
  'desktop_operation': {
    default: 'Preparando archivo en escritorio...',
    contextual: {
      'excel': [
        'Creando archivo Excel...',
        'Aplicando formato de tabla...',
        'Guardando en escritorio...'
      ],
      'pdf': [
        'Generando documento PDF...',
        'Aplicando formato profesional...',
        'Finalizando documento...'
      ],
      'reporte': [
        'Estructurando reporte ejecutivo...',
        'Añadiendo gráficos y tablas...',
        'Guardando reporte finalizado...'
      ],
      'guardar': [
        'Preparando ubicación de guardado...',
        'Escribiendo archivo en disco...',
        'Confirmando guardado exitoso...'
      ],
      'crear': [
        'Creando nuevo documento...',
        'Configurando formato inicial...',
        'Preparando contenido...'
      ]
    },
    progressive: [
      'Verificando espacio en disco...',
      'Preparando estructura del archivo...',
      'Escribiendo información...'
    ]
  },

  // Capi Noticias - Análisis de noticias
  'news_analysis': {
    default: 'Analizando noticias relevantes...',
    contextual: {
      'mercado': [
        'Buscando noticias del mercado...',
        'Analizando tendencias actuales...',
        'Evaluando impacto financiero...'
      ],
      'alerta': [
        'Verificando alertas del sistema...',
        'Analizando notificaciones críticas...',
        'Priorizando información urgente...'
      ],
      'liquidez': [
        'Evaluando indicadores de liquidez...',
        'Analizando flujo de efectivo...',
        'Verificando disponibilidad de fondos...'
      ]
    },
    progressive: [
      'Conectando con fuentes de noticias...',
      'Filtrando información relevante...',
      'Analizando contenido...'
    ]
  },

  // Summary Agent - Resumen financiero
  'summary_generation': {
    default: 'Generando resumen financiero...',
    contextual: {
      'diario': [
        'Recopilando datos del día...',
        'Calculando métricas principales...',
        'Preparando resumen ejecutivo...'
      ],
      'mensual': [
        'Analizando tendencias del mes...',
        'Comparando con período anterior...',
        'Identificando variaciones importantes...'
      ],
      'total': [
        'Consolidando información global...',
        'Calculando totales generales...',
        'Preparando vista integral...'
      ]
    },
    progressive: [
      'Recopilando información...',
      'Analizando datos...',
      'Generando resumen...'
    ]
  },

  // Branch Agent - Análisis de sucursal
  'branch_analysis': {
    default: 'Analizando rendimiento de sucursal...',
    contextual: {
      'rendimiento': [
        'Evaluando métricas de rendimiento...',
        'Comparando con objetivos...',
        'Identificando áreas de mejora...'
      ],
      'comparar': [
        'Comparando con otras sucursales...',
        'Analizando diferencias clave...',
        'Evaluando posición relativa...'
      ],
      'tendencia': [
        'Identificando tendencias históricas...',
        'Proyectando comportamiento futuro...',
        'Analizando patrones recurrentes...'
      ]
    },
    progressive: [
      'Cargando datos históricos...',
      'Procesando métricas...',
      'Generando análisis...'
    ]
  },

  // Anomaly Agent - Detección de anomalías
  'anomaly_detection': {
    default: 'Buscando irregularidades...',
    contextual: {
      'transaccion': [
        'Escaneando transacciones inusuales...',
        'Verificando montos atípicos...',
        'Identificando patrones sospechosos...'
      ],
      'alerta': [
        'Verificando alertas de seguridad...',
        'Analizando eventos críticos...',
        'Evaluando nivel de riesgo...'
      ],
      'irregular': [
        'Detectando operaciones irregulares...',
        'Analizando desviaciones...',
        'Clasificando por severidad...'
      ]
    },
    progressive: [
      'Aplicando algoritmos de detección...',
      'Analizando patrones...',
      'Evaluando resultados...'
    ]
  },

  // SmallTalk Agent - Conversación
  'conversation': {
    default: 'Procesando tu mensaje...',
    contextual: {
      'hola': [
        'Preparando un saludo amistoso...',
        'Generando respuesta cordial...'
      ],
      'ayuda': [
        'Identificando cómo puedo ayudarte...',
        'Preparando información útil...'
      ],
      'gracias': [
        'Procesando agradecimiento...',
        'Preparando respuesta cortés...'
      ]
    },
    progressive: [
      'Interpretando mensaje...',
      'Formulando respuesta...'
    ]
  }
};

// Agregar mapeos adicionales para nombres reales de agentes
AGENT_MESSAGES['capi_datab'] = AGENT_MESSAGES['database_query'];
AGENT_MESSAGES['capidatab'] = AGENT_MESSAGES['database_query'];
AGENT_MESSAGES['capi_elcajas'] = AGENT_MESSAGES['branch_operations'];
AGENT_MESSAGES['capielcajas'] = AGENT_MESSAGES['branch_operations'];
AGENT_MESSAGES['capi_desktop'] = AGENT_MESSAGES['desktop_operation'];
AGENT_MESSAGES['capidesktop'] = AGENT_MESSAGES['desktop_operation'];
AGENT_MESSAGES['capi_noticias'] = AGENT_MESSAGES['news_analysis'];
AGENT_MESSAGES['capinoticias'] = AGENT_MESSAGES['news_analysis'];
AGENT_MESSAGES['summary'] = AGENT_MESSAGES['summary_generation'];
AGENT_MESSAGES['branch'] = AGENT_MESSAGES['branch_analysis'];
AGENT_MESSAGES['anomaly'] = AGENT_MESSAGES['anomaly_detection'];
AGENT_MESSAGES['smalltalk'] = AGENT_MESSAGES['conversation'];

/**
 * Obtiene mensajes contextuales basados en el query del usuario
 */
export function getContextualMessages(
  actionType: string,
  query: string,
  agentName?: string
): string[] {
  // Normalizar el actionType (minúsculas y sin guiones)
  const normalizedAction = actionType.toLowerCase().replace(/[-_]/g, '');

  const config = AGENT_MESSAGES[normalizedAction] || AGENT_MESSAGES[actionType];
  if (!config) {
    // Si no se encuentra, dar mensajes por defecto más descriptivos
    return [
      'Procesando solicitud...',
      'Analizando información...',
      'Preparando respuesta...'
    ];
  }

  const queryLower = query.toLowerCase();

  // Buscar coincidencias con keywords
  for (const [keyword, messages] of Object.entries(config.contextual)) {
    if (queryLower.includes(keyword)) {
      return messages;
    }
  }

  // Si no hay coincidencias, usar progressive o default
  return config.progressive || [config.default];
}

/**
 * Obtiene un mensaje específico para mostrar inmediatamente
 */
export function getInstantMessage(
  actionType: string,
  query: string,
  messageIndex: number = 0
): string {
  const messages = getContextualMessages(actionType, query);
  return messages[Math.min(messageIndex, messages.length - 1)];
}

/**
 * Mapeo de nombres de agentes a nombres amigables
 */
export const AGENT_FRIENDLY_NAMES: Record<string, string> = {
  'capi_datab': 'Sistema Financiero',
  'capi_elcajas': 'Control de Cajas',
  'capi_desktop': 'Gestor de Archivos',
  'capi_noticias': 'Monitor de Noticias',
  'summary': 'Analizador General',
  'branch': 'Evaluador de Sucursales',
  'anomaly': 'Detector de Anomalías',
  'smalltalk': 'Asistente Virtual'
};