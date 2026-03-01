"use client"

import { useState } from "react"
import { Loader2, ChevronRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import type { IterationData } from "./types"
import { IterationHeader } from "./iteration-header"
import { generateStepSummary } from "./step-summary"
import { IterationDetailDrawer } from "./iteration-detail-drawer"

interface IterationCardProps {
  data: IterationData
  summary?: string
  size?: "default" | "compact"
  variant?: "card" | "inline"
  defaultCollapsed?: boolean
  showReasoning?: boolean
}

export function IterationCard({
  data,
  summary: summaryProp,
  size = "default",
  variant = "card",
}: IterationCardProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const isCompact = size === "compact"
  const isLoading = data.loading || data.type === "tool_start"

  const hasDetail = !isLoading && (
    (data.tool_args && Object.keys(data.tool_args).length > 0) ||
    data.observation ||
    data.error ||
    data.reasoning
  )

  const summary = summaryProp ?? (
    (data.type === "tool_call" || data.type === "tool_start")
      ? generateStepSummary(data.tool_name, data.tool_args, data.reasoning)
      : undefined
  )

  const content = (
    <div
      className={`flex items-center gap-2 ${hasDetail ? "cursor-pointer group" : ""}`}
      onClick={hasDetail ? () => setDrawerOpen(true) : undefined}
    >
      <div className="flex-1 min-w-0">
        <IterationHeader data={data} summary={summary} size={size} />
      </div>
      {isLoading && (
        <div className={`flex items-center gap-1.5 shrink-0 ${isCompact ? "" : "mr-1"}`}>
          <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
          <span className="shiny-text text-[10px] text-muted-foreground">Executing…</span>
        </div>
      )}
      {hasDetail && (
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0 group-hover:text-foreground transition-colors" />
      )}
    </div>
  )

  if (variant === "card") {
    return (
      <>
        <Card className="animate-in fade-in-0 slide-in-from-bottom-2 duration-300 border-amber-500/20 py-3 hover:bg-muted/30 transition-colors">
          <CardContent>{content}</CardContent>
        </Card>
        <IterationDetailDrawer
          data={drawerOpen ? data : null}
          summary={summary}
          onClose={() => setDrawerOpen(false)}
        />
      </>
    )
  }

  // variant === "inline"
  return (
    <>
      <div className="rounded-md border border-border/30 bg-muted/20 p-2.5 hover:bg-muted/30 transition-colors">
        {content}
      </div>
      <IterationDetailDrawer
        data={drawerOpen ? data : null}
        summary={summary}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  )
}
