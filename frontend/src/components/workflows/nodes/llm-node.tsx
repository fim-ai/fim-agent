"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { Brain } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { LLMNodeData, NodeRunStatus } from "@/types/workflow"

function LLMNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as LLMNodeData & { runStatus?: NodeRunStatus }

  return (
    <BaseWorkflowNode
      nodeType="llm"
      icon={<Brain className="h-3.5 w-3.5 text-blue-500" />}
      title={t("nodeType_llm")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      {nodeData.model && (
        <p className="text-[10px] text-muted-foreground truncate">
          {nodeData.model}
        </p>
      )}
      {nodeData.prompt_template && (
        <p className="text-[10px] text-muted-foreground/70 line-clamp-1">
          {nodeData.prompt_template}
        </p>
      )}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-blue-500 !border-blue-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        className="!w-2 !h-2 !bg-blue-500 !border-blue-500"
      />
    </BaseWorkflowNode>
  )
}

export const LLMNode = memo(LLMNodeComponent)
