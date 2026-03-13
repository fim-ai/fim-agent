"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { Variable } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { VariableAssignNodeData, NodeRunStatus } from "@/types/workflow"

function VariableAssignNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as VariableAssignNodeData & { runStatus?: NodeRunStatus; note?: string }
  const count = nodeData.assignments?.length ?? 0

  return (
    <BaseWorkflowNode
      nodeType="variableAssign"
      icon={<Variable className="h-3 w-3 text-gray-500" />}
      title={t("nodeType_variableAssign")}
      note={nodeData.note}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      <p className="text-[10px] text-muted-foreground">
        {t("assignmentCount", { count })}
      </p>
      <Handle
        type="target"
        position={Position.Left}
        id="target"
        className="!w-2 !h-2 !bg-gray-500 !border-gray-600/30 !-left-1"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="source"
        className="!w-2 !h-2 !bg-gray-500 !border-gray-600/30 !-right-1"
      />
    </BaseWorkflowNode>
  )
}

export const VariableAssignNode = memo(VariableAssignNodeComponent)
