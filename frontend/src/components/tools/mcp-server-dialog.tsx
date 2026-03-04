"use client"

import { useState, useEffect } from "react"
import { Loader2, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { mcpServerApi } from "@/lib/api"
import type { MCPServerResponse, MCPServerCreate, MCPServerUpdate } from "@/types/mcp-server"

interface MCPServerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  server?: MCPServerResponse | null
  onSuccess: (server: MCPServerResponse) => void
}

export function MCPServerDialog({
  open,
  onOpenChange,
  server,
  onSuccess,
}: MCPServerDialogProps) {
  const isEdit = !!server

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [transport, setTransport] = useState<"stdio" | "sse">("stdio")
  const [command, setCommand] = useState("")
  const [args, setArgs] = useState("")
  const [url, setUrl] = useState("")
  const [envPairs, setEnvPairs] = useState<Array<{ key: string; value: string }>>([])
  const [isActive, setIsActive] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  // Reset form when dialog opens or server changes
  useEffect(() => {
    if (open) {
      if (server) {
        setName(server.name)
        setDescription(server.description || "")
        setTransport(server.transport)
        setCommand(server.command || "")
        setArgs(server.args?.join(", ") || "")
        setUrl(server.url || "")
        setEnvPairs(
          server.env
            ? Object.entries(server.env).map(([key, value]) => ({ key, value }))
            : []
        )
        setIsActive(server.is_active)
      } else {
        setName("")
        setDescription("")
        setTransport("stdio")
        setCommand("")
        setArgs("")
        setUrl("")
        setEnvPairs([])
        setIsActive(true)
      }
    }
  }, [open, server])

  const addEnvPair = () => setEnvPairs((prev) => [...prev, { key: "", value: "" }])

  const removeEnvPair = (index: number) =>
    setEnvPairs((prev) => prev.filter((_, i) => i !== index))

  const updateEnvPair = (index: number, field: "key" | "value", val: string) =>
    setEnvPairs((prev) =>
      prev.map((pair, i) => (i === index ? { ...pair, [field]: val } : pair))
    )

  const handleSubmit = async () => {
    if (!name.trim()) return

    setIsSaving(true)
    try {
      const envObj =
        envPairs.length > 0
          ? Object.fromEntries(
              envPairs
                .filter((p) => p.key.trim())
                .map((p) => [p.key.trim(), p.value])
            )
          : null

      const parsedArgs =
        args.trim()
          ? args.split(",").map((a) => a.trim()).filter(Boolean)
          : null

      if (isEdit && server) {
        const body: MCPServerUpdate = {
          name: name.trim(),
          description: description.trim() || null,
          transport,
          command: transport === "stdio" ? command.trim() || null : null,
          args: transport === "stdio" ? parsedArgs : null,
          env: transport === "stdio" ? envObj : null,
          url: transport === "sse" ? url.trim() || null : null,
          is_active: isActive,
        }
        const updated = await mcpServerApi.update(server.id, body)
        onSuccess(updated)
      } else {
        const body: MCPServerCreate = {
          name: name.trim(),
          description: description.trim() || null,
          transport,
          command: transport === "stdio" ? command.trim() || null : null,
          args: transport === "stdio" ? parsedArgs : null,
          env: transport === "stdio" ? envObj : null,
          url: transport === "sse" ? url.trim() || null : null,
          is_active: isActive,
        }
        const created = await mcpServerApi.create(body)
        onSuccess(created)
      }
      onOpenChange(false)
    } catch (err) {
      console.error("Failed to save MCP server:", err)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit MCP Server" : "Add MCP Server"}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update the MCP server configuration."
              : "Configure a new MCP server connection."}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          {/* Name */}
          <div className="grid gap-1.5">
            <label className="text-sm font-medium">Name</label>
            <Input
              placeholder="e.g. filesystem-server"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Description */}
          <div className="grid gap-1.5">
            <label className="text-sm font-medium">Description</label>
            <Textarea
              placeholder="Optional description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {/* Transport */}
          <div className="grid gap-1.5">
            <label className="text-sm font-medium">Transport</label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={transport === "stdio" ? "default" : "outline"}
                size="sm"
                onClick={() => setTransport("stdio")}
              >
                STDIO
              </Button>
              <Button
                type="button"
                variant={transport === "sse" ? "default" : "outline"}
                size="sm"
                onClick={() => setTransport("sse")}
              >
                SSE
              </Button>
            </div>
          </div>

          {/* STDIO fields */}
          {transport === "stdio" && (
            <>
              <div className="grid gap-1.5">
                <label className="text-sm font-medium">Command</label>
                <Input
                  placeholder="e.g. npx or python"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <label className="text-sm font-medium">Arguments</label>
                <Input
                  placeholder="Comma-separated, e.g. -y, @modelcontextprotocol/server-filesystem, /tmp"
                  value={args}
                  onChange={(e) => setArgs(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Separate multiple arguments with commas
                </p>
              </div>
              <div className="grid gap-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Environment Variables</label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 gap-1 text-xs"
                    onClick={addEnvPair}
                  >
                    <Plus className="h-3 w-3" />
                    Add
                  </Button>
                </div>
                {envPairs.map((pair, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Input
                      placeholder="KEY"
                      className="flex-1 font-mono text-xs"
                      value={pair.key}
                      onChange={(e) => updateEnvPair(idx, "key", e.target.value)}
                    />
                    <span className="text-muted-foreground text-xs">=</span>
                    <Input
                      placeholder="value"
                      className="flex-1 text-xs"
                      value={pair.value}
                      onChange={(e) => updateEnvPair(idx, "value", e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-xs"
                      onClick={() => removeEnvPair(idx)}
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* SSE fields */}
          {transport === "sse" && (
            <div className="grid gap-1.5">
              <label className="text-sm font-medium">Server URL</label>
              <Input
                placeholder="e.g. http://localhost:3001/sse"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
          )}

          {/* Active toggle */}
          <div className="flex items-center justify-between rounded-md border border-border px-3 py-2">
            <div>
              <p className="text-sm font-medium">Active</p>
              <p className="text-xs text-muted-foreground">
                Enable this server for agent tool usage
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={isActive}
              onClick={() => setIsActive(!isActive)}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors ${
                isActive ? "bg-primary" : "bg-muted"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 rounded-full bg-background shadow-sm transition-transform ${
                  isActive ? "translate-x-[18px]" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!name.trim() || isSaving}>
            {isSaving && <Loader2 className="h-4 w-4 animate-spin mr-1.5" />}
            {isEdit ? "Save Changes" : "Add Server"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
