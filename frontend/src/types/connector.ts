export interface ConnectorActionResponse {
  id: string
  connector_id: string
  name: string
  description: string | null
  method: string // GET | POST | PUT | DELETE
  path: string
  parameters_schema: Record<string, unknown> | null
  request_body_template: Record<string, unknown> | null
  response_extract: string | null
  requires_confirmation: boolean
  created_at: string
  updated_at: string | null
}

export interface ConnectorActionCreate {
  name: string
  description?: string | null
  method?: string
  path: string
  parameters_schema?: Record<string, unknown> | null
  request_body_template?: Record<string, unknown> | null
  response_extract?: string | null
  requires_confirmation?: boolean
}

export interface ConnectorActionUpdate {
  name?: string
  description?: string | null
  method?: string
  path?: string
  parameters_schema?: Record<string, unknown> | null
  request_body_template?: Record<string, unknown> | null
  response_extract?: string | null
  requires_confirmation?: boolean
}

export interface ConnectorResponse {
  id: string
  name: string
  description: string | null
  icon: string | null
  type: string // "api" | "database"
  base_url: string
  auth_type: string // "api_key" | "bearer" | "oauth2" | "basic" | "none"
  auth_config: Record<string, unknown> | null
  status: string // "draft" | "published"
  is_official: boolean
  forked_from: string | null
  version: number
  actions: ConnectorActionResponse[]
  created_at: string
  updated_at: string | null
}

export interface ConnectorCreate {
  name: string
  description?: string | null
  icon?: string | null
  type?: string
  base_url: string
  auth_type?: string
  auth_config?: Record<string, unknown> | null
}

export interface ConnectorUpdate {
  name?: string
  description?: string | null
  icon?: string | null
  type?: string
  base_url?: string
  auth_type?: string
  auth_config?: Record<string, unknown> | null
}
