"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import { Check, Copy, Loader2, Send } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { channelsApi } from "@/lib/api/channels"
import { getErrorMessage } from "@/lib/error-utils"
import type { Channel } from "@/types/channel"

interface ChannelDetailsSheetProps {
  channel: Channel | null
  onOpenChange: (open: boolean) => void
}

export function ChannelDetailsSheet({
  channel,
  onOpenChange,
}: ChannelDetailsSheetProps) {
  const t = useTranslations("channels")
  const tError = useTranslations("errors")

  const [copied, setCopied] = useState(false)
  const [isSending, setIsSending] = useState(false)

  const handleCopyUrl = async () => {
    if (!channel) return
    try {
      await navigator.clipboard.writeText(channel.callback_url)
      setCopied(true)
      toast.success(t("details.copyToastSuccess"))
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error(t("details.copyToastFailed"))
    }
  }

  const handleTest = async () => {
    if (!channel) return
    setIsSending(true)
    try {
      const result = await channelsApi.test(channel.id)
      if (result.ok) {
        const chat = result.chat_name ?? channel.config.chat_name
        if (chat) {
          toast.success(t("messages.testSentWithChat", { chat }))
        } else {
          toast.success(t("messages.testSent"))
        }
      } else {
        toast.error(
          t("messages.testFailed", {
            error: result.error ?? "unknown",
          }),
        )
      }
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, tError))
    } finally {
      setIsSending(false)
    }
  }

  return (
    <Sheet
      open={channel !== null}
      onOpenChange={(open) => {
        if (!open) onOpenChange(false)
      }}
    >
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t("details.title")}</SheetTitle>
          <SheetDescription>{channel?.name}</SheetDescription>
        </SheetHeader>

        {channel && (
          <div className="space-y-6 px-6 pb-6">
            {/* Callback URL block */}
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-foreground">
                  {t("details.callbackUrlLabel")}
                </h3>
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={handleCopyUrl}
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                  {t("details.copyUrl")}
                </Button>
              </div>
              <div className="rounded-md border border-border bg-muted/40 px-3 py-3 font-mono text-sm break-all select-all">
                {channel.callback_url}
              </div>
              <p className="text-xs text-muted-foreground">
                {t("details.callbackUrlHint")}
              </p>
            </section>

            {/* How-to block */}
            <section className="space-y-2 rounded-md border border-primary/30 bg-primary/5 px-4 py-3">
              <h3 className="text-sm font-semibold text-foreground">
                {t("details.howTo")}
              </h3>
              <ol className="ml-5 list-decimal space-y-1 text-sm text-muted-foreground">
                <li>{t("details.step1")}</li>
                <li>{t("details.step2")}</li>
                <li>{t("details.step3")}</li>
                <li>{t("details.step4")}</li>
                <li>{t("details.step5")}</li>
                <li>{t("details.step6")}</li>
                <li>{t("details.step7")}</li>
              </ol>
            </section>

            {/* Metadata */}
            <section className="space-y-3">
              <DetailRow
                label={t("details.appIdLabel")}
                value={channel.config.app_id ?? "—"}
                mono
              />
              <DetailRow
                label={t("details.chatIdLabel")}
                value={channel.config.chat_id ?? "—"}
                mono
              />
              {channel.config.chat_name && (
                <DetailRow
                  label={t("details.chatNameLabel")}
                  value={channel.config.chat_name}
                />
              )}
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm text-muted-foreground">
                  {channel.config.app_secret_configured &&
                  channel.config.verification_token_configured
                    ? t("details.secretsConfigured")
                    : t("details.secretsMissing")}
                </span>
                <Badge
                  variant="outline"
                  className={
                    channel.config.app_secret_configured &&
                    channel.config.verification_token_configured
                      ? "border-green-500/30 bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-400"
                      : "border-amber-500/30 bg-amber-50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-400"
                  }
                >
                  {channel.config.app_secret_configured &&
                  channel.config.verification_token_configured
                    ? t("status.enabled")
                    : t("status.disabled")}
                </Badge>
              </div>
            </section>

            {/* Test send */}
            <section>
              <Button
                variant="default"
                className="w-full gap-1.5"
                onClick={handleTest}
                disabled={isSending || !channel.is_active}
              >
                {isSending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                {isSending ? t("details.testing") : t("details.testSend")}
              </Button>
            </section>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}

function DetailRow({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-sm text-muted-foreground shrink-0">{label}</span>
      <span
        className={`text-sm text-foreground text-right break-all ${mono ? "font-mono" : ""}`}
      >
        {value}
      </span>
    </div>
  )
}
