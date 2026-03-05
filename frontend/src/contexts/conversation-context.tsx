"use client"

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react"
import { conversationApi, ApiError } from "@/lib/api"
import { useAuth } from "./auth-context"
import type {
  ConversationResponse,
  ConversationDetail,
} from "@/types/conversation"

interface ConversationContextValue {
  conversations: ConversationResponse[]
  activeConversation: ConversationDetail | null
  activeId: string | null
  isLoadingList: boolean
  isLoadingDetail: boolean
  loadConversations: () => Promise<void>
  selectConversation: (id: string) => Promise<void>
  createConversation: (
    mode: "react" | "dag",
    title?: string,
    agentId?: string,
  ) => Promise<ConversationResponse>
  deleteConversation: (id: string) => Promise<void>
  updateTitle: (id: string, title: string) => Promise<void>
  toggleStar: (id: string) => Promise<void>
  batchDeleteConversations: (ids: string[]) => Promise<void>
  clearActive: () => void
}

const ConversationContext = createContext<ConversationContextValue | null>(null)

export function ConversationProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const { user } = useAuth()
  const [conversations, setConversations] = useState<ConversationResponse[]>([])
  const [activeConversation, setActiveConversation] =
    useState<ConversationDetail | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [isLoadingList, setIsLoadingList] = useState(false)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)

  const loadConversations = useCallback(async () => {
    setIsLoadingList(true)
    try {
      const res = await conversationApi.list(1, 20)
      setConversations(res.items)
    } catch (err) {
      console.error("Failed to load conversations:", err)
    } finally {
      setIsLoadingList(false)
    }
  }, [])

  // Load when user changes
  useEffect(() => {
    if (user) {
      loadConversations()
    } else {
      setConversations([])
      setActiveConversation(null)
      setActiveId(null)
    }
  }, [user, loadConversations])

  const selectConversation = useCallback(async (id: string) => {
    setActiveId(id)
    setIsLoadingDetail(true)
    try {
      const detail = await conversationApi.get(id)
      setActiveConversation(detail)
    } catch (err) {
      setActiveId(null)
      setActiveConversation(null)
      if (err instanceof ApiError && err.status === 404) {
        // Conversation was deleted — prune stale entry from sidebar list
        setConversations((prev) => prev.filter((c) => c.id !== id))
      } else {
        console.error("Failed to load conversation:", err)
      }
    } finally {
      setIsLoadingDetail(false)
    }
  }, [])

  const createConversation = useCallback(
    async (mode: "react" | "dag", title?: string, agentId?: string) => {
      const conv = await conversationApi.create({ mode, title, agent_id: agentId })
      setConversations((prev) => [conv, ...prev])
      setActiveId(conv.id)
      setActiveConversation({ ...conv, messages: [] })
      return conv
    },
    [],
  )

  const deleteConversation = useCallback(
    async (id: string) => {
      await conversationApi.delete(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (activeId === id) {
        setActiveConversation(null)
        setActiveId(null)
      }
    },
    [activeId],
  )

  const updateTitle = useCallback(
    async (id: string, title: string) => {
      await conversationApi.update(id, { title })
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title } : c)),
      )
      if (activeConversation?.id === id) {
        setActiveConversation((prev) => (prev ? { ...prev, title } : prev))
      }
    },
    [activeConversation?.id],
  )

  const toggleStar = useCallback(async (id: string) => {
    const conv = conversations.find((c) => c.id === id)
    if (!conv) return
    const updated = await conversationApi.update(id, { starred: !conv.starred })
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, starred: updated.starred } : c)),
    )
  }, [conversations])

  const batchDeleteConversations = useCallback(
    async (ids: string[]) => {
      await conversationApi.batchDelete(ids)
      setConversations((prev) => prev.filter((c) => !ids.includes(c.id)))
      if (activeId && ids.includes(activeId)) {
        setActiveConversation(null)
        setActiveId(null)
      }
    },
    [activeId],
  )

  const clearActive = useCallback(() => {
    setActiveConversation(null)
    setActiveId(null)
  }, [])

  return (
    <ConversationContext.Provider
      value={{
        conversations,
        activeConversation,
        activeId,
        isLoadingList,
        isLoadingDetail,
        loadConversations,
        selectConversation,
        createConversation,
        deleteConversation,
        updateTitle,
        toggleStar,
        batchDeleteConversations,
        clearActive,
      }}
    >
      {children}
    </ConversationContext.Provider>
  )
}

export function useConversation() {
  const ctx = useContext(ConversationContext)
  if (!ctx)
    throw new Error("useConversation must be used within ConversationProvider")
  return ctx
}
