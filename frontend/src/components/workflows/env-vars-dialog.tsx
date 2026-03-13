"use client"

import { useState, useEffect, useCallback } from "react"
import { useTranslations } from "next-intl"
import { toast } from "sonner"
import { Key, Plus, Trash2, Eye, EyeOff, Loader2, AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { workflowApi } from "@/lib/api"

interface EnvVar {
  key: string
  value: string
  isExisting: boolean
  showValue: boolean
}

interface EnvVarsDialogProps {
  workflowId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function EnvVarsDialog({ workflowId, open, onOpenChange }: EnvVarsDialogProps) {
  const t = useTranslations("workflows")
  const tc = useTranslations("common")

  const [envVars, setEnvVars] = useState<EnvVar[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<number, string>>({})

  const loadKeys = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await workflowApi.getEnvKeys(workflowId)
      setEnvVars(
        data.keys.map((k) => ({
          key: k,
          value: "",
          isExisting: true,
          showValue: false,
        })),
      )
      setFieldErrors({})
    } catch {
      toast.error(t("envVarsSaveFailed"))
    } finally {
      setIsLoading(false)
    }
  }, [workflowId, t])

  useEffect(() => {
    if (open) {
      loadKeys()
    }
  }, [open, loadKeys])

  const clearFieldError = (index: number) => {
    setFieldErrors((prev) => {
      const next = { ...prev }
      delete next[index]
      return next
    })
  }

  const handleAddVar = () => {
    setEnvVars((prev) => [
      ...prev,
      { key: "", value: "", isExisting: false, showValue: true },
    ])
  }

  const handleRemoveVar = (index: number) => {
    setEnvVars((prev) => prev.filter((_, i) => i !== index))
    clearFieldError(index)
  }

  const handleKeyChange = (index: number, newKey: string) => {
    setEnvVars((prev) =>
      prev.map((v, i) => (i === index ? { ...v, key: newKey } : v)),
    )
    clearFieldError(index)
  }

  const handleValueChange = (index: number, newValue: string) => {
    setEnvVars((prev) =>
      prev.map((v, i) => (i === index ? { ...v, value: newValue } : v)),
    )
  }

  const handleToggleVisibility = (index: number) => {
    setEnvVars((prev) =>
      prev.map((v, i) => (i === index ? { ...v, showValue: !v.showValue } : v)),
    )
  }

  const validate = (): boolean => {
    const errors: Record<number, string> = {}
    const keysSeen = new Set<string>()

    for (let i = 0; i < envVars.length; i++) {
      const key = envVars[i].key.trim()
      if (!key) {
        errors[i] = t("envVarsKeyEmpty")
      } else if (keysSeen.has(key.toUpperCase())) {
        errors[i] = t("envVarsKeyDuplicate")
      }
      keysSeen.add(key.toUpperCase())
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSave = async () => {
    if (!validate()) return

    setIsSaving(true)
    try {
      const envMap: Record<string, string> = {}
      for (const v of envVars) {
        const key = v.key.trim()
        if (key) {
          envMap[key] = v.value
        }
      }

      const data = await workflowApi.updateEnv(workflowId, envMap)
      toast.success(t("envVarsSaved"))

      // Refresh with the returned keys
      setEnvVars(
        data.keys.map((k) => ({
          key: k,
          value: "",
          isExisting: true,
          showValue: false,
        })),
      )
      setFieldErrors({})
    } catch {
      toast.error(t("envVarsSaveFailed"))
    } finally {
      setIsSaving(false)
    }
  }

  const hasExistingVars = envVars.some((v) => v.isExisting)
  const hasNewVars = envVars.some((v) => !v.isExisting)
  const hasAnyVars = envVars.length > 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            {t("envVarsTitle")}
          </DialogTitle>
          <DialogDescription>
            {t("envVarsDescription")}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {/* Warning about re-entering values */}
            {hasExistingVars && hasNewVars && (
              <div className="flex items-start gap-2 rounded-md border border-amber-400/30 bg-amber-500/10 p-2.5">
                <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  {t("envVarsReenterWarning")}
                </p>
              </div>
            )}

            {!hasAnyVars && (
              <p className="py-4 text-center text-sm text-muted-foreground">
                {t("envVarsEmpty")}
              </p>
            )}

            {hasAnyVars && (
              <ScrollArea className="max-h-[320px] overflow-y-auto">
                <div className="space-y-2">
                  {/* Column headers */}
                  <div className="grid grid-cols-[1fr_1fr_auto_auto] gap-1.5 px-0.5">
                    <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                      {t("envVarsKeyLabel")}
                    </span>
                    <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                      {t("envVarsValueLabel")}
                    </span>
                    <span className="w-7" />
                    <span className="w-7" />
                  </div>

                  {envVars.map((envVar, index) => (
                    <div key={index} className="space-y-0.5">
                      <div className="grid grid-cols-[1fr_1fr_auto_auto] gap-1.5 items-center">
                        <Input
                          className="h-7 text-xs font-mono"
                          value={envVar.key}
                          onChange={(e) => handleKeyChange(index, e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""))}
                          placeholder={t("envVarsKeyPlaceholder")}
                          disabled={envVar.isExisting}
                          aria-invalid={!!fieldErrors[index]}
                        />
                        <Input
                          className="h-7 text-xs"
                          type={envVar.showValue ? "text" : "password"}
                          value={envVar.value}
                          onChange={(e) => handleValueChange(index, e.target.value)}
                          placeholder={
                            envVar.isExisting
                              ? t("envVarsValueMasked")
                              : t("envVarsValuePlaceholder")
                          }
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => handleToggleVisibility(index)}
                          type="button"
                        >
                          {envVar.showValue ? (
                            <EyeOff className="h-3.5 w-3.5" />
                          ) : (
                            <Eye className="h-3.5 w-3.5" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          onClick={() => handleRemoveVar(index)}
                          type="button"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                      {fieldErrors[index] && (
                        <p className="text-xs text-destructive px-0.5">
                          {fieldErrors[index]}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}

            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 w-full text-xs"
              onClick={handleAddVar}
            >
              <Plus className="h-3.5 w-3.5" />
              {t("envVarsAdd")}
            </Button>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="ghost"
            className="px-6"
            onClick={() => onOpenChange(false)}
          >
            {tc("cancel")}
          </Button>
          <Button
            className="px-6"
            onClick={handleSave}
            disabled={isSaving || isLoading}
          >
            {isSaving && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
            {tc("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
