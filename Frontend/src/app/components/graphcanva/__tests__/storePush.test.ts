import { beforeEach, describe, expect, it } from "vitest";

import { mapWorkflowToElements } from "../mapper";
import { resetGraphCanvaStore, useGraphCanvaStore } from "../store";
import type { GraphCanvaPushMessage, GraphCanvaWorkflow } from "../types";

const now = new Date().toISOString();

const sampleWorkflow: GraphCanvaWorkflow = {
  id: "wf",
  name: "Sample",
  active: true,
  is_archived: false,
  nodes: [
    {
      id: "start",
      name: "Start",
      type: "capi.start",
      type_version: 1,
      parameters: {},
      credentials: null,
      position: [0, 0],
      runtime_status: "idle",
      last_run_at: null,
      disabled: false,
      notes: null,
      always_output_data: true,
      retry_on_fail: false,
      max_concurrency: null,
      hooks: null,
    },
    {
      id: "end",
      name: "End",
      type: "capi.output",
      type_version: 1,
      parameters: {},
      credentials: null,
      position: [240, 0],
      runtime_status: "idle",
      last_run_at: null,
      disabled: false,
      notes: null,
      always_output_data: false,
      retry_on_fail: false,
      max_concurrency: null,
      hooks: null,
    },
  ],
  connections: {
    main: {
      start: [{ node: "end", type: "main", index: 0 }],
    },
  },
  settings: {},
  pin_data: null,
  meta: {
    viewport: { pan_x: 0, pan_y: 0, zoom: 1 },
    grid: { size: 20, snap: true },
    panels: { inspector_open: false, execution_sidebar_mode: "hidden", ndv_open_node: null },
    selection: { nodes: [], edges: [] },
    analytics: { tidy_count: 0, tidy_last_at: null },
    layout_dirty: false,
    data_dirty: false,
  },
  version_id: "v1",
  trigger_count: 0,
  tags: [],
  shared: [],
  permissions: [],
  created_at: now,
  updated_at: now,
};

const startMessage: GraphCanvaPushMessage = {
  type: "execution_started",
  execution_id: "exec-1",
  workflow_id: "wf",
  emitted_at: now,
  data: {},
  mode: "manual",
};

const nodeBefore: GraphCanvaPushMessage = {
  type: "node_execute_before",
  execution_id: "exec-1",
  workflow_id: "wf",
  emitted_at: now,
  data: {},
  node_name: "Start",
};

const nodeAfter: GraphCanvaPushMessage = {
  type: "node_execute_after",
  execution_id: "exec-1",
  workflow_id: "wf",
  emitted_at: now,
  data: {},
  node_name: "Start",
  status: "success",
};

const nodeData: GraphCanvaPushMessage = {
  type: "node_execute_after_data",
  execution_id: "exec-1",
  workflow_id: "wf",
  emitted_at: now,
  data: { preview: { foo: "bar" } },
  node_name: "Start",
};

const finishedMessage: GraphCanvaPushMessage = {
  type: "execution_finished",
  execution_id: "exec-1",
  workflow_id: "wf",
  emitted_at: now,
  data: {},
  status: "success",
  error: null,
};

beforeEach(() => {
  resetGraphCanvaStore();
  const mapped = mapWorkflowToElements(sampleWorkflow);
  useGraphCanvaStore.getState().setWorkflow(sampleWorkflow, mapped.nodes, mapped.edges);
});

describe("GraphCanva store push handling", () => {
  it("updates execution lifecycle and node outputs", () => {
    const store = useGraphCanvaStore.getState();
    store.applyPushMessage(startMessage);
    expect(useGraphCanvaStore.getState().execution?.status).toBe("running");

    store.applyPushMessage(nodeBefore);
    expect(useGraphCanvaStore.getState().nodes[0].data.status).toBe("running");

    store.applyPushMessage(nodeAfter);
    expect(useGraphCanvaStore.getState().nodes[0].data.status).toBe("success");

    store.applyPushMessage(nodeData);
    const ndv = useGraphCanvaStore.getState().nodeOutputs;
    const workflowNodeId = sampleWorkflow.nodes[0].id;
    expect(ndv[workflowNodeId]).toEqual(nodeData.data);
    expect(useGraphCanvaStore.getState().activeNdvNode).toBe(workflowNodeId);

    store.applyPushMessage(finishedMessage);
    expect(useGraphCanvaStore.getState().execution?.status).toBe("success");
  });
});
