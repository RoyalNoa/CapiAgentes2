const DEFAULT_API_BASE = 'http://localhost:8000';

function normalizeBase(base: string): string {
  return base.replace(/\/$/, '');
}

let cachedBrowserBase: string | null = null;

export function getApiBase(): string {
  const envBase = process.env.NEXT_PUBLIC_API_BASE;

  if (typeof window === 'undefined') {
    return normalizeBase(envBase ?? DEFAULT_API_BASE);
  }

  if (cachedBrowserBase) {
    return cachedBrowserBase;
  }

  const fallback = normalizeBase(`${window.location.protocol}//${window.location.host}`);
  if (!envBase) {
    cachedBrowserBase = fallback;
    return cachedBrowserBase;
  }

  try {
    const candidate = new URL(envBase, fallback);
    const serviceHosts = ['backend', 'capi-backend'];
    if (serviceHosts.includes(candidate.hostname)) {
      candidate.hostname = window.location.hostname;
      if (!candidate.port && window.location.port) {
        candidate.port = window.location.port;
      }
      candidate.protocol = window.location.protocol;
    }
    cachedBrowserBase = normalizeBase(candidate.toString());
    return cachedBrowserBase;
  } catch (_error) {
    cachedBrowserBase = fallback;
    return cachedBrowserBase;
  }
}

export const API_BASE = getApiBase();
// Enhanced logging system
class OrchestratorLogger {
  private static instance: OrchestratorLogger;
  private logs: Array<{timestamp: string, level: string, message: string, data?: any}> = [];
  
  static getInstance(): OrchestratorLogger {
    if (!OrchestratorLogger.instance) {
      OrchestratorLogger.instance = new OrchestratorLogger();
    }
    return OrchestratorLogger.instance;
  }

  private formatMessage(level: string, message: string, data?: any): string {
    const timestamp = new Date().toISOString();
    const logEntry = { timestamp, level, message, data };
    this.logs.push(logEntry);
    
    // Keep only last 100 logs to prevent memory issues
    if (this.logs.length > 100) {
      this.logs.shift();
    }
    
    return `[${timestamp}] [ORCH-${level}] ${message}${data ? ' | Data: ' + JSON.stringify(data, null, 2) : ''}`;
  }

  info(message: string, data?: any) {
    console.log(this.formatMessage('INFO', message, data));
  }

  warn(message: string, data?: any) {
    console.warn(this.formatMessage('WARN', message, data));
  }

  error(message: string, data?: any) {
    console.error(this.formatMessage('ERROR', message, data));
  }

  debug(message: string, data?: any) {
    console.debug(this.formatMessage('DEBUG', message, data));
  }

  getLogs() {
    return [...this.logs];
  }

  clearLogs() {
    this.logs = [];
  }
}

const logger = OrchestratorLogger.getInstance();

// Debug: informar configuración completa
if (typeof window !== 'undefined') {
  if (!(window as any).__ORCH_INIT_LOGGED) {
    (window as any).__ORCH_INIT_LOGGED = true;
    logger.info('Orchestrator Client Initialized', {
      API_BASE,
      NODE_ENV: process.env.NODE_ENV,
      NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE,
      userAgent: navigator.userAgent,
      location: window.location.href
    });
    
    // Expose logger globally for debugging
    (window as any).orchestratorLogger = logger;
  }
}

interface OrchestratorResult {
  json?: any;
  summary?: any;
  anomalies?: any;
  dashboard?: any;
  agent?: string;
  response?: any;
  data?: any;
  message?: string;
  error?: { code: string; message: string };
}

interface ErrorShape { code: string; message: string }

function buildError(code: string, message: string): never { throw { code, message } as ErrorShape }

const TIMEOUT_MS = 15000; // 15s timeout

// Enhanced fetch wrapper with comprehensive logging
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = TIMEOUT_MS): Promise<Response> {
  const startTime = Date.now();
  const requestId = Math.random().toString(36).slice(2, 8);
  
  logger.info(`Fetch Request Started [${requestId}]`, {
    url,
    method: options.method || 'GET',
    headers: options.headers,
    bodyLength: options.body ? (typeof options.body === 'string' ? options.body.length : '[object]') : 0,
    timeout
  });

  const controller = new AbortController();
  const id = setTimeout(() => {
    logger.warn(`Fetch Timeout [${requestId}]`, { url, timeoutMs: timeout });
    controller.abort();
  }, timeout);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const duration = Date.now() - startTime;
    
    logger.info(`Fetch Response Received [${requestId}]`, {
      url,
      status: response.status,
      statusText: response.statusText,
      duration,
      headers: Object.fromEntries(response.headers.entries()),
      ok: response.ok
    });

    return response;
  } catch (err: any) {
    const duration = Date.now() - startTime;
    logger.error(`Fetch Error [${requestId}]`, {
      url,
      duration,
      errorName: err?.name,
      errorMessage: err?.message,
      errorStack: err?.stack?.split('\n').slice(0, 3) // First 3 lines of stack
    });

    if (err?.name === 'AbortError') {
      buildError('NETWORK_ERROR', `Timeout alcanzado después de ${timeout}ms`);
    }
    if (err?.name === 'TypeError' && err?.message?.includes('fetch')) {
      buildError('NETWORK_ERROR', `Error de conexión: ${err.message} - Verificar que el backend esté ejecutándose en ${url}`);
    }
    buildError('NETWORK_ERROR', `Error de red: ${err?.message || 'Unknown error'}`);
  } finally {
    clearTimeout(id);
  }
}

async function request(path: string, body: any): Promise<OrchestratorResult> {
  const requestId = Math.random().toString(36).slice(2, 8);
  const primaryUrl = `${API_BASE}${path}`;
  
  logger.info(`API Request Started [${requestId}]`, {
    path,
    primaryUrl,
    body,
    API_BASE
  });

  let res = await fetchWithTimeout(primaryUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  // Fallback logic with enhanced logging
  if (res.status === 405 && !primaryUrl.startsWith('http://localhost:8000')) {
    const fallbackUrl = `http://localhost:8000${path}`;
    logger.warn(`405 Method Not Allowed [${requestId}]`, {
      primaryUrl,
      fallbackUrl,
      attempting: 'fallback to localhost:8000'
    });
    
    try {
      res = await fetchWithTimeout(fallbackUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      logger.info(`Fallback Request Success [${requestId}]`, { fallbackUrl });
    } catch (e: any) {
      logger.error(`Fallback Request Failed [${requestId}]`, {
        fallbackUrl,
        error: e?.message
      });
      // Continue with normal error handling
    }
  }

  // Response parsing with detailed logging
  let data: any = null;
  const responseText = await res.text();
  logger.debug(`Raw Response [${requestId}]`, {
    status: res.status,
    statusText: res.statusText,
    responseLength: responseText.length,
    responsePreview: responseText.slice(0, 200) // First 200 chars
  });

  try {
    data = JSON.parse(responseText);
    logger.info(`Response Parsed Successfully [${requestId}]`, {
      dataKeys: data ? Object.keys(data) : [],
      hasError: !!data?.error
    });
  } catch (parseError: any) {
    logger.error(`JSON Parse Error [${requestId}]`, {
      responseText: responseText.slice(0, 500), // More context for parse errors
      parseError: parseError.message
    });
    buildError('PARSE_ERROR', `Respuesta inválida del servidor: ${parseError.message}`);
  }

  if (!res.ok || data?.error) {
    const err = data?.error || { code: `HTTP_${res.status}`, message: res.statusText };
    logger.error(`API Request Failed [${requestId}]`, {
      status: res.status,
      error: err,
      responseData: data
    });
    buildError(err.code, err.message);
  }

  logger.info(`API Request Completed Successfully [${requestId}]`, {
    status: res.status,
    dataStructure: data ? {
      keys: Object.keys(data),
      hasAgent: !!data.agent,
      hasResponse: !!data.response,
      hasError: !!data.error
    } : null
  });

  return data;
}

// Función ingest removida - los datos se cargan automáticamente en el backend

export async function command(text: string, clientId?: string): Promise<OrchestratorResult> {
  logger.info('Command Function Called', {
    textLength: text?.length || 0,
    clientId,
    textPreview: text?.slice(0, 100) // First 100 chars
  });
  
  try {
    const result = await request('/api/command', { instruction: text, client_id: clientId });
    logger.info('Command Executed Successfully', {
      resultKeys: result ? Object.keys(result) : [],
      hasAgent: !!result?.agent,
      hasResponse: !!result?.response
    });
    return result;
  } catch (error: any) {
    logger.error('Command Execution Failed', {
      errorCode: error?.code,
      errorMessage: error?.message,
      textPreview: text?.slice(0, 100)
    });
    throw error;
  }
}

export async function health(): Promise<OrchestratorResult> {
  logger.info('Health Check Started', { endpoint: `${API_BASE}/api/health` });
  
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/health`);
    if (!res.ok) {
      logger.error('Health Check HTTP Error', {
        status: res.status,
        statusText: res.statusText
      });
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    
    const data = await res.json();
    logger.info('Health Check Success', { data });
    return data;
  } catch (error: any) {
    logger.error('Health Check Failed', {
      errorMessage: error?.message,
      errorCode: error?.code
    });
    if (error?.code) throw error; // Re-throw our formatted errors
    buildError('PARSE_ERROR', 'Respuesta inválida en health check');
  }
}

export type { OrchestratorResult };

// Agents management API
export interface AgentStatusDto {
  name: string;
  enabled: boolean;
}

export async function getAgents(): Promise<AgentStatusDto[]> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/agents`);
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    const agents: AgentStatusDto[] = (data?.agents || []).map((a: any) => ({
      name: String(a?.name || '').toLowerCase(),
      enabled: Boolean(a?.enabled),
    }));
    logger.info('Fetched agents', { count: agents.length });
    return agents;
  } catch (error: any) {
    logger.error('getAgents failed', { error: error?.message || error });
    throw error;
  }
}

export async function setAgentEnabled(name: string, enabled: boolean): Promise<Record<string, boolean>> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, enabled }),
    });
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    const config = data?.agents || {};
    logger.info('Agent toggled', { name, enabled, config });
    return config;
  } catch (error: any) {
    logger.error('setAgentEnabled failed', { name, enabled, error: error?.message || error });
    throw error;
  }
}

export async function refreshAgents(): Promise<{ status: string; agents_found: number; agents: Array<{name: string; enabled: boolean}> }> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    logger.info('Agents refreshed', {
      status: data.status,
      agents_found: data.agents_found,
      agents: data.agents
    });
    return data;
  } catch (error: any) {
    logger.error('refreshAgents failed', { error: error?.message || error });
    throw error;
  }
}

export interface AgentMetricsDto {
  agents: Array<{
    name: string;
    enabled: boolean;
    description: string;
    status: 'active' | 'idle';
  }>;
  timestamp: string;
  system_status: string;
  active_agents_count: number;
  total_agents_count: number;
}

export async function getAgentsMetrics(): Promise<AgentMetricsDto> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/metrics`);
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    logger.info('Fetched agents metrics', {
      agentCount: data?.agents?.length || 0,
      activeCount: data?.active_agents_count || 0
    });
    return data;
  } catch (error: any) {
    logger.error('getAgentsMetrics failed', { error: error?.message || error });
    throw error;
  }
}

export interface SystemStatusDto {
  timestamp: string;
  system_operational: boolean;
  cpu_percent?: number;
  memory_percent?: number;
  memory_available_gb?: number;
  active_agents: number;
  total_agents: number;
  note?: string;
}

export async function getSystemStatus(): Promise<SystemStatusDto> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/system-status`);
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    logger.info('Fetched system status', {
      operational: data?.system_operational,
      activeAgents: data?.active_agents
    });
    return data;
  } catch (error: any) {
    logger.error('getSystemStatus failed', { error: error?.message || error });
    throw error;
  }
}


export interface HistoricalAlertAffectedEntity {
  entity_type?: string | null;
  entity_name?: string | null;
  impact_level?: string | null;
}

export interface HistoricalAlertBranchInfo {
  sucursal_id: string;
  nombre?: string | null;
  saldo_total?: number | null;
  caja_teorica?: number | null;
  saldo_cobertura_pct?: number | null;
}

export interface HistoricalAlertDeviceInfo {
  dispositivo_id: string;
  tipo?: string | null;
  saldo_total?: number | null;
  caja_teorica?: number | null;
  saldo_cobertura_pct?: number | null;
  latitud?: number | null;
  longitud?: number | null;
}

export interface HistoricalAlertSummaryDto {
  id: string;
  alert_code: string;
  timestamp: string;
  title: string;
  priority: string;
  status: string;
  financial_impact?: number | null;
  currency?: string;
  confidence_score?: number | null;
  pending_tasks: number;
  affected_entities: HistoricalAlertAffectedEntity[];
  sucursal?: HistoricalAlertBranchInfo | null;
  dispositivo?: HistoricalAlertDeviceInfo | HistoricalAlertDeviceInfo[] | null;
}

export interface HistoricalAlertHumanTaskDto {
  id: string;
  task_title?: string | null;
  task_description?: string | null;
  priority?: number | null;
  status?: string | null;
  assigned_to_team?: string | null;
  due_date?: string | null;
  progress_percentage?: number | null;
}

export interface HistoricalAlertDetailDto extends HistoricalAlertSummaryDto {
  alert_type: string;
  agent_source: string;
  description?: string | null;
  acciones?: string | null;
  datos_clave?: string[] | null;
  evento?: {
    id?: string | null;
    estado?: string | null;
    timestamp?: string | null;
    duracion_ms?: number | null;
    tokens_total?: number | null;
    costo_usd?: number | null;
    mensaje?: string | null;
  };
  resolved_at?: string | null;
  resolved_by?: string | null;
  created_at: string;
  updated_at: string;
  root_cause?: string | null;
  probability_fraud?: number | null;
  probability_system_error?: number | null;
  similar_incidents_count?: number | null;
  trend_analysis?: string | null;
  risk_assessment?: string | null;
  confidence_level?: number | null;
  model_version?: string | null;
  human_tasks: HistoricalAlertHumanTaskDto[];
}

export interface HistoricalAlertsQuery {
  limit?: number;
  offset?: number;
  status?: string;
  priority?: string;
  agent?: string;
}

export async function getHistoricalAlertsSummary(query: HistoricalAlertsQuery = {}): Promise<HistoricalAlertSummaryDto[]> {
  try {
    const params = new URLSearchParams();
    if (query.limit !== undefined) params.set('limit', query.limit.toString());
    if (query.offset !== undefined) params.set('offset', query.offset.toString());
    if (query.status) params.set('status', query.status);
    if (query.priority) params.set('priority', query.priority);
    if (query.agent) params.set('agent', query.agent);

    const queryString = params.toString();
    const url = `${API_BASE}/api/alerts${queryString ? `?${queryString}` : ''}`;
    const res = await fetchWithTimeout(url);
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    logger.info('Fetched historical alerts summary', { count: Array.isArray(data) ? data.length : 0 });
    return data as HistoricalAlertSummaryDto[];
  } catch (error: any) {
    logger.error('getHistoricalAlertsSummary failed', { error: error?.message || error });
    throw error;
  }
}

export async function getHistoricalAlertDetail(alertId: string): Promise<HistoricalAlertDetailDto> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/alerts/${encodeURIComponent(alertId)}`);
    if (!res.ok) {
      const detail = await res.text();
      buildError(`HTTP_${res.status}`, detail || res.statusText);
    }
    const data = await res.json();
    logger.info('Fetched historical alert detail', { alertId });
    return data as HistoricalAlertDetailDto;
  } catch (error: any) {
    logger.error('getHistoricalAlertDetail failed', { alertId, error: error?.message || error });
    throw error;
  }
}

export type HumanGateStatus = 'pending' | 'accepted' | 'rejected';

export interface AlertStatusUpdateRequest {
  status: HumanGateStatus;
  reason?: string;
  actor?: string;
  metadata?: Record<string, any>;
}

export interface AlertStatusUpdateResponse {
  alert_id: string;
  status: HumanGateStatus;
  stored_status: string;
  reason?: string | null;
}

export async function updateAlertStatus(
  alertId: string,
  payload: AlertStatusUpdateRequest
): Promise<AlertStatusUpdateResponse> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/api/alerts/${encodeURIComponent(alertId)}/status`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    );

    if (!res.ok) {
      const detail = await res.text();
      buildError(`HTTP_${res.status}`, detail || res.statusText);
    }

    const data = await res.json();
    logger.info('Alert status updated', { alertId, status: payload.status });
    return data as AlertStatusUpdateResponse;
  } catch (error: any) {
    logger.error('updateAlertStatus failed', {
      alertId,
      status: payload.status,
      error: error?.message || error,
    });
    throw error;
  }
}
export interface HistoricalAlertAIRecommendedAction {
  title?: string | null;
  description?: string | null;
  priority?: number | null;
  team?: string | null;
  status?: string | null;
  progress?: number | null;
}

export interface HistoricalAlertAIContext {
  alert_summary: {
    code?: string | null;
    title?: string | null;
    priority?: string | null;
    financial_impact?: number | null;
    confidence?: number | null;
  };
  ai_analysis: {
    root_cause?: string | null;
    fraud_probability?: number | null;
    trend_analysis?: string | null;
    risk_assessment?: string | null;
  };
  operational_context: {
    affected_entities: HistoricalAlertAffectedEntity[];
  sucursal?: HistoricalAlertBranchInfo | null;
  dispositivo?: HistoricalAlertDeviceInfo | HistoricalAlertDeviceInfo[] | null;
    pending_tasks: number;
    status?: string | null;
  };
  recommended_actions: HistoricalAlertAIRecommendedAction[];
}

export async function getHistoricalAlertAIContext(alertId: string): Promise<HistoricalAlertAIContext> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/alerts/${encodeURIComponent(alertId)}/ai-context`);
    if (!res.ok) {
      const detail = await res.text();
      buildError(`HTTP_${res.status}`, detail || res.statusText);
    }
    const data = await res.json();
    logger.info('Fetched historical alert AI context', { alertId });
    return data as HistoricalAlertAIContext;
  } catch (error: any) {
    logger.error('getHistoricalAlertAIContext failed', { alertId, error: error?.message || error });
    throw error;
  }
}

// Token tracking API
export interface TokenUsageHistoryEntry {
  timestamp: string;
  tokens: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  cost_usd: number;
  model?: string | null;
  provider?: string | null;
}

export interface TokenTrackingAgentEntry {
  total_tokens: number;
  prompt_tokens_total?: number;
  completion_tokens_total?: number;
  cost_usd: number;
  provider?: string;
  last_model?: string | null;
  last_seen?: string | null;
  status?: 'active' | 'inactive' | 'idle';
  history: TokenUsageHistoryEntry[];
}

export interface CostTimelineAgentPoint {
  tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
}

export interface CostTimelinePoint {
  date: string;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  agents: Record<string, CostTimelineAgentPoint>;
}

export interface TokenTrackingDto {
  timestamp: string;
  agents: Record<string, TokenTrackingAgentEntry>;
  total_tokens: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_cost_usd: number;
  cost_timeline: CostTimelinePoint[];
  error?: string;
}

export async function getTokenTracking(): Promise<TokenTrackingDto> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/token-tracking`);
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }

    const data: TokenTrackingDto = await res.json();
    if (!Array.isArray(data.cost_timeline)) {
      data.cost_timeline = [];
    }

    logger.info('Fetched token tracking', {
      totalTokens: data?.total_tokens || 0,
      totalPromptTokens: data?.total_prompt_tokens || 0,
      totalCompletionTokens: data?.total_completion_tokens || 0,
      totalCost: data?.total_cost_usd || 0,
      agentCount: Object.keys(data?.agents || {}).length,
      timelinePoints: data.cost_timeline.length,
    });

    return data;
  } catch (error: any) {
    logger.error('getTokenTracking failed', { error: error?.message || error });
    throw error;
  }
}
export async function recordTokenUsage(agent: string, tokens: number, costUsd: number): Promise<any> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/token-usage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent, tokens, cost_usd: costUsd }),
    });
    if (!res.ok) {
      buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    logger.info('Token usage recorded', { agent, tokens, costUsd });
    return data;
  } catch (error: any) {
    logger.error('recordTokenUsage failed', { agent, tokens, costUsd, error: error?.message || error });
    throw error;
  }
}

// ==========================================
// NUEVAS INTERFACES: REGISTRO DINÁMICO DE AGENTES
export interface MermaidGraphSvgDto {
  status: string;
  timestamp: string;
  source: string;
  diagram: string;
}

export interface MermaidGraphPngDto {
  status: string;
  timestamp: string;
  source: string;
  diagram_png?: string | null;
  diagram_png_mime?: string | null;
  diagram_png_error?: string | null;
}


// ==========================================

export interface AgentRegistrationRequest {
  agent_name: string;
  display_name: string;
  description: string;
  agent_class_path: string;
  node_class_path: string;
  supported_intents: string[];
  capabilities?: Record<string, any>;
  metadata?: Record<string, any>;
  enabled?: boolean;
}

export interface AgentManifestDto {
  agent_name: string;
  display_name: string;
  version: string;
  description: string;
  category: string;
  supported_intents: string[];
  capabilities: Record<string, any>;
  enabled: boolean;
  created_at: string;
  author: string;
}

export interface RegistryStatsDto {
  total_agents: number;
  categories: Record<string, number>;
  enabled_agents: number;
  recent_registrations: number;
}

export interface DynamicGraphStatusDto {
  dynamic_system_available: boolean;
  graph_status?: {
    total_nodes: number;
    total_edges: number;
    core_nodes: string[];
    agent_nodes: string[];
    registered_agents_count: number;
    enabled_agents_count: number;
    enabled_agents: string[];
    entry_point: string;
  };
  registry?: RegistryStatsDto;
  error?: string;
}

// ==========================================

export interface CapiNoticiasSegmentConfigDto {
  file: string;
  min_priority: number;
  fallback_min: number;
  max_items: number;
  lookback_hours?: number;
  lookback_days?: number;
}

export interface CapiNoticiasConfigDto {
  enabled: boolean;
  interval_minutes: number;
  max_articles_per_source: number;
  source_urls: string[];
  segments: Record<string, CapiNoticiasSegmentConfigDto>;
}

export interface CapiNoticiasRuntimeDto {
  is_running?: boolean;
  is_executing?: boolean;
  last_run: string | null;
  last_success: string | null;
  last_error: string | null;
  next_run: string | null;
  last_trigger?: string | null;
  run_history?: Array<Record<string, any>>;
  last_result?: Record<string, any> | null;
}

export interface CapiNoticiasStatusDto {
  status: string;
  timestamp: string;
  data: {
    config: CapiNoticiasConfigDto;
    status: CapiNoticiasRuntimeDto;
  };
}

export type UpdateCapiNoticiasSegmentConfig = Partial<Omit<CapiNoticiasSegmentConfigDto, 'file'>>;

export interface UpdateCapiNoticiasConfigRequest {
  interval_minutes?: number;
  max_articles_per_source?: number;
  source_urls?: string[];
  enabled?: boolean;
  segments?: Record<string, UpdateCapiNoticiasSegmentConfig>;
}

export interface RunCapiNoticiasPayload {
  source_urls?: string[];
  max_articles_per_source?: number;
}

export interface RunCapiNoticiasResponse {
  status: string;
  message: string;
  result: Record<string, any>;
  timestamp: string;
}

export async function getCapiNoticiasStatus(): Promise<CapiNoticiasStatusDto> {
  try {
    logger.debug('Loading Capi Noticias status');
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/capi_noticias/status`);
    if (!res.ok) {
      throw buildError(`HTTP_${res.status}`, res.statusText);
    }
    const data = await res.json();
    return data as CapiNoticiasStatusDto;
  } catch (error: any) {
    logger.error('getCapiNoticiasStatus failed', { error: error?.message || error });
    throw error;
  }
}

export async function updateCapiNoticiasConfig(payload: UpdateCapiNoticiasConfigRequest): Promise<{ status: string; message: string; config: CapiNoticiasConfigDto; timestamp: string; }> {
  try {
    logger.info('Updating Capi Noticias configuration', payload);
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/capi_noticias/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errorData = await res.json();
      throw buildError(`HTTP_${res.status}`, errorData.error?.message || res.statusText);
    }
    const data = await res.json();
    return data as { status: string; message: string; config: CapiNoticiasConfigDto; timestamp: string; };
  } catch (error: any) {
    logger.error('updateCapiNoticiasConfig failed', { payload, error: error?.message || error });
    throw error;
  }
}

export async function startCapiNoticiasScheduler(): Promise<{ status: string; message: string; }> {
  try {
    logger.info('Starting Capi Noticias scheduler');
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/capi_noticias/start`, { method: 'POST' });
    if (!res.ok) {
      const errorData = await res.json();
      throw buildError(`HTTP_${res.status}`, errorData.error?.message || res.statusText);
    }
    return res.json();
  } catch (error: any) {
    logger.error('startCapiNoticiasScheduler failed', { error: error?.message || error });
    throw error;
  }
}

export async function stopCapiNoticiasScheduler(): Promise<{ status: string; message: string; }> {
  try {
    logger.info('Stopping Capi Noticias scheduler');
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/capi_noticias/stop`, { method: 'POST' });
    if (!res.ok) {
      const errorData = await res.json();
      throw buildError(`HTTP_${res.status}`, errorData.error?.message || res.statusText);
    }
    return res.json();
  } catch (error: any) {
    logger.error('stopCapiNoticiasScheduler failed', { error: error?.message || error });
    throw error;
  }
}

export async function runCapiNoticias(payload?: RunCapiNoticiasPayload): Promise<RunCapiNoticiasResponse> {
  try {
    logger.info('Running Capi Noticias manually', payload);
    const res = await fetchWithTimeout(`${API_BASE}/api/agents/capi_noticias/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) {
      const errorData = await res.json();
      throw buildError(`HTTP_${res.status}`, errorData.error?.message || res.statusText);
    }
    const data = await res.json();
    return data as RunCapiNoticiasResponse;
  } catch (error: any) {
    logger.error('runCapiNoticias failed', { payload, error: error?.message || error });
    throw error;
  }
}

// NUEVAS FUNCIONES: REGISTRO DINÁMICO DE AGENTES
// ==========================================

export async function registerAgent(request: AgentRegistrationRequest): Promise<{
  status: string;
  message: string;
  agent_name: string;
  enabled: boolean;
}> {
  try {
    logger.info('Registering new agent', { agent_name: request.agent_name });

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw buildError(`HTTP_${res.status}`, errorData.error?.message || res.statusText);
    }

    const data = await res.json();
    logger.info('Agent registered successfully', data);
    return data;

  } catch (error: any) {
    logger.error('registerAgent failed', { request, error: error?.message || error });
    throw error;
  }
}

export async function unregisterAgent(agentName: string): Promise<{
  status: string;
  message: string;
  agent_name: string;
}> {
  try {
    logger.info('Unregistering agent', { agent_name: agentName });

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/${encodeURIComponent(agentName)}/unregister`, {
      method: 'DELETE',
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw buildError(`HTTP_${res.status}`, errorData.error?.message || res.statusText);
    }

    const data = await res.json();
    logger.info('Agent unregistered successfully', data);
    return data;

  } catch (error: any) {
    logger.error('unregisterAgent failed', { agent_name: agentName, error: error?.message || error });
    throw error;
  }
}

export async function getRegisteredAgents(): Promise<{
  status: string;
  total_registered: number;
  agents: AgentManifestDto[];
}> {
  try {
    logger.debug('Loading registered agents');

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/registry`);
    if (!res.ok) {
      throw buildError(`HTTP_${res.status}`, res.statusText);
    }

    const data = await res.json();
    logger.info('Registered agents loaded', { count: data.total_registered });
    return data;

  } catch (error: any) {
    logger.error('getRegisteredAgents failed', { error: error?.message || error });
    throw error;
  }
}


export async function getLangGraphMermaidSvg(): Promise<MermaidGraphSvgDto> {
  try {
    logger.debug('Fetching LangGraph Mermaid SVG');

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/graph/mermaid_svg`);
    if (!res.ok) {
      throw buildError(`HTTP_${res.status}`, res.statusText);
    }

    const data = await res.json();
    logger.info('LangGraph Mermaid SVG loaded', { source: data.source });
    return data;

  } catch (error: any) {
    logger.error('getLangGraphMermaidSvg failed', { error: error?.message || error });
    throw error;
  }
}

export async function getLangGraphMermaidPng(): Promise<MermaidGraphPngDto> {
  try {
    logger.debug('Fetching LangGraph Mermaid PNG');

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/graph/mermaid_png`);
    if (!res.ok) {
      throw buildError(`HTTP_${res.status}`, res.statusText);
    }

    const data = await res.json();
    logger.info('LangGraph Mermaid PNG loaded', { source: data.source, hasPng: Boolean(data.diagram_png), hasError: Boolean(data.diagram_png_error) });
    return data;

  } catch (error: any) {
    logger.error('getLangGraphMermaidPng failed', { error: error?.message || error });
    throw error;
  }
}

export async function getLangGraphMermaidConceptual(): Promise<MermaidGraphSvgDto> {
  try {
    logger.debug('Fetching LangGraph Mermaid conceptual view');

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/graph/mermaid_conceptual`);
    if (!res.ok) {
      throw buildError(`HTTP_${res.status}`, res.statusText);
    }

    const data = await res.json();
    logger.info('LangGraph Mermaid conceptual loaded', { source: data.source });
    return data;

  } catch (error: any) {
    logger.error('getLangGraphMermaidConceptual failed', { error: error?.message || error });
    throw error;
  }
}

export async function getDynamicGraphStatus(): Promise<DynamicGraphStatusDto> {
  try {
    logger.debug('Loading dynamic graph status');

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/graph/status`);
    if (!res.ok) {
      throw buildError(`HTTP_${res.status}`, res.statusText);
    }

    const data = await res.json();
    logger.info('Dynamic graph status loaded', { available: data.dynamic_system_available });
    return data;

  } catch (error: any) {
    logger.error('getDynamicGraphStatus failed', { error: error?.message || error });
    throw error;
  }
}

export async function refreshDynamicGraph(): Promise<{
  status: string;
  message: string;
}> {
  try {
    logger.info('Refreshing dynamic graph');

    const res = await fetchWithTimeout(`${API_BASE}/api/agents/graph/refresh`, {
      method: 'POST',
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw buildError(`HTTP_${res.status}`, errorData.error?.message || res.statusText);
    }

    const data = await res.json();
    logger.info('Dynamic graph refreshed successfully', data);
    return data;

  } catch (error: any) {
    logger.error('refreshDynamicGraph failed', { error: error?.message || error });
    throw error;
  }
}


export async function submitHumanDecisionRequest(payload: {
  session_id: string;
  approved: boolean;
  interrupt_id?: string | null;
  message?: string | null;
  reason?: string | null;
  metadata?: Record<string, any> | null;
}): Promise<OrchestratorResult> {
  logger.info('Submitting human decision', payload);
  return request('/api/orchestrator/human/decision', payload);
}
