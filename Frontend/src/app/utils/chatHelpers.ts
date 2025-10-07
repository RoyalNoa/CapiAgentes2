import { Message } from '@/app/types/chat';
import type { AgentEvent } from '@/app/hooks/useAgentWebSocket';

// Tipo comn para payloads de eventos de agente
export type AgentEventPayload = {
  type?: string;
  actor?: string;
  action?: string;
  summary?: string;
  tone?: string;
  event?: any;
  data?: any;
};

/**
 * Verifica si un mensaje es un evento de agente
 */
export function isAgentEvent(payload: AgentEventPayload | undefined): boolean {
  if (!payload) return false;
  return payload.type === 'agent_event' || payload.type === 'agent_event_header';
}

/**
 * Extrae el payload de evento de un mensaje
 */
export function getEventPayload(msg: any): AgentEventPayload | undefined {
  const maybePayload = (msg as Message)?.payload as AgentEventPayload | undefined;
  if (maybePayload) {
    return maybePayload;
  }

  if (isRawAgentEvent(msg)) {
    const data = msg.data ?? {};
    const meta = msg.meta ?? {};
    return {
      type: 'agent_event',
      actor: msg.agent,
      action: data?.action ?? meta?.action,
      summary: meta?.content ?? data?.summary ?? data?.message,
      detail: meta?.detail ?? data?.detail,
      tone: meta?.tone,
      event: { type: msg.type, data, meta },
      data,
    } as AgentEventPayload;
  }

  return undefined;
}

/**
 * Extrae el nombre del agente/actor del mensaje
 */
export function getAgentName(msg: Message): string {
  const payload = getEventPayload(msg);
  return (payload?.actor || msg.agent || '').toLowerCase();
}

/**
 * Verifica si un agente es de orquestacin
 */
export function isOrchestrationAgent(agent: string): boolean {
  const orchestrationAgents = [
    'orchestrator', 'router', 'intent', 'start', 'finalize',
    'assemble', 'react', 'reasoning', 'supervisor', 'system', 'capi'
  ];
  const normalizedAgent = agent.toLowerCase();
  if (orchestrationAgents.includes(normalizedAgent)) {
    return true;
  }
  return normalizedAgent.startsWith('loop') || normalizedAgent.endsWith('controller') || normalizedAgent === 'finalizenode';
}

/**
 * Filtra eventos de agentes (excluyendo orquestacin)
 */
export function filterAgentEvents(messages: any[]): Message[] {
  const results: Message[] = [];

  messages.forEach((msg) => {
    if (isRawAgentEvent(msg)) {
      const payload = getEventPayload(msg);
      if (!payload || payload.type !== 'agent_event') {
        return;
      }
      const synthetic: Message = {
        id: msg.id ?? `agent-event-${payload.actor ?? 'agent'}-${msg.timestamp ?? Date.now()}` ,
        agent: payload.actor || msg.agent || '',
        role: 'agent',
        payload,
        meta: msg.meta,
        content: typeof payload.summary === 'string' ? payload.summary : undefined,
      } as Message;
      results.push(synthetic);
      return;
    }

    const payload = getEventPayload(msg as Message);
    if (!payload || payload.type !== 'agent_event') {
      return;
    }

    const agent = getAgentName(msg as Message);
    if (agent && !isOrchestrationAgent(agent)) {
      results.push(msg as Message);
    }
  });

  return results;
}

/**
 * Filtra mensajes regulares (no eventos)
 */
export function filterRegularMessages(messages: any[]): any[] {
  return messages.filter(msg => {
    const payload = getEventPayload(msg);
    // Aceptar mensajes con content O text (para compatibilidad con ambos formatos)
    return !isAgentEvent(payload) && (msg.content || msg.text);
  });
}

/**
 * Obtiene el action type del evento
 * VERSIN MEJORADA: Incluye mapeo completo de agentes
 */
export function getActionType(msg: Message): string {
  const payload = getEventPayload(msg);

  // Primero intentar obtener del data del evento
  if (payload?.data?.action) {
    return payload.data.action;
  }

  // Luego intentar del event
  if (payload?.event?.data?.action) {
    return payload.event.data.action;
  }

  // Si hay action directo en payload
  if (payload?.action) {
    return payload.action;
  }

  // Mapeo por defecto basado en el nombre del agente
  const agent = (payload?.actor || (msg as any).agent || '').toLowerCase();
  const normalizedAgent = agent.replace(/[-_]/g, '');

  // Mapeo completo incluyendo variantes con/sin guiones
  const actionMap: Record<string, string> = {
    'capidatab': 'database_query',
    'capielcajas': 'branch_operations',
    'capidesktop': 'desktop_operation',
    'capinoticias': 'news_analysis',
    'summary': 'summary_generation',
    'branch': 'branch_analysis',
    'anomaly': 'anomaly_detection',
    'smalltalk': 'conversation'
  };

  return actionMap[normalizedAgent] || 'agent_processing';
}

/**
 * Normaliza el nombre del agente para mapeo
 */
export function normalizeAgentName(agent: string): string {
  return agent.toLowerCase().replace(/[-_]/g, '');
}

// Mapeo de nombres de agentes a action types
const ACTION_TYPE_MAP: Record<string, string> = {
  'capidatab': 'database_query',
  'capielcajas': 'branch_operations',
  'capidesktop': 'desktop_operation',
  'capinoticias': 'news_analysis',
  'summary': 'summary_generation',
  'branch': 'branch_analysis',
  'anomaly': 'anomaly_detection',
  'smalltalk': 'conversation'
};

/**
 * Obtiene el action type basado en el nombre del agente
 */
export function getActionTypeForAgent(agent: string): string {
  const normalized = normalizeAgentName(agent);
  return ACTION_TYPE_MAP[normalized] || 'process';
}

/**
 * Helper para construir clases CSS condicionales
 */
export function getConditionalClass(
  base: string,
  conditions: Record<string, boolean>
): string {
  const classes = [base];
  Object.entries(conditions).forEach(([className, condition]) => {
    if (condition && className) {
      classes.push(className);
    }
  });
  return classes.filter(Boolean).join(' ');
}

/**
 * Helper para clases de morphing
 */
export function getMorphingClasses(
  styles: any,
  phase: 'shimmer' | 'morph' | 'waiting' | 'final' | null
): string {
  const classMap = {
    shimmer: styles.withShimmer,
    waiting: styles.waitingBatch,
    final: styles.final,
    morph: ''
  };
  return getConditionalClass(styles.morphingText, {
    [classMap[phase || 'morph']]: !!phase
  });
}

/**
 * Helper para clases de eventos
 */
export function getEventClasses(
  styles: any,
  status: SimulatedEventStatus
): { containerClass: string; bulletClass: string; textClass: string } {
  const isActive = status === 'active';
  const isCompleted = status === 'completed';

  return {
    containerClass: getConditionalClass(styles.eventContainer, {
      [styles.eventContainerActive]: isActive
    }),
    bulletClass: getConditionalClass(styles.eventBullet, {
      [styles.eventBulletCompleted]: isCompleted,
      [styles.eventBulletActive]: isActive && !isCompleted
    }),
    textClass: getConditionalClass(styles.eventText, {
      [styles.eventTextCompleted]: isCompleted,
      [styles.eventTextActive]: isActive && !isCompleted
    })
  };
}

/**
 * Re-exportar MORPHING_SEQUENCE desde la configuracin centralizada
 * @deprecated Usar MORPHING_CONFIG de morphingConfig.ts directamente
 */
export { ORCHESTRATOR_SEQUENCE as MORPHING_SEQUENCE } from '../config/morphingConfig';

/**
 * Nombres amigables de agentes
 */
export const AGENT_FRIENDLY_NAMES: Record<string, string> = {
  'capidatab': 'Capi DataB',
  'capi_datab': 'Capi DataB',
  'datab': 'Capi DataB',
  'capielcajas': 'Capi ElCajas',
  'capi_elcajas': 'Capi ElCajas',
  'elcajas': 'Capi ElCajas',
  'capidesktop': 'Capi Desktop',
  'capi_desktop': 'Capi Desktop',
  'desktop': 'Capi Desktop',
  'capinoticias': 'Capi Noticias',
  'capi_noticias': 'Capi Noticias',
  'noticias': 'Capi Noticias',
  'summary': 'Capi Summary',
  'summaryagent': 'Capi Summary',
  'summarynode': 'Capi Summary',
  'branch': 'Capi Branch',
  'branchagent': 'Capi Branch',
  'branchnode': 'Capi Branch',
  'anomaly': 'Capi Anomaly',
  'anomalyagent': 'Capi Anomaly',
  'anomalynode': 'Capi Anomaly',
  'smalltalk': 'Capi Smalltalk',
  'smalltalk_fallback': 'Capi Smalltalk',
  'smalltalkfallback': 'Capi Smalltalk',
  'smalltalknode': 'Capi Smalltalk',
  'capi': 'Sistema' // Fallback for generic 'capi'
};

/**
 * Obtiene nombre amigable del agente
 */
export function getFriendlyAgentName(agent: string): string {
  if (!agent) return 'Sistema';

  // Normalizar: lowercase, sin guiones ni underscores
  const normalizedAgent = agent.toLowerCase().replace(/[-_]/g, '');

  // Buscar en el mapeo
  if (AGENT_FRIENDLY_NAMES[normalizedAgent]) {
    return AGENT_FRIENDLY_NAMES[normalizedAgent];
  }

  // Tambin buscar con underscores si no lo encontr
  const withUnderscore = agent.toLowerCase();
  if (AGENT_FRIENDLY_NAMES[withUnderscore]) {
    return AGENT_FRIENDLY_NAMES[withUnderscore];
  }

  // Si no est en el mapeo, formatear el nombre
  return agent
    .replace(/[-_]/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * Timer Manager para gestin centralizada de timers
 */
export class TimerManager {
  private timers: Map<string, NodeJS.Timeout> = new Map();

  set(key: string, callback: () => void, delay: number): void {
    // Limpiar timer existente si hay uno
    this.clear(key);

    const timerId = setTimeout(() => {
      callback();
      this.timers.delete(key);
    }, delay);

    this.timers.set(key, timerId);
  }

  clear(key: string): void {
    const timerId = this.timers.get(key);
    if (timerId) {
      clearTimeout(timerId);
      this.timers.delete(key);
    }
  }

  clearAll(): void {
    this.timers.forEach(timerId => clearTimeout(timerId));
    this.timers.clear();
  }

  has(key: string): boolean {
    return this.timers.has(key);
  }
}

/**
 * Tipo para eventos simulados
 */
export type SimulatedEventStatus = 'pending' | 'active' | 'completed';

export interface SimulatedEvent {
  id: string;
  agent: string;
  friendlyName: string;
  primaryText: string;
  detail?: string;
  status: SimulatedEventStatus;
}

export interface ReasoningPlanStep {
  id?: string;
  title?: string;
  description?: string;
  expected_output?: string;
  agent?: string;
}

const pickFirstString = (values: unknown[]): string | undefined => {
  for (const value of values) {
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed.length > 0) {
        return trimmed;
      }
    }
  }
  return undefined;
};

const MAX_AGENT_EVENT_TEXT = 96;

const isRawAgentEvent = (value: any): value is AgentEvent => {
  if (!value || typeof value !== 'object') {
    return false;
  }
  const eventType = (value as AgentEvent).type;
  return typeof eventType === 'string' && eventType.startsWith('agent_');
};

const shortenText = (value: string, maxLength: number = MAX_AGENT_EVENT_TEXT): string => {
  if (!value) {
    return '';
  }
  const normalized = value.replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  const slice = normalized.slice(0, maxLength);
  const lastSpace = slice.lastIndexOf(' ');
  const base = lastSpace > 40 ? slice.slice(0, lastSpace) : slice;
  return `${base.trim()}...`;
};

const formatRowCountText = (rows: number): string => {
  const rounded = Math.max(0, Math.round(rows));
  if (rounded === 1) {
    return 'Procesando 1 resultado';
  }
  return `Procesando ${rounded} resultados`;
};

const DB_OPERATION_VERB_MAP: Record<string, string> = {
  select: 'Consultando',
  insert: 'Insertando',
  update: 'Actualizando',
  delete: 'Eliminando'
};

const formatDbOperation = (operation: any, branchName?: string): string | undefined => {
  if (!operation || typeof operation !== 'object') {
    return undefined;
  }
  const operationType = typeof operation.operation === 'string' ? operation.operation.toLowerCase() : '';
  const verb = DB_OPERATION_VERB_MAP[operationType] || `Operacion ${operationType.toUpperCase() || 'SQL'}`;
  const table = typeof operation.table === 'string' && operation.table.trim().length
    ? ` ${operation.table.trim()}`
    : ' base de datos';
  const branchSuffix = branchName ? ` (${branchName})` : '';
  return shortenText(`${verb}${table}${branchSuffix}`);
};

const extractBranchName = (artifact: any): string | undefined => {
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

const getSharedArtifacts = (payload: any): Record<string, any> => {
  const paths: Array<Array<string>> = [
    ['response_metadata', 'shared_artifacts'],
    ['data', 'shared_artifacts'],
    ['shared_artifacts'],
    ['response_metadata', 'data', 'shared_artifacts']
  ];
  for (const path of paths) {
    let current: any = payload;
    let found = true;
    for (const key of path) {
      if (current && typeof current === 'object' && key in current) {
        current = current[key];
      } else {
        found = false;
        break;
      }
    }
    if (found && current && typeof current === 'object') {
      return current as Record<string, any>;
    }
  }
  return {};
};

const getReasoningPlan = (payload: any): { steps?: ReasoningPlanStep[] } | undefined => {
  const paths: Array<Array<string>> = [
    ['response_metadata', 'reasoning_plan'],
    ['data', 'reasoning_plan'],
    ['reasoning_plan']
  ];
  for (const path of paths) {
    let current: any = payload;
    let found = true;
    for (const key of path) {
      if (current && typeof current === 'object' && key in current) {
        current = current[key];
      } else {
        found = false;
        break;
      }
    }
    if (found && current && typeof current === 'object') {
      return current as { steps?: ReasoningPlanStep[] };
    }
  }
  return undefined;
};

const pickArtifactForAgent = (artifacts: Record<string, any>, agent: string): any => {
  const normalizedAgent = normalizeAgentName(agent);
  for (const [key, value] of Object.entries(artifacts)) {
    if (normalizeAgentName(key) === normalizedAgent) {
      return value;
    }
  }
  return undefined;
};

const extractAlertSummary = (alert: any): string | undefined => {
  if (!alert || typeof alert !== 'object') {
    return undefined;
  }
  const candidates = [
    alert.summary,
    alert.headline,
    alert.problem,
    alert.description,
    alert.payload?.summary,
    alert.payload?.problem
  ];
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim().length > 0) {
      return candidate.trim();
    }
  }
  return undefined;
};

const buildEventsFromAgentMessages = (messages: Message[]): SimulatedEvent[] => {
  const events: SimulatedEvent[] = [];
  const seen = new Set<string>();
  const agentCounts = new Map<string, number>();
  const timestamp = Date.now();

  messages.forEach((msg, index) => {
    const payload = getEventPayload(msg) as AgentEventPayload & { event?: { data?: any; meta?: any } };
    const envelope = payload?.event || {};
    const data = envelope.data || {};
    const meta = envelope.meta || {};
    const primaryText = pickFirstString([
      data.summary,
      data.message,
      data.text,
      meta.summary,
      meta.message,
      payload?.summary,
      payload?.message,
      msg.content,
      msg.text
    ]);
    if (!primaryText) {
      return;
    }

    const detailText = pickFirstString([
      data.detail,
      data.result,
      meta.detail,
      meta.status,
      payload?.detail
    ]);

    const agentRaw = payload?.actor || msg.agent || getAgentName(msg);
    const agent = agentRaw && agentRaw.trim().length > 0 ? agentRaw.trim() : 'agente';
    const friendlyName = getFriendlyAgentName(agent);
    const dedupeKey = `${normalizeAgentName(agent)}-${primaryText.trim()}`;
    if (seen.has(dedupeKey)) {
      return;
    }
    const currentCount = agentCounts.get(agent) ?? 0;
    if (currentCount >= 6) {
      return;
    }
    seen.add(dedupeKey);
    agentCounts.set(agent, currentCount + 1);
    events.push({
      id: msg.id || `agent-msg-${normalizeAgentName(agent)}-${index}-${timestamp}`,
      agent,
      friendlyName,
      primaryText: shortenText(primaryText),
      detail: detailText ? shortenText(detailText) : undefined,
      status: 'pending'
    });
  });

  return events;
};

const buildEventsFromArtifacts = (payload: any, planSteps?: ReasoningPlanStep[]): SimulatedEvent[] => {
  if (!payload || typeof payload !== 'object') {
    return [];
  }

  const artifacts = getSharedArtifacts(payload);
  if (!artifacts || Object.keys(artifacts).length === 0) {
    return [];
  }

  const events: SimulatedEvent[] = [];
  const seen = new Set<string>();
  const agentCounts = new Map<string, number>();
  const timestamp = Date.now();

  const pushEvent = (agent: string, text: string, detail?: string) => {
    const normalizedAgent = agent.trim() || 'agente';
    const cleanText = shortenText(text);
    if (!cleanText) {
      return;
    }
    const dedupeKey = `${normalizeAgentName(normalizedAgent)}-${cleanText}`;
    if (seen.has(dedupeKey)) {
      return;
    }
    const currentCount = agentCounts.get(normalizedAgent) ?? 0;
    if (currentCount >= 6) {
      return;
    }
    seen.add(dedupeKey);
    agentCounts.set(normalizedAgent, currentCount + 1);
    events.push({
      id: `artifact-${normalizeAgentName(normalizedAgent)}-${events.length}-${timestamp}`,
      agent: normalizedAgent,
      friendlyName: getFriendlyAgentName(normalizedAgent),
      primaryText: cleanText,
      detail: detail ? shortenText(detail) : undefined,
      status: 'pending'
    });
  };

  const addArtifactExtras = (agent: string, artifact: any) => {
    if (!artifact || typeof artifact !== 'object') {
      return;
    }

    if (typeof artifact.rowcount === 'number') {
      pushEvent(agent, formatRowCountText(artifact.rowcount));
    } else if (Array.isArray(artifact.rows)) {
      pushEvent(agent, formatRowCountText(artifact.rows.length));
    }

    if (typeof artifact.export_file === 'string' && artifact.export_file.trim().length > 0) {
      const parts = artifact.export_file.trim().split(/[\/]/);
      const fileName = parts.length > 0 ? parts[parts.length - 1] : artifact.export_file.trim();
      pushEvent(agent, `Exportando resultados a ${fileName}`);
    }

    if (Array.isArray(artifact.analysis) && artifact.analysis.length > 0) {
      const headline = extractAlertSummary(artifact.analysis[0]);
      if (headline) {
        pushEvent(agent, `Analizando ${headline}`);
      }
    }

    if (Array.isArray(artifact.alerts)) {
      artifact.alerts.slice(0, 2).forEach(alert => {
        const summary = extractAlertSummary(alert);
        if (summary) {
          pushEvent(agent, `Generando alerta: ${summary}`);
        }
      });
    }

    if (Array.isArray(artifact.recommendation_files) && artifact.recommendation_files.length > 0) {
      const recommendation = artifact.recommendation_files[0];
      const label = typeof recommendation?.summary === 'string' && recommendation.summary.trim().length > 0
        ? recommendation.summary.trim()
        : recommendation?.filename;
      if (label) {
        pushEvent(agent, `Registrando recomendacion ${label}`);
      }
    }

    if (typeof artifact.summary_message === 'string' && artifact.summary_message.trim().length > 0) {
      pushEvent(agent, artifact.summary_message);
    }
  };

  const processedAgents = new Set<string>();
  const planList = Array.isArray(planSteps) ? planSteps : [];

  if (planList.length > 0) {
    planList.forEach(step => {
      if (!step) {
        return;
      }
      const agent = step.agent && step.agent.trim().length > 0 ? step.agent : 'planificador';
      const artifact = pickArtifactForAgent(artifacts, agent);
      const branchName = artifact ? extractBranchName(artifact) : undefined;
      let addedFromArtifact = false;
      if (artifact) {
        const operationText = formatDbOperation(artifact.operation, branchName);
        if (operationText) {
          pushEvent(agent, operationText);
          addedFromArtifact = true;
        }
      }
      if (!addedFromArtifact) {
        const fallback = pickFirstString([step.title, step.description, step.expected_output]);
        if (fallback) {
          pushEvent(agent, fallback);
        }
      }
      if (artifact) {
        addArtifactExtras(agent, artifact);
        processedAgents.add(agent);
      }
    });
  }

  Object.entries(artifacts).forEach(([agent, artifact]) => {
    if (processedAgents.has(agent)) {
      return;
    }
    const branchName = extractBranchName(artifact);
    const operationText = formatDbOperation(artifact?.operation, branchName);
    if (operationText) {
      pushEvent(agent, operationText);
    }
    addArtifactExtras(agent, artifact);
  });

  return events;
};

interface BuildAgentTaskEventsParams {
  agentEvents: Message[];
  planSteps?: ReasoningPlanStep[];
  finalMessage?: Message;
}

export function buildAgentTaskEvents({ agentEvents, planSteps, finalMessage }: BuildAgentTaskEventsParams): SimulatedEvent[] {
  const primary = buildEventsFromAgentMessages(agentEvents);
  if (primary.length > 0) {
    return primary;
  }

  const payload = finalMessage && typeof finalMessage === 'object' ? (finalMessage.payload ?? finalMessage) : undefined;
  return buildEventsFromArtifacts(payload, planSteps);
}


/**
 * Estado consolidado para la simulacin
 */
export interface SimulationState {
  morphingText: string;
  morphingPhase: 'shimmer' | 'morph' | 'waiting' | 'final' | null;
  morphingKey: number;
  simulatedEvents: SimulatedEvent[];
  currentEventIndex: number;
  originalQuery: string;
  isWaitingForBatch: boolean;
}

export const initialSimulationState: SimulationState = {
  morphingText: '',
  morphingPhase: null,
  morphingKey: 0,
  simulatedEvents: [],
  currentEventIndex: -1,
  originalQuery: '',
  isWaitingForBatch: false
};

/**
 * Reducer para manejar actualizaciones del estado de simulacin
 */
export function simulationReducer(
  state: SimulationState,
  action: { type: string; payload?: any }
): SimulationState {
  switch (action.type) {
    case 'RESET':
      return initialSimulationState;

    case 'START_SIMULATION':
      return {
        ...initialSimulationState,
        originalQuery: action.payload.query,
        isWaitingForBatch: true
      };

    case 'SET_MORPHING':
      return {
        ...state,
        morphingText: action.payload.text,
        morphingPhase: action.payload.phase,
        morphingKey: action.payload.incrementKey
          ? state.morphingKey + 1
          : state.morphingKey
      };

    case 'SET_EVENTS':
      return {
        ...state,
        simulatedEvents: action.payload,
        currentEventIndex: action.payload.length > 0 ? 0 : -1
      };

    case 'SET_EVENT_INDEX':
      return {
        ...state,
        currentEventIndex: action.payload
      };

    case 'NEXT_EVENT':
      return {
        ...state,
        currentEventIndex: state.currentEventIndex + 1
      };

    case 'UPDATE_EVENT':
      const { index, update } = action.payload;
      return {
        ...state,
        simulatedEvents: state.simulatedEvents.map((evt, i) =>
          i === index ? { ...evt, ...update } : evt
        )
      };

    case 'COMPLETE_SIMULATION':
      return {
        ...state,
        isWaitingForBatch: false
      };

    case 'CLEAR_MORPHING':
      return {
        ...state,
        morphingText: '',
        morphingPhase: null,
        morphingKey: state.morphingKey + 1
      };

    case 'RESET_FOR_NEW_MESSAGE':
      return {
        ...initialSimulationState,
        originalQuery: action.payload,
        isWaitingForBatch: true
      };

    case 'STOP_WAITING':
      return {
        ...state,
        isWaitingForBatch: false
      };

    default:
      return state;
  }
}



