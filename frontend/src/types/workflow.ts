// --- Core workflow types ---

export interface WorkflowResponse {
  id: string
  name: string
  icon: string | null
  description: string | null
  blueprint: WorkflowBlueprint
  input_schema: Record<string, unknown> | null
  output_schema: Record<string, unknown> | null
  status: "draft" | "active"
  is_active: boolean
  visibility: string
  created_at: string
  updated_at: string
}

export interface WorkflowBlueprint {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  viewport: { x: number; y: number; zoom: number }
}

export interface WorkflowNode {
  id: string
  type: WorkflowNodeType
  position: { x: number; y: number }
  data: Record<string, unknown>
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

export type WorkflowNodeType =
  | "start"
  | "end"
  | "llm"
  | "conditionBranch"
  | "questionClassifier"
  | "agent"
  | "knowledgeRetrieval"
  | "connector"
  | "httpRequest"
  | "variableAssign"
  | "templateTransform"
  | "codeExecution"

// --- Per-node data interfaces ---

export interface StartNodeData {
  variables: Array<{
    name: string
    type: string
    default_value?: string
    required?: boolean
  }>
}

export interface EndNodeData {
  output_mapping: Record<string, string>
}

export interface LLMNodeData {
  model?: string
  prompt_template: string
  output_variable: string
  temperature?: number
  max_tokens?: number
}

export interface ConditionNodeData {
  mode: "expression" | "llm"
  conditions: Array<{
    id: string
    label: string
    expression?: string
    llm_prompt?: string
  }>
}

export interface QuestionClassifierNodeData {
  model?: string
  prompt?: string
  classes: Array<{
    id: string
    label: string
    description?: string
  }>
}

export interface AgentNodeData {
  agent_id: string
  prompt_template?: string
  output_variable: string
}

export interface KnowledgeRetrievalNodeData {
  kb_id: string
  query_template: string
  top_k?: number
  output_variable: string
}

export interface ConnectorNodeData {
  connector_id: string
  action: string
  parameters: Record<string, string>
  output_variable: string
}

export interface HTTPRequestNodeData {
  method: string
  url: string
  headers?: Record<string, string>
  body?: string
  output_variable: string
}

export interface VariableAssignNodeData {
  assignments: Array<{
    variable: string
    expression: string
  }>
}

export interface TemplateTransformNodeData {
  template: string
  output_variable: string
}

export interface CodeExecutionNodeData {
  language: "python" | "javascript"
  code: string
  output_variable: string
}

// --- Create / Update payloads ---

export interface WorkflowCreate {
  name: string
  icon?: string | null
  description?: string | null
  blueprint?: WorkflowBlueprint
}

export interface WorkflowUpdate {
  name?: string
  icon?: string | null
  description?: string | null
  blueprint?: WorkflowBlueprint
  input_schema?: Record<string, unknown> | null
  output_schema?: Record<string, unknown> | null
  status?: "draft" | "active"
}

// --- Run types ---

export interface WorkflowRunResponse {
  id: string
  workflow_id: string
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  inputs: Record<string, unknown> | null
  outputs: Record<string, unknown> | null
  node_results: Record<string, NodeRunResult> | null
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  error: string | null
  created_at: string
}

export interface NodeRunResult {
  status: "pending" | "running" | "completed" | "failed" | "skipped"
  output: unknown
  error: string | null
  started_at: string | null
  completed_at: string | null
  duration: number | null
}

// --- Node run status for canvas overlay ---

export type NodeRunStatus = "pending" | "running" | "completed" | "failed" | "skipped"
