"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"
import { Plus, GitBranch, Upload } from "lucide-react"
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
import { WorkflowCard } from "@/components/workflows/workflow-card"
import { Skeleton } from "@/components/ui/skeleton"
import type { WorkflowResponse } from "@/types/workflow"

export default function WorkflowsPage() {
  const t = useTranslations("workflows")
  const tc = useTranslations("common")
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()

  const [workflows, setWorkflows] = useState<WorkflowResponse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login")
    }
  }, [authLoading, user, router])

  const loadWorkflows = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await workflowApi.list()
      setWorkflows(data.items as WorkflowResponse[])
    } catch (err) {
      console.error("Failed to load workflows:", err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (user) loadWorkflows()
  }, [user, loadWorkflows])

  const handleDelete = (id: string) => setPendingDeleteId(id)

  const confirmDelete = async () => {
    if (!pendingDeleteId) return
    const id = pendingDeleteId
    setPendingDeleteId(null)
    try {
      await workflowApi.delete(id)
      setWorkflows((prev) => prev.filter((w) => w.id !== id))
      toast.success(t("workflowDeleted"))
    } catch {
      toast.error(t("workflowDeleteFailed"))
    }
  }

  const handleCreate = async () => {
    try {
      const workflow = await workflowApi.create({
        name: t("editorUntitled"),
        blueprint: {
          nodes: [
            { id: "start_1", type: "start", position: { x: 250, y: 50 }, data: { variables: [] } },
            { id: "end_1", type: "end", position: { x: 250, y: 400 }, data: { output_mapping: {} } },
          ],
          edges: [],
          viewport: { x: 0, y: 0, zoom: 1 },
        },
      })
      router.push(`/workflows/${workflow.id}`)
    } catch {
      toast.error(t("workflowCreateFailed"))
    }
  }

  const handleImport = () => {
    fileInputRef.current?.click()
  }

  const onFileImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const workflow = await workflowApi.import(data)
      setWorkflows((prev) => [workflow, ...prev])
      toast.success(t("workflowImported"))
    } catch {
      toast.error(t("workflowImportFailed"))
    }
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  if (authLoading || !user) return null

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 shrink-0 border-b border-border/40">
        <div>
          <h1 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <GitBranch className="h-5 w-5" />
            {t("title")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t("subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-1.5" onClick={handleImport}>
            <Upload className="h-3.5 w-3.5" />
            {tc("import")}
          </Button>
          <Button size="sm" className="gap-1.5" onClick={handleCreate}>
            <Plus className="h-4 w-4" />
            {t("newWorkflow")}
          </Button>
        </div>
      </div>

      {/* Hidden file input for import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={onFileImport}
      />

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton.AgentCard key={i} />
            ))}
          </div>
        ) : workflows.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-sm text-muted-foreground">
              {t("emptyState")}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4 gap-1.5"
              onClick={handleCreate}
            >
              <Plus className="h-4 w-4" />
              {t("createWorkflow")}
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {workflows.map((workflow) => (
              <WorkflowCard
                key={workflow.id}
                workflow={workflow}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation */}
      <Dialog open={pendingDeleteId !== null} onOpenChange={(open) => { if (!open) setPendingDeleteId(null) }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <GitBranch className="h-4 w-4" />
              {t("deleteDialogTitle")}
            </DialogTitle>
            <DialogDescription>
              {t("deleteDialogDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" className="px-6" onClick={() => setPendingDeleteId(null)}>{tc("cancel")}</Button>
            <Button variant="destructive" className="px-6" onClick={confirmDelete}>{tc("delete")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
