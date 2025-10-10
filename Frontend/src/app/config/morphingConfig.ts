/**
 * Configuración centralizada de frases de morphing text
 * Basado en docs/MORPHING_TEXT_PHRASES.md
 */

// Secuencia principal del orquestador - Orden específico
export const ORCHESTRATOR_SEQUENCE = [
  'Identificando objetivo...',
  'Evaluando contexto...',
  'Razonando...',
  'Diseñando estrategia...',
  'Coordinando agentes...'
] as const;

// Frases por nodo del orquestador
export const NODE_PHRASES = {
  start: [
    'Iniciando sistema...',
    'Conectando servicios...',
    'Preparando entorno...',
    'Verificando recursos...',
    'Activando módulos...'
  ],
  intent: [
    'Identificando objetivo...',
    'Clasificando consulta...',
    'Analizando intención...',
    'Detectando propósito...',
    'Interpretando solicitud...',
    'Decodificando mensaje...',
    'Reconociendo patrón...'
  ],
  react: [
    'Evaluando contexto...',
    'Recopilando métricas...',
    'Inspeccionando datos...',
    'Procesando información...',
    'Analizando variables...',
    'Examinando parámetros...',
    'Verificando condiciones...'
  ],
  reasoning: [
    'Razonando...',
    'Planificando pasos...',
    'Diseñando estrategia...',
    'Formulando respuesta...',
    'Construyendo lógica...',
    'Elaborando solución...',
    'Generando hipótesis...'
  ],
  supervisor: [
    'Supervisando flujo...',
    'Coordinando agentes...',
    'Asignando tareas...',
    'Verificando recursos...',
    'Distribuyendo carga...',
    'Sincronizando procesos...',
    'Monitoreando estado...'
  ],
  router: [
    'Enrutando consulta...',
    'Seleccionando agente...',
    'Dirigiendo petición...',
    'Optimizando ruta...',
    'Determinando destino...',
    'Estableciendo conexión...',
    'Priorizando canal...'
  ],
  humanGate: [
    'Validando respuesta...',
    'Verificando calidad...',
    'Revisando resultados...',
    'Confirmando precisión...',
    'Evaluando coherencia...',
    'Comprobando integridad...'
  ],
  assemble: [
    'Ensamblando respuesta...',
    'Consolidando datos...',
    'Integrando resultados...',
    'Unificando información...',
    'Estructurando salida...',
    'Combinando elementos...',
    'Organizando contenido...'
  ],
  finalize: [
    'Finalizando proceso...',
    'Completando operación...',
    'Preparando entrega...',
    'Cerrando transacción...',
    'Confirmando éxito...',
    'Liberando recursos...'
  ]
} as const;

// Frases por agente especializado
export const AGENT_PHRASES = {
  capidatab: [
    'Consultando base de datos...',
    'Ejecutando query...',
    'Recuperando registros...',
    'Accediendo a tablas...',
    'Filtrando resultados...'
  ],
  capielcajas: [
    'Verificando cajas...',
    'Calculando saldos...',
    'Analizando sucursal...',
    'Procesando transacciones...',
    'Validando operaciones...'
  ],
  capidesktop: [
    'Accediendo a archivos...',
    'Generando documento...',
    'Preparando exportación...',
    'Creando reporte...',
    'Guardando resultados...'
  ],
  capinoticias: [
    'Buscando noticias...',
    'Analizando contenido...',
    'Extrayendo información...',
    'Evaluando relevancia...',
    'Procesando artículos...'
  ],
  summary: [
    'Generando resumen...',
    'Sintetizando datos...',
    'Compilando métricas...',
    'Calculando totales...',
    'Preparando vista general...'
  ],
  branch: [
    'Analizando sucursal...',
    'Evaluando rendimiento...',
    'Comparando métricas...',
    'Identificando tendencias...',
    'Calculando indicadores...'
  ],
  anomaly: [
    'Detectando anomalías...',
    'Buscando irregularidades...',
    'Analizando patrones...',
    'Identificando outliers...',
    'Evaluando desviaciones...'
  ],
  capi_gus: [
    'Procesando saludo...',
    'Generando respuesta...',
    'Preparando mensaje...',
    'Construyendo diálogo...',
    'Formulando cortesía...'
  ]
} as const;

// Configuración de animación
export const ANIMATION_CONFIG = {
  // Duración por palabra
  wordDuration: 1000, // 1 segundo

  // Shimmer (brillo blanco)
  shimmerPasses: 2,
  shimmerDirection: 'left-to-right',

  // Colores
  colors: {
    initial: '#ff9a00', // Naranja
    final: '#00e5ff',   // Cian
    processing: '#ff9a00',
    completed: '#00e5ff'
  },

  // Tiempos
  timings: {
    betweenWords: 2000,      // Entre palabras del morphing
    betweenEvents: 300,      // Entre eventos de agentes
    shimmerDuration: 1000,   // Duración de cada pasada del shimmer
    finalDisplay: 500,       // Tiempo que se muestra el texto final
    morphingDelay: 100       // Delay inicial antes de empezar
  },

  // Espaciado
  spacing: {
    eventMargin: 2 // px entre eventos
  }
} as const;

/**
 * Obtiene una frase aleatoria para un nodo específico
 */
export function getNodePhrase(nodeType: keyof typeof NODE_PHRASES): string {
  const phrases = NODE_PHRASES[nodeType];
  return phrases[Math.floor(Math.random() * phrases.length)];
}

/**
 * Obtiene una frase aleatoria para un agente específico
 */
export function getAgentPhrase(agentName: string): string {
  const normalizedAgent = agentName.toLowerCase().replace(/[-_]/g, '');
  const phrases = AGENT_PHRASES[normalizedAgent as keyof typeof AGENT_PHRASES];

  if (!phrases) {
    return 'Procesando...'; // Fallback genérico
  }

  return phrases[Math.floor(Math.random() * phrases.length)];
}

/**
 * Obtiene la secuencia completa del orquestador con variación opcional
 */
export function getOrchestratorSequence(randomize: boolean = false): readonly string[] {
  if (!randomize) {
    return ORCHESTRATOR_SEQUENCE;
  }

  // Crear una secuencia con frases aleatorias de los nodos correspondientes
  return [
    getNodePhrase('intent'),
    getNodePhrase('react'),
    getNodePhrase('reasoning'),
    getNodePhrase('supervisor'),
    getNodePhrase('router')
  ];
}

/**
 * Obtiene frases contextuales basadas en el tipo de acción
 */
export function getMorphingPhrasesForAction(actionType: string): string[] {
  // Mapeo de action types a nodos
  const actionToNode: Record<string, keyof typeof NODE_PHRASES> = {
    'identify': 'intent',
    'analyze': 'react',
    'reason': 'reasoning',
    'coordinate': 'supervisor',
    'route': 'router',
    'validate': 'humanGate',
    'assemble': 'assemble',
    'finalize': 'finalize'
  };

  const nodeType = actionToNode[actionType.toLowerCase()];
  if (nodeType) {
    return NODE_PHRASES[nodeType];
  }

  // Si no hay mapeo, usar la secuencia principal
  return [...ORCHESTRATOR_SEQUENCE];
}

/**
 * Tipo para las fases del morphing
 */
export type MorphingPhase = 'shimmer' | 'morph' | 'waiting' | 'final' | null;

/**
 * Configuración completa del morphing text
 */
export const MORPHING_CONFIG = {
  sequences: {
    orchestrator: ORCHESTRATOR_SEQUENCE,
    nodes: NODE_PHRASES,
    agents: AGENT_PHRASES
  },
  animation: ANIMATION_CONFIG,
  helpers: {
    getNodePhrase,
    getAgentPhrase,
    getOrchestratorSequence,
    getMorphingPhrasesForAction
  }
} as const;

export default MORPHING_CONFIG;