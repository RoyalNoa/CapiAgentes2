import { getApiBase } from '@/app/utils/orchestrator/client';

import type {
  GraphCanvaCatalog,
  GraphCanvaExecution,
  GraphCanvaExecutionRequest,
  GraphCanvaWorkflow,
  GraphCanvaWorkflowUpdate,
} from "@/app/components/graphcanva/types";

const API_BASE = getApiBase();

const jsonHeaders = {
  "Content-Type": "application/json",
};

const toJson = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`GraphCanva API error (${response.status}): ${detail}`);
  }
  return (await response.json()) as T;
};

export const fetchWorkflow = async (workflowId: string): Promise<GraphCanvaWorkflow> => {
  const response = await fetch(`${API_BASE}/api/graph-canva/workflows/${workflowId}`);
  return toJson<GraphCanvaWorkflow>(response);
};

export const fetchCatalog = async (): Promise<GraphCanvaCatalog> => {
  const response = await fetch(`${API_BASE}/api/graph-canva/catalog`);
  return toJson<GraphCanvaCatalog>(response);
};

export const patchWorkflow = async (
  workflowId: string,
  payload: GraphCanvaWorkflowUpdate,
): Promise<GraphCanvaWorkflow> => {
  const response = await fetch(`${API_BASE}/api/graph-canva/workflows/${workflowId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  return toJson<GraphCanvaWorkflow>(response);
};

export const runWorkflow = async (
  workflowId: string,
  payload: GraphCanvaExecutionRequest = {},
): Promise<GraphCanvaExecution> => {
  const response = await fetch(`${API_BASE}/api/graph-canva/workflows/${workflowId}/run`, {
    method: "POST",
    headers: jsonHeaders,
    body: JSON.stringify(payload),
  });
  return toJson<GraphCanvaExecution>(response);
};

export const fetchExecutions = async (
  workflowId: string,
): Promise<GraphCanvaExecution[]> => {
  const response = await fetch(`${API_BASE}/api/graph-canva/workflows/${workflowId}/executions`);
  return toJson<GraphCanvaExecution[]>(response);
};
