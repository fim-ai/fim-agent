import { apiFetch } from "./api"

interface BuilderSession {
  builder_agent_id: string
}

export const builderApi = {
  createSession: (body: { target_type: string; target_id: string }) =>
    apiFetch<BuilderSession>("/api/builder/session", {
      method: "POST",
      body: JSON.stringify(body),
    }),
}
