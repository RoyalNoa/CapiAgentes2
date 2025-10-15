import type {
  GraphCanvaConnectionMap,
  GraphCanvaMeta,
  GraphCanvaNode,
  GraphCanvaWorkflow,
} from "./types";

const ISO_NOW = "2024-07-15T12:30:00.000Z";

const buildMeta = (): GraphCanvaMeta => ({
  viewport: { pan_x: -80, pan_y: -160, zoom: 0.9 },
  grid: { size: 24, snap: false },
  panels: {
    inspector_open: false,
    execution_sidebar_mode: "summary",
    ndv_open_node: null,
  },
  selection: { nodes: [], edges: [] },
  analytics: { tidy_count: 12, tidy_last_at: "2024-07-10T18:22:00.000Z" },
  layout_dirty: false,
  data_dirty: false,
});

const buildNode = (node: Partial<GraphCanvaNode> & Pick<GraphCanvaNode, "id">): GraphCanvaNode => ({
  id: node.id,
  name: node.name ?? node.id,
  type: node.type ?? "agent",
  type_version: node.type_version ?? 1,
  parameters: node.parameters ?? {},
  credentials: node.credentials ?? null,
  position: node.position ?? [0, 0],
  disabled: node.disabled ?? false,
  notes: node.notes ?? null,
  always_output_data: node.always_output_data ?? null,
  retry_on_fail: node.retry_on_fail ?? null,
  max_concurrency: node.max_concurrency ?? null,
  hooks: node.hooks ?? null,
  runtime_status: node.runtime_status ?? "idle",
  last_run_at: node.last_run_at ?? ISO_NOW,
});

const buildConnections = (): GraphCanvaConnectionMap => ({
  main: {
    entry_router: [
      { node: "intent_classifier", type: "main", index: 0 },
      { node: "priority_queue", type: "main", index: 1 },
    ],
    intent_classifier: [
      { node: "governance_guard", type: "main", index: 0 },
      { node: "playbook_planner", type: "main", index: 1 },
    ],
    priority_queue: [
      { node: "ops_router_agent", type: "main", index: 0 },
      { node: "sentinel_watchdog", type: "main", index: 1 },
    ],
    governance_guard: [
      { node: "agent_capi_gus", type: "main", index: 0 },
      { node: "agent_branch_insights", type: "main", index: 1 },
    ],
    playbook_planner: [
      { node: "agent_vector_forge", type: "main", index: 0 },
      { node: "agent_atlas_mapper", type: "main", index: 1 },
    ],
    ops_router_agent: [
      { node: "agent_risk_guardian", type: "main", index: 0 },
      { node: "agent_capi_datab", type: "main", index: 1 },
    ],
    agent_capi_gus: [
      { node: "metrics_collector", type: "main", index: 0 },
      { node: "notifier_ops", type: "main", index: 1 },
    ],
    agent_branch_insights: [
      { node: "notifier_ops", type: "main", index: 0 },
      { node: "metrics_collector", type: "main", index: 1 },
    ],
    agent_risk_guardian: [
      { node: "notifier_clients", type: "main", index: 0 },
    ],
    agent_vector_forge: [
      { node: "notifier_clients", type: "main", index: 0 },
    ],
    agent_atlas_mapper: [
      { node: "audit_logger", type: "main", index: 0 },
    ],
    agent_capi_datab: [
      { node: "metrics_collector", type: "main", index: 0 },
    ],
    sentinel_watchdog: [
      { node: "governance_guard", type: "main", index: 0 },
    ],
    notifier_ops: [
      { node: "audit_logger", type: "main", index: 0 },
    ],
    notifier_clients: [
      { node: "audit_logger", type: "main", index: 0 },
    ],
    metrics_collector: [
      { node: "audit_logger", type: "main", index: 0 },
    ],
    audit_logger: [
      { node: "knowledge_hub", type: "main", index: 0 },
    ],
  },
  telemetry: {
    metrics_collector: [
      {
        node: "observability_panel",
        type: "telemetry",
        index: 0,
        meta: {
          last_status: "running",
          last_latency_ms: 182,
          last_error: null,
          last_payload_sample: { gauge: "token_usage", value: 0.78 },
        },
      },
    ],
    sentinel_watchdog: [
      {
        node: "observability_panel",
        type: "telemetry",
        index: 1,
        meta: {
          last_status: "success",
          last_latency_ms: 94,
          last_error: null,
          last_payload_sample: { alerts: 0 },
        },
      },
    ],
  },
});

const buildNodes = (): GraphCanvaNode[] => [
  buildNode({
    id: "entry_router",
    name: "Entry Router",
    type: "router",
    position: [0, 0],
    runtime_status: "success",
  }),
  buildNode({
    id: "intent_classifier",
    name: "Intent Classifier",
    type: "classifier",
    position: [240, -140],
    runtime_status: "success",
  }),
  buildNode({
    id: "priority_queue",
    name: "Priority Queue",
    type: "queue",
    position: [240, 120],
    runtime_status: "running",
  }),
  buildNode({
    id: "governance_guard",
    name: "Governance Guard",
    type: "safety",
    position: [480, -160],
    runtime_status: "success",
  }),
  buildNode({
    id: "playbook_planner",
    name: "Playbook Planner",
    type: "planner",
    position: [480, 40],
    runtime_status: "success",
  }),
  buildNode({
    id: "sentinel_watchdog",
    name: "Sentinel Watchdog",
    type: "monitor",
    position: [480, 220],
    runtime_status: "running",
  }),
  buildNode({
    id: "ops_router_agent",
    name: "Ops Router Agent",
    type: "router",
    position: [480, 120],
    runtime_status: "success",
  }),
  buildNode({
    id: "agent_capi_gus",
    name: "Agent capi_gus",
    type: "assistant",
    position: [720, -220],
    runtime_status: "success",
  }),
  buildNode({
    id: "agent_branch_insights",
    name: "Agent branch",
    type: "assistant",
    position: [720, -60],
    runtime_status: "success",
  }),
  buildNode({
    id: "agent_risk_guardian",
    name: "Agent risk_guardian",
    type: "assistant",
    position: [720, 100],
    runtime_status: "running",
  }),
  buildNode({
    id: "agent_vector_forge",
    name: "Agent vector_forge",
    type: "assistant",
    position: [720, 260],
    runtime_status: "success",
  }),
  buildNode({
    id: "agent_atlas_mapper",
    name: "Agent atlas_mapper",
    type: "assistant",
    position: [720, 380],
    runtime_status: "idle",
  }),
  buildNode({
    id: "agent_capi_datab",
    name: "Agent capi_datab",
    type: "assistant",
    position: [720, 20],
    runtime_status: "success",
  }),
  buildNode({
    id: "metrics_collector",
    name: "Metrics Collector",
    type: "telemetry",
    position: [960, -120],
    runtime_status: "success",
  }),
  buildNode({
    id: "notifier_ops",
    name: "Notifier Ops",
    type: "notifier",
    position: [960, 40],
    runtime_status: "success",
  }),
  buildNode({
    id: "notifier_clients",
    name: "Notifier Clients",
    type: "notifier",
    position: [960, 200],
    runtime_status: "success",
  }),
  buildNode({
    id: "audit_logger",
    name: "Audit Logger",
    type: "logger",
    position: [1200, 80],
    runtime_status: "success",
  }),
  buildNode({
    id: "knowledge_hub",
    name: "Knowledge Hub",
    type: "repository",
    position: [1420, 80],
    runtime_status: "idle",
  }),
  buildNode({
    id: "observability_panel",
    name: "Observability Panel",
    type: "telemetry",
    position: [1180, -120],
    runtime_status: "running",
  }),
];

const buildWorkflow = (workflowId: string): GraphCanvaWorkflow => ({
  id: workflowId,
  name: "CAPI Agentic Mesh",
  active: true,
  is_archived: false,
  nodes: buildNodes(),
  connections: buildConnections(),
  settings: { environment: "demo", owner: "GraphCanva" },
  pin_data: null,
  meta: buildMeta(),
  version_id: "demo-v7",
  trigger_count: 87,
  tags: ["demo", "agents", "overview"],
  shared: [],
  permissions: [],
  created_at: "2024-05-01T09:00:00.000Z",
  updated_at: ISO_NOW,
});

export const getFallbackWorkflow = (workflowId: string): GraphCanvaWorkflow | null => {
  if (workflowId !== "graph-canva-demo") {
    return null;
  }
  return buildWorkflow(workflowId);
};
