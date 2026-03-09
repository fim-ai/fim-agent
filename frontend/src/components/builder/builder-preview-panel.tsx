"use client"

import { useState, useEffect, useCallback } from "react"
import { useTranslations } from "next-intl"
import { RefreshCw } from "lucide-react"
import { connectorApi } from "@/lib/api"
import type { ConnectorResponse } from "@/types/connector"

interface BuilderPreviewPanelProps {
  targetType: "connector" | "agent"
  targetId: string
  onUpdated?: () => void
}

export function BuilderPreviewPanel({ targetType, targetId, onUpdated }: BuilderPreviewPanelProps) {
  const t = useTranslations("builder")
  const [connector, setConnector] = useState<ConnectorResponse | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const refresh = useCallback(async () => {
    if (targetType !== "connector") return
    try {
      const data = await connectorApi.get(targetId)
      setConnector(data)
      onUpdated?.()
    } catch {
      // Silently ignore poll errors
    }
  }, [targetType, targetId, onUpdated])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 3000)
    return () => clearInterval(interval)
  }, [refresh])

  const actions = connector?.actions ?? []

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
        <span className="text-sm font-medium">{t("previewTitle")}</span>
        <button
          onClick={() => {
            setIsRefreshing(true)
            refresh().finally(() => setIsRefreshing(false))
          }}
          className="text-muted-foreground hover:text-foreground transition-colors"
          type="button"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {actions.length === 0 && (
          <p className="text-sm text-muted-foreground py-4 text-center">{t("noActions")}</p>
        )}
        {actions.map((action) => (
          <div key={action.id} className="rounded-md border border-border/60 px-3 py-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                {action.method}
              </span>
              <span className="font-medium truncate">{action.name}</span>
            </div>
            {action.path && (
              <p className="text-xs text-muted-foreground mt-0.5 font-mono truncate">{action.path}</p>
            )}
          </div>
        ))}
      </div>

      {connector && (
        <div className="px-4 py-2 border-t shrink-0 text-xs text-muted-foreground">
          {t("actionCount", { count: actions.length })}
        </div>
      )}
    </div>
  )
}
