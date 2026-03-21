// Provider
export interface ModelProviderResponse {
  id: string
  name: string
  base_url: string | null
  has_api_key: boolean // Never expose actual key
  is_active: boolean
  models: ModelProviderModelResponse[]
  created_at: string
  updated_at: string | null
}

export interface ModelProviderCreate {
  name: string
  base_url?: string
  api_key?: string
  is_active?: boolean
}

export type ModelProviderUpdate = Partial<ModelProviderCreate>

// Provider Model (child of Provider)
export interface ModelProviderModelResponse {
  id: string
  provider_id?: string // May be omitted when nested under a provider response
  name: string // Display name: "DeepSeek V3"
  model_name: string // API identifier: "deepseek-chat"
  temperature: number | null
  max_output_tokens: number | null
  context_size: number | null
  json_mode_enabled: boolean
  tool_choice_enabled: boolean
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface ModelProviderModelCreate {
  name: string
  model_name: string
  temperature?: number
  max_output_tokens?: number
  context_size?: number
  json_mode_enabled?: boolean
  tool_choice_enabled?: boolean
}

export type ModelProviderModelUpdate = Partial<
  ModelProviderModelCreate & { is_active: boolean }
>

// Model Group (Profile)
export interface ModelGroupResponse {
  id: string
  name: string
  description: string | null
  general_model_id: string | null
  fast_model_id: string | null
  reasoning_model_id: string | null
  general_model: ModelSlotInfo | null
  fast_model: ModelSlotInfo | null
  reasoning_model: ModelSlotInfo | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface ModelSlotInfo {
  id: string
  name: string
  model_name: string
  provider_name: string
  is_available: boolean
}

export interface ModelGroupCreate {
  name: string
  description?: string
  general_model_id?: string
  fast_model_id?: string
  reasoning_model_id?: string
}

export type ModelGroupUpdate = Partial<ModelGroupCreate>

// Active Configuration
export interface ModelActiveConfig {
  mode: "env" | "group"
  active_group: { id: string; name: string } | null
  effective: {
    general: EffectiveModel
    fast: EffectiveModel
    reasoning: EffectiveModel
  }
  env_fallback: EnvFallbackInfo
}

export interface EffectiveModel {
  model_name: string
  provider_name: string | null
  source: "group" | "env"
}

export interface EnvFallbackInfo {
  llm_model: string
  llm_base_url: string
  fast_llm_model: string
  fast_llm_base_url: string
  reasoning_llm_model: string
  reasoning_llm_base_url: string
  has_api_key: boolean
  has_fast_api_key: boolean
  has_reasoning_api_key: boolean
}

// List responses
export interface ModelProvidersListResponse {
  providers: ModelProviderResponse[]
  total: number
}

export interface ModelGroupsListResponse {
  groups: ModelGroupResponse[]
  env_fallback: EnvFallbackInfo
  active_group_id: string | null
}
