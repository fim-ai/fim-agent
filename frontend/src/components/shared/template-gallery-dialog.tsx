"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useTranslations } from "next-intl"
import {
  BarChart3,
  BookOpen,
  Bot,
  BrainCircuit,
  Check,
  Code,
  Database,
  FileText,
  GitBranch,
  GitFork,
  Globe,
  KeyRound,
  Languages,
  Layers,
  LayoutTemplate,
  ListFilter,
  Loader2,
  Mail,
  MessageCircleQuestion,
  MessageSquare,
  RefreshCcw,
  UserCheck,
  type LucideIcon,
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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

// ---------------------------------------------------------------------------
// Icon map — covers common Lucide icon names used across all entity templates
// ---------------------------------------------------------------------------

const iconMap: Record<string, LucideIcon> = {
  BarChart3,
  BookOpen,
  Bot,
  BrainCircuit,
  Code,
  Database,
  FileText,
  GitBranch,
  GitFork,
  Globe,
  KeyRound,
  Languages,
  Layers,
  ListFilter,
  Mail,
  MessageCircleQuestion,
  MessageSquare,
  RefreshCcw,
  UserCheck,
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BaseTemplate {
  id: string
  name: string
  description: string
  icon?: string | null
  category: string
}

export interface TemplateGalleryDialogProps<T extends BaseTemplate> {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Dialog title text */
  title: string
  /** Dialog description text */
  description: string
  /** Async function that returns the list of templates */
  fetchTemplates: () => Promise<T[]>
  /** Called when the user confirms creation. Receives the selected template id. */
  onCreateFromTemplate: (templateId: string) => Promise<void>
  /** Map of category key to display label, e.g. { basic: "Basic", ai: "AI" } */
  categoryLabels: Record<string, string>
  /**
   * Optional category icons. Keys are category names, values are ReactNodes
   * (typically a Lucide icon). When omitted, category tabs render label-only.
   */
  categoryIcons?: Record<string, React.ReactNode>
  /**
   * Render extra metadata below the description on each card (e.g. node count).
   * Receives the full template object so consumers can access domain-specific
   * fields without the shared component knowing about them.
   */
  renderExtra?: (template: T) => React.ReactNode
  /** Hint text shown in the footer when nothing is selected */
  selectHint?: string
  /** Text shown when there are no templates in the current category */
  emptyText?: string
  /** Text shown on the create button while the creation is in progress */
  creatingText?: string
  /** Error toast message when creation fails */
  createFailedText?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TemplateGalleryDialog<T extends BaseTemplate>({
  open,
  onOpenChange,
  title,
  description,
  fetchTemplates,
  onCreateFromTemplate,
  categoryLabels,
  categoryIcons: categoryIconsProp,
  renderExtra,
  selectHint,
  emptyText,
}: TemplateGalleryDialogProps<T>) {
  const tc = useTranslations("common")

  const [templates, setTemplates] = useState<T[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [activeCategory, setActiveCategory] = useState("all")

  const loadTemplates = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await fetchTemplates()
      setTemplates(data)
    } catch {
      setTemplates([])
    } finally {
      setIsLoading(false)
    }
  }, [fetchTemplates])

  useEffect(() => {
    if (open) {
      loadTemplates()
      setSelectedId(null)
      setActiveCategory("all")
    }
  }, [open, loadTemplates])

  // Extract categories from both templates AND categoryLabels keys
  // This ensures tabs like "Database" appear even with 0 templates
  const categories = useMemo(() => {
    const cats = new Set([
      ...templates.map((tmpl) => tmpl.category),
      ...Object.keys(categoryLabels),
    ])
    return Array.from(cats).sort()
  }, [templates, categoryLabels])

  // Filter templates by active category
  const filteredTemplates = useMemo(() => {
    if (activeCategory === "all") return templates
    return templates.filter((tmpl) => tmpl.category === activeCategory)
  }, [templates, activeCategory])

  const selectedTemplate = useMemo(
    () => templates.find((tmpl) => tmpl.id === selectedId) ?? null,
    [templates, selectedId],
  )

  const handleCreate = async () => {
    if (!selectedId) return
    setIsCreating(true)
    try {
      await onCreateFromTemplate(selectedId)
      onOpenChange(false)
    } catch {
      // The consumer's onCreateFromTemplate is responsible for showing
      // error feedback (e.g. toast) — we just stop the spinner here.
    } finally {
      setIsCreating(false)
    }
  }

  // Resolve the icon for a template: explicit icon name -> category icon -> fallback
  const resolveIcon = (tmpl: T): React.ReactNode => {
    const Icon = tmpl.icon ? iconMap[tmpl.icon] : null
    if (Icon) return <Icon className="h-5 w-5" />
    if (categoryIconsProp?.[tmpl.category]) return categoryIconsProp[tmpl.category]
    return <GitBranch className="h-5 w-5" />
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LayoutTemplate className="h-4 w-4" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {/* Category filter tabs */}
        {!isLoading && categories.length > 0 && (
          <Tabs
            value={activeCategory}
            onValueChange={setActiveCategory}
            className="w-full"
          >
            <TabsList className="w-full justify-start flex-wrap h-auto gap-1">
              <TabsTrigger value="all" className="text-xs">
                {tc("all")}
              </TabsTrigger>
              {categories.map((cat) => (
                <TabsTrigger key={cat} value={cat} className="text-xs gap-1">
                  {categoryIconsProp?.[cat] ? (
                    <span className="[&_svg]:h-3.5 [&_svg]:w-3.5">
                      {categoryIconsProp[cat]}
                    </span>
                  ) : null}
                  {categoryLabels[cat] ?? cat}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        )}

        {/* Template grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="rounded-lg border p-4 space-y-3">
                <Skeleton className="h-10 w-10 rounded-md" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : filteredTemplates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <LayoutTemplate className="h-10 w-10 text-muted-foreground/40 mb-3" />
            <p className="text-sm text-muted-foreground">
              {emptyText ?? tc("noResults")}
            </p>
          </div>
        ) : (
          <ScrollArea className="max-h-[400px]">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 pr-3">
              {filteredTemplates.map((tmpl) => {
                const isSelected = selectedId === tmpl.id
                return (
                  <button
                    key={tmpl.id}
                    type="button"
                    className={cn(
                      "relative text-left rounded-lg border p-4 transition-all",
                      isSelected
                        ? "border-ring bg-accent/20 ring-1 ring-ring"
                        : "border-border hover:border-ring/40 hover:bg-accent/10",
                    )}
                    onClick={() =>
                      setSelectedId(isSelected ? null : tmpl.id)
                    }
                  >
                    {/* Selected indicator */}
                    {isSelected && (
                      <div className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full bg-primary">
                        <Check className="h-3 w-3 text-primary-foreground" />
                      </div>
                    )}

                    {/* Icon */}
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted mb-3 text-muted-foreground">
                      {resolveIcon(tmpl)}
                    </div>

                    {/* Name */}
                    <p className="text-sm font-medium truncate pr-5">
                      {tmpl.name}
                    </p>

                    {/* Description */}
                    <p className="text-xs text-muted-foreground line-clamp-2 mt-1 min-h-[2rem]">
                      {tmpl.description}
                    </p>

                    {/* Footer: category badge + optional extra info */}
                    <div className="flex items-center gap-2 mt-3">
                      <Badge variant="secondary" className="text-[10px]">
                        {categoryLabels[tmpl.category] ?? tmpl.category}
                      </Badge>
                      {renderExtra?.(tmpl)}
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        )}

        {/* Footer actions */}
        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-muted-foreground">
            {selectedTemplate
              ? selectedTemplate.name
              : (selectHint ?? "")}
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isCreating}
            >
              {tc("cancel")}
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!selectedId || isCreating}
              className="gap-1.5"
            >
              {isCreating && (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              )}
              {tc("create")}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
