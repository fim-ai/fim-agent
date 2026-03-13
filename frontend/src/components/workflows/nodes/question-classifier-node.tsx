"use client"

import { memo } from "react"
import { Handle, Position } from "@xyflow/react"
import type { NodeProps } from "@xyflow/react"
import { MessageSquareMore } from "lucide-react"
import { useTranslations } from "next-intl"
import { BaseWorkflowNode } from "./base-workflow-node"
import type { QuestionClassifierNodeData, NodeRunStatus } from "@/types/workflow"

function QuestionClassifierNodeComponent({ data, selected }: NodeProps) {
  const t = useTranslations("workflows")
  const nodeData = data as unknown as QuestionClassifierNodeData & { runStatus?: NodeRunStatus }
  const classes = nodeData.classes ?? []

  return (
    <BaseWorkflowNode
      nodeType="questionClassifier"
      icon={<MessageSquareMore className="h-3.5 w-3.5 text-teal-500" />}
      title={t("nodeType_questionClassifier")}
      selected={selected}
      runStatus={nodeData.runStatus}
    >
      {classes.length > 0 && (
        <div className="space-y-0.5">
          {classes.map((c, i) => (
            <p key={c.id ?? i} className="text-[10px] text-muted-foreground truncate">
              {c.label || `Class ${i + 1}`}
            </p>
          ))}
        </div>
      )}
      <Handle
        type="target"
        position={Position.Top}
        id="target"
        className="!w-2 !h-2 !bg-teal-500 !border-teal-500"
      />
      {classes.length > 0
        ? classes.map((c, i) => (
            <Handle
              key={c.id ?? i}
              type="source"
              position={Position.Bottom}
              id={`class-${c.id ?? i}`}
              className="!w-2 !h-2 !bg-teal-500 !border-teal-500"
              style={{ left: `${((i + 1) / (classes.length + 1)) * 100}%` }}
            />
          ))
        : (
            <Handle
              type="source"
              position={Position.Bottom}
              id="source-default"
              className="!w-2 !h-2 !bg-teal-500 !border-teal-500"
            />
          )}
    </BaseWorkflowNode>
  )
}

export const QuestionClassifierNode = memo(QuestionClassifierNodeComponent)
