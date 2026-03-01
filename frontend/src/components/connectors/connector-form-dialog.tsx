"use client"

import { useState, useEffect } from "react"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import type { ConnectorCreate, ConnectorUpdate, ConnectorResponse } from "@/types/connector"

interface ConnectorFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  connector: ConnectorResponse | null // null = create mode
  onSubmit: (data: ConnectorCreate | ConnectorUpdate) => Promise<void>
  isSubmitting: boolean
}

export function ConnectorFormDialog({
  open,
  onOpenChange,
  connector,
  onSubmit,
  isSubmitting,
}: ConnectorFormDialogProps) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [type, setType] = useState("api")
  const [baseUrl, setBaseUrl] = useState("")
  const [authType, setAuthType] = useState("none")
  const [headerName, setHeaderName] = useState("X-API-Key")

  // Pre-fill when editing or reset when creating
  useEffect(() => {
    if (!open) return
    if (connector) {
      setName(connector.name)
      setDescription(connector.description || "")
      setType(connector.type)
      setBaseUrl(connector.base_url)
      setAuthType(connector.auth_type)
      const hdr = connector.auth_config?.header_name
      setHeaderName(typeof hdr === "string" ? hdr : "X-API-Key")
    } else {
      setName("")
      setDescription("")
      setType("api")
      setBaseUrl("")
      setAuthType("none")
      setHeaderName("X-API-Key")
    }
  }, [open, connector])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedName = name.trim()
    const trimmedUrl = baseUrl.trim()
    if (!trimmedName || !trimmedUrl) return

    let authConfig: Record<string, unknown> | null = null
    if (authType === "api_key") {
      authConfig = { header_name: headerName.trim() || "X-API-Key" }
    }

    const data: ConnectorCreate = {
      name: trimmedName,
      description: description.trim() || null,
      type,
      base_url: trimmedUrl,
      auth_type: authType,
      ...(authConfig && { auth_config: authConfig }),
    }

    await onSubmit(data)
  }

  const isEditing = connector !== null

  const inputClass =
    "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? "Edit Connector" : "Create Connector"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-1.5">
            <label htmlFor="connector-name" className="text-sm font-medium">
              Name <span className="text-destructive">*</span>
            </label>
            <input
              id="connector-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="GitHub API"
              required
              className={inputClass}
            />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label htmlFor="connector-description" className="text-sm font-medium">
              Description
            </label>
            <textarea
              id="connector-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A brief description of this connector..."
              rows={2}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
            />
          </div>

          {/* Type */}
          <div className="space-y-1.5">
            <label htmlFor="connector-type" className="text-sm font-medium">
              Type
            </label>
            <select
              id="connector-type"
              value={type}
              onChange={(e) => setType(e.target.value)}
              className={inputClass}
            >
              <option value="api">API</option>
              <option value="database">Database</option>
            </select>
          </div>

          {/* Base URL */}
          <div className="space-y-1.5">
            <label htmlFor="connector-base-url" className="text-sm font-medium">
              Base URL <span className="text-destructive">*</span>
            </label>
            <input
              id="connector-base-url"
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://api.example.com"
              required
              className={inputClass}
            />
          </div>

          {/* Auth Type */}
          <div className="space-y-1.5">
            <label htmlFor="connector-auth-type" className="text-sm font-medium">
              Auth Type
            </label>
            <select
              id="connector-auth-type"
              value={authType}
              onChange={(e) => setAuthType(e.target.value)}
              className={inputClass}
            >
              <option value="none">None</option>
              <option value="bearer">Bearer Token</option>
              <option value="api_key">API Key</option>
              <option value="basic">Basic Auth</option>
            </select>
          </div>

          {/* Auth Config — conditional */}
          {authType === "api_key" && (
            <div className="space-y-1.5">
              <label htmlFor="connector-header-name" className="text-sm font-medium">
                Header Name
              </label>
              <input
                id="connector-header-name"
                type="text"
                value={headerName}
                onChange={(e) => setHeaderName(e.target.value)}
                placeholder="X-API-Key"
                className={inputClass}
              />
              <p className="text-xs text-muted-foreground">
                The HTTP header used to send the API key. Default: X-API-Key.
              </p>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !name.trim() || !baseUrl.trim()}>
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEditing ? "Save Changes" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
