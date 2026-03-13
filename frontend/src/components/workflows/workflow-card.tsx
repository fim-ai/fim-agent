"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import {
  GitBranch,
  MoreHorizontal,
  Pencil,
  Play,
  Trash2,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { WorkflowResponse } from "@/types/workflow"

interface WorkflowCardProps {
  workflow: WorkflowResponse
  onDelete: (id: string) => void
}

export function WorkflowCard({ workflow, onDelete }: WorkflowCardProps) {
  const t = useTranslations("workflows")
  const tc = useTranslations("common")
  const isActive = workflow.status === "active"
  const nodeCount = workflow.blueprint?.nodes?.length ?? 0

  return (
    <div className="group flex flex-col rounded-lg border border-border bg-card p-4 transition-colors hover:border-ring/40 hover:bg-accent/10">
      {/* Header: icon + name + dropdown menu */}
      <div className="flex items-center gap-2 mb-1.5">
        <h3 className="flex-1 min-w-0 text-sm font-medium truncate text-card-foreground flex items-center gap-1.5">
          {workflow.icon ? (
            <span className="shrink-0 text-base leading-none">{workflow.icon}</span>
          ) : (
            <GitBranch className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          {workflow.name}
        </h3>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className="shrink-0 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100 transition-opacity"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link href={`/workflows/${workflow.id}`}>
                <Pencil className="h-4 w-4" />
                {tc("edit")}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href={`/workflows/${workflow.id}?run=true`}>
                <Play className="h-4 w-4" />
                {t("editorRun")}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={() => onDelete(workflow.id)}>
              <Trash2 className="h-4 w-4" />
              {tc("delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Status badges */}
      <div className="flex items-center gap-1.5 mb-2 flex-wrap">
        <Badge
          variant="secondary"
          className={cn(
            "text-[10px] px-1.5 py-0 h-5",
            isActive
              ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
              : "opacity-60",
          )}
        >
          {isActive ? t("statusActive") : t("statusDraft")}
        </Badge>
        {nodeCount > 0 && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-5 opacity-60">
            {t("nodeCount", { count: nodeCount })}
          </Badge>
        )}
      </div>

      {/* Description */}
      <p className="flex-1 text-xs text-muted-foreground line-clamp-2 mb-3">
        {workflow.description || t("noDescription")}
      </p>

      {/* Edit CTA */}
      <Button
        variant="outline"
        size="sm"
        className="mt-auto w-full gap-1.5 text-xs h-7"
        asChild
      >
        <Link href={`/workflows/${workflow.id}`}>
          <Pencil className="h-3 w-3" />
          {tc("edit")}
        </Link>
      </Button>
    </div>
  )
}
