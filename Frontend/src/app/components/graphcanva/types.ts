export type GraphCanvaVector = [number, number];

export type GraphCanvaNodeRuntimeStatus =
  | "idle"
  | "running"
  | "success"
  | "error"
  | "waiting";

export interface GraphCanvaNode {
  id: string;
  name: string;
  type: string;
  type_version: number;
  parameters: Record<string, unknown>;
  credentials?: Record<string, unknown> | null;
  position: GraphCanvaVector;
  disabled?: boolean;
  notes?: string | null;
  always_output_data?: boolean | null;
  retry_on_fail?: boolean | null;
  max_concurrency?: number | null;
  hooks?: Record<string, unknown> | null;
  runtime_status: GraphCanvaNodeRuntimeStatus;
  last_run_at?: string | null;
}

export interface GraphCanvaConnectionEndpoint {
  node: string;
  type: string;
  index: number;
  connection_id?: string | null;
  meta?: {
    last_status?: string | null;
    last_latency_ms?: number | null;
    last_error?: string | null;
    last_payload_sample?: Record<string, unknown> | null;
  } | null;
}

export type GraphCanvaConnectionMap = Record<string, Record<string, GraphCanvaConnectionEndpoint[]>>;

export interface GraphCanvaViewportMeta {
  pan_x: number;
  pan_y: number;
  zoom: number;
}

export interface GraphCanvaGridMeta {
  size: number;
  snap: boolean;
}

export interface GraphCanvaPanelsMeta {
  inspector_open: boolean;
  execution_sidebar_mode: "hidden" | "summary" | "detail";
  ndv_open_node: string | null;
}

export interface GraphCanvaSelectionMeta {
  nodes: string[];
  edges: string[];
}

export interface GraphCanvaAnalyticsMeta {
  tidy_count: number;
  tidy_last_at: string | null;
}

export interface GraphCanvaMeta {
  viewport: GraphCanvaViewportMeta;
  grid: GraphCanvaGridMeta;
  panels: GraphCanvaPanelsMeta;
  selection: GraphCanvaSelectionMeta;
  analytics: GraphCanvaAnalyticsMeta;
  layout_dirty: boolean;
  data_dirty: boolean;
}

export interface GraphCanvaPinEntry {
  json: Record<string, unknown>;
  binary?: Record<string, unknown> | null;
  paired_item?: unknown;
}

export type GraphCanvaPinData = Record<string, GraphCanvaPinEntry[]>;

export interface GraphCanvaWorkflow {
  id: string;
  name: string;
  active: boolean;
  is_archived: boolean;
  nodes: GraphCanvaNode[];
  connections: GraphCanvaConnectionMap;
  settings: Record<string, unknown>;
  pin_data?: GraphCanvaPinData | null;
  meta: GraphCanvaMeta;
  version_id?: string | null;
  trigger_count: number;
  tags: string[];
  shared: string[];
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export type GraphCanvaWorkflowUpdate = Partial<{
  meta: GraphCanvaMeta;
  node_positions: Record<string, GraphCanvaVector>;
  pin_data: GraphCanvaPinData | null;
}>;

export type GraphCanvaExecutionStatus = "queued" | "running" | "success" | "error" | "cancelled";

export interface GraphCanvaExecution {
  execution_id: string;
  workflow_id: string;
  status: GraphCanvaExecutionStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_ms?: number | null;
  error?: string | null;
  summary: Record<string, unknown>;
}

export interface GraphCanvaExecutionRequest {
  mode?: "manual" | "scheduled" | "webhook";
  session_id?: string | null;
  payload?: Record<string, unknown>;
}

export interface GraphCanvaPushBase {
  execution_id: string;
  workflow_id: string;
  emitted_at: string;
  data: Record<string, unknown>;
  meta?: Record<string, unknown>;
}

export type GraphCanvaPushMessage =
  | (GraphCanvaPushBase & { type: "execution_started"; mode: string })
  | (GraphCanvaPushBase & { type: "execution_finished"; status: GraphCanvaExecutionStatus; error?: string | null })
  | (GraphCanvaPushBase & { type: "node_execute_before"; node_name: string })
  | (GraphCanvaPushBase & { type: "node_execute_after"; node_name: string; status: GraphCanvaExecutionStatus })
  | (GraphCanvaPushBase & { type: "node_execute_after_data"; node_name: string });

export interface GraphCanvaNodeType {
  name: string;
  display_name: string;
  group: string;
  description?: string;
  icon?: string;
  defaults: Record<string, unknown>;
  inputs: string[];
  outputs: string[];
  properties: Array<{
    name: string;
    display_name?: string;
    type: string;
    description?: string;
  }>;
  documentation_url?: string | null;
}

export interface GraphCanvaCredentialType {
  name: string;
  display_name: string;
  properties: Record<string, unknown>;
  icon?: string;
  documentation_url?: string | null;
}

export interface GraphCanvaCatalog {
  nodes: GraphCanvaNodeType[];
  credentials: GraphCanvaCredentialType[];
}

export interface GraphCanvaRunResponse extends GraphCanvaExecution {}
export interface GraphCanvaNodeDataPayload {
  nodeId: string;
  label: string;
  subtitle?: string;
  status: GraphCanvaNodeRuntimeStatus;
  isDisabled: boolean;
  lastRunAt?: string | null;
  metrics?: Record<string, unknown>;
}
