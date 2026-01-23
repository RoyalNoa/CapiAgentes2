/**
 * @file cashPoliciesService.ts
 * @module services
 * @description Servicio de Políticas de Efectivo - Gestión de reglas y límites de manejo de efectivo.
 * Define políticas por canal con límites de superávit, déficit, retiros y depósitos.
 */

/**
 * Interfaz para política de efectivo.
 * @description Representa las reglas y límites de manejo de efectivo por canal.
 */
export interface CashPolicy {
  channel: string;
  max_surplus_pct?: number | null;
  max_deficit_pct?: number | null;
  min_buffer_amount?: number | null;
  daily_withdrawal_limit?: number | null;
  daily_deposit_limit?: number | null;
  reload_lead_hours?: number | null;
  sla_hours?: number | null;
  truck_fixed_cost?: number | null;
  truck_variable_cost_per_kg?: number | null;
  notes?: string | null;
  updated_at?: string | null;
}

/** Tipo para actualización parcial de política (sin channel). */
type PolicyUpdate = Partial<Omit<CashPolicy, 'channel'>>;

/** Headers JSON para peticiones HTTP. */
const jsonHeaders = {
  'Content-Type': 'application/json',
};

/** URL base de la API configurada desde variables de entorno. */
const configuredApiBase = (process.env.NEXT_PUBLIC_API_BASE ?? 'http://backend:8000').replace(/\/$/, '');

/**
 * @function resolveApiBase
 * @description Resuelve la URL base de la API adaptándose al entorno (SSR vs cliente).
 * @returns {string} URL base resuelta
 */
const resolveApiBase = (): string => {
  if (typeof window === 'undefined') {
    return configuredApiBase;
  }

  if (!configuredApiBase || configuredApiBase.includes('://backend')) {
    try {
      const parsed = new URL(configuredApiBase || 'http://backend:8000');
      const protocol = window.location.protocol || parsed.protocol || 'http:';
      const hostname = window.location.hostname || parsed.hostname;
      const port = parsed.port || '8000';
      const normalizedPort = port && port !== '80' && port !== '443' ? `:${port}` : '';
      return `${protocol}//${hostname}${normalizedPort}`;
    } catch {
      const protocol = window.location.protocol || 'http:';
      const hostname = window.location.hostname || 'localhost';
      return `${protocol}//${hostname}:8000`;
    }
  }

  return configuredApiBase;
};

/**
 * @function buildUrl
 * @description Construye URL completa a partir de path relativo.
 * @param {string} path - Path relativo o absoluto
 * @returns {string} URL completa
 */
const buildUrl = (path: string): string => {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalized = path.startsWith('/') ? path : `/${path}`;
  const base = resolveApiBase();
  return base ? `${base}${normalized}` : normalized;
};

/**
 * @function handleResponse
 * @description Procesa la respuesta HTTP y maneja errores.
 * @template T - Tipo del dato esperado en la respuesta
 * @param {Response} response - Respuesta HTTP a procesar
 * @returns {Promise<T>} Datos parseados de la respuesta
 * @throws {Error} Si la respuesta no es exitosa
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return (await response.json()) as T;
}

/**
 * @function fetchCashPolicies
 * @description Obtiene todas las políticas de efectivo desde el backend.
 * @returns {Promise<CashPolicy[]>} Lista de políticas de efectivo
 * @throws {Error} Si la petición HTTP falla
 */
export const fetchCashPolicies = async (): Promise<CashPolicy[]> => {
  const response = await fetch(buildUrl('/api/cash-policies'), { cache: 'no-store' });
  return handleResponse<CashPolicy[]>(response);
};

/**
 * @function updateCashPolicy
 * @description Actualiza una política de efectivo existente.
 * @param {string} channel - Identificador del canal a actualizar
 * @param {PolicyUpdate} payload - Datos a actualizar
 * @returns {Promise<CashPolicy>} Política de efectivo actualizada
 * @throws {Error} Si la petición HTTP falla
 */
export const updateCashPolicy = async (
  channel: string,
  payload: PolicyUpdate,
): Promise<CashPolicy> => {
  const response = await fetch(buildUrl(`/api/cash-policies/${encodeURIComponent(channel)}`), {
    method: 'PUT',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });

  return handleResponse<CashPolicy>(response);
};
