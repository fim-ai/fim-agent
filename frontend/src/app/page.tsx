"use client"

import { useState, useCallback, useRef, useEffect, useMemo } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Loader2, Trash2, PanelRightOpen, PanelRightClose, ArrowDown, Square, Zap, GitBranch, User } from "lucide-react"
import { useSSE } from "@/hooks/use-sse"
import { useDagSteps } from "@/hooks/use-dag-steps"
import { useReactSteps } from "@/hooks/use-react-steps"
import { useMediaQuery } from "@/hooks/use-media-query"
import { useLocalStorage } from "@/hooks/use-local-storage"
import { useAuth } from "@/contexts/auth-context"
import { useConversation } from "@/contexts/conversation-context"
import { API_BASE_URL } from "@/lib/constants"
import { cn } from "@/lib/utils"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { ReactOutput } from "@/components/playground/react-output"
import { DagOutput } from "@/components/playground/dag-output"
import { Examples } from "@/components/playground/examples"
import { RightSidebar } from "@/components/playground/right-sidebar"
import { ReactSidebarTimeline } from "@/components/playground/react-sidebar-timeline"
import { DagFlowGraph } from "@/components/dag/dag-flow-graph"
import { HistoryMessages } from "@/components/playground/history-messages"
import { reconstructSSEMessages } from "@/lib/sse-utils"
import type { SSEMessage } from "@/hooks/use-sse"
import type { MessageResponse } from "@/types/conversation"
import type { AgentMode, Language } from "@/components/playground/examples"

export default function PlaygroundPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const {
    activeConversation,
    activeId,
    createConversation,
    selectConversation,
    loadConversations,
    clearActive,
  } = useConversation()

  const [mode, setMode] = useState<AgentMode>("react")
  const [query, setQuery] = useState("")
  const [language, setLanguage] = useState<Language>("en")
  const [sourceMode, setSourceMode] = useState<AgentMode | null>(null)
  const [pendingQuery, setPendingQuery] = useState<string | null>(null)
  const [pendingMode, setPendingMode] = useState<AgentMode | null>(null)
  const { messages, isRunning, start, reset, abort } = useSSE()

  // Ref to track conversation IDs we created ourselves (via send),
  // so the "switch conversation" effect doesn't reset SSE for them.
  const selfCreatedIdRef = useRef<string | null>(null)

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login")
    }
  }, [authLoading, user, router])

  // URL → state: on mount, if ?c=<id> is in URL, select that conversation
  const initializedRef = useRef(false)
  useEffect(() => {
    if (initializedRef.current || authLoading || !user) return
    initializedRef.current = true
    const cParam = searchParams.get("c")
    if (cParam && cParam !== activeId) {
      selectConversation(cParam)
    }
  }, [authLoading, user]) // eslint-disable-line react-hooks/exhaustive-deps

  // State → URL: sync activeId to URL search param (use history API to avoid RSC flight request)
  // Skip the first run — on mount activeId is null but URL may have ?c=xxx from direct navigation
  const urlSyncSkipRef = useRef(true)
  useEffect(() => {
    if (!initializedRef.current) return
    if (urlSyncSkipRef.current) {
      urlSyncSkipRef.current = false
      return
    }
    const url = activeId ? `/?c=${activeId}` : "/"
    const currentUrl = window.location.pathname + window.location.search
    if (url !== currentUrl) {
      window.history.replaceState(null, "", url)
    }
  }, [activeId])

  // When user clicks a DIFFERENT conversation in sidebar, sync mode and reset SSE.
  // Skip if we just created this conversation ourselves (selfCreatedIdRef).
  const prevActiveIdRef = useRef<string | null>(null)
  useEffect(() => {
    if (activeConversation && activeConversation.id !== prevActiveIdRef.current) {
      // Skip reset if this is a conversation we just created via send
      if (activeConversation.id === selfCreatedIdRef.current) {
        selfCreatedIdRef.current = null
        prevActiveIdRef.current = activeConversation.id
        return
      }
      setMode(activeConversation.mode as AgentMode)
      reset()
      setQuery("")
      setSourceMode(null)
      setPendingQuery(null)
    }
    if (activeConversation) {
      prevActiveIdRef.current = activeConversation.id
    }
  }, [activeConversation?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  // When active conversation is cleared (new chat), reset everything
  useEffect(() => {
    if (!activeId && prevActiveIdRef.current !== null) {
      reset()
      setQuery("")
      setSourceMode(null)
      setPendingQuery(null)
      prevActiveIdRef.current = null
    }
  }, [activeId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Refresh conversation list when SSE completes (keep live state for sidebar)
  const sseJustFinishedRef = useRef(false)
  useEffect(() => {
    if (isRunning) {
      sseJustFinishedRef.current = true
    } else if (sseJustFinishedRef.current) {
      sseJustFinishedRef.current = false
      loadConversations()
    }
  }, [isRunning]) // eslint-disable-line react-hooks/exhaustive-deps

  const runWithQuery = useCallback(
    async (q: string) => {
      const trimmed = q.trim()
      if (!trimmed || isRunning) return

      // Clear input and show user message immediately
      setQuery("")
      setPendingQuery(trimmed)

      let convId = activeId

      // Auto-create conversation if none selected
      if (!convId) {
        try {
          const conv = await createConversation(mode, trimmed.slice(0, 60))
          convId = conv.id
          // Mark as self-created so the activeConversation effect doesn't reset SSE
          selfCreatedIdRef.current = convId
        } catch (err) {
          console.error("Failed to create conversation:", err)
          return
        }
      } else {
        // Existing conversation — refresh to get all previous messages (with sse_events)
        // so they render as history while the new turn streams live.
        await selectConversation(convId)
      }

      const endpoint = mode === "react" ? "react" : "dag"
      const url = `${API_BASE_URL}/api/${endpoint}?q=${encodeURIComponent(trimmed)}&conversation_id=${convId}`
      setSourceMode(mode)
      start(url)
    },
    [isRunning, mode, start, activeId, createConversation, selectConversation],
  )

  const handleRun = useCallback(() => {
    runWithQuery(query)
  }, [query, runWithQuery])

  const handleReset = useCallback(() => {
    reset()
    setQuery("")
    setSourceMode(null)
    setPendingQuery(null)
  }, [reset])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault()
        handleRun()
      }
    },
    [handleRun],
  )

  const handleExampleSelect = useCallback(
    (example: string) => {
      setQuery(example)
      runWithQuery(example)
    },
    [runWithQuery],
  )

  if (authLoading || !user) return null

  return (
    <div className="flex h-full flex-col">
      <PlaygroundContent
        mode={mode}
        sourceMode={sourceMode}
        query={query}
        pendingQuery={pendingQuery}
        language={language}
        messages={messages}
        isRunning={isRunning}
        activeConversation={activeConversation}
        onQueryChange={setQuery}
        onLanguageChange={setLanguage}
        onModeChange={(m) => {
          if (isRunning) return
          if (activeId) {
            setPendingMode(m)
          } else {
            setMode(m)
          }
        }}
        onRun={handleRun}
        onAbort={abort}
        onReset={handleReset}
        onKeyDown={handleKeyDown}
        onExampleSelect={handleExampleSelect}
      />

      {/* Mode switch confirmation dialog */}
      <Dialog open={pendingMode !== null} onOpenChange={(open) => { if (!open) setPendingMode(null) }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Switch to {pendingMode?.toUpperCase()} mode?</DialogTitle>
            <DialogDescription>
              This will start a new conversation. Your current conversation is saved and accessible from the sidebar.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" className="px-6" onClick={() => setPendingMode(null)}>
              Cancel
            </Button>
            <Button className="px-6" onClick={() => {
              if (pendingMode) {
                reset()
                setPendingQuery(null)
                setSourceMode(null)
                clearActive()
                setMode(pendingMode)
              }
              setPendingMode(null)
            }}>
              Switch
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

/** Renders a single history turn (user message + execution steps) using the same hooks as live mode. */
function HistoryTurn({ userContent, sseMessages, mode, hideDagGraph }: {
  userContent: string | null
  sseMessages: SSEMessage[]
  mode: "react" | "dag"
  hideDagGraph: boolean
}) {
  const reactItems = useReactSteps(sseMessages, false)
  const dagData = useDagSteps(sseMessages, false)

  return (
    <>
      {userContent && (
        <div className="flex gap-3">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
            <User className="h-3.5 w-3.5 text-primary" />
          </div>
          <div className="flex-1 pt-0.5">
            <p className="text-sm text-foreground">{userContent}</p>
          </div>
        </div>
      )}
      {mode === "react" ? (
        <ReactOutput items={reactItems} />
      ) : (
        <DagOutput
          planSteps={dagData.planSteps}
          stepStates={dagData.stepStates}
          analysisPhase={dagData.analysisPhase}
          doneEvent={dagData.doneEvent}
          currentPhase={dagData.currentPhase}
          hideDagGraph={hideDagGraph}
        />
      )}
    </>
  )
}

interface PlaygroundContentProps {
  mode: AgentMode
  sourceMode: AgentMode | null
  query: string
  pendingQuery: string | null
  language: Language
  messages: ReturnType<typeof useSSE>["messages"]
  isRunning: boolean
  activeConversation: ReturnType<typeof useConversation>["activeConversation"]
  onQueryChange: (q: string) => void
  onLanguageChange: (lang: Language) => void
  onModeChange: (mode: AgentMode) => void
  onRun: () => void
  onAbort: () => void
  onReset: () => void
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void
  onExampleSelect: (example: string) => void
}

function PlaygroundContent({
  mode,
  sourceMode,
  query,
  pendingQuery,
  language,
  messages,
  isRunning,
  activeConversation,
  onQueryChange,
  onLanguageChange,
  onModeChange,
  onRun,
  onAbort,
  onReset,
  onKeyDown,
  onExampleSelect,
}: PlaygroundContentProps) {
  const modeMatches = sourceMode === mode
  const hasLiveMessages = modeMatches && messages.length > 0
  const hasHistory = !!(activeConversation?.messages && activeConversation.messages.length > 0)
  const hasMessages = hasLiveMessages || hasHistory || !!pendingQuery
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const isNearBottomRef = useRef(true)
  const [showScrollBtn, setShowScrollBtn] = useState(false)

  // Sidebar state — persisted to localStorage
  const [sidebarOpen, setSidebarOpen] = useLocalStorage("fim-sidebar-open", true)
  const [sidebarExpanded, setSidebarExpanded] = useLocalStorage("fim-sidebar-expanded", false)
  const [customRatio, setCustomRatio] = useLocalStorage<number | null>("fim-sidebar-custom-ratio", null)
  const isWideScreen = useMediaQuery("(min-width: 1024px)")

  // Drag resize state (transient, not persisted)
  const [dragRatio, setDragRatio] = useState<number | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [resizeKey, setResizeKey] = useState(0)
  const panelContainerRef = useRef<HTMLDivElement>(null)
  const dragRatioRef = useRef<number | null>(null)

  // Priority: active drag > custom drag (persisted) > expand preset > normal preset
  const NORMAL_RATIO = 0.3
  const EXPANDED_RATIO = 0.7
  const currentRatio = dragRatio ?? customRatio ?? (sidebarExpanded ? EXPANDED_RATIO : NORMAL_RATIO)

  // Parse data at this level via hooks
  const dagData = useDagSteps(messages, isRunning)
  const reactItems = useReactSteps(messages, isRunning)

  // Reconstruct all persisted execution steps from conversation messages.
  // Available during BOTH live mode (shows previous turns) and history mode (shows all turns).
  const allHistoryTurns = useMemo(() => {
    if (!activeConversation?.messages?.length) return null
    const turns: Array<{ user: MessageResponse | null; sseMessages: SSEMessage[] }> = []
    const msgs = activeConversation.messages
    for (let i = 0; i < msgs.length; i++) {
      const msg = msgs[i]
      if (msg.role === "assistant") {
        const reconstructed = reconstructSSEMessages(msg)
        if (reconstructed) {
          const userMsg = i > 0 && msgs[i - 1].role === "user" ? msgs[i - 1] : null
          turns.push({ user: userMsg, sseMessages: reconstructed })
        }
      }
    }
    return turns.length > 0 ? turns : null
  }, [activeConversation?.messages])

  const hasRichHistory = !hasLiveMessages && allHistoryTurns !== null

  // Sidebar only shown during live streaming (history shows all turns — sidebar would mismatch)
  const showSidebar = hasLiveMessages && sidebarOpen && isWideScreen

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)

    const container = panelContainerRef.current
    if (!container) return

    const onMouseMove = (ev: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      const ratio = 1 - (ev.clientX - rect.left) / rect.width
      const clamped = Math.max(0.15, Math.min(0.85, ratio))
      dragRatioRef.current = clamped
      setDragRatio(clamped)
    }

    const onMouseUp = () => {
      if (dragRatioRef.current !== null) {
        setCustomRatio(dragRatioRef.current)
      }
      dragRatioRef.current = null
      setDragRatio(null)
      setIsDragging(false)
      setResizeKey((k) => k + 1)
      document.removeEventListener("mousemove", onMouseMove)
      document.removeEventListener("mouseup", onMouseUp)
    }

    document.addEventListener("mousemove", onMouseMove)
    document.addEventListener("mouseup", onMouseUp)
  }, [setCustomRatio])

  // Track scroll position — only auto-scroll when user is near bottom
  useEffect(() => {
    const root = scrollAreaRef.current
    if (!root) return
    const viewport = root.querySelector<HTMLElement>("[data-radix-scroll-area-viewport]")
    if (!viewport) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = viewport
      const nearBottom = scrollHeight - scrollTop - clientHeight < 80
      isNearBottomRef.current = nearBottom
      if (nearBottom) setShowScrollBtn(false)
    }

    viewport.addEventListener("scroll", handleScroll, { passive: true })
    return () => viewport.removeEventListener("scroll", handleScroll)
  }, [hasMessages])

  // Scroll the ScrollArea viewport to bottom (avoids scrollIntoView cascading to parent containers)
  const scrollViewportToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const root = scrollAreaRef.current
    if (!root) return
    const viewport = root.querySelector<HTMLElement>("[data-radix-scroll-area-viewport]")
    if (!viewport) return
    viewport.scrollTo({ top: viewport.scrollHeight, behavior })
  }, [])

  // Auto-scroll only when user is already near bottom.
  const msgCountRef = useRef(messages.length)
  useEffect(() => {
    if (messages.length <= msgCountRef.current) {
      msgCountRef.current = messages.length
      return
    }
    msgCountRef.current = messages.length
    if (isNearBottomRef.current) {
      scrollViewportToBottom()
    } else {
      setShowScrollBtn(true)
    }
  }, [messages, scrollViewportToBottom])

  // Reset scroll state on clear
  useEffect(() => {
    if (!hasMessages) {
      isNearBottomRef.current = true
      setShowScrollBtn(false)
    }
  }, [hasMessages])

  const scrollToBottom = useCallback(() => {
    scrollViewportToBottom()
    setShowScrollBtn(false)
  }, [scrollViewportToBottom])

  const scrollInViewport = useCallback((selector: string) => {
    const root = scrollAreaRef.current
    if (!root) return
    const viewport = root.querySelector<HTMLElement>("[data-radix-scroll-area-viewport]")
    if (!viewport) return
    const el = viewport.querySelector<HTMLElement>(selector)
    if (!el) return
    const elRect = el.getBoundingClientRect()
    const viewportRect = viewport.getBoundingClientRect()
    const scrollOffset = elRect.top - viewportRect.top + viewport.scrollTop
    viewport.scrollTo({ top: Math.max(0, scrollOffset - 16), behavior: "smooth" })
  }, [])

  const scrollToStep = useCallback((stepId: string) => {
    scrollInViewport(`[data-step-id="${stepId}"]`)
  }, [scrollInViewport])

  const scrollToReactItem = useCallback((idx: number) => {
    scrollInViewport(`[data-react-idx="${idx}"]`)
  }, [scrollInViewport])

  const statusText = (() => {
    if (!isRunning || !modeMatches) return null
    if (mode === "dag") {
      if (dagData.doneEvent) return null
      if (dagData.currentPhase === "planning") return "Planning..."
      if (dagData.currentPhase === "executing") return "Executing steps..."
      if (dagData.currentPhase === "analyzing") return "Analyzing..."
      return "Processing..."
    } else {
      if (reactItems.some(i => i.event === "done")) return null
      return "Processing..."
    }
  })()

  return (
    <div className="flex flex-1 flex-col overflow-hidden p-6 gap-4">
      {/* Output area / empty state */}
      {hasMessages ? (
        <div ref={panelContainerRef} className="flex flex-1 min-h-0">
          {/* Main content */}
          <div
            className={cn(
              "flex flex-col min-h-0 rounded-lg border border-border/50 bg-muted/10 overflow-hidden",
              !isDragging && "transition-all duration-300",
              !showSidebar && "flex-1 min-w-0"
            )}
            style={showSidebar ? { flex: `${1 - currentRatio} 1 0%`, minWidth: 0 } : undefined}
          >
            {/* Output header bar */}
            <div className="flex items-center shrink-0 px-4 py-3 border-b border-border/30 gap-1">
              <span className="text-sm font-medium">
                {hasLiveMessages || pendingQuery || hasRichHistory ? "Execution Log" : "History"}
              </span>
              {statusText && (
                <span className="flex items-center gap-1.5 ml-3 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span className="shiny-text">{statusText}</span>
                </span>
              )}
              <div className="flex-1" />
              {hasLiveMessages && !isRunning && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onReset}
                  className="h-7 w-7 text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
              {hasLiveMessages && isWideScreen && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="h-7 w-7 text-muted-foreground"
                >
                  {sidebarOpen ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
                </Button>
              )}
            </div>

            <div className="relative flex-1 min-h-0">
              <ScrollArea ref={scrollAreaRef} className="h-full p-4">
                <div className="min-w-0 max-w-full space-y-4">
                  {/* Previous turns from DB (shown during both live and history mode) */}
                  {allHistoryTurns?.map((turn, idx) => (
                    <HistoryTurn
                      key={idx}
                      userContent={turn.user?.content ?? null}
                      sseMessages={turn.sseMessages}
                      mode={(activeConversation?.mode as AgentMode) ?? mode}
                      hideDagGraph={showSidebar}
                    />
                  ))}
                  {/* Fallback: old messages without sse_events */}
                  {!allHistoryTurns && !hasLiveMessages && hasHistory && (
                    <HistoryMessages messages={activeConversation!.messages} />
                  )}
                  {/* Current turn: user message + live output */}
                  {pendingQuery && (
                    <div className="flex gap-3">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10">
                        <User className="h-3.5 w-3.5 text-primary" />
                      </div>
                      <div className="flex-1 pt-0.5">
                        <p className="text-sm text-foreground">{pendingQuery}</p>
                      </div>
                    </div>
                  )}
                  {hasLiveMessages && (
                    mode === "react" ? (
                      <ReactOutput items={reactItems} />
                    ) : (
                      <DagOutput
                        planSteps={dagData.planSteps}
                        stepStates={dagData.stepStates}
                        analysisPhase={dagData.analysisPhase}
                        doneEvent={dagData.doneEvent}
                        currentPhase={dagData.currentPhase}
                        hideDagGraph={showSidebar}
                      />
                    )
                  )}
                </div>
              </ScrollArea>
              {showScrollBtn && (
                <button
                  onClick={scrollToBottom}
                  className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-1.5 rounded-full border border-border/60 bg-background/90 px-3 py-1.5 text-xs text-muted-foreground shadow-md backdrop-blur-sm transition-colors hover:text-foreground hover:border-border"
                >
                  <ArrowDown className="h-3 w-3" />
                  New updates
                </button>
              )}
            </div>
          </div>

          {/* Resize handle */}
          {showSidebar && (
            <div
              className="shrink-0 w-3 cursor-col-resize flex items-center justify-center group"
              onMouseDown={handleDragStart}
            >
              <div className="w-0.5 h-8 rounded-full bg-border group-hover:bg-primary/40 group-active:bg-primary/60 transition-colors" />
            </div>
          )}

          {/* Right sidebar */}
          {showSidebar && (
            <RightSidebar
              title={mode === "dag" ? "Execution Plan" : "Steps Timeline"}
              badge={mode === "dag" ? dagData.planSteps?.length : reactItems.filter(i => i.event === "step" || i.event === "done").length}
              expanded={sidebarExpanded}
              onToggleExpand={() => { setSidebarExpanded(!sidebarExpanded); setCustomRatio(null) }}
              className={cn(!isDragging && "transition-all duration-300")}
              style={{ flex: `${currentRatio} 1 0%`, minWidth: 0 }}
            >
              {mode === "dag" ? (
                dagData.planSteps && dagData.planSteps.length > 0 ? (
                  <DagFlowGraph
                    planSteps={dagData.planSteps}
                    stepStates={dagData.stepStates}
                    mode="sidebar"
                    expanded={sidebarExpanded}
                    resizeKey={resizeKey}
                    onStepClick={scrollToStep}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                    Waiting for plan...
                  </div>
                )
              ) : (
                <ReactSidebarTimeline items={reactItems} isRunning={isRunning} onItemClick={scrollToReactItem} />
              )}
            </RightSidebar>
          )}
        </div>
      ) : (
        <div className="flex flex-1 flex-col justify-center min-h-0 w-full">
          <Examples
            mode={mode}
            language={language}
            onLanguageChange={onLanguageChange}
            onSelect={onExampleSelect}
            disabled={isRunning}
          />
        </div>
      )}

      {/* Input area — pinned to bottom */}
      <div className="shrink-0 space-y-2">
        <div className="flex items-end gap-2">
          <Textarea
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              mode === "react"
                ? "Ask the ReAct agent to solve a problem..."
                : "Describe a multi-step task for the DAG planner..."
            }
            className="min-h-[72px] max-h-[160px] resize-none"
          />
          <Button
            onClick={isRunning ? onAbort : onRun}
            disabled={!isRunning && !query.trim()}
            className="h-[72px] w-16 shrink-0"
            variant={isRunning ? "destructive" : "default"}
          >
            {isRunning ? (
              <Square className="h-4 w-4" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        {/* Mode toggle toolbar */}
        <div className="flex items-center">
          <button
            type="button"
            disabled={isRunning}
            onClick={() => onModeChange(mode === "react" ? "dag" : "react")}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors",
              "border select-none",
              isRunning && "opacity-50 cursor-not-allowed",
              mode === "react"
                ? "border-border/60 bg-muted/40 text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                : "border-blue-500/40 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20"
            )}
          >
            {mode === "react" ? (
              <Zap className="h-3 w-3" />
            ) : (
              <GitBranch className="h-3 w-3" />
            )}
            {mode === "react" ? "ReAct" : "DAG"}
          </button>
        </div>
      </div>
    </div>
  )
}
