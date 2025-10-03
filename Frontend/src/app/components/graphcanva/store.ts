import { create } from "zustand";
import type { Edge, Node, Viewport } from "@xyflow/react";

import type {
  GraphCanvaExecution,
  GraphCanvaNodeDataPayload,
  GraphCanvaPushMessage,
  GraphCanvaVector,
  GraphCanvaWorkflow,
} from "./types";

const baseState = {
  workflow: null as GraphCanvaWorkflow | null,
  nodes: [] as Node<GraphCanvaNodeDataPayload>[],
  edges: [] as Edge[],
  viewport: null as Viewport | null,
  execution: null as GraphCanvaExecution | null,
  loading: true,
  nodeOutputs: {} as Record<string, Record<string, unknown>>,
  activeNdvNode: null as string | null,
};

export interface GraphCanvaState {
  workflow: GraphCanvaWorkflow | null;
  nodes: Node<GraphCanvaNodeDataPayload>[];
  edges: Edge[];
  viewport: Viewport | null;
  execution: GraphCanvaExecution | null;
  loading: boolean;
  nodeOutputs: Record<string, Record<string, unknown>>;
  activeNdvNode: string | null;
  setWorkflow: (
    workflow: GraphCanvaWorkflow,
    nodes: Node<GraphCanvaNodeDataPayload>[],
    edges: Edge[],
  ) => void;
  setNodes: (nodes: Node<GraphCanvaNodeDataPayload>[]) => void;
  setEdges: (edges: Edge[]) => void;
  setViewport: (viewport: Viewport) => void;
  setLoading: (loading: boolean) => void;
  setExecution: (execution: GraphCanvaExecution | null) => void;
  updateSelection: (payload: { nodes: string[]; edges: string[] }) => void;
  updateNodePosition: (nodeId: string, position: GraphCanvaVector) => void;
  resetExecution: () => void;
  clearNodeOutputs: () => void;
  setActiveNdvNode: (nodeId: string | null) => void;
  applyPushMessage: (message: GraphCanvaPushMessage) => void;
}

export const useGraphCanvaStore = create<GraphCanvaState>((set, get) => ({
  ...baseState,
  setWorkflow: (workflow, nodes, edges) =>
    set({ workflow, nodes, edges, loading: false, nodeOutputs: {}, activeNdvNode: null }),
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setViewport: (viewport) => set({ viewport }),
  setLoading: (loading) => set({ loading }),
  setExecution: (execution) => set({ execution }),
  updateSelection: ({ nodes, edges }) =>
    set((state) => {
      if (!state.workflow) {
        return state;
      }
      const nextMeta = {
        ...state.workflow.meta,
        selection: { nodes, edges },
      };
      return {
        ...state,
        workflow: { ...state.workflow, meta: nextMeta },
      };
    }),
  updateNodePosition: (nodeId, position) =>
    set((state) => {
      if (!state.workflow) {
        return state;
      }
      const nodes = state.nodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              position: { x: position[0], y: position[1] },
            }
          : node,
      );
      const workflowNodes = state.workflow.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, position }
          : node,
      );
      return {
        ...state,
        nodes,
        workflow: {
          ...state.workflow,
          nodes: workflowNodes,
          updated_at: new Date().toISOString(),
        },
      };
    }),
  resetExecution: () => set({ execution: null }),
  clearNodeOutputs: () => set({ nodeOutputs: {}, activeNdvNode: null }),
  setActiveNdvNode: (nodeId) => set({ activeNdvNode: nodeId }),
  applyPushMessage: (message) =>
    set((state) => {
      const workflow = state.workflow;
      if (!workflow) {
        return state;
      }

      const resolveNodeId = (nodeName: string) =>
        workflow.nodes.find((node) => node.name === nodeName)?.id ?? null;

      const toNodeStatus = (status: string): GraphCanvaNodeDataPayload["status"] => {
        switch (status) {
          case "success":
            return "success";
          case "error":
            return "error";
          case "running":
            return "running";
          case "cancelled":
            return "waiting";
          default:
            return "idle";
        }
      };

      const patchNodeStatus = (
        nodeId: string,
        status: GraphCanvaNodeDataPayload["status"],
        lastRunAt?: string | null,
      ) => {
        const nodes = state.nodes.map((node) =>
          node.id === nodeId
            ? {
                ...node,
                data: {
                  ...node.data,
                  status,
                  lastRunAt: lastRunAt ?? node.data.lastRunAt ?? null,
                },
              }
            : node,
        );
        const workflowNodes = workflow.nodes.map((node) =>
          node.id === nodeId
            ? { ...node, runtime_status: status, last_run_at: lastRunAt ?? node.last_run_at }
            : node,
        );
        return { nodes, workflowNodes };
      };

      switch (message.type) {
        case "execution_started": {
          const runningNodes = state.nodes.map((node) => ({
            ...node,
            data: { ...node.data, status: "running" },
          }));
          const workflowNodes = workflow.nodes.map((node) => ({
            ...node,
            runtime_status: "running",
          }));
          const execution: GraphCanvaExecution = {
            execution_id: message.execution_id,
            workflow_id: message.workflow_id,
            status: "running",
            started_at: message.emitted_at,
            finished_at: null,
            duration_ms: null,
            error: null,
            summary: message.data ?? {},
          };
          return {
            ...state,
            nodes: runningNodes,
            workflow: { ...workflow, nodes: workflowNodes },
            execution,
            nodeOutputs: {},
            activeNdvNode: null,
          };
        }
        case "node_execute_before": {
          const nodeId = resolveNodeId(message.node_name);
          if (!nodeId) {
            return state;
          }
          const { nodes, workflowNodes } = patchNodeStatus(nodeId, "running");
          return {
            ...state,
            nodes,
            workflow: { ...workflow, nodes: workflowNodes },
          };
        }
        case "node_execute_after": {
          const nodeId = resolveNodeId(message.node_name);
          if (!nodeId) {
            return state;
          }
          const { nodes, workflowNodes } = patchNodeStatus(
            nodeId,
            toNodeStatus(message.status),
            message.emitted_at,
          );
          return {
            ...state,
            nodes,
            workflow: { ...workflow, nodes: workflowNodes },
          };
        }
        case "node_execute_after_data": {
          const nodeId = resolveNodeId(message.node_name);
          if (!nodeId) {
            return state;
          }
          const nodeOutputs = { ...state.nodeOutputs, [nodeId]: message.data };
          return {
            ...state,
            nodeOutputs,
            activeNdvNode: nodeId,
          };
        }
        case "execution_finished": {
          const metrics = message.data?.metrics as Record<string, unknown> | undefined;
          const durationCandidate =
            metrics && typeof metrics === "object" && metrics !== null && "duration_ms" in metrics
              ? (metrics as { duration_ms?: unknown }).duration_ms
              : undefined;
          const durationMs =
            typeof durationCandidate === "number" ? durationCandidate : state.execution?.duration_ms ?? null;
          const execution: GraphCanvaExecution = {
            execution_id: message.execution_id,
            workflow_id: message.workflow_id,
            status: message.status,
            started_at: state.execution?.started_at ?? message.emitted_at,
            finished_at: message.emitted_at,
            duration_ms: durationMs,
            error: message.error ?? null,
            summary: {
              ...(state.execution?.summary ?? {}),
              ...message.data,
            },
          };
          return {
            ...state,
            execution,
          };
        }
        default:
          return state;
      }
    }),
}));

export const resetGraphCanvaStore = () =>
  useGraphCanvaStore.setState((state) => ({ ...state, ...baseState }));
