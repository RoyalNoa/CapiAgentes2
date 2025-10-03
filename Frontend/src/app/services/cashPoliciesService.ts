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

type PolicyUpdate = Partial<Omit<CashPolicy, 'channel'>>;

const jsonHeaders = {
  'Content-Type': 'application/json',
};

const configuredApiBase = (process.env.NEXT_PUBLIC_API_BASE ?? 'http://backend:8000').replace(/\/$/, '');

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

export const fetchCashPolicies = async (): Promise<CashPolicy[]> => {
  const response = await fetch(buildUrl('/api/cash-policies'), { cache: 'no-store' });
  return handleResponse<CashPolicy[]>(response);
};

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
