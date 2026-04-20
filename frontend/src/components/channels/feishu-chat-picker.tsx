"use client"

/**
 * Feishu group (chat) picker.
 *
 * Opens as a secondary Dialog on top of the channel form; calls
 * `POST /api/channels/discover-chats` and lets the user click a group
 * to fill its `chat_id` back into the parent form.
 *
 * Error handling:
 * - Field-level guard ("fill credentials first") is handled by the caller,
 *   which disables the trigger button when inputs are empty.
 * - API/network failures are shown **inline** inside the picker with a
 *   Retry button — no toast spam.
 */

import { useCallback, useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import { Loader2, RefreshCw, Users } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { channelsApi } from "@/lib/api/channels"
import { ApiError } from "@/lib/api"
import type { ChatDiscoveryRequest, ChatInfo } from "@/types/channel"

interface FeishuChatPickerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** App ID — required for both create and edit mode. */
  appId: string
  /** App secret — required in create mode; may be empty in edit mode. */
  appSecret: string
  /** Channel ID — only present in edit mode. */
  channelId?: string | null
  /** Org ID — required in create mode. */
  orgId?: string
  /** Callback fired when the user selects a group. */
  onSelect: (chat: ChatInfo) => void
}

function formatError(err: unknown): string {
  if (err instanceof ApiError) {
    // The backend returns the Feishu failure reason in `message`.
    return err.message
  }
  if (err instanceof Error) return err.message
  return "Unknown error"
}

export function FeishuChatPicker({
  open,
  onOpenChange,
  appId,
  appSecret,
  channelId,
  orgId,
  onSelect,
}: FeishuChatPickerProps) {
  const t = useTranslations("channels.picker")

  const [isLoading, setIsLoading] = useState(false)
  const [chats, setChats] = useState<ChatInfo[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const body: ChatDiscoveryRequest = { app_id: appId.trim() }
      if (appSecret) body.app_secret = appSecret
      if (channelId) body.channel_id = channelId
      else if (orgId) body.org_id = orgId
      const resp = await channelsApi.discoverChats(body)
      setChats(resp.items)
    } catch (err: unknown) {
      setChats(null)
      setError(formatError(err))
    } finally {
      setIsLoading(false)
    }
  }, [appId, appSecret, channelId, orgId])

  // Fetch on open; reset on close so each open is fresh.
  useEffect(() => {
    if (open) {
      void load()
    } else {
      setChats(null)
      setError(null)
      setIsLoading(false)
    }
  }, [open, load])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("description")}</DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t("loading")}
            </div>
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-48" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && error && (
          <div className="space-y-3">
            <p className="text-sm text-destructive">
              {t("error", { error })}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void load()}
            >
              <RefreshCw className="h-4 w-4" />
              {t("retry")}
            </Button>
          </div>
        )}

        {!isLoading && !error && chats && chats.length === 0 && (
          <p className="py-6 text-center text-sm text-muted-foreground">
            {t("empty")}
          </p>
        )}

        {!isLoading && !error && chats && chats.length > 0 && (
          <ScrollArea className="max-h-80 pr-2">
            <ul className="space-y-1">
              {chats.map((chat) => (
                <li key={chat.chat_id}>
                  <button
                    type="button"
                    onClick={() => {
                      onSelect(chat)
                      onOpenChange(false)
                    }}
                    className="flex w-full items-start gap-3 rounded-md p-2 text-left hover:bg-muted focus-visible:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  >
                    <Avatar className="h-10 w-10">
                      {chat.avatar ? (
                        <AvatarImage src={chat.avatar} alt={chat.name} />
                      ) : null}
                      <AvatarFallback>
                        <Users className="h-4 w-4" />
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium">
                          {chat.name}
                        </span>
                        {chat.external && (
                          <span className="rounded-sm bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-900 dark:bg-amber-900/40 dark:text-amber-200">
                            {t("externalBadge")}
                          </span>
                        )}
                      </div>
                      <div className="truncate text-xs text-muted-foreground">
                        {chat.chat_id}
                      </div>
                      {(chat.description || chat.member_count != null) && (
                        <div className="truncate text-xs text-muted-foreground">
                          {chat.description}
                          {chat.description && chat.member_count != null
                            ? " · "
                            : ""}
                          {chat.member_count != null
                            ? t("memberCount", { n: chat.member_count })
                            : ""}
                        </div>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  )
}
