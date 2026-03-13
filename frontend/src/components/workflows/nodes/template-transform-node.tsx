"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { FileText } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { TemplateTransformNodeData, NodeRunStatus } from "@/types/workflow"

function TemplateTransformNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as TemplateTransformNodeData & { runStatus?: NodeRunStatus }

  return (
    <BaseWorkflowNode
      nodeType="templateTransform"
      icon={<FileText className="h-3.5 w-3.5 text-amber-500" />}
      title={t("nodeType_templateTransform")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      {nodeData.template && (
        <p className="text-[10px] text-muted-foreground/70 line-clamp-1 font-mono">
          {nodeData.template}
        </p>
      )}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-amber-500 !border-amber-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        className="!w-2 !h-2 !bg-amber-500 !border-amber-500"
      />
    </BaseWorkflowNode>
  )
}

export const TemplateTransformNode = memo(TemplateTransformNodeComponent)
