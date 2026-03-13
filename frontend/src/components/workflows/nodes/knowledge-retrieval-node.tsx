"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { Library } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { KnowledgeRetrievalNodeData, NodeRunStatus } from "@/types/workflow"

function KnowledgeRetrievalNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as KnowledgeRetrievalNodeData & { runStatus?: NodeRunStatus; kb_name?: string }

  return (
    <BaseWorkflowNode
      nodeType="knowledgeRetrieval"
      icon={<Library className="h-3.5 w-3.5 text-teal-500" />}
      title={t("nodeType_knowledgeRetrieval")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      {nodeData.kb_name && (
        <p className="text-[10px] text-muted-foreground truncate">
          {nodeData.kb_name}
        </p>
      )}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-teal-500 !border-teal-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        className="!w-2 !h-2 !bg-teal-500 !border-teal-500"
      />
    </BaseWorkflowNode>
  )
}

export const KnowledgeRetrievalNode = memo(KnowledgeRetrievalNodeComponent)
