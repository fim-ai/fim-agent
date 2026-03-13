"use client"

import { memo } from "react"
import { cn } from "@/lib/utils"
import type { NodeRunStatus, WorkflowNodeType } from "@/types/workflow"

const categoryColorMap: Record<string, string> = {
  start: "bg-green-500",
  end: "bg-red-500",
  llm: "bg-blue-500",
  questionClassifier: "bg-teal-500",
  agent: "bg-indigo-500",
  knowledgeRetrieval: "bg-teal-500",
  conditionBranch: "bg-orange-500",
  connector: "bg-purple-500",
  httpRequest: "bg-slate-500",
  variableAssign: "bg-gray-500",
  templateTransform: "bg-amber-500",
  codeExecution: "bg-emerald-500",
}

const runStatusStyles: Record<NodeRunStatus, { border: string; extra: string }> = {
  pending: {
    border: "border-zinc-400/40 dark:border-zinc-600/40",
    extra: "",
  },
  running: {
    border: "border-blue-500/60",
    extra: "shadow-[0_0_12px_rgba(59,130,246,0.25)] animate-pulse",
  },
  completed: {
    border: "border-green-500/60",
    extra: "",
  },
  failed: {
    border: "border-red-500/60",
    extra: "",
  },
  skipped: {
    border: "border-zinc-400/40 dark:border-zinc-600/40 border-dashed",
    extra: "opacity-60",
  },
}

interface BaseWorkflowNodeProps {
  nodeType: WorkflowNodeType
  icon: React.ReactNode
  title: string
  selected?: boolean
  runStatus?: NodeRunStatus
  children?: React.ReactNode
}

function BaseWorkflowNodeComponent({
  nodeType,
  icon,
  title,
  selected,
  runStatus,
  children,
}: BaseWorkflowNodeProps) {
  const barColor = categoryColorMap[nodeType] ?? "bg-muted"
  const statusStyle = runStatus ? runStatusStyles[runStatus] : null

  return (
    <div
      className={cn(
        "w-[240px] rounded-lg border bg-card transition-all duration-200 hover:brightness-[1.03] dark:hover:brightness-110 overflow-hidden",
        statusStyle ? statusStyle.border : "border-border",
        statusStyle?.extra,
        selected && "outline-2 outline-primary",
      )}
    >
      {/* Top colored bar */}
      <div className={cn("h-1 w-full", barColor)} />

      {/* Icon + title row */}
      <div className="flex items-center gap-2 px-3 pt-2 pb-1">
        <div className="flex h-5 w-5 shrink-0 items-center justify-center">
          {icon}
        </div>
        <span className="text-xs font-medium text-card-foreground truncate flex-1">
          {title}
        </span>
        {runStatus && runStatus !== "pending" && (
          <RunStatusBadge status={runStatus} />
        )}
      </div>

      {/* Node-specific content */}
      {children && (
        <div className="px-3 pb-2 pt-0.5">
          {children}
        </div>
      )}
    </div>
  )
}

function RunStatusBadge({ status }: { status: NodeRunStatus }) {
  const config: Record<NodeRunStatus, { bg: string; text: string; label: string }> = {
    pending: { bg: "bg-zinc-500/10", text: "text-zinc-500", label: "" },
    running: { bg: "bg-blue-500/10", text: "text-blue-500", label: "..." },
    completed: { bg: "bg-green-500/10", text: "text-green-500", label: "OK" },
    failed: { bg: "bg-red-500/10", text: "text-red-500", label: "ERR" },
    skipped: { bg: "bg-zinc-500/10", text: "text-zinc-500", label: "SKIP" },
  }
  const c = config[status]
  return (
    <span className={cn("text-[9px] font-mono px-1 py-0.5 rounded", c.bg, c.text)}>
      {c.label}
    </span>
  )
}

export const BaseWorkflowNode = memo(BaseWorkflowNodeComponent)
