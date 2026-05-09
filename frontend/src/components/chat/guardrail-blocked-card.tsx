"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { ShieldAlert, ChevronRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import type { GuardrailTripwiredEvent } from "@/types/api"

export interface GuardrailBlockedCardProps {
  /** "input" → user prompt blocked. "output" → final answer blocked. */
  kind: GuardrailTripwiredEvent["kind"]
  guardrailName: string
  reason: string
  outputInfo: Record<string, unknown>
}

/**
 * Renders a destructive "blocked by guardrail" bubble in the chat
 * transcript. Used when the backend emits a ``guardrail_tripwired`` SSE
 * event — the turn is terminated and no further ``answer`` events arrive.
 *
 * Visual contract:
 *  - Destructive color tokens (border + tinted bg + foreground)
 *  - ShieldAlert icon
 *  - Headline differs by ``kind`` (input vs output)
 *  - "Details" collapsible section pretty-prints ``output_info`` (default closed)
 */
export function GuardrailBlockedCard({
  kind,
  guardrailName,
  reason,
  outputInfo,
}: GuardrailBlockedCardProps) {
  const t = useTranslations("playground")
  const [open, setOpen] = useState(false)

  const headline =
    kind === "input"
      ? t("guardrail.inputBlocked")
      : t("guardrail.outputBlocked")

  const hasOutputInfo = outputInfo && Object.keys(outputInfo).length > 0
  const prettyJson = hasOutputInfo
    ? JSON.stringify(outputInfo, null, 2)
    : ""

  return (
    <Card
      role="alert"
      data-testid="guardrail-blocked-card"
      className="border-destructive/40 bg-destructive/10 py-4"
    >
      <CardContent className="space-y-2">
        <div className="flex items-start gap-2">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-destructive/15">
            <ShieldAlert className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-destructive">
              {headline}
            </p>
            <p className="mt-1 text-xs text-destructive/90 leading-relaxed">
              <span className="font-medium">{guardrailName}</span>
              <span className="mx-1.5 text-destructive/60">{"—"}</span>
              <span className="text-foreground/80">{reason}</span>
            </p>
          </div>
        </div>

        {hasOutputInfo && (
          <Collapsible open={open} onOpenChange={setOpen}>
            <CollapsibleTrigger
              data-testid="guardrail-details-trigger"
              className="group inline-flex items-center gap-1 rounded text-[11px] text-destructive/80 hover:text-destructive transition-colors cursor-pointer"
            >
              <ChevronRight className="h-3 w-3 transition-transform duration-200 group-data-[state=open]:rotate-90" />
              {t("guardrail.detailsLabel")}
            </CollapsibleTrigger>
            <CollapsibleContent>
              <pre
                data-testid="guardrail-details-content"
                className="mt-1.5 max-h-64 overflow-auto rounded-md border border-destructive/20 bg-background/40 p-2 text-[11px] leading-snug text-foreground/80 font-mono whitespace-pre-wrap break-words"
              >
                {prettyJson}
              </pre>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  )
}
