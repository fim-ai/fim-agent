export interface ConversationResponse {
  id: string
  title: string
  mode: string
  agent_id: string | null
  status: string
  model_name: string | null
  total_tokens: number
  created_at: string
  updated_at: string | null
}

export interface MessageResponse {
  id: string
  role: string
  content: string | null
  message_type: string
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface ConversationDetail extends ConversationResponse {
  messages: MessageResponse[]
}

export interface ConversationCreate {
  title?: string
  mode: "react" | "dag"
  agent_id?: string
  model_name?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}
