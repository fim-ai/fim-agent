"use client"

import { useState, useEffect, useMemo } from "react"
import { useTranslations } from "next-intl"
import {
  Cable,
  Server,
  BookOpen,
  Bot,
  Loader2,
  Search,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { connectorApi, mcpServerApi, kbApi, agentApi } from "@/lib/api"
import type { ConnectorResponse } from "@/types/connector"
import type { MCPServerResponse } from "@/types/mcp-server"
import type { KBResponse } from "@/types/kb"
import type { AgentResponse } from "@/types/agent"
import type { ResourceRef, ResourceRefType } from "@/types/skill"

interface ResourcePickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  existingRefs: ResourceRef[]
  onAdd: (ref: ResourceRef) => void
}

/** Generate a default alias from a resource name, e.g. "My CRM" -> "@my_crm" */
function defaultAlias(name: string): string {
  return (
    "@" +
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_|_$/g, "")
      .slice(0, 24)
  )
}

type ResourceItem = {
  id: string
  name: string
  description: string | null
  type: ResourceRefType
}

export function ResourcePickerDialog({
  open,
  onOpenChange,
  existingRefs,
  onAdd,
}: ResourcePickerDialogProps) {
  const t = useTranslations("skills")
  const tc = useTranslations("common")

  const [activeTab, setActiveTab] = useState<ResourceRefType>("connector")
  const [isLoading, setIsLoading] = useState(false)
  const [connectors, setConnectors] = useState<ConnectorResponse[]>([])
  const [mcpServers, setMcpServers] = useState<MCPServerResponse[]>([])
  const [kbs, setKbs] = useState<KBResponse[]>([])
  const [agents, setAgents] = useState<AgentResponse[]>([])
  const [search, setSearch] = useState("")

  // Selected resource before confirming
  const [selected, setSelected] = useState<ResourceItem | null>(null)
  const [alias, setAlias] = useState("")

  // Load all resources when dialog opens
  useEffect(() => {
    if (!open) return
    setIsLoading(true)
    setSelected(null)
    setAlias("")
    setSearch("")

    Promise.all([
      connectorApi.list(1, 100).then((d) => setConnectors(d.items || [])).catch(() => setConnectors([])),
      mcpServerApi.list(1, 100).then((d) => setMcpServers(d.items || [])).catch(() => setMcpServers([])),
      kbApi.list(1, 100).then((d) => setKbs(d.items || [])).catch(() => setKbs([])),
      agentApi.list(1, 100).then((d) => setAgents((d.items || []) as AgentResponse[])).catch(() => setAgents([])),
    ]).finally(() => setIsLoading(false))
  }, [open])

  const existingIds = useMemo(
    () => new Set(existingRefs.map((r) => `${r.type}:${r.id}`)),
    [existingRefs],
  )

  const filterItems = (items: ResourceItem[]): ResourceItem[] => {
    const q = search.toLowerCase().trim()
    return items.filter((item) => {
      if (existingIds.has(`${item.type}:${item.id}`)) return false
      if (!q) return true
      return item.name.toLowerCase().includes(q) || (item.description?.toLowerCase().includes(q) ?? false)
    })
  }

  const connectorItems: ResourceItem[] = connectors.map((c) => ({
    id: c.id,
    name: c.name,
    description: c.description,
    type: "connector" as const,
  }))

  const mcpItems: ResourceItem[] = mcpServers.map((m) => ({
    id: m.id,
    name: m.name,
    description: m.description,
    type: "mcp_server" as const,
  }))

  const kbItems: ResourceItem[] = kbs.map((k) => ({
    id: k.id,
    name: k.name,
    description: k.description,
    type: "knowledge_base" as const,
  }))

  const agentItems: ResourceItem[] = agents.map((a) => ({
    id: a.id,
    name: a.name,
    description: a.description,
    type: "agent" as const,
  }))

  const tabDataMap: Record<ResourceRefType, ResourceItem[]> = {
    connector: filterItems(connectorItems),
    mcp_server: filterItems(mcpItems),
    knowledge_base: filterItems(kbItems),
    agent: filterItems(agentItems),
  }

  const tabIcons: Record<ResourceRefType, React.ReactNode> = {
    connector: <Cable className="h-3.5 w-3.5" />,
    mcp_server: <Server className="h-3.5 w-3.5" />,
    knowledge_base: <BookOpen className="h-3.5 w-3.5" />,
    agent: <Bot className="h-3.5 w-3.5" />,
  }

  const tabLabels: Record<ResourceRefType, string> = {
    connector: t("resourceTypeConnector"),
    mcp_server: t("resourceTypeMcpServer"),
    knowledge_base: t("resourceTypeKnowledgeBase"),
    agent: t("resourceTypeAgent"),
  }

  const handleSelectResource = (item: ResourceItem) => {
    setSelected(item)
    setAlias(defaultAlias(item.name))
  }

  const handleConfirm = () => {
    if (!selected) return
    const finalAlias = alias.trim() || defaultAlias(selected.name)
    onAdd({
      type: selected.type,
      id: selected.id,
      name: selected.name,
      alias: finalAlias.startsWith("@") ? finalAlias : `@${finalAlias}`,
    })
    setSelected(null)
    setAlias("")
    onOpenChange(false)
  }

  const renderItems = (items: ResourceItem[]) => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      )
    }

    if (items.length === 0) {
      return (
        <p className="text-sm text-muted-foreground text-center py-8">
          {t("noResourcesAvailable")}
        </p>
      )
    }

    return (
      <div className="flex flex-col gap-1">
        {items.map((item) => {
          const isSelected = selected?.id === item.id && selected?.type === item.type
          return (
            <button
              key={`${item.type}:${item.id}`}
              type="button"
              onClick={() => handleSelectResource(item)}
              className={`flex items-start gap-3 rounded-md border px-3 py-2.5 text-left text-sm transition-colors ${
                isSelected
                  ? "border-primary bg-primary/5"
                  : "border-transparent hover:bg-accent/50"
              }`}
            >
              <span className="shrink-0 mt-0.5 text-muted-foreground">
                {tabIcons[item.type]}
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-medium truncate">{item.name}</p>
                {item.description && (
                  <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">
                    {item.description}
                  </p>
                )}
              </div>
            </button>
          )
        })}
      </div>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("resourcePickerTitle")}</DialogTitle>
          <DialogDescription>{t("resourcePickerDescription")}</DialogDescription>
        </DialogHeader>

        <Tabs
          value={activeTab}
          onValueChange={(v) => {
            setActiveTab(v as ResourceRefType)
            setSelected(null)
            setAlias("")
          }}
        >
          <TabsList className="w-full">
            {(["connector", "mcp_server", "knowledge_base", "agent"] as ResourceRefType[]).map(
              (tab) => (
                <TabsTrigger key={tab} value={tab} className="flex-1 gap-1.5 text-xs">
                  {tabIcons[tab]}
                  <span className="hidden sm:inline">{tabLabels[tab]}</span>
                </TabsTrigger>
              ),
            )}
          </TabsList>

          {/* Search input */}
          <div className="relative mt-3">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={tc("searchPlaceholder")}
              className="pl-8"
            />
          </div>

          {/* Resource lists */}
          {(["connector", "mcp_server", "knowledge_base", "agent"] as ResourceRefType[]).map(
            (tab) => (
              <TabsContent key={tab} value={tab} className="mt-2 max-h-[240px] overflow-y-auto">
                {renderItems(tabDataMap[tab])}
              </TabsContent>
            ),
          )}
        </Tabs>

        {/* Alias input — show when a resource is selected */}
        {selected && (
          <div className="space-y-2 border-t border-border pt-3 mt-1">
            <Label htmlFor="resource-alias">{t("resourceAlias")}</Label>
            <p className="text-xs text-muted-foreground">{t("resourceAliasHint")}</p>
            <Input
              id="resource-alias"
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder={t("resourceAliasPlaceholder")}
            />
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 mt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {tc("cancel")}
          </Button>
          <Button onClick={handleConfirm} disabled={!selected}>
            {tc("add")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
