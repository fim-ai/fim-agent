"use client"

import { useTranslations } from "next-intl"
import { Download, ExternalLink, FileText, FileImage, FileCode, File, FileSpreadsheet } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { ArtifactInfo } from "./types"

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith("image/")) return FileImage
  if (mimeType === "text/html") return FileCode
  if (mimeType === "text/csv" || mimeType.includes("spreadsheet") || mimeType.includes("excel")) return FileSpreadsheet
  if (mimeType.startsWith("text/") || mimeType === "application/json") return FileText
  return File
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function canPreview(mimeType: string): boolean {
  return mimeType === "text/html" || mimeType.startsWith("image/")
}

interface ArtifactChipsProps {
  artifacts: ArtifactInfo[]
  className?: string
}

export function ArtifactChips({ artifacts, className }: ArtifactChipsProps) {
  const t = useTranslations("dag")

  if (!artifacts.length) return null

  return (
    <div className={`flex flex-wrap gap-2 ${className ?? ""}`}>
      {artifacts.map((artifact, idx) => {
        const Icon = getFileIcon(artifact.mime_type)
        return (
          <div
            key={idx}
            className="flex items-center gap-2 rounded-md border border-border/40 bg-background/50 px-2.5 py-1.5 text-xs"
          >
            <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <span className="font-medium truncate max-w-[200px]">{artifact.name}</span>
            <span className="text-muted-foreground shrink-0">({formatSize(artifact.size)})</span>
            <div className="flex items-center gap-1 shrink-0">
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5"
                onClick={() => window.open(artifact.url, "_blank")}
                title={t("download")}
              >
                <Download className="h-3 w-3" />
              </Button>
              {canPreview(artifact.mime_type) && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5"
                  onClick={() => window.open(artifact.url, "_blank")}
                  title={t("openInNewTab")}
                >
                  <ExternalLink className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
