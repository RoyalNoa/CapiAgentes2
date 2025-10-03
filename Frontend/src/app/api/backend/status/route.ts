import { NextRequest, NextResponse } from 'next/server';

// Fuerza runtime Node (evita edge donde puede fallar DNS interno docker)
export const runtime = 'nodejs';

const CANDIDATE_BACKENDS = [
  process.env.NEXT_PUBLIC_API_BASE,
  'http://backend:8011',
  'http://capi-backend:8011',
  'http://localhost:8011',
  'http://host.docker.internal:8011'
].filter(Boolean) as string[];

async function tryFetch(base: string) {
  const r = await fetch(`${base}/api/status`, { cache: 'no-store' });
  const data = await r.json().catch(() => ({}));
  return { r, data, base };
}

export async function GET(_req: NextRequest) {
  const errors: string[] = [];
  for (const base of CANDIDATE_BACKENDS) {
    try {
      const { r, data, base: used } = await tryFetch(base);
      return NextResponse.json({ ok: r.ok, upstream: data, baseTried: used }, { status: 200 });
    } catch (e: any) {
      errors.push(`${base} -> ${e.message}`);
    }
  }
  return NextResponse.json({ ok: false, error: 'all backends failed', attempts: errors }, { status: 200 });
}
