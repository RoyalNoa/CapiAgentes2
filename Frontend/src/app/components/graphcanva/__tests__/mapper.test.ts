import { describe, expect, it } from "vitest";

import { mapWorkflowToElements } from "../mapper";
import type { GraphCanvaWorkflow } from "../types";

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
      position: [200, 0],
      runtime_status: "success",
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
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe("mapWorkflowToElements", () => {
  it("converts nodes and connections into React Flow elements", () => {
    const { nodes, edges, viewport } = mapWorkflowToElements(sampleWorkflow);
    expect(nodes).toHaveLength(2);
    expect(edges).toHaveLength(1);
    expect(nodes[0].id).toBe("start");
    expect(edges[0].source).toBe("start");
    expect(edges[0].target).toBe("end");
    expect(viewport).toEqual({ x: 0, y: 0, zoom: 1 });
  });
});
