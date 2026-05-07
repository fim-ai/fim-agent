"use client"

import * as React from "react"
import Link from "next/link"
import { useTranslations } from "next-intl"
import { Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

/**
 * Payload schema for the structured `error` SSE terminator emitted by
 * `chat.py` when the user's monthly token quota runs out partway
 * through a streamed answer. Mirrors the backend's
 * `_build_quota_terminator_payload` exactly — keep in sync.
 */
export interface QuotaExceededPayload {
  type: "error"
  code: "QUOTA_EXCEEDED"
  tokens_used: number
  quota: number
  /** ISO-8601 timestamp of next monthly reset boundary. */
  reset_at: string
  /** Reserved for the upcoming Stripe billing tiers. */
  plan_slug: string
}

/**
 * Type guard: does an unknown SSE payload match the quota terminator?
 *
 * Defensive against future event-name collisions — we only treat a
 * payload as quota-exhausted when it carries the exact code string,
 * so introducing other `type === "error"` codes later (rate limit,
 * sensitive content, etc.) won't accidentally pop this dialog.
 */
export function isQuotaExceededPayload(
  data: unknown,
): data is QuotaExceededPayload {
  if (!data || typeof data !== "object") return false
  const d = data as Partial<QuotaExceededPayload>
  return (
    d.type === "error" &&
    d.code === "QUOTA_EXCEEDED" &&
    typeof d.tokens_used === "number" &&
    typeof d.quota === "number" &&
    typeof d.reset_at === "string"
  )
}

interface QuotaExceededDialogProps {
  /** When non-null, the dialog is shown with this payload's data. */
  payload: QuotaExceededPayload | null
  /** Fired when the dialog is dismissed (X button, backdrop, or "Wait"). */
  onDismiss: () => void
}

/**
 * Modal that surfaces the structured `QUOTA_EXCEEDED` terminator from
 * the streaming chat endpoints. Shows used / quota / reset / plan and
 * offers "Upgrade now" (deep-links to /settings/billing) and "Wait for
 * reset" (close).
 *
 * Renders nothing when `payload` is null — the caller controls the
 * lifecycle so the dialog can be dismissed locally and re-armed by the
 * next stream that hits the same condition.
 */
export function QuotaExceededDialog({
  payload,
  onDismiss,
}: QuotaExceededDialogProps) {
  const t = useTranslations("chat")
  const tc = useTranslations("common")

  const open = payload !== null

  const handleOpenChange = React.useCallback(
    (next: boolean) => {
      if (!next) onDismiss()
    },
    [onDismiss],
  )

  const formattedReset = React.useMemo(() => {
    if (!payload?.reset_at) return ""
    try {
      const d = new Date(payload.reset_at)
      if (Number.isNaN(d.getTime())) return payload.reset_at
      return d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return payload.reset_at
    }
  }, [payload?.reset_at])

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Sparkles className="h-5 w-5" />
          </div>
          <DialogTitle>{t("quota.title")}</DialogTitle>
          <DialogDescription>{t("quota.body")}</DialogDescription>
        </DialogHeader>

        {payload && (
          <dl className="grid grid-cols-2 gap-3 rounded-md border border-border/60 bg-muted/30 p-4 text-sm">
            <div>
              <dt className="text-xs font-medium text-muted-foreground">
                {t("quota.usageLabel")}
              </dt>
              <dd className="mt-0.5 font-medium tabular-nums">
                {payload.tokens_used.toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted-foreground">
                {t("quota.quotaLabel")}
              </dt>
              <dd className="mt-0.5 font-medium tabular-nums">
                {payload.quota.toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted-foreground">
                {t("quota.resetLabel")}
              </dt>
              <dd className="mt-0.5 font-medium">{formattedReset}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-muted-foreground">
                {t("quota.planLabel")}
              </dt>
              <dd className="mt-0.5 font-medium capitalize">
                {payload.plan_slug}
              </dd>
            </div>
          </dl>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={onDismiss}>
            {t("quota.ctaWait")}
          </Button>
          <Button asChild>
            <Link href="/settings/billing" onClick={onDismiss}>
              {t("quota.ctaUpgrade")}
            </Link>
          </Button>
        </DialogFooter>
        {/* Surfacing tc("close") via screen-reader on Dialog.Close keeps
            tabbing parity with other dialogs in the app. */}
        <span className="sr-only" aria-hidden>
          {tc("close")}
        </span>
      </DialogContent>
    </Dialog>
  )
}
