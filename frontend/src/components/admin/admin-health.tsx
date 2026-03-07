"use client"

import { useState, useEffect } from "react"
import { useTranslations } from "next-intl"
import { CheckCircle2, XCircle, AlertTriangle, Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { adminApi } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { IntegrationHealth } from "@/types/admin"

const GROUPS: Record<string, string[]> = {
  ai: ["llm", "fast_llm"],
  retrieval: ["embedding", "reranker"],
  web: ["web_search", "web_fetch"],
  email: ["smtp"],
  media: ["image_gen"],
}

export function AdminHealth() {
  const t = useTranslations("admin.health")
  const [items, setItems] = useState<IntegrationHealth[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi
      .getSystemHealth()
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t("loading")}
      </div>
    )
  }

  const itemMap = Object.fromEntries(items.map((i) => [i.key, i]))

  const groupEntries = Object.entries(GROUPS)
    .map(([group, keys]) => ({
      group,
      items: keys.map((k) => itemMap[k]).filter(Boolean),
    }))
    .filter((g) => g.items.length > 0)

  // Catch any items not in a group
  const groupedKeys = new Set(Object.values(GROUPS).flat())
  const ungrouped = items.filter((i) => !groupedKeys.has(i.key))

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-base font-semibold">{t("title")}</h2>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      <Separator />

      {groupEntries.map(({ group, items: groupItems }) => (
        <Card key={group}>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">{t(`group.${group}`)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {groupItems.map((item) => (
              <HealthRow key={item.key} item={item} />
            ))}
          </CardContent>
        </Card>
      ))}

      {ungrouped.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">{t("group.other")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {ungrouped.map((item) => (
              <HealthRow key={item.key} item={item} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function HealthRow({ item }: { item: IntegrationHealth }) {
  const t = useTranslations("admin.health")

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        {item.configured ? (
          <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500 shrink-0" />
        )}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="text-sm font-medium">{item.label}</span>
          {item.detail && (
            <span className="text-xs text-muted-foreground truncate">
              {item.detail}
            </span>
          )}
          <span
            className={cn(
              "ml-auto text-xs shrink-0",
              item.configured ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400",
            )}
          >
            {item.configured ? t("configured") : t("notConfigured")}
          </span>
        </div>
      </div>
      {!item.configured && item.impact && (
        <div className="flex items-start gap-2 ml-6 rounded-md bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 px-3 py-2">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-700 dark:text-amber-300">
            {t("impactLabel")}: {item.impact}
          </p>
        </div>
      )}
    </div>
  )
}
