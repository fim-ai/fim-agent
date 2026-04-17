/**
 * Channels API client.
 *
 * Wraps `/api/channels` CRUD + test-send. The backend contract is fixed in
 * `feat/roadshow-feishu-channel`; the frontend mirrors the same schema
 * (see `@/types/channel`).
 */
import { apiFetch } from "@/lib/api"
import type {
  Channel,
  ChannelCreateRequest,
  ChannelListResponse,
  ChannelTestResponse,
  ChannelUpdateRequest,
} from "@/types/channel"

export const channelsApi = {
  list: (orgId: string) => {
    const qs = new URLSearchParams({ org_id: orgId })
    return apiFetch<ChannelListResponse>(`/api/channels?${qs.toString()}`)
  },

  get: (id: string) => apiFetch<Channel>(`/api/channels/${id}`),

  create: (body: ChannelCreateRequest) =>
    apiFetch<Channel>("/api/channels", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: string, body: ChannelUpdateRequest) =>
    apiFetch<Channel>(`/api/channels/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  delete: (id: string) =>
    apiFetch<void>(`/api/channels/${id}`, { method: "DELETE" }),

  test: (id: string) =>
    apiFetch<ChannelTestResponse>(`/api/channels/${id}/test`, {
      method: "POST",
    }),
}
