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
  const nodeData = data as unknown as VariableAssignNodeData & { runStatus?: NodeRunStatus }
  const count = nodeData.assignments?.length ?? 0

  return (
    <BaseWorkflowNode
      nodeType="variableAssign"
      icon={<Variable className="h-3.5 w-3.5 text-gray-500" />}
      title={t("nodeType_variableAssign")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      <p className="text-[10px] text-muted-foreground">
        {t("assignmentCount", { count })}
      </p>
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-gray-500 !border-gray-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="source"
        className="!w-2 !h-2 !bg-gray-500 !border-gray-500"
      />
    </BaseWorkflowNode>
  )
}

export const VariableAssignNode = memo(VariableAssignNodeComponent)
