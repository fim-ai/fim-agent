import { apiFetch } from "./api"

interface ApiResponse<T> {
  success: boolean
  data: T
  error: string | null
}

interface BuilderSession {
  builder_agent_id: string
}

export const builderApi = {
  createSession: (body: { target_type: string; target_id: string }) =>
    apiFetch<ApiResponse<BuilderSession>>("/api/builder/session", {
      method: "POST",
      body: JSON.stringify(body),
    }).then((r) => r.data),
}
