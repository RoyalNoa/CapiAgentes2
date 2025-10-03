export interface SucursalSaldo {
  sucursal_id: string;
  sucursal_numero: number;
  sucursal_nombre: string;
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

const jsonHeaders = {
  'Content-Type': 'application/json',
};

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

const buildUrl = (path: string): string => {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalized = path.startsWith('/') ? path : `/${path}`;
  const base = resolveApiBase();
  return base ? `${base}${normalized}` : normalized;
};

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

export const fetchSucursalSaldos = async (): Promise<SucursalSaldo[]> => {
  const response = await fetch(buildUrl('/api/saldos/sucursales'), { cache: 'no-store' });
  return handleResponse<SucursalSaldo[]>(response);
};

export const createSucursalSaldo = async (payload: Partial<SucursalSaldo> & { sucursal_id: string }): Promise<SucursalSaldo> => {
  const response = await fetch(buildUrl('/api/saldos/sucursales'), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  return handleResponse<SucursalSaldo>(response);
};

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

export const deleteSucursalSaldo = async (sucursalId: string): Promise<void> => {
  const response = await fetch(buildUrl(`/api/saldos/sucursales/${encodeURIComponent(sucursalId)}`), {
    method: 'DELETE',
  });
  await handleResponse(response);
};

export const fetchDispositivoSaldos = async (): Promise<DispositivoSaldo[]> => {
  const response = await fetch(buildUrl('/api/saldos/dispositivos'), { cache: 'no-store' });
  return handleResponse<DispositivoSaldo[]>(response);
};

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

export const deleteDispositivoSaldo = async (recordId: number): Promise<void> => {
  const response = await fetch(buildUrl(`/api/saldos/dispositivos/${recordId}`), {
    method: 'DELETE',
  });
  await handleResponse(response);
};
