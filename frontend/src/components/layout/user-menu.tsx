"use client"

import { LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAuth } from "@/contexts/auth-context"

interface UserMenuProps {
  collapsed: boolean
}

export function UserMenu({ collapsed }: UserMenuProps) {
  const { user, logout } = useAuth()

  if (!user) return null

  const initial = user.username.charAt(0).toUpperCase()

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2">
        <Avatar className="h-7 w-7">
          <AvatarFallback className="bg-primary/10 text-xs text-primary">
            {initial}
          </AvatarFallback>
        </Avatar>
        <button
          onClick={logout}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          title="Logout"
        >
          <LogOut className="h-3.5 w-3.5" />
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Avatar className="h-7 w-7 shrink-0">
        <AvatarFallback className="bg-primary/10 text-xs text-primary">
          {initial}
        </AvatarFallback>
      </Avatar>
      <span className="flex-1 truncate text-xs text-muted-foreground">
        {user.username}
      </span>
      <button
        onClick={logout}
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
          "text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors",
        )}
        title="Logout"
      >
        <LogOut className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
