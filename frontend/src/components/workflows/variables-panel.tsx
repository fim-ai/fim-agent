"use client"

import { useState, useCallback } from "react"
import { useTranslations } from "next-intl"
import { Plus, Trash2, Pencil, Check, X } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import type { WorkflowVariable } from "@/types/workflow"

const VARIABLE_NAME_REGEX = /^[a-zA-Z][a-zA-Z0-9_]*$/

const VARIABLE_TYPES: WorkflowVariable["type"][] = ["string", "number", "boolean", "json"]

interface VariablesPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  variables: WorkflowVariable[]
  onChange: (variables: WorkflowVariable[]) => void
}

interface EditingState {
  index: number
  variable: WorkflowVariable
}

export function VariablesPanel({
  open,
  onOpenChange,
  variables,
  onChange,
}: VariablesPanelProps) {
  const t = useTranslations("workflows")
  const tc = useTranslations("common")

  const [editingState, setEditingState] = useState<EditingState | null>(null)
  const [addingNew, setAddingNew] = useState(false)
  const [newVariable, setNewVariable] = useState<WorkflowVariable>({
    name: "",
    type: "string",
    default_value: "",
    description: "",
  })
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [deleteIndex, setDeleteIndex] = useState<number | null>(null)

  const typeLabel = useCallback(
    (type: WorkflowVariable["type"]) => {
      const labels: Record<WorkflowVariable["type"], string> = {
        string: t("variablesPanelTypeString"),
        number: t("variablesPanelTypeNumber"),
        boolean: t("variablesPanelTypeBoolean"),
        json: t("variablesPanelTypeJson"),
      }
      return labels[type]
    },
    [t],
  )

  const typeBadgeClass = (type: WorkflowVariable["type"]) => {
    const classes: Record<WorkflowVariable["type"], string> = {
      string: "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/20",
      number: "bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/20",
      boolean: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/20",
      json: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
    }
    return classes[type]
  }

  const validateName = useCallback(
    (name: string, excludeIndex?: number): string | null => {
      if (!name.trim()) return t("variablesPanelNameEmpty")
      if (!VARIABLE_NAME_REGEX.test(name)) return t("variablesPanelNameInvalid")
      const duplicate = variables.some(
        (v, i) => i !== excludeIndex && v.name === name,
      )
      if (duplicate) return t("variablesPanelNameDuplicate")
      return null
    },
    [variables, t],
  )

  const handleAddStart = useCallback(() => {
    setAddingNew(true)
    setNewVariable({ name: "", type: "string", default_value: "", description: "" })
    setFieldError(null)
  }, [])

  const handleAddSave = useCallback(() => {
    const error = validateName(newVariable.name)
    if (error) {
      setFieldError(error)
      return
    }
    onChange([...variables, { ...newVariable, name: newVariable.name.trim() }])
    setAddingNew(false)
    setNewVariable({ name: "", type: "string", default_value: "", description: "" })
    setFieldError(null)
  }, [newVariable, variables, onChange, validateName])

  const handleAddCancel = useCallback(() => {
    setAddingNew(false)
    setNewVariable({ name: "", type: "string", default_value: "", description: "" })
    setFieldError(null)
  }, [])

  const handleEditStart = useCallback(
    (index: number) => {
      setEditingState({ index, variable: { ...variables[index] } })
      setFieldError(null)
    },
    [variables],
  )

  const handleEditSave = useCallback(() => {
    if (!editingState) return
    const error = validateName(editingState.variable.name, editingState.index)
    if (error) {
      setFieldError(error)
      return
    }
    const updated = [...variables]
    updated[editingState.index] = {
      ...editingState.variable,
      name: editingState.variable.name.trim(),
    }
    onChange(updated)
    setEditingState(null)
    setFieldError(null)
  }, [editingState, variables, onChange, validateName])

  const handleEditCancel = useCallback(() => {
    setEditingState(null)
    setFieldError(null)
  }, [])

  const handleDeleteConfirm = useCallback(() => {
    if (deleteIndex === null) return
    const updated = variables.filter((_, i) => i !== deleteIndex)
    onChange(updated)
    setDeleteIndex(null)
  }, [deleteIndex, variables, onChange])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, action: "add" | "edit") => {
      if (e.key === "Enter") {
        e.preventDefault()
        if (action === "add") handleAddSave()
        else handleEditSave()
      }
      if (e.key === "Escape") {
        e.preventDefault()
        if (action === "add") handleAddCancel()
        else handleEditCancel()
      }
    },
    [handleAddSave, handleAddCancel, handleEditSave, handleEditCancel],
  )

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent side="right" className="flex flex-col p-0 sm:max-w-md">
          <SheetHeader className="px-6 pt-6 pb-4 border-b border-border/40">
            <SheetTitle>{t("variablesPanelTitle")}</SheetTitle>
            <SheetDescription>{t("variablesPanelDescription")}</SheetDescription>
          </SheetHeader>

          <ScrollArea className="flex-1 px-6">
            <div className="py-4 space-y-2">
              {variables.length === 0 && !addingNew && (
                <p className="text-sm text-muted-foreground text-center py-8">
                  {t("variablesPanelEmpty")}
                </p>
              )}

              {variables.map((variable, index) => {
                const isEditing = editingState?.index === index

                if (isEditing) {
                  return (
                    <div
                      key={index}
                      className="rounded-lg border border-primary/30 bg-muted/30 p-3 space-y-2"
                    >
                      <div className="flex items-center gap-2">
                        <Input
                          className="h-8 text-sm flex-1"
                          placeholder={t("variablesPanelNamePlaceholder")}
                          value={editingState.variable.name}
                          onChange={(e) => {
                            setEditingState({
                              ...editingState,
                              variable: { ...editingState.variable, name: e.target.value },
                            })
                            setFieldError(null)
                          }}
                          onKeyDown={(e) => handleKeyDown(e, "edit")}
                          autoFocus
                          aria-invalid={!!fieldError}
                        />
                        <Select
                          value={editingState.variable.type}
                          onValueChange={(val) =>
                            setEditingState({
                              ...editingState,
                              variable: {
                                ...editingState.variable,
                                type: val as WorkflowVariable["type"],
                              },
                            })
                          }
                        >
                          <SelectTrigger className="h-8 w-[100px] text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {VARIABLE_TYPES.map((vt) => (
                              <SelectItem key={vt} value={vt}>
                                {typeLabel(vt)}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <Input
                        className="h-8 text-sm"
                        placeholder={t("variablesPanelDefaultPlaceholder")}
                        value={editingState.variable.default_value}
                        onChange={(e) =>
                          setEditingState({
                            ...editingState,
                            variable: { ...editingState.variable, default_value: e.target.value },
                          })
                        }
                        onKeyDown={(e) => handleKeyDown(e, "edit")}
                      />
                      <Input
                        className="h-8 text-sm"
                        placeholder={t("variablesPanelDescriptionPlaceholder")}
                        value={editingState.variable.description}
                        onChange={(e) =>
                          setEditingState({
                            ...editingState,
                            variable: { ...editingState.variable, description: e.target.value },
                          })
                        }
                        onKeyDown={(e) => handleKeyDown(e, "edit")}
                      />
                      {fieldError && (
                        <p className="text-sm text-destructive">{fieldError}</p>
                      )}
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={handleEditCancel}
                          aria-label={tc("cancel")}
                        >
                          <X className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={handleEditSave}
                          aria-label={tc("save")}
                        >
                          <Check className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  )
                }

                return (
                  <div
                    key={index}
                    className="group rounded-lg border border-border/60 bg-card p-3 hover:border-border transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-sm font-mono font-medium truncate">
                          {variable.name}
                        </span>
                        <Badge
                          variant="outline"
                          className={`text-[10px] px-1.5 py-0 h-5 shrink-0 ${typeBadgeClass(variable.type)}`}
                        >
                          {typeLabel(variable.type)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => handleEditStart(index)}
                          aria-label={tc("edit")}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setDeleteIndex(index)}
                          aria-label={tc("delete")}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                    </div>
                    {variable.default_value && (
                      <p className="text-xs text-muted-foreground mt-1">
                        <span className="text-muted-foreground/60">
                          {t("variablesPanelDefaultValue")}:
                        </span>{" "}
                        <span className="font-mono">{variable.default_value}</span>
                      </p>
                    )}
                    {variable.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {variable.description}
                      </p>
                    )}
                  </div>
                )
              })}

              {/* Inline add form */}
              {addingNew && (
                <div className="rounded-lg border border-dashed border-primary/40 bg-muted/20 p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Input
                      className="h-8 text-sm flex-1"
                      placeholder={t("variablesPanelNamePlaceholder")}
                      value={newVariable.name}
                      onChange={(e) => {
                        setNewVariable({ ...newVariable, name: e.target.value })
                        setFieldError(null)
                      }}
                      onKeyDown={(e) => handleKeyDown(e, "add")}
                      autoFocus
                      aria-invalid={!!fieldError}
                    />
                    <Select
                      value={newVariable.type}
                      onValueChange={(val) =>
                        setNewVariable({
                          ...newVariable,
                          type: val as WorkflowVariable["type"],
                        })
                      }
                    >
                      <SelectTrigger className="h-8 w-[100px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {VARIABLE_TYPES.map((vt) => (
                          <SelectItem key={vt} value={vt}>
                            {typeLabel(vt)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Input
                    className="h-8 text-sm"
                    placeholder={t("variablesPanelDefaultPlaceholder")}
                    value={newVariable.default_value}
                    onChange={(e) =>
                      setNewVariable({ ...newVariable, default_value: e.target.value })
                    }
                    onKeyDown={(e) => handleKeyDown(e, "add")}
                  />
                  <Input
                    className="h-8 text-sm"
                    placeholder={t("variablesPanelDescriptionPlaceholder")}
                    value={newVariable.description}
                    onChange={(e) =>
                      setNewVariable({ ...newVariable, description: e.target.value })
                    }
                    onKeyDown={(e) => handleKeyDown(e, "add")}
                  />
                  {fieldError && (
                    <p className="text-sm text-destructive">{fieldError}</p>
                  )}
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={handleAddCancel}
                      aria-label={tc("cancel")}
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={handleAddSave}
                      aria-label={tc("save")}
                    >
                      <Check className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Footer with Add button */}
          <div className="border-t border-border/40 px-6 py-3">
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-1.5"
              onClick={handleAddStart}
              disabled={addingNew}
            >
              <Plus className="h-3.5 w-3.5" />
              {t("variablesPanelAdd")}
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation */}
      <AlertDialog
        open={deleteIndex !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteIndex(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("variablesPanelDeleteTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("variablesPanelDeleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {tc("delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
