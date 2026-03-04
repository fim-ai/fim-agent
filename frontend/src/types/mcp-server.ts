export interface MCPServerResponse {
  id: string
  name: string
  description: string | null
  transport: "stdio" | "sse"
  command: string | null
  args: string[] | null
  env: Record<string, string> | null
  url: string | null
  is_active: boolean
  tool_count: number
  created_at: string
  updated_at: string | null
}

export interface MCPServerCreate {
  name: string
  description?: string | null
  transport: "stdio" | "sse"
  command?: string | null
  args?: string[] | null
  env?: Record<string, string> | null
  url?: string | null
  is_active?: boolean
}

export interface MCPServerUpdate {
  name?: string
  description?: string | null
  transport?: "stdio" | "sse"
  command?: string | null
  args?: string[] | null
  env?: Record<string, string> | null
  url?: string | null
  is_active?: boolean
}
