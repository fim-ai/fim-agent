"use client"

import { useState, useEffect, useCallback } from "react"
import { useTranslations } from "next-intl"
import {
  MessageSquare,
  GitBranch,
  BookOpen,
  Globe,
  FileCode2,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { workflowApi } from "@/lib/api"
import type { WorkflowTemplate } from "@/types/workflow"

const categoryIcons: Record<string, React.ReactNode> = {
  basic: <MessageSquare className="h-4 w-4" />,
  ai: <BookOpen className="h-4 w-4" />,
  integration: <Globe className="h-4 w-4" />,
  data: <FileCode2 className="h-4 w-4" />,
}

interface TemplatePickerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelectTemplate: (templateId: string) => void
  onCreateBlank: () => void
  isCreating: boolean
}

export function TemplatePicker({
  open,
  onOpenChange,
  onSelectTemplate,
  onCreateBlank,
  isCreating,
}: TemplatePickerProps) {
  const t = useTranslations("workflows")
  const tc = useTranslations("common")

  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const loadTemplates = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await workflowApi.getTemplates()
      setTemplates(data)
    } catch {
      // Templates are optional — silently ignore if endpoint not ready
      setTemplates([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      loadTemplates()
      setSelectedId(null)
    }
  }, [open, loadTemplates])

  const handleUse = () => {
    if (selectedId) {
      onSelectTemplate(selectedId)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch className="h-4 w-4" />
            {t("newWorkflow")}
          </DialogTitle>
          <DialogDescription>
            {t("templatesDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Blank workflow option */}
          <button
            type="button"
            className={cn(
              "w-full text-left rounded-lg border p-3 transition-colors",
              selectedId === null
                ? "border-ring bg-accent/20"
                : "border-border hover:border-ring/40 hover:bg-accent/10",
            )}
            onClick={() => setSelectedId(null)}
          >
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
                <GitBranch className="h-4 w-4 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">{t("createWorkflow")}</p>
                <p className="text-xs text-muted-foreground">{t("emptyState").split(".")[0]}</p>
              </div>
            </div>
          </button>

          {/* Templates */}
          {isLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : templates.length > 0 ? (
            <ScrollArea className="max-h-[280px]">
              <div className="space-y-2">
                {templates.map((tmpl) => (
                  <button
                    key={tmpl.id}
                    type="button"
                    className={cn(
                      "w-full text-left rounded-lg border p-3 transition-colors",
                      selectedId === tmpl.id
                        ? "border-ring bg-accent/20"
                        : "border-border hover:border-ring/40 hover:bg-accent/10",
                    )}
                    onClick={() => setSelectedId(tmpl.id)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
                        {categoryIcons[tmpl.category] ?? <GitBranch className="h-4 w-4 text-muted-foreground" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium truncate">{tmpl.name}</p>
                          <Badge variant="secondary" className="text-[10px] shrink-0">
                            {t(`templateCategory_${tmpl.category}` as Parameters<typeof t>[0])}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                          {tmpl.description}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </ScrollArea>
          ) : null}
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={isCreating}
          >
            {tc("cancel")}
          </Button>
          <Button
            onClick={selectedId ? handleUse : onCreateBlank}
            disabled={isCreating}
            className="gap-1.5"
          >
            {isCreating && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {selectedId ? t("templateUse") : t("createWorkflow")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
