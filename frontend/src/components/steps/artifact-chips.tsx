"use client"

import { useCallback } from "react"
import { useTranslations } from "next-intl"
import { Download, ExternalLink, FileText, FileImage, FileCode, File, FileSpreadsheet } from "lucide-react"
import { Button } from "@/components/ui/button"
import { getApiBaseUrl, ACCESS_TOKEN_KEY } from "@/lib/constants"
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

/** Fetch an artifact with auth, return an object URL. */
async function fetchArtifactBlob(url: string): Promise<string> {
  const token = typeof window !== "undefined" ? localStorage.getItem(ACCESS_TOKEN_KEY) : null
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`
  const res = await fetch(`${getApiBaseUrl()}${url}`, { headers })
  if (!res.ok) throw new Error(`Failed to fetch artifact: ${res.status}`)
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}

interface ArtifactChipsProps {
  artifacts: ArtifactInfo[]
  className?: string
}

export function ArtifactChips({ artifacts, className }: ArtifactChipsProps) {
  const t = useTranslations("dag")

  const handleDownload = useCallback(async (artifact: ArtifactInfo) => {
    try {
      const blobUrl = await fetchArtifactBlob(artifact.url)
      const a = document.createElement("a")
      a.href = blobUrl
      a.download = artifact.name
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
    } catch {
      // Fallback: direct open (will fail with auth error but nothing else we can do)
      window.open(`${getApiBaseUrl()}${artifact.url}`, "_blank")
    }
  }, [])

  const handleOpen = useCallback(async (artifact: ArtifactInfo) => {
    try {
      const blobUrl = await fetchArtifactBlob(artifact.url)
      window.open(blobUrl, "_blank")
      // Don't revoke immediately — the new tab needs it.
      // Browser will clean up when the tab is closed.
    } catch {
      window.open(`${getApiBaseUrl()}${artifact.url}`, "_blank")
    }
  }, [])

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
                onClick={() => handleDownload(artifact)}
                title={t("download")}
              >
                <Download className="h-3 w-3" />
              </Button>
              {canPreview(artifact.mime_type) && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-5 w-5"
                  onClick={() => handleOpen(artifact)}
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
