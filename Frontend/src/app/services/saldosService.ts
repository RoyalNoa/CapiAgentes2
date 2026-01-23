/**
 * @file saldosService.ts
 * @module services
 * @description Servicio de Saldos - Manejo de saldos de sucursales y dispositivos.
 * Proporciona operaciones CRUD para la gestión de saldos financieros via API REST.
 */

/**
 * Interfaz para saldo de sucursal.
 * @description Representa los datos completos de saldo de una sucursal bancaria.
 */
export interface SucursalSaldo {
  sucursal_id: string;
  sucursal_numero: number;
  sucursal_nombre: string;
  tipo_sucursal?: string | null;
  telefonos?: string | null;
  calle?: string | null;
  altura?: number | null;
  barrio?: string | null;
  comuna?: number | null;
  codigo_postal?: number | null;
  codigo_postal_argentino?: string | null;
  saldo_total_sucursal: number;
  caja_teorica_sucursal?: number | null;
  total_atm?: number | null;
  total_ats?: number | null;
  total_tesoro?: number | null;
  total_cajas_ventanilla?: number | null;
  total_buzon_depositos?: number | null;
  total_recaudacion?: number | null;
  total_caja_chica?: number | null;
  total_otros?: number | null;
  direccion_sucursal?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  observacion?: string | null;
  medido_en?: string | null;
}

/**
 * Interfaz para saldo de dispositivo.
 * @description Representa los datos de saldo de un dispositivo (ATM, ATS, etc.).
 */
export interface DispositivoSaldo {
  id: number;
  sucursal_id: string;
  dispositivo_id: string;
  tipo_dispositivo: string;
  saldo_total: number;
  caja_teorica?: number | null;
  cant_d1?: number | null;
  cant_d2?: number | null;
  cant_d3?: number | null;
  cant_d4?: number | null;
  direccion?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  observacion?: string | null;
  medido_en?: string | null;
}

/** Headers JSON para peticiones HTTP. */
const jsonHeaders = {
  'Content-Type': 'application/json',
};

/**
 * @function resolveApiBase
 * @description Resuelve la URL base de la API adaptándose al entorno (SSR vs cliente).
 * @returns {string} URL base resuelta
 */
const resolveApiBase = (): string => {
  const configured = (process.env.NEXT_PUBLIC_API_BASE ?? 'http://backend:8000').replace(/\/$/, '');

  if (typeof window === 'undefined') {
    return configured;
  }

  if (!configured || configured.includes('://backend')) {
    try {
      const parsed = new URL(configured || 'http://backend:8000');
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

  return configured;
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
 * @function fetchSucursalSaldos
 * @description Obtiene todos los saldos de sucursales desde el backend.
 * @returns {Promise<SucursalSaldo[]>} Lista de saldos de sucursales
 * @throws {Error} Si la petición HTTP falla
 */
export const fetchSucursalSaldos = async (): Promise<SucursalSaldo[]> => {
  const response = await fetch(buildUrl('/api/saldos/sucursales'), { cache: 'no-store' });
  return handleResponse<SucursalSaldo[]>(response);
};

/**
 * @function createSucursalSaldo
 * @description Crea un nuevo registro de saldo de sucursal.
 * @param {Partial<SucursalSaldo> & { sucursal_id: string }} payload - Datos del saldo a crear
 * @returns {Promise<SucursalSaldo>} Saldo de sucursal creado
 * @throws {Error} Si la petición HTTP falla
 */
export const createSucursalSaldo = async (payload: Partial<SucursalSaldo> & { sucursal_id: string }): Promise<SucursalSaldo> => {
  const response = await fetch(buildUrl('/api/saldos/sucursales'), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  return handleResponse<SucursalSaldo>(response);
};

/**
 * @function updateSucursalSaldo
 * @description Actualiza un registro de saldo de sucursal existente.
 * @param {string} sucursalId - ID de la sucursal a actualizar
 * @param {Partial<SucursalSaldo>} payload - Datos a actualizar
 * @returns {Promise<SucursalSaldo>} Saldo de sucursal actualizado
 * @throws {Error} Si la petición HTTP falla
 */
export const updateSucursalSaldo = async (
  sucursalId: string,
  payload: Partial<SucursalSaldo>,
  ): Promise<SucursalSaldo> => {
  const response = await fetch(buildUrl(`/api/saldos/sucursales/${encodeURIComponent(sucursalId)}`), {
    method: 'PUT',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  return handleResponse<SucursalSaldo>(response);
};

/**
 * @function deleteSucursalSaldo
 * @description Elimina un registro de saldo de sucursal.
 * @param {string} sucursalId - ID de la sucursal a eliminar
 * @returns {Promise<void>}
 * @throws {Error} Si la petición HTTP falla
 */
export const deleteSucursalSaldo = async (sucursalId: string): Promise<void> => {
  const response = await fetch(buildUrl(`/api/saldos/sucursales/${encodeURIComponent(sucursalId)}`), {
    method: 'DELETE',
  });
  await handleResponse(response);
};

/**
 * @function fetchDispositivoSaldos
 * @description Obtiene todos los saldos de dispositivos desde el backend.
 * @returns {Promise<DispositivoSaldo[]>} Lista de saldos de dispositivos
 * @throws {Error} Si la petición HTTP falla
 */
export const fetchDispositivoSaldos = async (): Promise<DispositivoSaldo[]> => {
  const response = await fetch(buildUrl('/api/saldos/dispositivos'), { cache: 'no-store' });
  return handleResponse<DispositivoSaldo[]>(response);
};

/**
 * @function createDispositivoSaldo
 * @description Crea un nuevo registro de saldo de dispositivo.
 * @param {Partial<DispositivoSaldo> & { sucursal_id: string; dispositivo_id: string; tipo_dispositivo: string }} payload - Datos del saldo
 * @returns {Promise<DispositivoSaldo>} Saldo de dispositivo creado
 * @throws {Error} Si la petición HTTP falla
 */
export const createDispositivoSaldo = async (
  payload: Partial<DispositivoSaldo> & { sucursal_id: string; dispositivo_id: string; tipo_dispositivo: string },
  ): Promise<DispositivoSaldo> => {
  const response = await fetch(buildUrl('/api/saldos/dispositivos'), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  return handleResponse<DispositivoSaldo>(response);
};

/**
 * @function updateDispositivoSaldo
 * @description Actualiza un registro de saldo de dispositivo existente.
 * @param {number} recordId - ID del registro a actualizar
 * @param {Partial<DispositivoSaldo>} payload - Datos a actualizar
 * @returns {Promise<DispositivoSaldo>} Saldo de dispositivo actualizado
 * @throws {Error} Si la petición HTTP falla
 */
export const updateDispositivoSaldo = async (
  recordId: number,
  payload: Partial<DispositivoSaldo>,
  ): Promise<DispositivoSaldo> => {
  const response = await fetch(buildUrl(`/api/saldos/dispositivos/${recordId}`), {
    method: 'PUT',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  return handleResponse<DispositivoSaldo>(response);
};

/**
 * @function deleteDispositivoSaldo
 * @description Elimina un registro de saldo de dispositivo.
 * @param {number} recordId - ID del registro a eliminar
 * @returns {Promise<void>}
 * @throws {Error} Si la petición HTTP falla
 */
export const deleteDispositivoSaldo = async (recordId: number): Promise<void> => {
  const response = await fetch(buildUrl(`/api/saldos/dispositivos/${recordId}`), {
    method: 'DELETE',
  });
  await handleResponse(response);
};
