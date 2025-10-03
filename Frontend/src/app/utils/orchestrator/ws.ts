// Lightweight WebSocket wrapper with reconnect (exponential backoff) for Orchestrator.
// No external dependencies. Keeps API minimal.

import { getApiBase } from './client';

export type WSHandler = (...args: any[]) => void;

interface ListenerMap { [event: string]: Set<WSHandler>; }

interface BackoffConfig { base: number; factor: number; maxAttempts: number; }

export class OrchestratorSocket {
  private url: string;
  private ws: WebSocket | null = null;
  private listeners: ListenerMap = {};
  private attempts = 0;
  private backoff: BackoffConfig = { base: 500, factor: 2, maxAttempts: 5 };
  private manualClose = false;

  constructor(url?: string, cfg?: Partial<BackoffConfig>) {
    // Convert http/https base to ws/wss for proper WebSocket handshake
    const resolvedBase = getApiBase();
    const base = resolvedBase
      .replace(/^http:/, 'ws:')
      .replace(/^https:/, 'wss:');
    this.url = url || `${base}/ws`;
    if (cfg) this.backoff = { ...this.backoff, ...cfg };
  }

  on(event: string, handler: WSHandler) {
    if (!this.listeners[event]) this.listeners[event] = new Set();
    this.listeners[event].add(handler);
  }

  off(event: string, handler: WSHandler) {
    this.listeners[event]?.delete(handler);
  }

  private emit(event: string, ...args: any[]) {
    this.listeners[event]?.forEach(h => {
      try { h(...args); } catch { /* swallow */ }
    });
  }

  connect() {
    this.manualClose = false;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.attempts = 0;
      this.emit('open');
    };

    this.ws.onmessage = (evt) => {
      let payload: any = evt.data;
      try { payload = JSON.parse(evt.data); } catch { /* keep raw */ }
      this.emit('message', payload);
    };

    this.ws.onerror = (err) => {
      this.emit('error', err);
    };

    this.ws.onclose = () => {
      this.emit('close');
      if (!this.manualClose) this.scheduleReconnect();
    };
  }

  private scheduleReconnect() {
    if (this.attempts >= this.backoff.maxAttempts) {
      this.emit('reconnect_failed');
      return;
    }
    const delay = this.backoff.base * Math.pow(this.backoff.factor, this.attempts);
    this.attempts += 1;
    setTimeout(() => this.connect(), delay);
    this.emit('reconnecting', { attempt: this.attempts, delay });
  }

  send(payload: object | string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
    this.ws.send(data);
    return true;
  }

  close() {
    this.manualClose = true;
    if (this.ws) {
      try { this.ws.close(); } catch { /* ignore */ }
    }
  }
}
