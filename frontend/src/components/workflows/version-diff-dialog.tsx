"use client"

import { useMemo, useState } from "react"
import { useTranslations } from "next-intl"
import {
  Plus,
  Minus,
  Pencil,
  Equal,
  ChevronDown,
  ArrowRight,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import type {
  WorkflowVersionResponse,
  WorkflowNode,
  WorkflowEdge,
} from "@/types/workflow"

// ---------- diff types ----------

interface NodeChange {
  type: "added" | "removed" | "modified"
  node: WorkflowNode
  changedFields?: string[]
}

interface EdgeChange {
  type: "added" | "removed"
  edge: WorkflowEdge
}

interface DiffResult {
  addedNodes: NodeChange[]
  removedNodes: NodeChange[]
  modifiedNodes: NodeChange[]
  unchangedCount: number
  addedEdges: EdgeChange[]
  removedEdges: EdgeChange[]
}

// ---------- diff algorithm ----------

function computeDiff(
  versionA: WorkflowVersionResponse,
  versionB: WorkflowVersionResponse,
): DiffResult {
  const nodesA = versionA.blueprint.nodes
  const nodesB = versionB.blueprint.nodes
  const edgesA = versionA.blueprint.edges
  const edgesB = versionB.blueprint.edges

  const nodeMapA = new Map(nodesA.map((n) => [n.id, n]))
  const nodeMapB = new Map(nodesB.map((n) => [n.id, n]))

  const addedNodes: NodeChange[] = []
  const removedNodes: NodeChange[] = []
  const modifiedNodes: NodeChange[] = []
  let unchangedCount = 0

  // Check nodes in B that are not in A (added) or differ (modified)
  for (const [id, nodeB] of nodeMapB) {
    const nodeA = nodeMapA.get(id)
    if (!nodeA) {
      addedNodes.push({ type: "added", node: nodeB })
    } else {
      // Compare data (deep equality via JSON)
      const dataA = JSON.stringify(nodeA.data)
      const dataB = JSON.stringify(nodeB.data)
      if (dataA !== dataB) {
        const changedFields = findChangedFields(nodeA.data, nodeB.data)
        modifiedNodes.push({ type: "modified", node: nodeB, changedFields })
      } else {
        unchangedCount++
      }
    }
  }

  // Nodes in A not in B (removed)
  for (const [id, nodeA] of nodeMapA) {
    if (!nodeMapB.has(id)) {
      removedNodes.push({ type: "removed", node: nodeA })
    }
  }

  // Edge comparison by composite key: source+target+sourceHandle
  function edgeKey(e: WorkflowEdge): string {
    return `${e.source}|${e.target}|${e.sourceHandle ?? ""}`
  }

  const edgeSetA = new Set(edgesA.map(edgeKey))
  const edgeSetB = new Set(edgesB.map(edgeKey))
  const edgeMapA = new Map(edgesA.map((e) => [edgeKey(e), e]))
  const edgeMapB = new Map(edgesB.map((e) => [edgeKey(e), e]))

  const addedEdges: EdgeChange[] = []
  const removedEdges: EdgeChange[] = []

  for (const [key, edge] of edgeMapB) {
    if (!edgeSetA.has(key)) {
      addedEdges.push({ type: "added", edge })
    }
  }

  for (const [key, edge] of edgeMapA) {
    if (!edgeSetB.has(key)) {
      removedEdges.push({ type: "removed", edge })
    }
  }

  return {
    addedNodes,
    removedNodes,
    modifiedNodes,
    unchangedCount,
    addedEdges,
    removedEdges,
  }
}

function findChangedFields(
  dataA: Record<string, unknown>,
  dataB: Record<string, unknown>,
): string[] {
  const allKeys = new Set([...Object.keys(dataA), ...Object.keys(dataB)])
  const changed: string[] = []
  for (const key of allKeys) {
    if (JSON.stringify(dataA[key]) !== JSON.stringify(dataB[key])) {
      changed.push(key)
    }
  }
  return changed
}

// ---------- helper to get node label ----------

function getNodeLabel(node: WorkflowNode): string {
  const data = node.data as Record<string, unknown>
  if (typeof data.label === "string" && data.label) return data.label
  if (typeof data.name === "string" && data.name) return data.name
  return node.id
}

// ---------- component ----------

interface VersionDiffDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  versionA: WorkflowVersionResponse | null
  versionB: WorkflowVersionResponse | null
}

export function VersionDiffDialog({
  open,
  onOpenChange,
  versionA,
  versionB,
}: VersionDiffDialogProps) {
  const t = useTranslations("workflows")
  const [unchangedOpen, setUnchangedOpen] = useState(false)

  const diff = useMemo(() => {
    if (!versionA || !versionB) return null
    return computeDiff(versionA, versionB)
  }, [versionA, versionB])

  if (!versionA || !versionB || !diff) return null

  const totalNodeChanges =
    diff.addedNodes.length + diff.removedNodes.length + diff.modifiedNodes.length
  const totalEdgeChanges = diff.addedEdges.length + diff.removedEdges.length
  const hasNoChanges = totalNodeChanges === 0 && totalEdgeChanges === 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col p-0 gap-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-border/40 shrink-0">
          <DialogTitle className="text-sm">
            {t("versionDiffTitle", {
              versionA: versionA.version_number,
              versionB: versionB.version_number,
            })}
          </DialogTitle>
          <DialogDescription className="sr-only">
            {t("versionDiffTitle", {
              versionA: versionA.version_number,
              versionB: versionB.version_number,
            })}
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 min-h-0">
          <div className="px-6 py-4 space-y-5">
            {/* ---------- No Changes ---------- */}
            {hasNoChanges && (
              <p className="text-sm text-muted-foreground text-center py-6">
                {t("versionDiffNoChanges")}
              </p>
            )}

            {/* ---------- Summary ---------- */}
            {!hasNoChanges && (
              <section>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                  {t("versionDiffSummary")}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {diff.addedNodes.length > 0 && (
                    <Badge
                      variant="secondary"
                      className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {t("versionDiffNodesAdded", {
                        count: diff.addedNodes.length,
                      })}
                    </Badge>
                  )}
                  {diff.removedNodes.length > 0 && (
                    <Badge
                      variant="secondary"
                      className="bg-destructive/10 text-destructive border-destructive/20"
                    >
                      <Minus className="h-3 w-3 mr-1" />
                      {t("versionDiffNodesRemoved", {
                        count: diff.removedNodes.length,
                      })}
                    </Badge>
                  )}
                  {diff.modifiedNodes.length > 0 && (
                    <Badge
                      variant="secondary"
                      className="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
                    >
                      <Pencil className="h-3 w-3 mr-1" />
                      {t("versionDiffNodesModified", {
                        count: diff.modifiedNodes.length,
                      })}
                    </Badge>
                  )}
                  {diff.addedEdges.length > 0 && (
                    <Badge
                      variant="secondary"
                      className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {t("versionDiffEdgesAdded", {
                        count: diff.addedEdges.length,
                      })}
                    </Badge>
                  )}
                  {diff.removedEdges.length > 0 && (
                    <Badge
                      variant="secondary"
                      className="bg-destructive/10 text-destructive border-destructive/20"
                    >
                      <Minus className="h-3 w-3 mr-1" />
                      {t("versionDiffEdgesRemoved", {
                        count: diff.removedEdges.length,
                      })}
                    </Badge>
                  )}
                </div>
              </section>
            )}

            {/* ---------- Node Changes ---------- */}
            {totalNodeChanges > 0 && (
              <section>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                  {t("versionDiffNodeChanges")}
                </h3>
                <div className="space-y-1.5">
                  {/* Added */}
                  {diff.addedNodes.map((change) => (
                    <div
                      key={change.node.id}
                      className="border-l-2 border-emerald-500 rounded-r-md bg-emerald-500/5 px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <Plus className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
                          {t(`nodeType_${change.node.type}` as Parameters<typeof t>[0])}
                        </span>
                        <span className="text-xs text-muted-foreground truncate">
                          {getNodeLabel(change.node)}
                        </span>
                      </div>
                    </div>
                  ))}

                  {/* Removed */}
                  {diff.removedNodes.map((change) => (
                    <div
                      key={change.node.id}
                      className="border-l-2 border-destructive rounded-r-md bg-destructive/5 px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <Minus className="h-3.5 w-3.5 text-destructive shrink-0" />
                        <span className="text-xs font-medium text-destructive line-through">
                          {t(`nodeType_${change.node.type}` as Parameters<typeof t>[0])}
                        </span>
                        <span className="text-xs text-muted-foreground line-through truncate">
                          {getNodeLabel(change.node)}
                        </span>
                      </div>
                    </div>
                  ))}

                  {/* Modified */}
                  {diff.modifiedNodes.map((change) => (
                    <div
                      key={change.node.id}
                      className="border-l-2 border-amber-500 rounded-r-md bg-amber-500/5 px-3 py-2"
                    >
                      <div className="flex items-center gap-2">
                        <Pencil className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                        <span className="text-xs font-medium text-amber-600 dark:text-amber-400">
                          {t(`nodeType_${change.node.type}` as Parameters<typeof t>[0])}
                        </span>
                        <span className="text-xs text-muted-foreground truncate">
                          {getNodeLabel(change.node)}
                        </span>
                      </div>
                      {change.changedFields && change.changedFields.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5 ml-5">
                          {change.changedFields.map((field) => (
                            <Badge
                              key={field}
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 h-4 text-amber-600 dark:text-amber-400 border-amber-500/30"
                            >
                              {t("versionDiffFieldChanged", { field })}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Unchanged — collapsed */}
                  {diff.unchangedCount > 0 && (
                    <Collapsible
                      open={unchangedOpen}
                      onOpenChange={setUnchangedOpen}
                    >
                      <CollapsibleTrigger className="flex items-center gap-2 w-full border-l-2 border-border rounded-r-md bg-muted/30 px-3 py-2 text-xs text-muted-foreground hover:bg-muted/50 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                        <Equal className="h-3.5 w-3.5 shrink-0" />
                        <span>
                          {t("versionDiffNodesUnchanged", {
                            count: diff.unchangedCount,
                          })}
                        </span>
                        <ChevronDown className="h-3 w-3 ml-auto transition-transform data-[state=open]:rotate-180" />
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <UnchangedNodesList
                          versionA={versionA}
                          versionB={versionB}
                          t={t}
                        />
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                </div>
              </section>
            )}

            {/* ---------- Edge Changes ---------- */}
            {totalEdgeChanges > 0 && (
              <section>
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                  {t("versionDiffEdgeChanges")}
                </h3>
                <div className="space-y-1.5">
                  {diff.addedEdges.map((change) => (
                    <div
                      key={change.edge.id}
                      className="border-l-2 border-emerald-500 rounded-r-md bg-emerald-500/5 px-3 py-2"
                    >
                      <div className="flex items-center gap-2 text-xs">
                        <Plus className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <span className="text-muted-foreground font-mono">
                          {change.edge.source}
                        </span>
                        <ArrowRight className="h-3 w-3 text-muted-foreground/60 shrink-0" />
                        <span className="text-muted-foreground font-mono">
                          {change.edge.target}
                        </span>
                      </div>
                    </div>
                  ))}
                  {diff.removedEdges.map((change) => (
                    <div
                      key={change.edge.id}
                      className="border-l-2 border-destructive rounded-r-md bg-destructive/5 px-3 py-2"
                    >
                      <div className="flex items-center gap-2 text-xs">
                        <Minus className="h-3.5 w-3.5 text-destructive shrink-0" />
                        <span className="text-muted-foreground font-mono line-through">
                          {change.edge.source}
                        </span>
                        <ArrowRight className="h-3 w-3 text-muted-foreground/60 shrink-0" />
                        <span className="text-muted-foreground font-mono line-through">
                          {change.edge.target}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}

// ---------- Unchanged nodes sub-component ----------

function UnchangedNodesList({
  versionA,
  versionB,
  t,
}: {
  versionA: WorkflowVersionResponse
  versionB: WorkflowVersionResponse
  t: ReturnType<typeof useTranslations<"workflows">>
}) {
  const nodeMapA = new Map(versionA.blueprint.nodes.map((n) => [n.id, n]))

  const unchangedNodes = versionB.blueprint.nodes.filter((nodeB) => {
    const nodeA = nodeMapA.get(nodeB.id)
    if (!nodeA) return false
    return JSON.stringify(nodeA.data) === JSON.stringify(nodeB.data)
  })

  return (
    <div className="space-y-1 mt-1">
      {unchangedNodes.map((node) => (
        <div
          key={node.id}
          className="border-l-2 border-border rounded-r-md bg-muted/20 px-3 py-1.5"
        >
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Equal className="h-3 w-3 shrink-0 opacity-50" />
            <span>
              {t(`nodeType_${node.type}` as Parameters<typeof t>[0])}
            </span>
            <span className="truncate opacity-60">
              {getNodeLabel(node)}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
