"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  Play,
  Bot,
  Database,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { APP_NAME, APP_VERSION } from "@/lib/constants"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  disabled?: boolean
  tooltip?: string
}

const navItems: NavItem[] = [
  {
    label: "Playground",
    href: "/",
    icon: <Play className="h-4 w-4" />,
  },
  {
    label: "Agents",
    href: "/agents",
    icon: <Bot className="h-4 w-4" />,
    disabled: true,
    tooltip: "Coming in v0.5",
  },
  {
    label: "Knowledge Base",
    href: "/knowledge",
    icon: <Database className="h-4 w-4" />,
    disabled: true,
    tooltip: "Coming in v0.4",
  },
  {
    label: "Settings",
    href: "/settings",
    icon: <Settings className="h-4 w-4" />,
    disabled: true,
    tooltip: "Coming in v0.7",
  },
]

function getPageTitle(pathname: string): string {
  const item = navItems.find((i) => i.href === pathname)
  return item?.label ?? "FIM Agent"
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()
  const pageTitle = getPageTitle(pathname)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "flex flex-col border-r border-border bg-sidebar transition-all duration-200",
          collapsed ? "w-16" : "w-60"
        )}
      >
        {/* Logo area */}
        <div className="flex h-14 items-center gap-2 px-4">
          <img src="/fim-mark.svg" alt="FIM" className="h-6 w-auto shrink-0" />
          {!collapsed && (
            <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
              {APP_NAME}
            </span>
          )}
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-2 py-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href
            const linkContent = (
              <span
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground",
                  item.disabled &&
                    "pointer-events-none cursor-not-allowed opacity-50"
                )}
              >
                {item.icon}
                {!collapsed && <span>{item.label}</span>}
              </span>
            )

            if (item.disabled && item.tooltip) {
              return (
                <Tooltip key={item.href} delayDuration={0}>
                  <TooltipTrigger asChild>
                    <div className="cursor-not-allowed">{linkContent}</div>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>{item.tooltip}</p>
                  </TooltipContent>
                </Tooltip>
              )
            }

            return (
              <Link key={item.href} href={item.href}>
                {linkContent}
              </Link>
            )
          })}
        </nav>

        {/* Bottom area */}
        <div className="space-y-2 px-3 pb-4">
          <Separator />
          <div className="flex items-center justify-between pt-2">
            {!collapsed && (
              <Badge variant="secondary" className="text-xs font-normal">
                v{APP_VERSION}
              </Badge>
            )}
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              {collapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <ChevronLeft className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-background px-6">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-semibold text-foreground">
              {pageTitle}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="bg-muted text-xs text-muted-foreground">
                U
              </AvatarFallback>
            </Avatar>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
