export interface AdminUser {
  id: string
  username: string
  display_name: string | null
  email: string | null
  is_admin: boolean
  is_active: boolean
  created_at: string
  has_active_session: boolean
  monthly_tokens: number
  token_quota: number | null
}

export interface IntegrationHealth {
  key: string
  label: string
  configured: boolean
  detail: string | null
}

export interface AdminConversation {
  id: string
  title: string | null
  mode: string | null
  model_name: string | null
  total_tokens: number
  message_count: number
  user_id: string
  username: string
  created_at: string
}

export interface UserStorageStat {
  user_id: string
  username: string
  file_count: number
  total_bytes: number
}

export interface StorageStats {
  total_bytes: number
  users: UserStorageStat[]
}

export interface InviteCode {
  id: string
  code: string
  note: string | null
  max_uses: number
  use_count: number
  expires_at: string | null
  is_active: boolean
  created_at: string
}

export interface AdminMCPServer {
  id: string
  name: string
  description: string | null
  transport: string
  command: string | null
  args: string[] | null
  url: string | null
  is_active: boolean
  is_global: boolean
  tool_count: number
  created_at: string
}
