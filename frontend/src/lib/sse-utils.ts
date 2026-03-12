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

/**
 * Detect the execution mode of a turn from its SSE events.
 * DAG turns emit step_progress / phase (planning/executing/analyzing) events;
 * React turns emit step events.
 */
export function detectTurnMode(sseMessages: SSEMessage[]): "react" | "dag" {
  for (const m of sseMessages) {
    if (m.event === "step_progress") return "dag"
    if (m.event === "phase") {
      const d = m.data as Record<string, unknown>
      if (d.name === "planning" || d.name === "executing" || d.name === "analyzing") return "dag"
    }
    if (m.event === "step") return "react"
  }
  return "react" // fallback
}
