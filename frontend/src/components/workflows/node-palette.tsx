"use client"

import { useState } from "react"
import { useTranslations } from "next-intl"
import {
  Play,
  Square,
  Brain,
  GitBranch,
  MessageSquareMore,
  Bot,
  Library,
  Plug,
  Globe,
  Variable,
  FileText,
  Code,
} from "lucide-react"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { WorkflowNodeType } from "@/types/workflow"

interface NodePaletteItem {
  type: WorkflowNodeType
  icon: React.ReactNode
  color: string
}

interface NodePaletteCategory {
  key: string
  items: NodePaletteItem[]
}

const categories: NodePaletteCategory[] = [
  {
    key: "categoryFlow",
    items: [
      { type: "start", icon: <Play className="h-3.5 w-3.5" />, color: "text-green-500" },
      { type: "end", icon: <Square className="h-3.5 w-3.5" />, color: "text-red-500" },
    ],
  },
  {
    key: "categoryAI",
    items: [
      { type: "llm", icon: <Brain className="h-3.5 w-3.5" />, color: "text-blue-500" },
      { type: "questionClassifier", icon: <MessageSquareMore className="h-3.5 w-3.5" />, color: "text-teal-500" },
      { type: "agent", icon: <Bot className="h-3.5 w-3.5" />, color: "text-indigo-500" },
      { type: "knowledgeRetrieval", icon: <Library className="h-3.5 w-3.5" />, color: "text-teal-500" },
    ],
  },
  {
    key: "categoryLogic",
    items: [
      { type: "conditionBranch", icon: <GitBranch className="h-3.5 w-3.5" />, color: "text-orange-500" },
    ],
  },
  {
    key: "categoryIntegration",
    items: [
      { type: "connector", icon: <Plug className="h-3.5 w-3.5" />, color: "text-purple-500" },
      { type: "httpRequest", icon: <Globe className="h-3.5 w-3.5" />, color: "text-slate-500" },
    ],
  },
  {
    key: "categoryData",
    items: [
      { type: "variableAssign", icon: <Variable className="h-3.5 w-3.5" />, color: "text-gray-500" },
      { type: "templateTransform", icon: <FileText className="h-3.5 w-3.5" />, color: "text-amber-500" },
      { type: "codeExecution", icon: <Code className="h-3.5 w-3.5" />, color: "text-emerald-500" },
    ],
  },
]

export function NodePalette() {
  const t = useTranslations("workflows")
  const [search, setSearch] = useState("")

  const handleDragStart = (
    event: React.DragEvent,
    nodeType: WorkflowNodeType,
  ) => {
    event.dataTransfer.setData("application/reactflow-node-type", nodeType)
    event.dataTransfer.effectAllowed = "move"
  }

  const searchLower = search.toLowerCase()

  return (
    <div className="flex flex-col h-full border-r border-border/40 bg-background w-[220px]">
      <div className="px-3 pt-3 pb-2 shrink-0">
        <h3 className="text-xs font-semibold text-foreground mb-2">
          {t("paletteTitle")}
        </h3>
        <Input
          placeholder={t("paletteSearch")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-7 text-xs"
        />
      </div>
      <ScrollArea className="flex-1 min-h-0">
        <div className="px-3 pb-3 space-y-3">
          {categories.map((cat) => {
            const filtered = cat.items.filter((item) => {
              if (!searchLower) return true
              const name = t(`nodeType_${item.type}` as Parameters<typeof t>[0]).toLowerCase()
              return name.includes(searchLower) || item.type.toLowerCase().includes(searchLower)
            })
            if (filtered.length === 0) return null
            return (
              <div key={cat.key}>
                <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-1">
                  {t(cat.key as Parameters<typeof t>[0])}
                </p>
                <div className="space-y-0.5">
                  {filtered.map((item) => (
                    <div
                      key={item.type}
                      draggable
                      onDragStart={(e) => handleDragStart(e, item.type)}
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 cursor-grab active:cursor-grabbing hover:bg-accent/50 transition-colors"
                    >
                      <div className={cn("shrink-0", item.color)}>
                        {item.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-foreground truncate">
                          {t(`nodeType_${item.type}` as Parameters<typeof t>[0])}
                        </p>
                        <p className="text-[10px] text-muted-foreground/60 truncate">
                          {t(`nodeDesc_${item.type}` as Parameters<typeof t>[0])}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </ScrollArea>
    </div>
  )
}
