"use client"

import { useState } from "react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import {
  Calculator,
  Clock,
  Code2,
  Globe,
  Search,
  Network,
  Files,
  Terminal,
  Library,
  Database,
  Sparkles,
  Plug,
  Server,
  ArrowRight,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"

interface ToolEntry {
  name: string
  description: string
  note?: string
  category: string
}

interface ToolCategory {
  category: string
  tools: ToolEntry[]
}

const BUILTIN_TOOLS: ToolCategory[] = [
  {
    category: "General",
    tools: [
      {
        name: "datetime",
        description: "Get the current date, time, and weekday. Supports any IANA timezone (e.g. UTC, Asia/Shanghai).",
        category: "General",
      },
    ],
  },
  {
    category: "Computation",
    tools: [
      {
        name: "calculator",
        description: "Safe AST-based math expression evaluation — add, sub, mul, div, pow, sqrt, sin, cos, log, …",
        category: "Computation",
      },
      {
        name: "python_exec",
        description: "Execute Python code in a sandboxed namespace; stdout/stderr captured; supports file I/O and most stdlib",
        category: "Computation",
      },
      {
        name: "shell_exec",
        description: "Run shell commands in a sandboxed directory; blocked: sudo, rm -rf /, network reconfig, dangerous binaries",
        category: "Computation",
      },
    ],
  },
  {
    category: "Web",
    tools: [
      {
        name: "web_fetch",
        description: "Fetch a URL and return clean Markdown via Jina Reader (r.jina.ai)",
        category: "Web",
      },
      {
        name: "web_search",
        description: "Search the web and return ranked results via Jina Search (s.jina.ai)",
        category: "Web",
      },
      {
        name: "http_request",
        description: "Send arbitrary HTTP requests (GET/POST/PUT/DELETE/PATCH) to REST APIs; SSRF-protected",
        category: "Web",
      },
    ],
  },
  {
    category: "Filesystem",
    tools: [
      {
        name: "file_ops",
        description: "Sandboxed file operations within a per-conversation workspace",
        note: "read · write · append · delete · list · mkdir · exists · get_info · read_json · write_json · read_csv · write_csv · find_replace",
        category: "Filesystem",
      },
    ],
  },
  {
    category: "Knowledge",
    tools: [
      {
        name: "kb_list",
        description: "List all knowledge bases available to the current user (id, name, description, doc count)",
        category: "Knowledge",
      },
      {
        name: "kb_retrieve",
        description: "Basic vector retrieval from knowledge bases — returns top-K chunks by relevance score",
        category: "Knowledge",
      },
      {
        name: "grounded_retrieve",
        description: "5-stage grounding pipeline: multi-KB retrieve → citation extraction → alignment scoring → conflict detection → confidence scoring",
        category: "Knowledge",
      },
    ],
  },
]

const ALL_TOOLS: ToolEntry[] = BUILTIN_TOOLS.flatMap((g) => g.tools)

const CATEGORIES = ["All", "General", "Computation", "Web", "Filesystem", "Knowledge", "Connector", "MCP"] as const
type CategoryFilter = (typeof CATEGORIES)[number]

const TOOL_ICONS: Record<string, LucideIcon> = {
  datetime: Clock,
  calculator: Calculator,
  python_exec: Code2,
  web_fetch: Globe,
  web_search: Search,
  http_request: Network,
  file_ops: Files,
  shell_exec: Terminal,
  kb_list: Library,
  kb_retrieve: Database,
  grounded_retrieve: Sparkles,
}

const CATEGORY_ICON_COLOR: Record<string, string> = {
  General: "text-muted-foreground",
  Computation: "text-blue-500",
  Web: "text-green-500",
  Filesystem: "text-orange-500",
  Knowledge: "text-purple-500",
}

function ToolCard({ tool }: { tool: ToolEntry }) {
  const Icon = TOOL_ICONS[tool.name]
  const iconColor = CATEGORY_ICON_COLOR[tool.category] ?? "text-muted-foreground"

  return (
    <div className="rounded-lg border border-border bg-card p-4 flex flex-col gap-2 hover:border-border/80 hover:bg-accent/30 transition-colors">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          {Icon && <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} />}
          <Badge variant="secondary" className="shrink-0 text-xs font-mono">
            {tool.name}
          </Badge>
        </div>
        <Badge variant="outline" className="shrink-0 text-xs text-muted-foreground">
          {tool.category}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">
        {tool.description}
      </p>
      {tool.note && (
        <p className="font-mono text-xs text-muted-foreground/60 leading-relaxed">
          {tool.note}
        </p>
      )}
    </div>
  )
}

function ConnectorLinkCard() {
  return (
    <Link href="/connectors" className="block group">
      <div className="rounded-lg border border-dashed border-border bg-card p-4 flex flex-col gap-2 hover:border-primary/50 hover:bg-accent/30 transition-colors">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Plug className="h-4 w-4 shrink-0 text-cyan-500" />
            <Badge variant="secondary" className="shrink-0 text-xs font-mono">
              connector
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="shrink-0 text-xs text-muted-foreground">
              Connector
            </Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground/50 group-hover:text-primary transition-colors" />
          </div>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Custom HTTP API actions bound to this agent. Managed on the Connectors page.
        </p>
      </div>
    </Link>
  )
}

function MCPLinkCard({ onSwitch }: { onSwitch: () => void }) {
  return (
    <button onClick={onSwitch} className="text-left w-full group">
      <div className="rounded-lg border border-dashed border-border bg-card p-4 flex flex-col gap-2 hover:border-primary/50 hover:bg-accent/30 transition-colors">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Server className="h-4 w-4 shrink-0 text-indigo-500" />
            <Badge variant="secondary" className="shrink-0 text-xs font-mono">
              mcp
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="shrink-0 text-xs text-muted-foreground">
              MCP
            </Badge>
            <ArrowRight className="h-3 w-3 text-muted-foreground/50 group-hover:text-primary transition-colors" />
          </div>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Tools provided by external MCP servers. Configure them in the MCP Servers tab.
        </p>
      </div>
    </button>
  )
}

interface BuiltinToolsSectionProps {
  onSwitchToMCP: () => void
}

export function BuiltinToolsSection({ onSwitchToMCP }: BuiltinToolsSectionProps) {
  const [activeCategory, setActiveCategory] = useState<CategoryFilter>("All")

  const showConnector = activeCategory === "All" || activeCategory === "Connector"
  const showMCP = activeCategory === "All" || activeCategory === "MCP"

  const filteredTools =
    activeCategory === "All" || activeCategory === "Connector" || activeCategory === "MCP"
      ? activeCategory === "All"
        ? ALL_TOOLS
        : []
      : ALL_TOOLS.filter((t) => t.category === activeCategory)

  return (
    <div className="flex flex-col gap-4">
      {/* Category filter chips */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeCategory === cat
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Tool cards grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {filteredTools.map((tool) => (
          <ToolCard key={tool.name} tool={tool} />
        ))}
        {showConnector && <ConnectorLinkCard />}
        {showMCP && <MCPLinkCard onSwitch={onSwitchToMCP} />}
      </div>
    </div>
  )
}
