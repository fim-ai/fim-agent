"use client"

import { useState, useCallback } from "react"
import { useTranslations } from "next-intl"
import {
  CheckCircle2,
  XCircle,
  Loader2,
  X,
  Play,
  CircleDashed,
  SkipForward,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { fmtDuration } from "@/lib/utils"
import type { StartNodeData, NodeRunResult, NodeRunStatus } from "@/types/workflow"

interface RunPanelProps {
  isOpen: boolean
  isRunning: boolean
  startVariables: StartNodeData["variables"]
  nodeResults: Record<string, NodeRunResult> | null
  finalOutputs: Record<string, unknown> | null
  finalError: string | null
  runDuration: number | null
  onStartRun: (inputs: Record<string, unknown>) => void
  onCancel: () => void
  onClose: () => void
}

const statusIcons: Record<NodeRunStatus, React.ReactNode> = {
  pending: <CircleDashed className="h-3.5 w-3.5 text-zinc-500" />,
  running: <Loader2 className="h-3.5 w-3.5 text-blue-500 animate-spin" />,
  completed: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
  failed: <XCircle className="h-3.5 w-3.5 text-red-500" />,
  skipped: <SkipForward className="h-3.5 w-3.5 text-zinc-400" />,
}

export function RunPanel({
  isOpen,
  isRunning,
  startVariables,
  nodeResults,
  finalOutputs,
  finalError,
  runDuration,
  onStartRun,
  onCancel,
  onClose,
}: RunPanelProps) {
  const t = useTranslations("workflows")
  const [inputValues, setInputValues] = useState<Record<string, string>>({})

  const handleInputChange = useCallback(
    (name: string, value: string) => {
      setInputValues((prev) => ({ ...prev, [name]: value }))
    },
    [],
  )

  const handleStartRun = useCallback(() => {
    const inputs: Record<string, unknown> = {}
    for (const v of startVariables) {
      const raw = inputValues[v.name] ?? v.default_value ?? ""
      if (v.type === "number") {
        inputs[v.name] = raw ? Number(raw) : 0
      } else if (v.type === "boolean") {
        inputs[v.name] = raw === "true"
      } else {
        inputs[v.name] = raw
      }
    }
    onStartRun(inputs)
  }, [startVariables, inputValues, onStartRun])

  if (!isOpen) return null

  const hasInputs = startVariables.length > 0
  const hasResults = nodeResults && Object.keys(nodeResults).length > 0
  const showInputForm = !isRunning && !hasResults

  return (
    <div className="absolute bottom-0 left-0 right-0 z-10 border-t border-border bg-background/95 backdrop-blur-sm">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/40">
        <h3 className="text-xs font-semibold text-foreground">
          {t("runPanelTitle")}
        </h3>
        <div className="flex items-center gap-1.5">
          {isRunning && (
            <Button variant="outline" size="sm" className="h-6 text-xs gap-1" onClick={onCancel}>
              {t("runPanelCancel")}
            </Button>
          )}
          {runDuration != null && (
            <span className="text-[10px] text-muted-foreground tabular-nums">
              {t("runPanelDuration")}: {fmtDuration(runDuration / 1000)}
            </span>
          )}
          <Button variant="ghost" size="icon-sm" onClick={onClose}>
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      <ScrollArea className="max-h-[280px]">
        <div className="p-4 space-y-4">
          {/* Input form */}
          {showInputForm && (
            <div className="space-y-3">
              {hasInputs ? (
                <>
                  <p className="text-xs text-muted-foreground">{t("runPanelProvideInputs")}</p>
                  {startVariables.map((v) => (
                    <div key={v.name} className="space-y-1">
                      <label className="text-xs font-medium">
                        {v.name}
                        {v.required && <span className="text-destructive ml-0.5">*</span>}
                        <span className="text-[10px] text-muted-foreground ml-1.5">({v.type})</span>
                      </label>
                      <Input
                        className="h-7 text-xs"
                        placeholder={v.default_value ?? ""}
                        value={inputValues[v.name] ?? ""}
                        onChange={(e) => handleInputChange(v.name, e.target.value)}
                      />
                    </div>
                  ))}
                </>
              ) : (
                <p className="text-xs text-muted-foreground">{t("runPanelNoInputs")}</p>
              )}
              <Button size="sm" className="gap-1.5" onClick={handleStartRun}>
                <Play className="h-3.5 w-3.5" />
                {t("runPanelStartRun")}
              </Button>
            </div>
          )}

          {/* Running/Results */}
          {hasResults && (
            <div className="space-y-2">
              <p className="text-xs font-medium">{t("runPanelNodeResults")}</p>
              {Object.entries(nodeResults).map(([nodeId, result]) => (
                <div
                  key={nodeId}
                  className="flex items-start gap-2 rounded-md border border-border p-2"
                >
                  {statusIcons[result.status]}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{nodeId}</p>
                    {result.duration != null && (
                      <p className="text-[10px] text-muted-foreground tabular-nums">
                        {fmtDuration(result.duration)}
                      </p>
                    )}
                    {result.error && (
                      <p className="text-[10px] text-destructive line-clamp-2">{result.error}</p>
                    )}
                    {result.output != null && result.status === "completed" && (
                      <pre className="text-[10px] text-muted-foreground line-clamp-2 font-mono mt-0.5">
                        {typeof result.output === "string"
                          ? result.output
                          : JSON.stringify(result.output, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Final output */}
          {finalOutputs && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium">{t("runPanelOutput")}</p>
              <pre className={cn(
                "text-xs p-2 rounded-md border border-border bg-muted/50 font-mono overflow-auto max-h-[120px]",
              )}>
                {JSON.stringify(finalOutputs, null, 2)}
              </pre>
            </div>
          )}

          {/* Error */}
          {finalError && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-destructive">{t("runPanelError")}</p>
              <p className="text-xs text-destructive bg-destructive/10 p-2 rounded-md">
                {finalError}
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
