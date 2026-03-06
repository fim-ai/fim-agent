"use client"

import { useState } from "react"
import { X } from "lucide-react"
import { EmojiPicker } from "frimousse"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Button } from "@/components/ui/button"

interface EmojiPickerPopoverProps {
  value: string | null
  onChange: (emoji: string | null) => void
  fallbackIcon?: React.ReactNode
}

export function EmojiPickerPopover({
  value,
  onChange,
  fallbackIcon,
}: EmojiPickerPopoverProps) {
  const [open, setOpen] = useState(false)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="flex items-center justify-center h-9 w-9 rounded-md border border-input bg-transparent transition-colors hover:bg-accent shrink-0"
          title="Pick icon"
        >
          {value ? (
            <span className="text-xl leading-none">{value}</span>
          ) : (
            <span className="text-muted-foreground">{fallbackIcon}</span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[320px] p-0 overflow-hidden"
        align="start"
        sideOffset={8}
      >
        <div className="flex flex-col">
          <EmojiPicker.Root
            onEmojiSelect={({ emoji }) => {
              onChange(emoji)
              setOpen(false)
            }}
            className="flex flex-col h-[340px]"
          >
            <EmojiPicker.Search
              className="mx-2 mt-2 mb-1 h-8 rounded-md border border-input bg-transparent px-2.5 text-sm placeholder:text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-[-2px] focus-visible:border-ring"
              autoFocus
            />
            <EmojiPicker.Viewport className="flex-1 overflow-y-auto px-1">
              <EmojiPicker.Loading className="flex items-center justify-center h-full text-xs text-muted-foreground">
                Loading...
              </EmojiPicker.Loading>
              <EmojiPicker.Empty className="flex items-center justify-center h-full text-xs text-muted-foreground">
                No emoji found
              </EmojiPicker.Empty>
              <EmojiPicker.List
                className="select-none"
                components={{
                  CategoryHeader: ({ category, ...props }) => (
                    <div
                      {...props}
                      className="px-1 pt-2 pb-1 text-xs font-medium text-muted-foreground sticky top-0 bg-popover/95 backdrop-blur-sm"
                    >
                      {category.label}
                    </div>
                  ),
                  Row: ({ children, ...props }) => (
                    <div {...props} className="flex">{children}</div>
                  ),
                  Emoji: ({ emoji, ...props }) => (
                    <button
                      {...props}
                      type="button"
                      className="flex items-center justify-center h-8 w-8 rounded text-xl hover:bg-accent transition-colors"
                    >
                      {emoji.emoji}
                    </button>
                  ),
                }}
              />
            </EmojiPicker.Viewport>
          </EmojiPicker.Root>

          {/* Remove / clear button */}
          {value && (
            <div className="border-t border-border px-2 py-1.5">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="w-full h-7 text-xs text-muted-foreground"
                onClick={() => {
                  onChange(null)
                  setOpen(false)
                }}
              >
                <X className="h-3 w-3 mr-1" />
                Remove icon
              </Button>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
