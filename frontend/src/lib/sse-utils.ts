import type { SSEMessage } from "@/hooks/use-sse"
import type { MessageResponse } from "@/types/conversation"

/**
 * Reconstruct SSEMessage[] from a persisted assistant message's metadata.
 * Returns null if the message has no stored sse_events (old format).
 */
export function reconstructSSEMessages(msg: MessageResponse): SSEMessage[] | null {
  const events = msg.metadata?.sse_events as Array<{ event: string; data: unknown }> | undefined
  if (!events?.length) return null
  return events.map((e) => ({
    event: e.event,
    data: e.data,
    timestamp: 0,
  }))
}
