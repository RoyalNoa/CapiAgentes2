import type { Edge, Node, Viewport } from "@xyflow/react";

import type {
  GraphCanvaConnectionMap,
  GraphCanvaMeta,
  GraphCanvaNode,
  GraphCanvaNodeDataPayload,
  GraphCanvaWorkflow,
} from "./types";

const DEFAULT_NODE_WIDTH = 260;

const STATUS_TO_CLASS: Record<string, string> = {
  idle: "idle",
  running: "running",
  success: "success",
  error: "error",
  waiting: "waiting",
};

export interface GraphCanvaElements {
  nodes: Node<GraphCanvaNodeDataPayload>[];
  edges: Edge[];
  viewport: Viewport | null;
}

export const mapWorkflowToElements = (workflow: GraphCanvaWorkflow): GraphCanvaElements => {
  const nodes = workflow.nodes.map((node) => toReactFlowNode(node, workflow));
  const edges = toReactFlowEdges(workflow.connections);
  const viewport = workflow.meta ? toViewport(workflow.meta) : null;

  return { nodes, edges, viewport };
};

const toReactFlowNode = (
  node: GraphCanvaNode,
  workflow: GraphCanvaWorkflow,
): Node<GraphCanvaNodeDataPayload> => {
  const selection = workflow.meta?.selection?.nodes ?? [];
  return {
    id: node.id,
    type: "graphCanvaNode",
    position: { x: node.position[0], y: node.position[1] },
    data: {
      nodeId: node.id,
      label: node.name,
      subtitle: node.type,
      status: node.runtime_status,
      isDisabled: Boolean(node.disabled),
      lastRunAt: node.last_run_at ?? null,
      metrics: {
        trigger_count: workflow.trigger_count,
      },
    },
    width: DEFAULT_NODE_WIDTH,
    selected: selection.includes(node.id),
    className: STATUS_TO_CLASS[node.runtime_status] ?? STATUS_TO_CLASS.idle,
  };
};

const toReactFlowEdges = (connections: GraphCanvaConnectionMap): Edge[] => {
  const edges: Edge[] = [];
  Object.entries(connections).forEach(([connectionType, sources]) => {
    Object.entries(sources).forEach(([sourceNode, endpoints]) => {
      endpoints.forEach((endpoint, index) => {
        const id = `${sourceNode}-${endpoint.node}-${connectionType}-${index}`;
        edges.push({
          id,
          source: sourceNode,
          target: endpoint.node,
          type: connectionType === "main" ? "smoothstep" : "step",
          label: connectionType !== "main" ? connectionType : undefined,
          animated: endpoint.meta?.last_status === "running",
          data: {
            meta: endpoint.meta,
          },
        });
      });
    });
  });
  return edges;
};

export const toViewport = (meta: GraphCanvaMeta): Viewport => ({
  x: meta.viewport.pan_x,
  y: meta.viewport.pan_y,
  zoom: meta.viewport.zoom,
});

