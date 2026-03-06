"use client"

import { useState, useRef, useEffect } from "react"
import { Sparkles, Send, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { toast } from "sonner"
import { connectorApi, ApiError } from "@/lib/api"
import type { ConnectorResponse } from "@/types/connector"

interface AIMessage {
  role: "user" | "assistant"
  content: string
}

interface AIActionPanelProps {
  connectorId: string | null
  onActionsChanged: () => void
  onConnectorUpdated?: (connector: ConnectorResponse) => void
  formDirty?: boolean
  isNewMode?: boolean
  onConnectorCreated?: (connector: ConnectorResponse) => void
}

export function AIActionPanel({
  connectorId,
  onActionsChanged,
  onConnectorUpdated,
  formDirty = false,
  isNewMode = false,
  onConnectorCreated,
}: AIActionPanelProps) {
  const [messages, setMessages] = useState<AIMessage[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (connectorId) {
      inputRef.current?.focus()
    }
  }, [connectorId])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    // In new mode (no connectorId), use AI create endpoint
    if (isNewMode && !connectorId) {
      const userMessage: AIMessage = { role: "user", content: trimmed }
      setMessages((prev) => [...prev, userMessage])
      setInput("")
      setIsLoading(true)

      try {
        const result = await connectorApi.aiCreateConnector({
          instruction: trimmed,
        })
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: result.message || "Connector created successfully." },
        ])
        toast.success("Connector created. Settings and actions have been populated.")
        onConnectorCreated?.(result.connector)
      } catch (err) {
        const errorMsg =
          err instanceof ApiError
            ? err.message
            : "Something went wrong. Please try again."
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${errorMsg}` },
        ])
      } finally {
        setIsLoading(false)
      }
      return
    }

    if (!connectorId) return

    // Block if connector form has unsaved changes
    if (formDirty) {
      toast.warning("Please save your connector settings first.")
      return
    }

    const userMessage: AIMessage = { role: "user", content: trimmed }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const result = await connectorApi.aiRefineAction(connectorId, {
        instruction: trimmed,
      })

      const parts: string[] = []
      if (result.created.length > 0) {
        parts.push(
          `Created ${result.created.length} action${result.created.length > 1 ? "s" : ""}: ${result.created.map((a) => a.name).join(", ")}`,
        )
      }
      if (result.updated.length > 0) {
        parts.push(
          `Updated ${result.updated.length} action${result.updated.length > 1 ? "s" : ""}: ${result.updated.map((a) => a.name).join(", ")}`,
        )
      }
      if (result.deleted.length > 0) {
        parts.push(
          `Deleted ${result.deleted.length} action${result.deleted.length > 1 ? "s" : ""}`,
        )
      }
      if (result.connector_updated) {
        parts.push("Connector settings updated")
        onConnectorUpdated?.(result.connector_updated)
      }

      const summary = parts.length > 0 ? parts.join(". ") + "." : result.message

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: summary },
      ])
      if (parts.length > 0) {
        toast.success("Connector modified. Check the updated settings and actions.")
      }
      onActionsChanged()
    } catch (err) {
      const errorMsg =
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again."
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${errorMsg}` },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isDisabled = !isNewMode && connectorId === null

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border shrink-0">
        <Sparkles className="h-3.5 w-3.5 text-amber-500" />
        <span className="text-sm font-medium">AI Assistant</span>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {isDisabled ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-muted-foreground text-center">
              Save the connector first to use AI assistant
            </p>
          </div>
        ) : (
          <>
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/10">
                  <Sparkles className="h-5 w-5 text-amber-500/60" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">
                    {isNewMode && !connectorId
                      ? "Describe the connector you want to create, or paste an OpenAPI spec URL."
                      : "Describe the API actions you want to create, and AI will generate them for you."}
                  </p>
                  <p className="text-xs text-muted-foreground/50">
                    {isNewMode && !connectorId
                      ? "AI will configure settings and actions"
                      : "AI will create, update, or delete actions"}
                  </p>
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={
                  msg.role === "user"
                    ? "flex justify-end"
                    : "flex justify-start"
                }
              >
                <div
                  className={
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground rounded-lg px-3 py-1.5 text-sm max-w-[85%]"
                      : "bg-muted rounded-lg px-3 py-1.5 text-sm max-w-[85%]"
                  }
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-3 py-1.5 text-sm flex items-center gap-1.5 text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input bar */}
      <div className="flex items-center gap-2 shrink-0 px-4 py-3 border-t border-border">
        <Input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isNewMode && !connectorId
            ? "e.g. Import from https://petstore.swagger.io/v2/swagger.json"
            : "e.g. Create CRUD actions for /users..."}
          disabled={isLoading || isDisabled}
          className="flex-1 h-8 text-sm"
        />
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="icon-xs"
              onClick={handleSend}
              disabled={isLoading || isDisabled || !input.trim()}
            >
              <Send className="h-3.5 w-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" sideOffset={5}>Send</TooltipContent>
        </Tooltip>
      </div>
    </div>
  )
}
