"use client"

import { useMemo } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { MarkdownContent } from "@/lib/markdown"
import { Loader2, Wrench, Brain, CheckCircle2, AlertCircle } from "lucide-react"
import type { SSEMessage } from "@/hooks/use-sse"
import type { ReactStepEvent, ReactDoneEvent } from "@/types/api"

interface ReactOutputProps {
  messages: SSEMessage[]
  isRunning: boolean
}

export function ReactOutput({ messages, isRunning }: ReactOutputProps) {
  const items = useMemo(() => {
    return messages.map((msg) => ({
      event: msg.event,
      data: msg.data,
    }))
  }, [messages])

  if (items.length === 0 && !isRunning) {
    return null
  }

  return (
    <div className="space-y-3">
      {items.map((item, idx) => {
        if (item.event === "step") {
          const step = item.data as ReactStepEvent
          return <StepCard key={idx} step={step} />
        }
        if (item.event === "done") {
          const done = item.data as ReactDoneEvent
          return <DoneCard key={idx} done={done} />
        }
        return null
      })}
      {isRunning && items.length > 0 && (
        <div className="flex items-center gap-2 px-1 text-sm text-muted-foreground animate-pulse">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Processing...</span>
        </div>
      )}
    </div>
  )
}

function StepCard({ step }: { step: ReactStepEvent }) {
  if (step.type === "thinking") {
    return (
      <Card className="animate-in fade-in-0 slide-in-from-bottom-2 duration-300 border-amber-500/20 py-4">
        <CardContent className="flex items-start gap-3">
          <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber-500/10">
            <Brain className="h-3.5 w-3.5 text-amber-500" />
          </div>
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className="border-amber-500/30 text-amber-500 text-[10px] uppercase tracking-wider"
              >
                Thinking
              </Badge>
              <span className="text-xs text-muted-foreground">
                Iteration {step.iteration}
              </span>
            </div>
            {step.reasoning && (
              <p className="text-sm italic text-muted-foreground leading-relaxed">
                {step.reasoning}
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (step.type === "tool_call") {
    return (
      <Card className="animate-in fade-in-0 slide-in-from-bottom-2 duration-300 border-blue-500/20 py-4">
        <CardContent className="flex items-start gap-3">
          <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-500/10">
            <Wrench className="h-3.5 w-3.5 text-blue-500" />
          </div>
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                variant="outline"
                className="border-blue-500/30 text-blue-500 text-[10px] uppercase tracking-wider"
              >
                Tool
              </Badge>
              <span className="text-sm font-medium text-foreground">
                {step.tool_name}
              </span>
              <span className="text-xs text-muted-foreground">
                Iteration {step.iteration}
              </span>
            </div>
            {step.reasoning && (
              <p className="text-sm italic text-muted-foreground leading-relaxed">
                {step.reasoning}
              </p>
            )}
            {step.tool_args && Object.keys(step.tool_args).length > 0 && (
              <pre className="overflow-x-auto rounded-md bg-muted/50 p-3 text-xs font-mono leading-relaxed">
                {JSON.stringify(step.tool_args, null, 2)}
              </pre>
            )}
            {step.observation && (
              <div className="rounded-md border border-border/50 bg-muted/30 p-3">
                <p className="text-xs font-medium text-muted-foreground mb-1 uppercase tracking-wider">
                  Observation
                </p>
                <pre className="whitespace-pre-wrap text-sm text-foreground/90 font-mono leading-relaxed">
                  {step.observation}
                </pre>
              </div>
            )}
            {step.error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3">
                <div className="flex items-center gap-1.5 mb-1">
                  <AlertCircle className="h-3 w-3 text-destructive" />
                  <p className="text-xs font-medium text-destructive uppercase tracking-wider">
                    Error
                  </p>
                </div>
                <pre className="whitespace-pre-wrap text-sm text-destructive/90 font-mono">
                  {step.error}
                </pre>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return null
}

function DoneCard({ done }: { done: ReactDoneEvent }) {
  return (
    <Card className="animate-in fade-in-0 slide-in-from-bottom-2 duration-300 border-green-500/20 py-4">
      <CardHeader className="pb-0">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-green-500/10">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
          </div>
          <CardTitle className="text-sm">Result</CardTitle>
          <div className="ml-auto flex items-center gap-2">
            <Badge variant="secondary" className="text-[10px]">
              {done.iterations} iteration{done.iterations !== 1 ? "s" : ""}
            </Badge>
            <Badge variant="secondary" className="text-[10px]">
              {done.elapsed.toFixed(1)}s
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <MarkdownContent
          content={done.answer}
          className="prose-sm text-sm text-foreground/90"
        />
      </CardContent>
    </Card>
  )
}
