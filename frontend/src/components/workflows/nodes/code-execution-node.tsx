"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { Code } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { CodeExecutionNodeData, NodeRunStatus } from "@/types/workflow"

function CodeExecutionNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as CodeExecutionNodeData & { runStatus?: NodeRunStatus }

  return (
    <BaseWorkflowNode
      nodeType="codeExecution"
      icon={<Code className="h-3.5 w-3.5 text-emerald-500" />}
      title={t("nodeType_codeExecution")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      {nodeData.language && (
        <span className="text-[10px] font-mono font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
          {nodeData.language}
        </span>
      )}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-emerald-500 !border-emerald-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        className="!w-2 !h-2 !bg-emerald-500 !border-emerald-500"
      />
    </BaseWorkflowNode>
  )
}

export const CodeExecutionNode = memo(CodeExecutionNodeComponent)
