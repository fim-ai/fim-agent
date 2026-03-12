"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"
import { Bot, MoreHorizontal, Pencil, Trash2, Globe, GlobeLock, MessageSquare, Radar } from "lucide-react"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { AgentResponse } from "@/types/agent"

interface AgentCardProps {
  agent: AgentResponse
  onDelete: (id: string) => void
  onPublish: (id: string) => void
  onUnpublish: (id: string) => void
}

export function AgentCard({
  agent,
  onDelete,
  onPublish,
  onUnpublish,
}: AgentCardProps) {
  const t = useTranslations("agents")
  const tc = useTranslations("common")
  const isPublished = agent.status === "published"
  const isDiscoverable = agent.discoverable === true

  return (
    <div className="group flex flex-col rounded-lg border border-border bg-card p-4 transition-colors hover:border-ring/40 hover:bg-accent/10">
      {/* Header: name + hover menu */}
      <div className="flex items-center gap-2 mb-1.5">
        <h3 className="flex-1 min-w-0 text-sm font-medium truncate text-card-foreground flex items-center gap-1.5">
          {agent.icon ? (
            <span className="shrink-0 text-base leading-none">{agent.icon}</span>
          ) : (
            <Bot className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
          {agent.name}
        </h3>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className="shrink-0 text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100 transition-opacity"
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link href={`/agents/${agent.id}`}>
                <Pencil className="h-4 w-4" />
                {tc("edit")}
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => isPublished ? onUnpublish(agent.id) : onPublish(agent.id)}>
              {isPublished ? <GlobeLock className="h-4 w-4" /> : <Globe className="h-4 w-4" />}
              {isPublished ? tc("unpublish") : tc("publish")}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={() => onDelete(agent.id)}>
              <Trash2 className="h-4 w-4" />
              {tc("delete")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Status badge */}
      <div className="flex items-center gap-1.5 mb-2">
        <Badge
          variant="secondary"
          className={cn(
            "text-[10px] px-1.5 py-0 h-5",
            isPublished
              ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
              : "opacity-60"
          )}
        >
          {isPublished ? tc("published") : tc("draft")}
        </Badge>
        {isDiscoverable && (
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-5 bg-violet-500/15 text-violet-600 dark:text-violet-400 border-violet-500/20"
          >
            <Radar className="h-2.5 w-2.5 mr-0.5" />
            {t("discoverable")}
          </Badge>
        )}
      </div>

      {/* Description */}
      <p className="flex-1 text-xs text-muted-foreground line-clamp-2 mb-3">
        {agent.description || t("noDescription")}
      </p>

      {/* Start Chat CTA — when published */}
      {isPublished && (
        <Button
          variant="outline"
          size="sm"
          className="mt-3 w-full gap-1.5 text-xs h-7"
          asChild
        >
          <Link href={`/new?agent=${agent.id}`}>
            <MessageSquare className="h-3 w-3" />
            {t("startChat")}
          </Link>
        </Button>
      )}
    </div>
  )
}
