"use client"

import { Badge } from "@/components/ui/badge"

const BUILTIN_TOOLS = [
  { category: "Computation", tools: ["calculator -- arithmetic & math", "python_exec -- run Python in sandbox"] },
  { category: "Web", tools: ["web_fetch -- read web pages", "web_search -- search the web"] },
  { category: "Filesystem", tools: ["file_ops -- read/write/list files"] },
  { category: "Knowledge", tools: ["kb_retrieve / grounded_retrieve -- retrieval from knowledge bases"] },
]

export function BuiltinToolsSection() {
  return (
    <div className="flex flex-wrap gap-4">
      {BUILTIN_TOOLS.map((group) => (
        <div
          key={group.category}
          className="flex flex-col rounded-lg border border-border bg-card p-4 min-w-[220px] flex-1"
        >
          <h3 className="text-sm font-medium text-card-foreground mb-3">
            {group.category}
          </h3>
          <div className="flex flex-col gap-1.5">
            {group.tools.map((tool) => {
              const [name, desc] = tool.split(" -- ")
              return (
                <div key={tool} className="flex items-start gap-2">
                  <Badge variant="secondary" className="shrink-0 text-xs font-mono">
                    {name}
                  </Badge>
                  {desc && (
                    <span className="text-xs text-muted-foreground pt-0.5">{desc}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
