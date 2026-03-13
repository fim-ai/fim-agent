"use client"

import { useCallback, useRef, useState, useEffect } from "react"
import { useTheme } from "next-themes"
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
} from "@xyflow/react"
import type {
  Connection,
  NodeMouseHandler,
  Node,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"

import { NodePalette } from "./node-palette"
import { NodeConfigPanel } from "./node-config-panel"
import { RunPanel } from "./run-panel"
import type {
  WorkflowBlueprint,
  WorkflowNodeType,
  StartNodeData,
  NodeRunResult,
} from "@/types/workflow"

import { StartNode } from "./nodes/start-node"
import { EndNode } from "./nodes/end-node"
import { LLMNode } from "./nodes/llm-node"
import { ConditionBranchNode } from "./nodes/condition-branch-node"
import { QuestionClassifierNode } from "./nodes/question-classifier-node"
import { AgentNode } from "./nodes/agent-node"
import { KnowledgeRetrievalNode } from "./nodes/knowledge-retrieval-node"
import { ConnectorNode } from "./nodes/connector-node"
import { HTTPRequestNode } from "./nodes/http-request-node"
import { VariableAssignNode } from "./nodes/variable-assign-node"
import { TemplateTransformNode } from "./nodes/template-transform-node"
import { CodeExecutionNode } from "./nodes/code-execution-node"

// MUST be defined outside the component to prevent ReactFlow infinite re-renders
const nodeTypes = {
  start: StartNode,
  end: EndNode,
  llm: LLMNode,
  conditionBranch: ConditionBranchNode,
  questionClassifier: QuestionClassifierNode,
  agent: AgentNode,
  knowledgeRetrieval: KnowledgeRetrievalNode,
  connector: ConnectorNode,
  httpRequest: HTTPRequestNode,
  variableAssign: VariableAssignNode,
  templateTransform: TemplateTransformNode,
  codeExecution: CodeExecutionNode,
}

const defaultNodeData: Record<WorkflowNodeType, Record<string, unknown>> = {
  start: { variables: [] },
  end: { output_mapping: {} },
  llm: { prompt_template: "", output_variable: "llm_result", temperature: 0.7 },
  conditionBranch: { mode: "expression", conditions: [] },
  questionClassifier: { classes: [] },
  agent: { agent_id: "", output_variable: "agent_result" },
  knowledgeRetrieval: { kb_id: "", query_template: "", top_k: 5, output_variable: "kb_result" },
  connector: { connector_id: "", action: "", parameters: {}, output_variable: "connector_result" },
  httpRequest: { method: "GET", url: "", output_variable: "http_result" },
  variableAssign: { assignments: [] },
  templateTransform: { template: "", output_variable: "template_result" },
  codeExecution: { language: "python", code: "", output_variable: "code_result" },
}

interface WorkflowEditorProps {
  blueprint: WorkflowBlueprint
  onBlueprintChange: (blueprint: WorkflowBlueprint) => void
  isRunning: boolean
  runPanelOpen: boolean
  startVariables: StartNodeData["variables"]
  nodeResults: Record<string, NodeRunResult> | null
  finalOutputs: Record<string, unknown> | null
  finalError: string | null
  runDuration: number | null
  onStartRun: (inputs: Record<string, unknown>) => void
  onCancelRun: () => void
  onCloseRunPanel: () => void
}

export function WorkflowEditor({
  blueprint,
  onBlueprintChange,
  isRunning,
  runPanelOpen,
  startVariables,
  nodeResults,
  finalOutputs,
  finalError,
  runDuration,
  onStartRun,
  onCancelRun,
  onCloseRunPanel,
}: WorkflowEditorProps) {
  const { resolvedTheme } = useTheme()
  const rfColorMode = resolvedTheme === "dark" ? "dark" : "light"
  const reactFlowWrapper = useRef<HTMLDivElement>(null)

  const [nodes, setNodes, onNodesChange] = useNodesState(
    blueprint.nodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: n.data,
    } as Node)),
  )
  const [edges, setEdges, onEdgesChange] = useEdgesState(
    blueprint.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle,
      targetHandle: e.targetHandle,
    })),
  )
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  // Sync node run results into node data
  useEffect(() => {
    if (!nodeResults) return
    setNodes((currentNodes) =>
      currentNodes.map((node) => {
        const result = nodeResults[node.id]
        const prevStatus = node.data.runStatus
        const newStatus = result?.status
        if (prevStatus === newStatus) return node
        return {
          ...node,
          data: { ...node.data, runStatus: newStatus },
        }
      }),
    )
  }, [nodeResults, setNodes])

  // Clear run status when run panel closes and no run is active
  useEffect(() => {
    if (!runPanelOpen && !isRunning) {
      setNodes((currentNodes) =>
        currentNodes.map((node) => {
          if (!node.data.runStatus) return node
          return { ...node, data: { ...node.data, runStatus: undefined } }
        }),
      )
    }
  }, [runPanelOpen, isRunning, setNodes])

  // Sync blueprint out when nodes/edges change (debounced)
  const syncTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (syncTimer.current) clearTimeout(syncTimer.current)
    syncTimer.current = setTimeout(() => {
      onBlueprintChange({
        nodes: nodes.map((n) => ({
          id: n.id,
          type: n.type as WorkflowNodeType,
          position: n.position,
          data: n.data as Record<string, unknown>,
        })),
        edges: edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle ?? undefined,
          targetHandle: e.targetHandle ?? undefined,
        })),
        viewport: blueprint.viewport,
      })
    }, 300)
    return () => {
      if (syncTimer.current) clearTimeout(syncTimer.current)
    }
    // Only sync when nodes/edges change, not blueprint ref
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, onBlueprintChange])

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            id: `e-${params.source}-${params.sourceHandle ?? "default"}-${params.target}-${params.targetHandle ?? "default"}`,
          },
          eds,
        ),
      )
    },
    [setEdges],
  )

  // Connection validation: don't connect to Start, don't connect from End
  const isValidConnection = useCallback(
    (connection: Connection | { source: string; target: string }) => {
      const targetNode = nodes.find((n) => n.id === connection.target)
      const sourceNode = nodes.find((n) => n.id === connection.source)
      if (targetNode?.type === "start") return false
      if (sourceNode?.type === "end") return false
      return true
    },
    [nodes],
  )

  // Drop handler for palette drag-and-drop
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()
      const nodeType = event.dataTransfer.getData("application/reactflow-node-type") as WorkflowNodeType
      if (!nodeType) return

      const wrapper = reactFlowWrapper.current
      if (!wrapper) return

      const bounds = wrapper.getBoundingClientRect()
      const position = {
        x: event.clientX - bounds.left - 120,
        y: event.clientY - bounds.top - 30,
      }

      const newNode: Node = {
        id: `${nodeType}_${Date.now()}`,
        type: nodeType,
        position,
        data: { ...defaultNodeData[nodeType] },
      }

      setNodes((nds) => [...nds, newNode])
    },
    [setNodes],
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = "move"
  }, [])

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNodeId(node.id)
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  const handleNodeDataUpdate = useCallback(
    (nodeId: string, data: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data } : n)),
      )
    },
    [setNodes],
  )

  const selectedNode = selectedNodeId
    ? nodes.find((n) => n.id === selectedNodeId) ?? null
    : null

  return (
    <div className="flex flex-1 min-h-0 overflow-hidden relative">
      {/* Left palette */}
      <NodePalette />

      {/* Center: React Flow canvas */}
      <div className="flex-1 min-w-0 relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          fitView
          colorMode={rfColorMode}
          proOptions={{ hideAttribution: true }}
          minZoom={0.2}
          maxZoom={2}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls showInteractive={false} />
          <MiniMap
            nodeStrokeWidth={3}
            pannable
            zoomable
            className="!bg-background/80 !border-border"
          />
        </ReactFlow>

        {/* Run Panel (overlay at bottom) */}
        <RunPanel
          isOpen={runPanelOpen}
          isRunning={isRunning}
          startVariables={startVariables}
          nodeResults={nodeResults}
          finalOutputs={finalOutputs}
          finalError={finalError}
          runDuration={runDuration}
          onStartRun={onStartRun}
          onCancel={onCancelRun}
          onClose={onCloseRunPanel}
        />
      </div>

      {/* Right config panel */}
      {selectedNodeId && (
        <NodeConfigPanel
          node={selectedNode}
          onUpdate={handleNodeDataUpdate}
          onClose={() => setSelectedNodeId(null)}
        />
      )}
    </div>
  )
}
