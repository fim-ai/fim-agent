"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useAuth } from "@/contexts/auth-context"
import { workflowApi } from "@/lib/api"
import { getApiBaseUrl, ACCESS_TOKEN_KEY } from "@/lib/constants"
import { WorkflowToolbar } from "@/components/workflows/workflow-toolbar"
import { WorkflowEditor } from "@/components/workflows/workflow-editor"
import type {
  WorkflowResponse,
  WorkflowBlueprint,
  StartNodeData,
  NodeRunResult,
} from "@/types/workflow"

export default function WorkflowEditorPage() {
  const t = useTranslations("workflows")
  const tc = useTranslations("common")
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const params = useParams()
  const workflowId = params.id as string

  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null)
  const [isLoadingWorkflow, setIsLoadingWorkflow] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false)
  const pendingNavigationRef = useRef<string | null>(null)

  // Run state
  const [isRunning, setIsRunning] = useState(false)
  const [runPanelOpen, setRunPanelOpen] = useState(false)
  const [nodeResults, setNodeResults] = useState<Record<string, NodeRunResult> | null>(null)
  const [finalOutputs, setFinalOutputs] = useState<Record<string, unknown> | null>(null)
  const [finalError, setFinalError] = useState<string | null>(null)
  const [runDuration, setRunDuration] = useState<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Blueprint state managed by editor
  const blueprintRef = useRef<WorkflowBlueprint>({
    nodes: [],
    edges: [],
    viewport: { x: 0, y: 0, zoom: 1 },
  })

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login")
    }
  }, [authLoading, user, router])

  // Load workflow
  useEffect(() => {
    if (!user || !workflowId) return
    let cancelled = false
    setIsLoadingWorkflow(true)
    workflowApi
      .get(workflowId)
      .then((data) => {
        if (cancelled) return
        setWorkflow(data)
        blueprintRef.current = data.blueprint ?? {
          nodes: [],
          edges: [],
          viewport: { x: 0, y: 0, zoom: 1 },
        }
      })
      .catch(() => {
        if (!cancelled) {
          toast.error(t("workflowUpdateFailed"))
          router.replace("/workflows")
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoadingWorkflow(false)
      })
    return () => {
      cancelled = true
    }
  }, [user, workflowId, router, t])

  // Dirty state beforeunload guard
  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [isDirty])

  const handleBlueprintChange = useCallback((bp: WorkflowBlueprint) => {
    blueprintRef.current = bp
    setIsDirty(true)
  }, [])

  const handleNameChange = useCallback(
    async (name: string) => {
      if (!workflow) return
      setWorkflow((prev) => prev ? { ...prev, name } : prev)
      setIsDirty(true)
    },
    [workflow],
  )

  const handleSave = useCallback(async () => {
    if (!workflow) return
    setIsSaving(true)
    try {
      // Extract input_schema from start node
      const startNode = blueprintRef.current.nodes.find((n) => n.type === "start")
      const startData = startNode?.data as StartNodeData | undefined
      const inputSchema: Record<string, unknown> = {}
      if (startData?.variables) {
        for (const v of startData.variables) {
          inputSchema[v.name] = { type: v.type, required: v.required ?? false }
        }
      }

      // Extract output_schema from end node
      const endNode = blueprintRef.current.nodes.find((n) => n.type === "end")
      const endData = endNode?.data as { output_mapping?: Record<string, string> } | undefined
      const outputSchema = endData?.output_mapping
        ? Object.fromEntries(Object.keys(endData.output_mapping).map((k) => [k, { type: "string" }]))
        : null

      const updated = await workflowApi.update(workflow.id, {
        name: workflow.name,
        description: workflow.description,
        icon: workflow.icon,
        blueprint: blueprintRef.current,
        input_schema: Object.keys(inputSchema).length > 0 ? inputSchema : null,
        output_schema: outputSchema,
      })
      setWorkflow(updated)
      setIsDirty(false)
      toast.success(t("workflowUpdated"))
    } catch {
      toast.error(t("workflowUpdateFailed"))
    } finally {
      setIsSaving(false)
    }
  }, [workflow, t])

  const handleRun = useCallback(() => {
    setRunPanelOpen(true)
    setNodeResults(null)
    setFinalOutputs(null)
    setFinalError(null)
    setRunDuration(null)
  }, [])

  const handleStartRun = useCallback(
    async (inputs: Record<string, unknown>) => {
      if (!workflow) return

      // Abort any existing run
      if (abortRef.current) {
        abortRef.current.abort()
      }

      const controller = new AbortController()
      abortRef.current = controller
      setIsRunning(true)
      setNodeResults({})
      setFinalOutputs(null)
      setFinalError(null)
      setRunDuration(null)

      try {
        const token = typeof window !== "undefined" ? localStorage.getItem(ACCESS_TOKEN_KEY) : null
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        }
        if (token) headers["Authorization"] = `Bearer ${token}`

        const res = await fetch(
          `${getApiBaseUrl()}/api/workflows/${workflow.id}/run`,
          {
            method: "POST",
            headers,
            body: JSON.stringify({ inputs }),
            signal: controller.signal,
          },
        )

        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.detail || `HTTP ${res.status}`)
        }

        if (!res.body) throw new Error("No response body")

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""
        let currentEvent = "message"
        let currentData = ""

        const dispatch = (eventType: string, rawData: string) => {
          try {
            const data = JSON.parse(rawData) as Record<string, unknown>

            if (eventType === "node_status") {
              const nodeId = data.node_id as string
              const result = data.result as NodeRunResult
              setNodeResults((prev) => ({
                ...(prev ?? {}),
                [nodeId]: result,
              }))
            } else if (eventType === "run_completed") {
              setFinalOutputs((data.outputs ?? null) as Record<string, unknown> | null)
              setRunDuration((data.duration_ms ?? null) as number | null)
              setIsRunning(false)
            } else if (eventType === "run_failed") {
              setFinalError((data.error ?? "Unknown error") as string)
              setRunDuration((data.duration_ms ?? null) as number | null)
              setIsRunning(false)
            } else if (eventType === "end") {
              setIsRunning(false)
            }
          } catch {
            // Ignore unparseable
          }
        }

        for (;;) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() ?? ""
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim()
            } else if (line.startsWith("data:")) {
              currentData = line.slice(5).trim()
            } else if (line === "") {
              if (currentData) dispatch(currentEvent, currentData)
              currentEvent = "message"
              currentData = ""
            }
          }
        }
      } catch (err) {
        if ((err as { name?: string })?.name === "AbortError") return
        setFinalError(err instanceof Error ? err.message : "Stream error")
        setIsRunning(false)
      }
    },
    [workflow],
  )

  const handleCancelRun = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setIsRunning(false)
    if (workflow) {
      workflowApi.cancelRun(workflow.id, "current").catch(() => {})
    }
  }, [workflow])

  const handleExport = useCallback(async () => {
    if (!workflow) return
    try {
      const data = await workflowApi.export(workflow.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `workflow-${workflow.id}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error(t("workflowUpdateFailed"))
    }
  }, [workflow, t])

  const handleImport = useCallback(() => {
    const input = document.createElement("input")
    input.type = "file"
    input.accept = ".json"
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      try {
        const text = await file.text()
        const data = JSON.parse(text)
        if (data.blueprint) {
          blueprintRef.current = data.blueprint
          // Force re-render by updating workflow state
          setWorkflow((prev) =>
            prev ? { ...prev, blueprint: data.blueprint } : prev,
          )
          setIsDirty(true)
          toast.success(t("workflowImported"))
        }
      } catch {
        toast.error(t("workflowImportFailed"))
      }
    }
    input.click()
  }, [t])

  const handleDelete = useCallback(async () => {
    if (!workflow) return
    setShowDeleteDialog(false)
    try {
      await workflowApi.delete(workflow.id)
      toast.success(t("workflowDeleted"))
      router.replace("/workflows")
    } catch {
      toast.error(t("workflowDeleteFailed"))
    }
  }, [workflow, router, t])

  // Get start variables for run panel
  const startNode = blueprintRef.current.nodes.find((n) => n.type === "start")
  const startData = startNode?.data as StartNodeData | undefined
  const startVariables = startData?.variables ?? []

  if (authLoading || !user) return null

  if (isLoadingWorkflow) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!workflow) return null

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <WorkflowToolbar
        name={workflow.name}
        status={workflow.status}
        isSaving={isSaving}
        isRunning={isRunning}
        onNameChange={handleNameChange}
        onSave={handleSave}
        onRun={handleRun}
        onExport={handleExport}
        onImport={handleImport}
        onDelete={() => setShowDeleteDialog(true)}
      />

      <WorkflowEditor
        blueprint={workflow.blueprint}
        onBlueprintChange={handleBlueprintChange}
        isRunning={isRunning}
        runPanelOpen={runPanelOpen}
        startVariables={startVariables}
        nodeResults={nodeResults}
        finalOutputs={finalOutputs}
        finalError={finalError}
        runDuration={runDuration}
        onStartRun={handleStartRun}
        onCancelRun={handleCancelRun}
        onCloseRunPanel={() => setRunPanelOpen(false)}
      />

      {/* Delete Confirmation */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{t("deleteDialogTitle")}</DialogTitle>
            <DialogDescription>
              {t("deleteDialogDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" className="px-6" onClick={() => setShowDeleteDialog(false)}>
              {tc("cancel")}
            </Button>
            <Button variant="destructive" className="px-6" onClick={handleDelete}>
              {tc("delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unsaved changes guard */}
      <Dialog open={showUnsavedDialog} onOpenChange={setShowUnsavedDialog}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{t("unsavedChangesTitle")}</DialogTitle>
            <DialogDescription>
              {t("unsavedChangesDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" className="px-6" onClick={() => setShowUnsavedDialog(false)}>
              {t("stay")}
            </Button>
            <Button
              variant="destructive"
              className="px-6"
              onClick={() => {
                setShowUnsavedDialog(false)
                setIsDirty(false)
                if (pendingNavigationRef.current) {
                  router.push(pendingNavigationRef.current)
                }
              }}
            >
              {t("discardAndLeave")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
