"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { Square } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { EndNodeData, NodeRunStatus } from "@/types/workflow"

function EndNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as EndNodeData & { runStatus?: NodeRunStatus }
  const mappingCount = nodeData.output_mapping
    ? Object.keys(nodeData.output_mapping).length
    : 0

  return (
    <BaseWorkflowNode
      nodeType="end"
      icon={<Square className="h-3.5 w-3.5 text-red-500" />}
      title={t("nodeType_end")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      <p className="text-[10px] text-muted-foreground">
        {t("mappingCount", { count: mappingCount })}
      </p>
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-red-500 !border-red-500"
      />
    </BaseWorkflowNode>
  )
}

export const EndNode = memo(EndNodeComponent)
