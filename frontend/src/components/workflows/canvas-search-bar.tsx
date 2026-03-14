"use client"

import { useCallback, useEffect, useRef } from "react"
import { Search, ChevronUp, ChevronDown, X } from "lucide-react"
import { useTranslations } from "next-intl"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface CanvasSearchBarProps {
  open: boolean
  query: string
  matchCount: number
  currentIndex: number
  onQueryChange: (query: string) => void
  onNext: () => void
  onPrev: () => void
  onClose: () => void
}

export function CanvasSearchBar({
  open,
  query,
  matchCount,
  currentIndex,
  onQueryChange,
  onNext,
  onPrev,
  onClose,
}: CanvasSearchBarProps) {
  const t = useTranslations("workflows")
  const inputRef = useRef<HTMLInputElement>(null)

  // Focus the input when search opens
  useEffect(() => {
    if (open) {
      // Small delay to let the element render
      requestAnimationFrame(() => {
        inputRef.current?.focus()
        inputRef.current?.select()
      })
    }
  }, [open])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault()
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key === "Enter") {
        e.preventDefault()
        if (e.shiftKey) {
          onPrev()
        } else {
          onNext()
        }
        return
      }
      if (e.key === "ArrowDown") {
        e.preventDefault()
        onNext()
        return
      }
      if (e.key === "ArrowUp") {
        e.preventDefault()
        onPrev()
        return
      }
    },
    [onClose, onNext, onPrev],
  )

  if (!open) return null

  return (
    <div
      className={cn(
        "absolute top-3 left-1/2 -translate-x-1/2 z-50",
        "flex items-center gap-1.5 rounded-lg border border-border bg-card/95 backdrop-blur-sm shadow-lg px-2 py-1.5",
        "animate-in fade-in-0 slide-in-from-top-2 duration-150",
      )}
    >
      <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
      <Input
        ref={inputRef}
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("canvasSearchPlaceholder")}
        className="h-7 w-52 border-0 shadow-none text-xs focus-visible:outline-none px-1"
      />
      {query.length > 0 && (
        <span className="text-[11px] text-muted-foreground whitespace-nowrap tabular-nums shrink-0">
          {matchCount > 0
            ? t("canvasSearchCount", { current: currentIndex + 1, total: matchCount })
            : t("canvasSearchNoResults")}
        </span>
      )}
      <div className="flex items-center gap-0.5 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onPrev}
          disabled={matchCount === 0}
          tabIndex={-1}
        >
          <ChevronUp className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onNext}
          disabled={matchCount === 0}
          tabIndex={-1}
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onClose}
          tabIndex={-1}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
