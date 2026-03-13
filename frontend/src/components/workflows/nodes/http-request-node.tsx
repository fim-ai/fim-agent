"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { Globe } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { HTTPRequestNodeData, NodeRunStatus } from "@/types/workflow"

function HTTPRequestNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as HTTPRequestNodeData & { runStatus?: NodeRunStatus }

  return (
    <BaseWorkflowNode
      nodeType="httpRequest"
      icon={<Globe className="h-3.5 w-3.5 text-slate-500" />}
      title={t("nodeType_httpRequest")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      <div className="flex items-center gap-1.5">
        {nodeData.method && (
          <span className="text-[10px] font-mono font-medium text-muted-foreground bg-muted px-1 py-0.5 rounded">
            {nodeData.method}
          </span>
        )}
        {nodeData.url && (
          <span className="text-[10px] text-muted-foreground/70 truncate">
            {nodeData.url}
          </span>
        )}
      </div>
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-slate-500 !border-slate-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        className="!w-2 !h-2 !bg-slate-500 !border-slate-500"
      />
    </BaseWorkflowNode>
  )
}

export const HTTPRequestNode = memo(HTTPRequestNodeComponent)
