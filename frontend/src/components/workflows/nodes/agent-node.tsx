"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { Bot } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { AgentNodeData, NodeRunStatus } from "@/types/workflow"

function AgentNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as AgentNodeData & { runStatus?: NodeRunStatus; agent_name?: string }

  return (
    <BaseWorkflowNode
      nodeType="agent"
      icon={<Bot className="h-3.5 w-3.5 text-indigo-500" />}
      title={t("nodeType_agent")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      {nodeData.agent_name && (
        <p className="text-[10px] text-muted-foreground truncate">
          {nodeData.agent_name}
        </p>
      )}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-indigo-500 !border-indigo-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        className="!w-2 !h-2 !bg-indigo-500 !border-indigo-500"
      />
    </BaseWorkflowNode>
  )
}

export const AgentNode = memo(AgentNodeComponent)
