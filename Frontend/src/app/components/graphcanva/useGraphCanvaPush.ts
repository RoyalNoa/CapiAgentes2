"use client";

import { useEffect } from "react";
import { getApiBase } from '@/app/utils/orchestrator/client';

import type { GraphCanvaPushMessage } from "./types";

export interface GraphCanvaPushOptions {
  workflowId: string;
  onMessage?: (message: GraphCanvaPushMessage) => void;
  onStatusChange?: (status: "connected" | "connecting" | "disconnected") => void;
}

const buildWebSocketUrl = (workflowId: string) => {
  const base = getApiBase();
  const url = new URL(base);
  const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.protocol = wsProtocol;

  const trimmedPath = url.pathname.replace(/\/$/, "");
  const prefix = trimmedPath.endsWith('/api') ? trimmedPath.slice(0, -4) : trimmedPath;
  const segments = prefix.split('/').filter(Boolean);
  segments.push('ws', 'graph-canva', workflowId);
  url.pathname = `/${segments.join('/')}`;
  url.search = '';
  url.hash = '';
  return url.toString();
};

export const useGraphCanvaPush = ({ workflowId, onMessage, onStatusChange }: GraphCanvaPushOptions) => {
  useEffect(() => {
    if (!workflowId || typeof window === "undefined") {
      return () => undefined;
    }

    let socket: WebSocket | null = null;
    let retries = 0;
    let closed = false;
    let retryHandle: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (closed) {
        return;
      }
      onStatusChange?.("connecting");
      const url = buildWebSocketUrl(workflowId);
      socket = new WebSocket(url);

      socket.onopen = () => {
        retries = 0;
        onStatusChange?.("connected");
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as GraphCanvaPushMessage;
          onMessage?.(parsed);
        } catch (error) {
          console.error("GraphCanva push parse error", error);
        }
      };

      socket.onclose = () => {
        onStatusChange?.("disconnected");
        if (!closed) {
          retries += 1;
          const delay = Math.min(5000, 500 * retries);
          retryHandle = setTimeout(connect, delay);
        }
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      closed = true;
      if (retryHandle) {
        clearTimeout(retryHandle);
      }
      socket?.close();
    };
  }, [workflowId, onMessage, onStatusChange]);
};
