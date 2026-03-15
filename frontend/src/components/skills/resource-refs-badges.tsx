"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import {
  Cable,
  Server,
  BookOpen,
  Bot,
  X,
  Pencil,
  Check,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { ResourceRef, ResourceRefType } from "@/types/skill"

interface ResourceRefsBadgesProps {
  refs: ResourceRef[]
  onRemove: (index: number) => void
  onUpdateAlias: (index: number, newAlias: string) => void
}

const TYPE_ICONS: Record<ResourceRefType, React.ReactNode> = {
  connector: <Cable className="h-3 w-3" />,
  mcp_server: <Server className="h-3 w-3" />,
  knowledge_base: <BookOpen className="h-3 w-3" />,
  agent: <Bot className="h-3 w-3" />,
}

const TYPE_LABEL_KEYS: Record<ResourceRefType, string> = {
  connector: "resourceTypeConnector",
  mcp_server: "resourceTypeMcpServer",
  knowledge_base: "resourceTypeKnowledgeBase",
  agent: "resourceTypeAgent",
}

export function ResourceRefsBadges({
  refs,
  onRemove,
  onUpdateAlias,
}: ResourceRefsBadgesProps) {
  const t = useTranslations("skills")
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editValue, setEditValue] = useState("")

  const startEdit = (index: number) => {
    setEditingIndex(index)
    setEditValue(refs[index].alias)
  }

  const commitEdit = () => {
    if (editingIndex === null) return
    const trimmed = editValue.trim()
    if (trimmed) {
      const finalAlias = trimmed.startsWith("@") ? trimmed : `@${trimmed}`
      onUpdateAlias(editingIndex, finalAlias)
    }
    setEditingIndex(null)
    setEditValue("")
  }

  const cancelEdit = () => {
    setEditingIndex(null)
    setEditValue("")
  }

  if (refs.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {refs.map((ref, index) => {
        const isEditing = editingIndex === index

        if (isEditing) {
          return (
            <div key={`${ref.type}:${ref.id}`} className="flex items-center gap-1">
              <Input
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") { e.preventDefault(); commitEdit() }
                  if (e.key === "Escape") cancelEdit()
                }}
                className="h-6 w-32 text-xs px-1.5"
                autoFocus
              />
              <button
                type="button"
                onClick={commitEdit}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <Check className="h-3 w-3" />
              </button>
            </div>
          )
        }

        return (
          <Badge
            key={`${ref.type}:${ref.id}`}
            variant="secondary"
            className="gap-1.5 pr-1 text-xs h-6 max-w-[280px]"
          >
            <span className="text-muted-foreground shrink-0">
              {TYPE_ICONS[ref.type]}
            </span>
            <span className="font-mono text-primary font-medium shrink-0">
              {ref.alias}
            </span>
            <span className="text-muted-foreground truncate">
              {t(TYPE_LABEL_KEYS[ref.type])}: {ref.name}
            </span>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={() => startEdit(index)}
                  className="shrink-0 text-muted-foreground hover:text-foreground transition-colors ml-0.5"
                >
                  <Pencil className="h-2.5 w-2.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">{t("editAlias")}</TooltipContent>
            </Tooltip>
            <button
              type="button"
              onClick={() => onRemove(index)}
              className="shrink-0 text-muted-foreground hover:text-destructive transition-colors"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        )
      })}
    </div>
  )
}
