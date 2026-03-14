"use client"

import { useTranslations } from "next-intl"
import { Package } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export function AdminPackages() {
  const t = useTranslations("admin.placeholders.packages")

  return (
    <div className="flex items-center justify-center py-24">
      <div className="max-w-md text-center space-y-4">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-muted">
          <Package className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">{t("title")}</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {t("description")}
        </p>
        <Badge variant="secondary" className="text-xs">
          {t("version")}
        </Badge>
      </div>
    </div>
  )
}
