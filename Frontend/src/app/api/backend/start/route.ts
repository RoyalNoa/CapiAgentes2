import { NextRequest, NextResponse } from 'next/server';
export const runtime = 'nodejs';

const CANDIDATES = [
  process.env.NEXT_PUBLIC_API_BASE,
  'http://backend:8011',
  'http://capi-backend:8011',
  'http://localhost:8011',
  'http://host.docker.internal:8011'
].filter(Boolean) as string[];

export async function POST(_req: NextRequest) {
  const errors: string[] = [];
  for (const base of CANDIDATES) {
    try {
      const r = await fetch(`${base}/api/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'start' }) });
      const data = await r.json().catch(() => ({}));
      return NextResponse.json({ ok: r.ok, upstream: data, base }, { status: 200 });
    } catch (e: any) {
      errors.push(`${base}: ${e.message}`);
    }
  }
  return NextResponse.json({ ok: false, error: 'all backends failed', attempts: errors }, { status: 200 });
}
