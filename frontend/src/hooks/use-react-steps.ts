import { useMemo } from "react"
import type { SSEMessage } from "@/hooks/use-sse"
import type { ReactStepEvent, ReactDoneEvent } from "@/types/api"

export interface StepItem {
  event: string
  data: unknown
  duration?: number
  displayIteration?: number
  timestamp?: number
}

export function useReactSteps(messages: SSEMessage[], isRunning: boolean): StepItem[] {
  return useMemo(() => {
    const result: StepItem[] = []
    let iterCount = 0
    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i]

      if (msg.event === "step") {
        const step = msg.data as ReactStepEvent

        // When a tool_call (complete) arrives, merge with its matching tool_start
        if (step.type === "tool_call") {
          const startIdx = result.findIndex(item => {
            const d = item.data as ReactStepEvent
            return d.type === "tool_start"
              && d.iteration === step.iteration
              && d.tool_name === step.tool_name
          })
          if (startIdx !== -1) {
            // Prefer server-side iter_elapsed (LLM + tool), fallback to client diff
            const clientDuration = (msg.timestamp - (result[startIdx].timestamp ?? msg.timestamp)) / 1000
            result[startIdx] = {
              event: msg.event,
              data: msg.data,
              duration: step.iter_elapsed ?? clientDuration,
              displayIteration: result[startIdx].displayIteration,
              timestamp: msg.timestamp,
            }
            continue
          }
        }
      }

      // Calculate duration: time between this event and the next event
      let duration: number | undefined
      if (msg.event === "done") {
        // Use server-side iter_elapsed for the final iteration
        const done = msg.data as ReactDoneEvent
        duration = done.iter_elapsed
      } else if (i + 1 < messages.length) {
        duration = (messages[i + 1].timestamp - msg.timestamp) / 1000
      }

      // Sequential display iteration for step events
      let displayIteration: number | undefined
      if (msg.event === "step") {
        iterCount++
        displayIteration = iterCount
      }

      result.push({ event: msg.event, data: msg.data, duration, displayIteration, timestamp: msg.timestamp })
    }
    // When still running after a completed tool_call (no done yet), append a
    // synthetic "thinking" step so the user sees an active indicator while the
    // LLM processes tool results.
    const hasDone = result.some(item => item.event === "done")
    if (isRunning && !hasDone && result.length > 0) {
      const last = result[result.length - 1]
      if (last.event === "step") {
        const lastStep = last.data as ReactStepEvent
        if (lastStep.type === "tool_call") {
          iterCount++
          result.push({
            event: "step",
            data: { type: "thinking", iteration: (lastStep.iteration ?? 0) + 1 } as ReactStepEvent,
            displayIteration: iterCount,
            timestamp: Date.now(),
          })
        }
      }
    }

    // When aborted (not running, no done event), convert remaining tool_start
    // items to tool_call so spinners and "Executing..." indicators stop.
    if (!isRunning && !hasDone && result.length > 0) {
      return result.map(item => {
        if (item.event === "step") {
          const step = item.data as ReactStepEvent
          if (step.type === "tool_start") {
            return { ...item, data: { ...step, type: "tool_call" as const } }
          }
        }
        return item
      })
    }

    // After completion, drop empty thinking steps — they were only useful as
    // live animated placeholders during streaming.
    if (hasDone) {
      return result.filter(item => {
        if (item.event !== "step") return true
        const step = item.data as ReactStepEvent
        return step.type !== "thinking" || !!step.reasoning
      })
    }

    return result
  }, [messages, isRunning])
}
