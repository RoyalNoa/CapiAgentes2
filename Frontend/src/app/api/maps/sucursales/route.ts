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
  'http://host.docker.internal:8011'
].filter((base): base is string => Boolean(base));

async function fetchSucursales(base: string) {
  const response = await fetch(`${base}/api/maps/sucursales`, { cache: 'no-store' });
  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(`HTTP ${response.status}${body ? `: ${body.slice(0, 180)}` : ''}`);
  }
  return response.json();
}

export async function GET() {
  const errors: string[] = [];

  for (const base of CANDIDATE_BACKENDS) {
    try {
      const payload = await fetchSucursales(base);
      return NextResponse.json(payload, { status: 200 });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'unknown error';
      errors.push(`${base}: ${message}`);
    }
  }

  return NextResponse.json(
    {
      error: 'No se pudo recuperar la informacion de sucursales desde el backend.',
      attempts: errors,
    },
    { status: 502 }
  );
}



