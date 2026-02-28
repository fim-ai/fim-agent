"use client"

import { useMemo } from "react"
import { parseEvidence, type ParsedEvidence } from "@/lib/evidence-utils"
import type { ReactStepEvent } from "@/types/api"
import type { StepItem } from "@/hooks/use-react-steps"

interface ReferencesSectionProps {
  items: StepItem[]
}

export function ReferencesSection({ items }: ReferencesSectionProps) {
  const evidence = useMemo<ParsedEvidence | null>(() => {
    // Scan items for tool observations containing "**Evidence**"
    for (const item of items) {
      if (item.event === "step") {
        const step = item.data as ReactStepEvent
        if (step.type === "tool_call" && step.observation?.includes("**Evidence**")) {
          const parsed = parseEvidence(step.observation)
          if (parsed) return parsed
        }
      }
    }
    return null
  }, [items])

  if (!evidence || evidence.sources.length === 0) return null

  // Determine confidence color
  const confidenceColor = evidence.confidence >= 70
    ? "text-green-600 dark:text-green-400"
    : evidence.confidence >= 40
      ? "text-yellow-600 dark:text-yellow-400"
      : "text-red-600 dark:text-red-400"

  return (
    <div className="mt-4 pt-3 border-t border-border">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-medium text-muted-foreground">References</span>
        <span className={`text-xs font-mono ${confidenceColor}`}>
          {Math.round(evidence.confidence)}% confidence
        </span>
      </div>
      <div className="space-y-1.5">
        {evidence.sources.map((source) => (
          <div key={source.index} className="text-xs text-muted-foreground">
            <div className="flex items-start gap-1.5">
              <span className="font-mono text-foreground/70 shrink-0">[{source.index}]</span>
              <div className="min-w-0">
                <span className="font-medium text-foreground/80">
                  {source.displayName}
                  {source.page != null && <span className="ml-1 text-muted-foreground">p.{source.page}</span>}
                </span>
                {source.quote && (
                  <p className="mt-0.5 pl-2 border-l-2 border-muted text-muted-foreground/80 break-words">
                    &ldquo;{source.quote.length > 150 ? source.quote.slice(0, 150) + "\u2026" : source.quote}&rdquo;
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
