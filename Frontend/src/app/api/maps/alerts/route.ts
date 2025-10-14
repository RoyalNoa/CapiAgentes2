import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const CANDIDATE_BACKENDS = [
  process.env.NEXT_PUBLIC_API_BASE,
  'http://backend:8000',
  'http://capi-backend:8000',
  'http://host.docker.internal:8000',
  'http://localhost:8000',
  'http://backend:8011',
  'http://capi-backend:8011',
  'http://localhost:8011',
  'http://host.docker.internal:8011',
].filter((base): base is string => Boolean(base));

async function fetchAlerts(base: string, queryString: string) {
  const url = `${base}/api/alerts${queryString ? `?${queryString}` : ''}`;
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(`HTTP ${response.status}${body ? `: ${body.slice(0, 180)}` : ''}`);
  }
  return response.json();
}

export async function GET(request: Request) {
  const errors: string[] = [];
  const { searchParams } = new URL(request.url);

  const queryParams = new URLSearchParams();
  const limit = searchParams.get('limit') ?? '200';
  if (limit) {
    queryParams.set('limit', limit);
  }

  const status = searchParams.get('status');
  if (status) {
    queryParams.set('status', status);
  }

  const priority = searchParams.get('priority');
  if (priority) {
    queryParams.set('priority', priority);
  }

  for (const base of CANDIDATE_BACKENDS) {
    try {
      const payload = await fetchAlerts(base, queryParams.toString());
      return NextResponse.json(payload, { status: 200 });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'unknown error';
      errors.push(`${base}: ${message}`);
    }
  }

  return NextResponse.json(
    {
      error: 'No se pudo recuperar la informacion de alertas desde el backend.',
      attempts: errors,
    },
    { status: 502 },
  );
}
