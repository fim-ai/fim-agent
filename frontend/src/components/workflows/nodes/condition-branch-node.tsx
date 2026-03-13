"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { GitBranch } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { ConditionNodeData, NodeRunStatus } from "@/types/workflow"

function ConditionBranchNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as ConditionNodeData & { runStatus?: NodeRunStatus }
  const conditions = nodeData.conditions ?? []

  return (
    <BaseWorkflowNode
      nodeType="conditionBranch"
      icon={<GitBranch className="h-3.5 w-3.5 text-orange-500" />}
      title={t("nodeType_conditionBranch")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      {conditions.length > 0 && (
        <div className="space-y-0.5">
          {conditions.map((c, i) => (
            <p key={c.id ?? i} className="text-[10px] text-muted-foreground truncate">
              {c.label || `Condition ${i + 1}`}
            </p>
          ))}
        </div>
      )}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-orange-500 !border-orange-500"
      />
      {/* One source handle per condition */}
      {conditions.length > 0
        ? conditions.map((c, i) => (
            <Handle
              key={c.id ?? i}
              type="source"
              position={Position.Bottom}
              id={`condition-${c.id ?? i}`}
              className="!w-2 !h-2 !bg-orange-500 !border-orange-500"
              style={{ left: `${((i + 1) / (conditions.length + 1)) * 100}%` }}
            />
          ))
        : (
            <Handle
              type="source"
              position={Position.Bottom}
              id="source-default"
              className="!w-2 !h-2 !bg-orange-500 !border-orange-500"
            />
          )}
    </BaseWorkflowNode>
  )
}

export const ConditionBranchNode = memo(ConditionBranchNodeComponent)
