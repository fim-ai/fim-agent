"use client"

import { useEffect, useState } from "react"
import { useTranslations } from "next-intl"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { APP_NAME } from "@/lib/constants"
import { apiFetch } from "@/lib/api"

interface VersionInfo {
  version: string
  build_time: string
  app_name: string
}

interface AboutDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AboutDialog({ open, onOpenChange }: AboutDialogProps) {
  const t = useTranslations("common")
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    apiFetch<VersionInfo>("/api/version")
      .then(setVersionInfo)
      .catch(() => setVersionInfo(null))
      .finally(() => setLoading(false))
  }, [open])

  const formatBuildTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString()
    } catch {
      return iso
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader className="items-center text-center">
          <DialogTitle className="text-2xl font-bold">{APP_NAME}</DialogTitle>
          <DialogDescription>{t("aboutTagline")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-3 text-sm">
          {loading ? (
            <div className="space-y-3">
              <div className="flex justify-between">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-4 w-24" />
              </div>
              <div className="flex justify-between">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-32" />
              </div>
            </div>
          ) : versionInfo ? (
            <>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("aboutVersion")}</span>
                <span className="font-medium">{versionInfo.version}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("aboutBuildTime")}</span>
                <span className="font-medium">{formatBuildTime(versionInfo.build_time)}</span>
              </div>
            </>
          ) : null}
        </div>

        <div className="space-y-1 pt-2 text-center text-xs text-muted-foreground">
          <p>{t("aboutCraftedBy")}</p>
          <p>{t("aboutCopyright", { year: new Date().getFullYear() })}</p>
        </div>

        <DialogFooter className="sm:justify-center">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("close")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
