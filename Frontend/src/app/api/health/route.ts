import { NextResponse } from 'next/server';

const DEFAULT_API_BASE = 'http://backend:8000';

function resolveBackendBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE ?? DEFAULT_API_BASE;
  return configured.replace(/\/$/, '');
}

export async function GET() {
  const backendBase = resolveBackendBase();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 2000);

  let backendStatus: 'online' | 'offline' | 'unreachable';
  let backendPayload: unknown = null;

  try {
    const response = await fetch(`${backendBase}/api/health`, {
      cache: 'no-store',
      signal: controller.signal,
    });

    if (response.ok) {
      backendStatus = 'online';
      try {
        backendPayload = await response.json();
      } catch {
        backendPayload = null;
      }
    } else {
      backendStatus = 'unreachable';
      backendPayload = {
        status: response.status,
        statusText: response.statusText,
      };
    }
  } catch (error) {
    backendStatus = 'offline';
    backendPayload = error instanceof Error ? error.message : String(error);
  } finally {
    clearTimeout(timeout);
  }

  return NextResponse.json({
    status: 'ok',
    service: 'frontend',
    timestamp: new Date().toISOString(),
    backend: {
      baseUrl: backendBase,
      status: backendStatus,
      payload: backendPayload,
    },
  });
}

export async function HEAD() {
  return new Response(null, { status: 204 });
}
