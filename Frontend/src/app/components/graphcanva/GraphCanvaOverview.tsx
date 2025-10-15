"use client";



import { useCallback, useEffect, useMemo, useState } from "react";

import { shallow } from "zustand/shallow";

import {

  Background,

  Controls,

  ReactFlow,

  ReactFlowProvider,

  type Edge,

  type Node,

  type OnSelectionChangeParams,

  type Viewport,

  useReactFlow,

} from "@xyflow/react";

import "@xyflow/react/dist/style.css";



import { fetchWorkflow, patchWorkflow, runWorkflow } from "@/services/graphCanva";



import { GraphCanvaNode } from "./GraphCanvaNode";

import { GraphCanvaNodeDetail } from "./GraphCanvaNodeDetail";

import { GraphCanvaToolbar } from "./GraphCanvaToolbar";

import { getFallbackWorkflow } from "./mockWorkflow";

import { mapWorkflowToElements, toViewport } from "./mapper";

import { useGraphCanvaPush } from "./useGraphCanvaPush";

import { useGraphCanvaShortcuts } from "./useGraphCanvaShortcuts";

import { useGraphCanvaStore } from "./store";

import type {

  GraphCanvaExecution,

  GraphCanvaPushMessage,

  GraphCanvaVector,

  GraphCanvaWorkflow,

} from "./types";

import styles from "./styles/graphCanva.module.css";



const nodeTypes = { graphCanvaNode: GraphCanvaNode };



type SocketStatus = "connected" | "connecting" | "disconnected";



interface GraphCanvaOverviewInnerProps {

  workflowId: string;

}



function GraphCanvaOverviewInner({ workflowId }: GraphCanvaOverviewInnerProps) {

  const instance = useReactFlow();

  const [error, setError] = useState<string | null>(null);

  const [runError, setRunError] = useState<string | null>(null);

  const [socketStatus, setSocketStatus] = useState<SocketStatus>("connecting");



  const {

    workflow,

    nodes,

    edges,

    loading,

    execution,

    nodeOutputs,

    activeNdvNode,

    setWorkflow,

    setNodes,

    setEdges,

    setViewport,

    setLoading,

    setExecution,

    updateNodePosition,

    updateSelection,

    resetExecution,

    clearNodeOutputs,

    setActiveNdvNode,

    applyPushMessage,

  } = useGraphCanvaStore(

    (state) => ({

      workflow: state.workflow,

      nodes: state.nodes,

      edges: state.edges,

      loading: state.loading,

      execution: state.execution,

      nodeOutputs: state.nodeOutputs,

      activeNdvNode: state.activeNdvNode,

      setWorkflow: state.setWorkflow,

      setNodes: state.setNodes,

      setEdges: state.setEdges,

      setViewport: state.setViewport,

      setLoading: state.setLoading,

      setExecution: state.setExecution,

      updateNodePosition: state.updateNodePosition,

      updateSelection: state.updateSelection,

      resetExecution: state.resetExecution,

      clearNodeOutputs: state.clearNodeOutputs,

      setActiveNdvNode: state.setActiveNdvNode,

      applyPushMessage: state.applyPushMessage,

    }),

    shallow,

  );



  const hydrateWorkflow = useCallback(

    (data: GraphCanvaWorkflow) => {

      const mapped = mapWorkflowToElements(data);

      setWorkflow(data, mapped.nodes, mapped.edges);

      const viewport = mapped.viewport ?? toViewport(data.meta);

      setViewport(viewport);

      requestAnimationFrame(() => {

        instance.setViewport(viewport, { duration: 0 });

      });

    },

    [instance, setViewport, setWorkflow],

  );



  const loadWorkflow = useCallback(async () => {

    setLoading(true);

    setError(null);

    try {

      const data = await fetchWorkflow(workflowId);

      hydrateWorkflow(data);

    } catch (err) {

      const message = err instanceof Error ? err.message : String(err);

      const fallback = getFallbackWorkflow(workflowId);

      if (fallback) {

        console.warn("[GraphCanvaOverview] Using fallback workflow", message);

        hydrateWorkflow(fallback);

        setError(null);

      } else {

        setError(message);

      }

    } finally {

      setLoading(false);

    }

  }, [hydrateWorkflow, setLoading, workflowId]);





  useEffect(() => {

    void loadWorkflow();

  }, [loadWorkflow]);


  const handlePushMessage = useCallback(

    (message: GraphCanvaPushMessage) => {

      applyPushMessage(message);

    },

    [applyPushMessage],

  );



  useGraphCanvaPush({

    workflowId,

    onMessage: handlePushMessage,

    onStatusChange: setSocketStatus,

  });



  useGraphCanvaShortcuts(() => {

    void handleRun();

  });



  const activeNdvPayload = useMemo(() => {

    if (!activeNdvNode) {

      return null;

    }

    return nodeOutputs[activeNdvNode] ?? null;

  }, [activeNdvNode, nodeOutputs]);



  const activeNdvName = useMemo(() => {

    if (!workflow || !activeNdvNode) {

      return null;

    }

    return workflow.nodes.find((node) => node.id === activeNdvNode)?.name ?? null;

  }, [workflow, activeNdvNode]);



  const handleRun = useCallback(async () => {

    if (!workflow) {

      return;

    }

    setRunError(null);

    resetExecution();

    clearNodeOutputs();

    const currentNodes = useGraphCanvaStore.getState().nodes;

    setNodes(

      currentNodes.map((node) => ({

        ...node,

        data: { ...node.data, status: "running" },

      })),

    );

    try {

      const executionResult: GraphCanvaExecution = await runWorkflow(workflow.id, {});

      setExecution(executionResult);

    } catch (err) {

      const message = err instanceof Error ? err.message : String(err);

      setRunError(message);

      setExecution({

        execution_id: "local-error",

        workflow_id: workflow.id,

        status: "error",

        started_at: new Date().toISOString(),

        finished_at: new Date().toISOString(),

        duration_ms: null,

        error: message,

        summary: {},

      });

      const reverted = useGraphCanvaStore.getState().nodes.map((node) => ({

        ...node,

        data: { ...node.data, status: "error" },

      }));

      setNodes(reverted);

    }

  }, [clearNodeOutputs, resetExecution, setExecution, setNodes, workflow]);



  const handleNodeDragStop = useCallback(

    (_event: React.MouseEvent, node: Node) => {

      if (!workflow) {

        return;

      }

      const position: GraphCanvaVector = [node.position.x, node.position.y];

      updateNodePosition(node.id, position);

      void patchWorkflow(workflow.id, { node_positions: { [node.id]: position } });

    },

    [updateNodePosition, workflow],

  );



  const handleMoveEnd = useCallback(

    (_event: React.MouseEvent | null, viewport: Viewport) => {

      if (!workflow) {

        return;

      }

      setViewport(viewport);

      const nextMeta = {

        ...workflow.meta,

        viewport: { pan_x: viewport.x, pan_y: viewport.y, zoom: viewport.zoom },

      };

      useGraphCanvaStore.setState((state) =>

        state.workflow ? { workflow: { ...state.workflow, meta: nextMeta } } : state,

      );

      void patchWorkflow(workflow.id, { meta: nextMeta });

    },

    [setViewport, workflow],

  );



  const handleSelectionChange = useCallback(

    (params: OnSelectionChangeParams) => {

      updateSelection({

        nodes: params.nodes.map((node) => node.id),

        edges: params.edges.map((edge) => edge.id),

      });

      if (params.nodes.length === 1) {
        setActiveNdvNode(params.nodes[0].id);
      } else if (params.nodes.length === 0) {
        setActiveNdvNode(null);
      }

    },

    [setActiveNdvNode, updateSelection],

  );



  const handleNodeDoubleClick = useCallback(

    (_event: React.MouseEvent, node: Node) => {

      setActiveNdvNode(node.id);

    },

    [setActiveNdvNode],

  );



  const handleFitView = useCallback(() => {

    instance.fitView({ padding: 0.12, duration: 300 });

  }, [instance]);



  const handleResetViewport = useCallback(() => {

    if (!workflow) {

      handleFitView();

      return;

    }

    const viewport = toViewport(workflow.meta);

    setViewport(viewport);

    instance.setViewport(viewport, { duration: 300 });

    void patchWorkflow(workflow.id, { meta: workflow.meta });

  }, [handleFitView, instance, setViewport, workflow]);



  const handleCloseNdv = useCallback(() => {

    setActiveNdvNode(null);

  }, [setActiveNdvNode]);



  const isRunning = execution?.status === "running";



  return (

    <div className={styles.container}>

      <GraphCanvaToolbar

        onRun={handleRun}

        onFitView={handleFitView}

        onResetViewport={handleResetViewport}

        disabled={loading || !workflow}

        isRunning={isRunning}

        connectionStatus={socketStatus}

      />

      <div className={styles.canvasWrapper}>

        {loading && (

          <div className={styles.loadingState}>

            <span>Cargando overview de GraphCanva…</span>

          </div>

        )}

        {error && (

          <div className={styles.loadingState}>

            <span>{error}</span>

            <button type="button" className={styles.toolbarButton} onClick={() => void loadWorkflow()}>

              Reintentar

            </button>

          </div>

        )}

        <ReactFlow

          nodes={nodes}

          edges={edges}

          nodeTypes={nodeTypes}

          fitView

          onNodeDragStop={handleNodeDragStop}

          onMoveEnd={handleMoveEnd}

          onSelectionChange={handleSelectionChange}

          onNodeDoubleClick={handleNodeDoubleClick}

          proOptions={{ hideAttribution: true }}

        >

          <Background color="rgba(148,163,184,0.2)" gap={16} />

          <Controls className={styles.flowControls} showInteractive={false} />

        </ReactFlow>

        {execution && (

          <section className={styles.executionSummary}>

            <strong>Última ejecución</strong>

            <p>Estado: {execution.status}</p>

            {typeof execution.summary?.metrics === "object" && execution.summary?.metrics !== null ? (

              <p>

                Duración:

                {" "}

                {String((execution.summary.metrics as Record<string, unknown>).duration_ms ?? "-")} ms

              </p>

            ) : null}

            {execution.error ? <p>Error: {execution.error}</p> : null}

            {runError ? <p>Error: {runError}</p> : null}

          </section>

        )}

        {activeNdvPayload && activeNdvName ? (

          <GraphCanvaNodeDetail nodeName={activeNdvName} payload={activeNdvPayload} onClose={handleCloseNdv} />

        ) : null}

      </div>

    </div>

  );

}



export function GraphCanvaOverview({ workflowId = "graph-canva-demo" }: { workflowId?: string }) {

  return (

    <ReactFlowProvider>

      <GraphCanvaOverviewInner workflowId={workflowId} />

    </ReactFlowProvider>

  );

}
