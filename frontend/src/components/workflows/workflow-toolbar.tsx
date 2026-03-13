"use client"

import { useState } from "react"
import Link from "next/link"
import { useTranslations } from "next-intl"
import {
  ArrowLeft,
  Download,
  Loader2,
  MoreHorizontal,
  Play,
  Save,
  Trash2,
  Upload,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface WorkflowToolbarProps {
  name: string
  status: "draft" | "active"
  isSaving: boolean
  isRunning: boolean
  onNameChange: (name: string) => void
  onSave: () => void
  onRun: () => void
  onExport: () => void
  onImport: () => void
  onDelete: () => void
}

export function WorkflowToolbar({
  name,
  status,
  isSaving,
  isRunning,
  onNameChange,
  onSave,
  onRun,
  onExport,
  onImport,
  onDelete,
}: WorkflowToolbarProps) {
  const t = useTranslations("workflows")
  const tc = useTranslations("common")
  const [isEditing, setIsEditing] = useState(false)
  const [editValue, setEditValue] = useState(name)

  const startEditing = () => {
    setEditValue(name)
    setIsEditing(true)
  }

  const finishEditing = () => {
    setIsEditing(false)
    const trimmed = editValue.trim()
    if (trimmed && trimmed !== name) {
      onNameChange(trimmed)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") finishEditing()
    if (e.key === "Escape") {
      setEditValue(name)
      setIsEditing(false)
    }
  }

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-border/40 bg-background shrink-0">
      {/* Back button */}
      <Button variant="ghost" size="sm" className="gap-1.5 shrink-0" asChild>
        <Link href="/workflows">
          <ArrowLeft className="h-3.5 w-3.5" />
          {t("editorBackToList")}
        </Link>
      </Button>

      {/* Workflow name */}
      <div className="flex items-center gap-2 flex-1 min-w-0">
        {isEditing ? (
          <Input
            className="h-7 text-sm font-medium max-w-[300px]"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={finishEditing}
            onKeyDown={handleKeyDown}
            autoFocus
          />
        ) : (
          <button
            onClick={startEditing}
            className="text-sm font-medium text-foreground hover:text-foreground/80 truncate max-w-[300px] text-left transition-colors"
          >
            {name || t("editorUntitled")}
          </button>
        )}
        <Badge
          variant="secondary"
          className="text-[10px] px-1.5 py-0 h-5 shrink-0"
        >
          {status === "active" ? t("statusActive") : t("statusDraft")}
        </Badge>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 shrink-0">
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={onSave}
          disabled={isSaving}
        >
          {isSaving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Save className="h-3.5 w-3.5" />
          )}
          {isSaving ? t("editorSaving") : t("editorSave")}
        </Button>

        <Button
          size="sm"
          className="gap-1.5"
          onClick={onRun}
          disabled={isRunning}
        >
          {isRunning ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          {isRunning ? t("editorRunning") : t("editorRun")}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onImport}>
              <Upload className="h-4 w-4" />
              {tc("import")}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onExport}>
              <Download className="h-4 w-4" />
              {tc("export")}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
              {tc("delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
