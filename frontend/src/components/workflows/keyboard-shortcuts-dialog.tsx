"use client"

import { useTranslations } from "next-intl"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface KeyboardShortcutsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.userAgent)
const MOD = isMac ? "\u2318" : "Ctrl"

const shortcuts = [
  { section: "general" as const, items: [
    { keys: [`${MOD}+S`], action: "save" },
    { keys: [`${MOD}+F`], action: "search" },
    { keys: [`${MOD}+Z`], action: "undo" },
    { keys: [`${MOD}+Shift+Z`, `${MOD}+Y`], action: "redo" },
    { keys: ["Escape"], action: "deselect" },
    { keys: ["?"], action: "shortcuts" },
  ]},
  { section: "selection" as const, items: [
    { keys: [`${MOD}+A`], action: "selectAll" },
    { keys: [`${MOD}+C`], action: "copy" },
    { keys: [`${MOD}+V`], action: "paste" },
    { keys: [`${MOD}+D`], action: "duplicate" },
    { keys: ["Delete", "Backspace"], action: "delete" },
  ]},
]

export function KeyboardShortcutsDialog({ open, onOpenChange }: KeyboardShortcutsDialogProps) {
  const t = useTranslations("workflows")

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[400px]">
        <DialogHeader>
          <DialogTitle className="text-sm">{t("shortcutsTitle")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-2">
          {shortcuts.map((section) => (
            <div key={section.section}>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {t(`shortcutsSection_${section.section}` as Parameters<typeof t>[0])}
              </h4>
              <div className="space-y-1.5">
                {section.items.map((item) => (
                  <div key={item.action} className="flex items-center justify-between">
                    <span className="text-xs text-foreground">
                      {t(`shortcutsAction_${item.action}` as Parameters<typeof t>[0])}
                    </span>
                    <div className="flex items-center gap-1">
                      {item.keys.map((key, i) => (
                        <span key={key}>
                          {i > 0 && <span className="text-[10px] text-muted-foreground mx-0.5">/</span>}
                          <kbd className="text-[10px] font-mono bg-muted px-1.5 py-0.5 rounded border border-border text-muted-foreground">
                            {key}
                          </kbd>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
