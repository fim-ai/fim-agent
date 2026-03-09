"use client"

import { useState, useEffect } from "react"
import { useTranslations } from "next-intl"
import { Wand2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { toast } from "sonner"
import { builderApi } from "@/lib/builder-api"
import { PlaygroundPage } from "@/components/playground/playground-page"
import { ConversationProvider } from "@/contexts/conversation-context"
import { BuilderPreviewPanel } from "./builder-preview-panel"

interface BuilderDialogProps {
  open: boolean
  onClose: () => void
  targetType: "connector" | "agent"
  targetId: string
  onTargetUpdated?: () => void
}

export function BuilderDialog({
  open,
  onClose,
  targetType,
  targetId,
  onTargetUpdated,
}: BuilderDialogProps) {
  const t = useTranslations("builder")
  const [builderAgentId, setBuilderAgentId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!open || !targetId) return
    setBuilderAgentId(null)
    setIsLoading(true)
    builderApi
      .createSession({ target_type: targetType, target_id: targetId })
      .then((res) => setBuilderAgentId(res.builder_agent_id))
      .catch((err) => toast.error(err.message || "Failed to initialize builder"))
      .finally(() => setIsLoading(false))
  }, [open, targetType, targetId])

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-[95vw] w-[95vw] h-[90vh] p-0 flex flex-col gap-0 overflow-hidden">
        <DialogHeader className="px-4 py-3 border-b shrink-0">
          <DialogTitle className="flex items-center gap-2 text-sm">
            <Wand2 className="h-4 w-4 text-primary" />
            {t("title")}
          </DialogTitle>
        </DialogHeader>

        {isLoading && (
          <div className="flex flex-1 items-center justify-center">
            <div className="h-8 w-48 rounded-md bg-muted animate-pulse" />
          </div>
        )}

        {!isLoading && builderAgentId && (
          <div className="flex flex-1 min-h-0 overflow-hidden">
            <div className="flex-1 overflow-hidden border-r min-w-0">
              <ConversationProvider>
                <PlaygroundPage
                  embedded
                  onClose={onClose}
                  initialAgentId={builderAgentId}
                  isNewChat
                />
              </ConversationProvider>
            </div>
            <div className="w-[380px] shrink-0 overflow-y-auto border-l">
              <BuilderPreviewPanel
                targetType={targetType}
                targetId={targetId}
                onUpdated={onTargetUpdated}
              />
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
