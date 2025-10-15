export interface NarrativePlanStep {
  id?: string;
  title?: string;
  description?: string;
  expected_output?: string;
  agent?: string;
}

export interface NarrativeAgentStep {
  agentKey: string;
  steps: string[];
}

type StepBuilder = (context: AgentContext) => string;

interface AgentContextDefinition {
  id: string;
  score: (context: AgentContext) => number;
  steps: StepBuilder[];
}

interface AgentNarrativeDefinition {
  contexts?: AgentContextDefinition[];
  sequence: StepBuilder[];
}

interface AgentContext {
  agentKey: string;
  normalizedAgent: string;
  actionType: string;
  artifact: any;
  planStep?: NarrativePlanStep;
  branchName?: string;
  tableName?: string;
  exportFileName?: string;
  fileName?: string;
  rowCount?: number;
  corpus: string;
}

// Mensajes de respaldo cuando ningun contexto coincide.
const FALLBACK_STEPS: string[] = [
  'Procesando informacion recibida',
  'Analizando contexto disponible',
  'Compilando respuesta clara'
];

// Prioridades numericas para ordenar los contextos de cada agente.
const PRIORIDAD_DATABASE = {
  OPERACION: 95,
  EXPORT: 90,
  SUCURSAL_OBJETIVO: 80,
  SALDO: 70,
  DISPOSITIVOS: 60,
  TRANSACCION: 50,
  TOTAL: 40,
  SUCURSAL: 30,
} as const;

const PRIORIDAD_ELCAJAS = {
  SALDO: 90,
  CANALES: 80,
  SUCURSAL_OBJETIVO: 70,
  CIERRE: 60,
  APERTURA: 50,
  TRANSACCION: 45,
} as const;

const MAX_AGENT_STEPS = 9;

// Mapea los nombres crudos de agentes al tipo de accion semantica que usa la UI.
const AGENT_ACTION_LOOKUP: Record<string, string> = {
  capidatab: 'database_query',
  capielcajas: 'branch_operations',
  capidesktop: 'desktop_operation',
  capinoticias: 'news_analysis',
  capigus: 'conversation',
  capi_gus: 'conversation',
  summary: 'conversation',
  branch: 'branch_analysis',
  anomaly: 'anomaly_detection',
};
const normalizeForSearch = (value: string): string => {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\x20-\x7E]/g, '');
};

// Recolecta fragmentos de texto plano en estructuras profundas para correr heuristicas de palabras clave.
const collectTextSamples = (value: unknown, bucket: string[], depth: number = 0): void => {
  if (!value || bucket.length >= 60 || depth > 3) {
    return;
  }

  if (typeof value === 'string') {
    const normalized = normalizeForSearch(value);
    if (normalized) {
      bucket.push(normalized);
    }
    return;
  }

  if (Array.isArray(value)) {
    for (let index = 0; index < value.length && bucket.length < 60; index += 1) {
      collectTextSamples(value[index], bucket, depth + 1);
    }
    return;
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    for (let index = 0; index < entries.length && bucket.length < 60; index += 1) {
      collectTextSamples(entries[index][1], bucket, depth + 1);
    }
  }
};

// Construye un corpus reutilizable con el artifact y el paso del plan para alimentar las puntuaciones.
const buildCorpus = (artifact: any, planStep?: NarrativePlanStep): string => {
  const samples: string[] = [];
  collectTextSamples(artifact?.summary_message, samples);
  collectTextSamples(artifact?.operation?.sql, samples);
  collectTextSamples(artifact?.operation?.metadata, samples);
  collectTextSamples(artifact?.planner_metadata, samples);
  collectTextSamples(artifact?.analysis, samples);
  collectTextSamples(artifact?.alerts, samples);
  collectTextSamples(artifact?.recommendations, samples);
  collectTextSamples(artifact?.recommendation, samples);
  collectTextSamples(artifact?.recommendation_files, samples);
  collectTextSamples(artifact?.rows, samples);
  collectTextSamples(artifact?.metadata, samples);
  collectTextSamples(artifact?.export_file, samples);
  collectTextSamples(artifact?.filename, samples);
  collectTextSamples(artifact?.file_name, samples);
  collectTextSamples(artifact?.output_filename, samples);

  if (planStep) {
    collectTextSamples(planStep.title, samples);
    collectTextSamples(planStep.description, samples);
    collectTextSamples(planStep.expected_output, samples);
  }

  return samples.join(' ');
};

// Ayudante simple que usan las reglas de puntuacion para detectar pistas en la narrativa del artifact.
const containsKeyword = (corpus: string, keywords: string[]): boolean => {
  if (!corpus) {
    return false;
  }
  return keywords.some(keyword => corpus.includes(normalizeForSearch(keyword)));
};

const extractFileName = (value?: string): string | undefined => {
  if (typeof value !== 'string') {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  const parts = trimmed.split(/[\\/]/);
  const candidate = parts[parts.length - 1];
  return candidate || undefined;
};

const getFileExtension = (fileName?: string): string | undefined => {
  if (!fileName) {
    return undefined;
  }
  const match = /\.([^.]+)$/.exec(fileName.trim());
  return match ? match[1].toLowerCase() : undefined;
};

const getBranchName = (artifact: any): string | undefined => {
  const candidates = [
    artifact?.operation?.metadata?.branch?.branch_name,
    artifact?.planner_metadata?.branch?.branch_name,
    artifact?.metadata?.branch?.branch_name,
    artifact?.analysis?.[0]?.branch_name,
    artifact?.alerts?.[0]?.branch_name,
    artifact?.alerts?.[0]?.payload?.branch_name
  ];
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }
  return undefined;
};

const getTableName = (artifact: any): string | undefined => {
  if (typeof artifact?.operation?.table === 'string') {
    const trimmed = artifact.operation.table.trim();
    if (trimmed) {
      return trimmed;
    }
  }
  if (typeof artifact?.operation?.metadata?.suggested_table === 'string') {
    const trimmed = artifact.operation.metadata.suggested_table.trim();
    if (trimmed) {
      return trimmed;
    }
  }
  return undefined;
};

const getExportFileName = (artifact: any): string | undefined => {
  return extractFileName(artifact?.export_file);
};

const getPrimaryFileName = (artifact: any, exportFileName?: string): string | undefined => {
  return extractFileName(
    artifact?.filename ??
    artifact?.file_name ??
    artifact?.output_filename ??
    exportFileName
  );
};

const getRowCount = (artifact: any): number | undefined => {
  if (typeof artifact?.rowcount === 'number') {
    return artifact.rowcount;
  }
  if (Array.isArray(artifact?.rows)) {
    return artifact.rows.length;
  }
  return undefined;
};
const buildAgentContext = (
  agentKey: string,
  artifact: any,
  planStep?: NarrativePlanStep
): AgentContext => {
  const normalizedAgent = agentKey.toLowerCase().replace(/[-_]/g, '');
  const exportFileName = getExportFileName(artifact);
  const planAgent = planStep?.agent?.toLowerCase()?.replace(/[-_]/g, '');
  const mappedAction = AGENT_ACTION_LOOKUP[normalizedAgent];
  const inferredAction = mappedAction || (planAgent ? (AGENT_ACTION_LOOKUP[planAgent] || planAgent) : undefined) || 'fallback';

  return {
    agentKey,
    normalizedAgent,
    actionType: inferredAction,
    artifact,
    planStep,
    branchName: getBranchName(artifact),
    tableName: getTableName(artifact),
    exportFileName,
    fileName: getPrimaryFileName(artifact, exportFileName),
    rowCount: getRowCount(artifact),
    corpus: buildCorpus(artifact, planStep)
  };
};

const ensureSteps = (builders: StepBuilder[] | undefined, context: AgentContext): string[] => {
  if (!builders || builders.length === 0) {
    return FALLBACK_STEPS.slice();
  }
  const steps = builders
    .map(builder => builder(context))
    .map(step => (typeof step === 'string' ? step.trim() : ''))
    .filter(step => step.length > 0);
  return steps.length > 0 ? steps : FALLBACK_STEPS.slice();
};

// Elige el contexto especializado con mayor puntaje o vuelve a la secuencia por defecto del agente.
const buildStepsForDefinition = (definition: AgentNarrativeDefinition | undefined, context: AgentContext): string[] => {
  if (!definition) {
    return FALLBACK_STEPS.slice();
  }

  const MAX_STEPS = MAX_AGENT_STEPS;
  const aggregated: string[] = [];
  const pushSteps = (steps: string[]) => {
    for (const step of steps) {
      if (!step || aggregated.includes(step)) {
        continue;
      }
      aggregated.push(step);
      if (aggregated.length >= MAX_STEPS) {
        break;
      }
    }
  };

  pushSteps(ensureSteps(definition.sequence, context));

  if (definition.contexts && aggregated.length < 6) {
    const scoredContexts = definition.contexts
      .map(candidate => ({ candidate, score: candidate.score(context) }))
      .filter(entry => entry.score > 0)
      .sort((a, b) => b.score - a.score);

    for (const entry of scoredContexts) {
      if (aggregated.length >= 6) {
        break;
      }
      const segment = ensureSteps(entry.candidate.steps, context);
      pushSteps(segment);
    }
  }

    if (aggregated.length > 0) {
    return aggregated.slice(0, MAX_AGENT_STEPS);
  }

  return FALLBACK_STEPS.slice();
};
// Plantillas narrativas por tipo de accion; cada definicion cuenta como relatar las tareas del agente.
const AGENT_DEFINITIONS: Record<string, AgentNarrativeDefinition> = {
  // capi_datab / flujos orientados a consultas SQL.
  database_query: {
    contexts: [
      {
        id: 'operacion',
        score: context => (typeof context.artifact?.operation?.operation === 'string' ? PRIORIDAD_DATABASE.OPERACION : 0),
        steps: [
          context => {
            const op = context.artifact?.operation?.operation || 'operacion';
            return `Definiendo operacion SQL (${op})`;
          },
          () => 'Confirmando integridad y permisos antes de ejecutar'
        ]
      },

      {
        id: 'export',
        score: context => (context.exportFileName ? PRIORIDAD_DATABASE.EXPORT : 0),
        steps: [
          () => 'Guardando dataset en workspace seguro',
          context => context.exportFileName
            ? `Archivo listo: ${context.exportFileName}`
            : 'Archivo listo en workspace'
        ]
      },
      {
        id: 'sucursal_objetivo',
        score: context => (context.branchName ? PRIORIDAD_DATABASE.SUCURSAL_OBJETIVO : 0),
        steps: [
          context => {
            const branch = context.branchName || 'sucursal objetivo';
            const table = context.tableName || 'saldos_sucursal';
            return `Filtrando ${table} por sucursal (${branch})`;
          },
          () => 'Consultando fila correspondiente en rows',
          () => 'Resumiendo KPIs de la sucursal en summary_message'
        ]
      },
      {
        id: 'saldo',
        score: context => (containsKeyword(context.corpus, ['saldo']) ? PRIORIDAD_DATABASE.SALDO : 0),
        steps: [
          context => context.branchName
            ? `Consultando saldo sucursal ${context.branchName}`
            : 'Consultando saldo en rows',
          context => context.branchName
            ? `Comparando contra planner_metadata de ${context.branchName}`
            : 'Comparando contra planner_metadata',
          () => 'Calculando saldo teorico (summary_message)'
        ]
      },
      {
        id: 'dispositivo',
        score: context => (containsKeyword(context.corpus, ['dispositivo', 'atm', 'pos']) ? PRIORIDAD_DATABASE.DISPOSITIVOS : 0),
        steps: [
          () => 'Consultando estado POS o ATM (rows)',
          () => 'Analizando heartbeats (metadata)',
          () => 'Resumiendo alertas de dispositivos'
        ]
      },
      {
        id: 'transaccion',
        score: context => (containsKeyword(context.corpus, ['transaccion', 'movimiento']) ? PRIORIDAD_DATABASE.TRANSACCION : 0),
        steps: [
          () => 'Listando transacciones (response_metadata)',
          () => 'Detectando outliers (planner_metadata)',
          () => 'Marcando revision en alerts'
        ]
      },
      {
        id: 'total',
        score: context => {
          if (typeof context.rowCount === 'number' && context.rowCount > 1) {
            return PRIORIDAD_DATABASE.TOTAL;
          }
          return containsKeyword(context.corpus, ['total', 'consolidado']) ? PRIORIDAD_DATABASE.TOTAL : 0;
        },
        steps: [
          () => 'Agregando montos (rows[*])',
          () => 'Calculando totales (summary_message)',
          () => 'Contrastando con planner_metadata'
        ]
      },
      {
        id: 'sucursal',
        score: context => (containsKeyword(context.corpus, ['sucursal', 'branch']) ? PRIORIDAD_DATABASE.SUCURSAL : 0),
        steps: [
          () => 'Normalizando identificador (branch_descriptor)',
          () => 'Filtrando registros en rows',
          () => 'Resumiendo dataset filtrado'
        ]
      }
    ],
    sequence: [
      () => 'Disenando script SQL a medida',
      context => {
        const table = context.tableName || 'tabla objetivo';
        return `Ejecutando consulta transaccional sobre ${table}`;
      },
      () => 'Consolidando evidencias en summary_message'
    ]
  },
  // El agente ElCajas razona sobre politicas de efectivo y distribucion por canal.
  branch_operations: {
    contexts: [
      {
        id: 'saldo',
        // Busca totales medidos/teoricos dentro del analysis de ElCajas.
        score: context => {
          const analysis = context.artifact?.analysis;
          const hasTotals = Array.isArray(analysis) && analysis.some(item => item && typeof item === 'object' && 'measured_total' in item);
          return hasTotals || containsKeyword(context.corpus, ['saldo']) ? PRIORIDAD_ELCAJAS.SALDO : 0;
        },
        steps: [
          () => 'Leyendo analysis[*].measured_total',
          () => 'Comparando con analysis[*].theoretical_total',
          () => 'Alertando gap en headline'
        ]
      },
      {
        id: 'caja',
        // Prioriza los desgloses por canal cuando hay recomendaciones.
        score: context => {
          const analysis = context.artifact?.analysis;
          const hasChannels = Array.isArray(analysis) && analysis.some(item => item && typeof item === 'object' && 'channels' in item);
          return hasChannels || containsKeyword(context.corpus, ['caja', 'canal']) ? PRIORIDAD_ELCAJAS.CANALES : 0;
        },
        steps: [
          () => 'Evaluando canales (analysis[*].channels)',
          () => 'Registrando incidencias en analysis',
          () => 'Ajustando acciones (recommendations)'
        ]
      },
      {
        id: 'sucursal_objetivo',
        // Se enfoca en la sucursal especifica que eligio el planner.
        score: context => (context.branchName ? PRIORIDAD_ELCAJAS.SUCURSAL_OBJETIVO : 0),
        steps: [
          context => `Filtrando analysis por ${context.branchName || 'sucursal objetivo'}`,
          () => 'Analizando flujo de la sucursal',
          () => 'Recomendando ajustes especificos (recommendations)'
        ]
      },
      {
        id: 'cierre',
        // Narra operaciones de cierre cuando el corpus menciona 'cierre'.
        score: context => (containsKeyword(context.corpus, ['cierre']) ? PRIORIDAD_ELCAJAS.CIERRE : 0),
        steps: [
          () => 'Contabilizando cierre (alerts_to_persist)',
          () => 'Conciliando datos_clave',
          () => 'Preparando resumen de cierre'
        ]
      },
      {
        id: 'apertura',
        // Narrativa equivalente para procedimientos de apertura.
        score: context => (containsKeyword(context.corpus, ['apertura']) ? PRIORIDAD_ELCAJAS.APERTURA : 0),
        steps: [
          () => 'Revisando estado inicial (analysis)',
          () => 'Validando fondos en channels',
          () => 'Notificando hallazgos en recommendation'
        ]
      },
      {
        id: 'transaccion',
        score: context => (containsKeyword(context.corpus, ['transaccion']) ? PRIORIDAD_ELCAJAS.TRANSACCION : 0),
        steps: [
          () => 'Procesando alert_operations',
          () => 'Detectando anomalias (analysis)',
          () => 'Ajustando ledger (alerts_to_persist)'
        ]
      }
    ],
    sequence: [
      () => 'Generando analisis (analysis)',
      () => 'Persistiendo alertas (alerts_to_persist)',
      () => 'Creando recomendacion (recommendation_artifact)'
    ]
  },
  // El agente Desktop arma instrucciones para las automatizaciones de Capi Desktop.
  desktop_operation: {
    contexts: [
      {
        id: 'excel',
        score: context => {
          const ext = getFileExtension(context.fileName);
          return ext === 'xlsx' || ext === 'xls' || containsKeyword(context.corpus, ['excel', 'planilla']) ? 8 : 0;
        },
        steps: [
          () => 'Creando planilla con rows',
          () => 'Aplicando formato tabular',
          () => 'Guardando XLSX seguro'
        ]
      },
      {
        id: 'pdf',
        score: context => (getFileExtension(context.fileName) === 'pdf' || containsKeyword(context.corpus, ['pdf']) ? 7 : 0),
        steps: [
          () => 'Renderizando summary_message',
          () => 'Aplicando layout profesional',
          () => 'Exportando PDF final'
        ]
      },
      {
        id: 'reporte',
        score: context => (containsKeyword(context.corpus, ['reporte', 'report']) ? 6 : 0),
        steps: [
          () => 'Estructurando recommendation',
          () => 'Insertando KPIs en el documento',
          () => 'Publicando reporte versionado'
        ]
      },
      {
        id: 'guardar',
        score: context => (containsKeyword(context.corpus, ['guardar', 'save']) ? 5 : 0),
        steps: [
          context => context.fileName
            ? `Confirmando ruta ${context.fileName}`
            : 'Confirmando ruta de guardado',
          () => 'Escribiendo archivo en disco',
          () => 'Validando hash de integridad'
        ]
      },
      {
        id: 'crear',
        score: context => (containsKeyword(context.corpus, ['crear', 'nuevo']) ? 4 : 0),
        steps: [
          () => 'Inicializando documento base',
          () => 'Configurando formato estandar',
          () => 'Cargando contenido inicial'
        ]
      }
    ],
    sequence: [
      () => 'Ensamblando contenido desde artefactos',
      context => context.fileName
        ? `Formateando archivo ${context.fileName}`
        : 'Formateando archivo segun filename',
      () => 'Guardando recurso con versionado'
    ]
  },
  // El agente Noticias resume fuentes externas de informacion.
  news_analysis: {
    contexts: [
      {
        id: 'mercado',
        score: context => (containsKeyword(context.corpus, ['mercado', 'market']) ? 6 : 0),
        steps: [
          () => 'Revisando notas de mercado',
          () => 'Evaluando tendencias (analysis)',
          () => 'Destacando impacto financiero'
        ]
      },
      {
        id: 'alerta',
        score: context => (containsKeyword(context.corpus, ['alerta', 'riesgo']) ? 5 : 0),
        steps: [
          () => 'Buscando alertas criticas',
          () => 'Cuantificando riesgo (metadata)',
          () => 'Recomendando seguimiento'
        ]
      },
      {
        id: 'liquidez',
        score: context => (containsKeyword(context.corpus, ['liquidez', 'liquidity']) ? 5 : 0),
        steps: [
          () => 'Revisando reportes de liquidez',
          () => 'Analizando flujos (analysis)',
          () => 'Resumiendo implicancias'
        ]
      }
    ],
    sequence: [
      () => 'Ingeriendo feeds (news)',
      () => 'Filtrando notas relevantes',
      () => 'Resumiendo hallazgos (summary)'
    ]
  },
  // El agente Capi Gus genera mensajes de recapitulación en lenguaje natural.
  conversation_summary: {
    contexts: [
      {
        id: 'diario',
        score: context => (containsKeyword(context.corpus, ['diario', 'dia', 'today']) ? 6 : 0),
        steps: [
          () => 'Tomando datos del dia (rows)',
          () => 'Comparando contra plan (metadata)',
          () => 'Resaltando highlights diarios'
        ]
      },
      {
        id: 'mensual',
        score: context => (containsKeyword(context.corpus, ['mensual', 'mes', 'monthly']) ? 6 : 0),
        steps: [
          () => 'Comparando mes previo (analysis)',
          () => 'Detectando variaciones relevantes',
          () => 'Sugiriendo proximos pasos'
        ]
      },
      {
        id: 'total',
        score: context => (containsKeyword(context.corpus, ['total', 'global']) ? 5 : 0),
        steps: [
          () => 'Consolidando cifras globales',
          () => 'Priorizando indicadores criticos',
          () => 'Cierre ejecutivo del resumen'
        ]
      }
    ],
    sequence: [
      () => 'Reuniendo artefactos asociados',
      () => 'Analizando metricas (response_metadata)',
      () => 'Redactando respuesta final'
    ]
  },
  // El agente Branch se centra en los KPI operativos de cada sucursal.
  branch_analysis: {
    contexts: [
      {
        id: 'rendimiento',
        score: context => (containsKeyword(context.corpus, ['rendimiento', 'performance']) ? 6 : 0),
        steps: [
          () => 'Midiendo contra objetivos',
          () => 'Detectando gaps relevantes',
          () => 'Proponiendo mejoras en el resumen'
        ]
      },
      {
        id: 'comparar',
        score: context => (containsKeyword(context.corpus, ['compar', 'benchmark']) ? 5 : 0),
        steps: [
          () => 'Comparando con pares (analysis)',
          () => 'Ubicando ranking en metadata',
          () => 'Ajustando prioridades operativas'
        ]
      },
      {
        id: 'tendencia',
        score: context => (containsKeyword(context.corpus, ['tendencia', 'trend']) ? 5 : 0),
        steps: [
          () => 'Analizando tendencias historicas',
          () => 'Proyectando escenarios futuros',
          () => 'Resumiendo patrones recurrentes'
        ]
      }
    ],
    sequence: [
      () => 'Ingeriendo analysis de sucursal',
      () => 'Calculando KPIs (metrics)',
      () => 'Presentando hallazgos clave'
    ]
  },
  // El agente Anomaly resalta outliers y alertas.
  anomaly_detection: {
    contexts: [
      {
        id: 'transaccion',
        score: context => (containsKeyword(context.corpus, ['transaccion', 'movimiento']) ? PRIORIDAD_DATABASE.TRANSACCION : 0),
        steps: [
          () => 'Escaneando transacciones (analysis)',
          () => 'Detectando montos fuera de rango',
          () => 'Marcando revision en alerts'
        ]
      },
      {
        id: 'alerta',
        score: context => (containsKeyword(context.corpus, ['alerta', 'riesgo']) ? 5 : 0),
        steps: [
          () => 'Revisando alertas recientes',
          () => 'Clasificando severidad (alerts)',
          () => 'Recomendando mitigacion'
        ]
      },
      {
        id: 'irregular',
        score: context => (containsKeyword(context.corpus, ['irregular', 'anomalia', 'outlier']) ? 5 : 0),
        steps: [
          () => 'Investigando desviaciones detectadas',
          () => 'Etiquetando severidad (analysis)',
          () => 'Notificando al orquestador central'
        ]
      }
    ],
    sequence: [
      () => 'Ejecutando modelos ML (analysis)',
      () => 'Analizando patrones fuera de norma',
      () => 'Reportando riesgos priorizados'
    ]
  },
  // Manejador de capi_gus / conversacion liviana.
  conversation: {
    contexts: [
      {
        id: 'hola',
        score: context => (containsKeyword(context.corpus, ['hola', 'buenas', 'hello']) ? 5 : 0),
        steps: [
          () => 'Preparando saludo cercano',
          () => 'Respondiendo con cordialidad'
        ]
      },
      {
        id: 'ayuda',
        score: context => (containsKeyword(context.corpus, ['ayuda', 'help']) ? 5 : 0),
        steps: [
          () => 'Detectando necesidad puntual',
          () => 'Ofreciendo alternativas utiles'
        ]
      },
      {
        id: 'gracias',
        score: context => (containsKeyword(context.corpus, ['gracias', 'thanks']) ? 5 : 0),
        steps: [
          () => 'Reconociendo el agradecimiento',
          () => 'Contestando con cortesia'
        ]
      }
    ],
    sequence: [
      () => 'Entendiendo intencion del usuario',
      () => 'Generando respuesta en lenguaje natural'
    ]
  }
};
const normalizeAgentKey = (value: string): string => value.toLowerCase().replace(/[-_]/g, '');

const orderArtifacts = (artifacts: Record<string, any>, planSteps?: NarrativePlanStep[]): string[] => {
  const keys = Object.keys(artifacts);
  if (keys.length === 0) {
    return [];
  }

  const normalizedMap = new Map<string, string>();
  keys.forEach(key => {
    normalizedMap.set(normalizeAgentKey(key), key);
  });

  const ordered: string[] = [];
  const seen = new Set<string>();

  if (Array.isArray(planSteps)) {
    planSteps.forEach(step => {
      if (!step || typeof step.agent !== 'string') {
        return;
      }
      const normalized = normalizeAgentKey(step.agent);
      const match = normalizedMap.get(normalized);
      if (match && !seen.has(match)) {
        ordered.push(match);
        seen.add(match);
      }
    });
  }

  keys.forEach(key => {
    if (!seen.has(key)) {
      ordered.push(key);
      seen.add(key);
    }
  });

  return ordered;
};

export const buildNarrativeAgentSteps = (
  artifacts: Record<string, any>,
  planSteps?: NarrativePlanStep[]
): NarrativeAgentStep[] => {
  const orderedKeys = orderArtifacts(artifacts, planSteps);
  const planLookup = new Map<string, NarrativePlanStep>();

  if (Array.isArray(planSteps)) {
    planSteps.forEach(step => {
      if (step && typeof step.agent === 'string') {
        const normalized = normalizeAgentKey(step.agent);
        if (!planLookup.has(normalized)) {
          planLookup.set(normalized, step);
        }
      }
    });
  }

  const results: NarrativeAgentStep[] = [];

  orderedKeys.forEach(agentKey => {
    const artifact = artifacts[agentKey];
    if (!artifact) {
      return;
    }

    const normalizedAgent = normalizeAgentKey(agentKey);
    const planStep = planLookup.get(normalizedAgent);
    const context = buildAgentContext(agentKey, artifact, planStep);

    const definition = AGENT_DEFINITIONS[context.actionType];
    const steps = buildStepsForDefinition(definition, context).slice(0, MAX_AGENT_STEPS);

    results.push({
      agentKey,
      steps
    });
  });

  return results;
};





