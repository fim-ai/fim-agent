"use client"

import { Wrench, Brain, Clock } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { fmtDuration } from "@/lib/utils"
import type { IterationData } from "./types"
import { ToolArgsBlock } from "./tool-args-block"
import { ObservationBlock } from "./observation-block"
import { ErrorBlock } from "./error-block"

interface IterationDetailDrawerProps {
  data: IterationData | null
  summary?: string
  onClose: () => void
}

export function IterationDetailDrawer({ data, summary, onClose }: IterationDetailDrawerProps) {
  const open = !!data
  const isTool = data?.type === "tool_call" || data?.type === "tool_start"
  const displayName = isTool && data?.tool_name ? data.tool_name : "Thinking"

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent
        side="right"
        className="sm:max-w-lg w-full flex flex-col p-0 gap-0"
      >
        {data && (
          <>
            {/* Header */}
            <div className="shrink-0 px-6 pt-6 pb-4 border-b border-border/40">
              <SheetHeader className="gap-1">
                <SheetTitle className="flex items-center gap-2 text-base">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-500/10">
                    {isTool ? (
                      <Wrench className="h-3.5 w-3.5 text-amber-500" />
                    ) : (
                      <Brain className="h-3.5 w-3.5 text-amber-500" />
                    )}
                  </div>
                  <Badge
                    variant="outline"
                    className="border-amber-500/30 text-amber-500 text-[10px] uppercase tracking-wider"
                  >
                    {isTool ? "Tool" : "Thinking"}
                  </Badge>
                  <span className="truncate">{displayName}</span>
                </SheetTitle>
                <SheetDescription asChild>
                  <div className="flex items-center gap-2 flex-wrap pl-8">
                    {summary && (
                      <span className="text-xs text-muted-foreground">{summary}</span>
                    )}
                    {data.duration != null && (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {fmtDuration(data.duration)}
                      </span>
                    )}
                  </div>
                </SheetDescription>
              </SheetHeader>
            </div>

            {/* Scrollable content */}
            <ScrollArea className="flex-1 min-h-0">
              <div className="px-6 py-4 space-y-4">
                {/* Reasoning */}
                {data.reasoning && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1 uppercase tracking-wider">
                      Reasoning
                    </p>
                    <p className="text-sm italic text-muted-foreground leading-relaxed">
                      {data.reasoning}
                    </p>
                  </div>
                )}

                {/* Arguments */}
                {data.tool_args && Object.keys(data.tool_args).length > 0 && (
                  <ToolArgsBlock args={data.tool_args} />
                )}

                {/* Observation */}
                {data.observation && (
                  <ObservationBlock observation={data.observation} />
                )}

                {/* Error */}
                {data.error && (
                  <ErrorBlock error={data.error} />
                )}
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
