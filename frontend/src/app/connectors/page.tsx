"use client"

import { useState, useEffect, useCallback, useRef, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { Plus, Plug, Trash2, LayoutGrid, Database, Globe, ChevronDown, Loader2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAuth } from "@/contexts/auth-context"
import { connectorApi, orgApi } from "@/lib/api"
import type { UserOrg } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { ConnectorCard } from "@/components/connectors/connector-card"
import { MCPServersSection, type MCPServersSectionActions } from "@/components/tools/mcp-servers-section"
import type { ConnectorResponse } from "@/types/connector"
import { toast } from "sonner"

function ConnectorsPageInner() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const t = useTranslations("connectors")
  const tt = useTranslations("tools")
  const tc = useTranslations("common")
  const mcpActionsRef = useRef<MCPServersSectionActions | null>(null)

  const activeTab = searchParams.get("tab") === "mcp" ? "mcp" : "connectors"

  const handleTabChange = (tab: string) => {
    if (tab === "connectors") {
      router.replace("/connectors")
    } else {
      router.replace(`/connectors?tab=${tab}`)
    }
  }

  const [connectors, setConnectors] = useState<ConnectorResponse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const [pendingPublishId, setPendingPublishId] = useState<string | null>(null)
  const [pendingUnpublishId, setPendingUnpublishId] = useState<string | null>(null)
  const [publishScope, setPublishScope] = useState<"personal" | "org">("personal")
  const [publishOrgId, setPublishOrgId] = useState<string>("")
  const [userOrgs, setUserOrgs] = useState<UserOrg[]>([])
  const [orgsLoading, setOrgsLoading] = useState(false)

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login")
    }
  }, [authLoading, user, router])

  const loadConnectors = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await connectorApi.list()
      setConnectors(data.items)
    } catch (err) {
      console.error("Failed to load connectors:", err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (user) loadConnectors()
  }, [user, loadConnectors])

  const handleDelete = (id: string) => setPendingDeleteId(id)

  const handlePublish = (id: string) => {
    setPendingPublishId(id)
    setPublishScope("personal")
    setPublishOrgId("")
    setOrgsLoading(true)
    orgApi.list().then((orgs) => {
      setUserOrgs(orgs)
    }).catch(() => {}).finally(() => setOrgsLoading(false))
  }

  const handleUnpublish = (id: string) => setPendingUnpublishId(id)

  const handleResubmit = async (id: string) => {
    try {
      const updated = await connectorApi.resubmit(id)
      setConnectors((prev) => prev.map((c) => (c.id === id ? updated : c)))
      toast.success(t("connectorResubmitted"))
    } catch {
      toast.error(t("connectorResubmitFailed"))
    }
  }

  const confirmDelete = async () => {
    if (!pendingDeleteId) return
    const id = pendingDeleteId
    setPendingDeleteId(null)
    try {
      await connectorApi.delete(id)
      setConnectors((prev) => prev.filter((c) => c.id !== id))
      toast.success(t("connectorDeleted"))
    } catch {
      toast.error(t("connectorDeleteFailed"))
    }
  }

  const confirmPublish = async () => {
    if (!pendingPublishId) return
    const id = pendingPublishId
    setPendingPublishId(null)
    try {
      const updated = await connectorApi.publish(id, {
        scope: "org",
        org_id: publishOrgId || undefined,
      })
      setConnectors((prev) => prev.map((c) => (c.id === id ? updated : c)))
      toast.success(t("connectorPublished"))
    } catch {
      toast.error(t("connectorPublishFailed"))
    }
  }

  const confirmUnpublish = async () => {
    if (!pendingUnpublishId) return
    const id = pendingUnpublishId
    setPendingUnpublishId(null)
    try {
      const updated = await connectorApi.unpublish(id)
      setConnectors((prev) => prev.map((c) => (c.id === id ? updated : c)))
      toast.success(t("connectorUnpublished"))
    } catch {
      toast.error(t("connectorUnpublishFailed"))
    }
  }

  if (authLoading || !user) return null

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 shrink-0 border-b border-border/40">
        <div>
          <h1 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Plug className="h-5 w-5" />
            {t("title")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t("subtitle")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeTab === "connectors" && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="sm" className="gap-1.5">
                  <Plus className="h-4 w-4" />
                  {t("newConnector")}
                  <ChevronDown className="h-3 w-3 opacity-60" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem asChild>
                  <Link href="/connectors/new">
                    <Globe className="h-4 w-4" />
                    {t("newApiConnector")}
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/connectors/new?type=database">
                    <Database className="h-4 w-4" />
                    {t("newDatabaseConnector")}
                  </Link>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
          {activeTab === "mcp" && (
            <>
              <Button variant="outline" size="sm" className="gap-1.5" onClick={() => mcpActionsRef.current?.openHub()}>
                <LayoutGrid className="h-4 w-4" />
                {tt("mcpCatalog")}
              </Button>
              <Button size="sm" className="gap-1.5" onClick={() => mcpActionsRef.current?.openAdd()}>
                <Plus className="h-4 w-4" />
                {tt("addServer")}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="flex flex-col flex-1 overflow-hidden">
        <div className="px-6 pt-4 shrink-0">
          <TabsList>
            <TabsTrigger value="connectors">{t("connectorsTab")}</TabsTrigger>
            <TabsTrigger value="mcp">{t("mcpTab")}</TabsTrigger>
          </TabsList>
        </div>

        {/* Connectors tab */}
        <TabsContent value="connectors" className="flex-1 overflow-y-auto p-6 mt-0">
          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton.ConnectorCard key={i} />
              ))}
            </div>
          ) : connectors.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <p className="text-sm text-muted-foreground">
                {t("emptyState")}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4 gap-1.5"
                asChild
              >
                <Link href="/connectors/new">
                  <Plus className="h-4 w-4" />
                  {t("createConnector")}
                </Link>
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {connectors.map((connector) => (
                <ConnectorCard
                  key={connector.id}
                  connector={connector}
                  currentUserId={user.id}
                  onDelete={handleDelete}
                  onPublish={handlePublish}
                  onUnpublish={handleUnpublish}
                  onResubmit={handleResubmit}
                />
              ))}
            </div>
          )}
        </TabsContent>

        {/* MCP Servers tab */}
        <TabsContent value="mcp" className="flex-1 overflow-y-auto px-6 py-4 mt-0">
          <MCPServersSection onReady={(actions) => { mcpActionsRef.current = actions }} />
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation */}
      <Dialog open={pendingDeleteId !== null} onOpenChange={(open) => { if (!open) setPendingDeleteId(null) }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Trash2 className="h-4 w-4" />
              {t("deleteConnectorTitle")}
            </DialogTitle>
            <DialogDescription>
              {t("deleteConnectorDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" className="px-6" onClick={() => setPendingDeleteId(null)}>{tc("cancel")}</Button>
            <Button variant="destructive" className="px-6" onClick={confirmDelete}>{tc("delete")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Publish Confirmation */}
      <Dialog open={pendingPublishId !== null} onOpenChange={(open) => { if (!open) setPendingPublishId(null) }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{tc("publish")}</DialogTitle>
            <DialogDescription>
              {t("subtitle")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-sm font-medium">{tc("publish")}</Label>
              <div className="flex gap-2">
                {(["personal", "org"] as const).map((scope) => (
                  <button
                    key={scope}
                    type="button"
                    onClick={() => {
                      setPublishScope(scope)
                      if (scope === "org" && userOrgs.length > 0) setPublishOrgId(userOrgs[0].id)
                    }}
                    className={`flex-1 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                      publishScope === scope
                        ? "border-primary bg-primary/10 text-primary font-medium"
                        : "border-input text-muted-foreground hover:border-foreground/30"
                    }`}
                  >
                    {scope === "personal" ? tc("draft") : tc("publish")}
                  </button>
                ))}
              </div>
            </div>
            {publishScope === "org" && (
              <div className="space-y-2">
                {orgsLoading ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  </div>
                ) : userOrgs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">{tc("unpublished")}</p>
                ) : (
                  <Select value={publishOrgId} onValueChange={setPublishOrgId}>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {userOrgs.map((org) => (
                        <SelectItem key={org.id} value={org.id}>{org.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" className="px-6" onClick={() => setPendingPublishId(null)}>{tc("cancel")}</Button>
            <Button
              className="px-6"
              onClick={confirmPublish}
              disabled={publishScope === "org" && (orgsLoading || userOrgs.length === 0 || !publishOrgId)}
            >
              {tc("publish")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Unpublish Confirmation */}
      <Dialog open={pendingUnpublishId !== null} onOpenChange={(open) => { if (!open) setPendingUnpublishId(null) }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{tc("unpublish")}</DialogTitle>
            <DialogDescription>
              {t("subtitle")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" className="px-6" onClick={() => setPendingUnpublishId(null)}>{tc("cancel")}</Button>
            <Button variant="secondary" className="px-6" onClick={confirmUnpublish}>{tc("unpublish")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default function ConnectorsPage() {
  return (
    <Suspense fallback={null}>
      <ConnectorsPageInner />
    </Suspense>
  )
}
