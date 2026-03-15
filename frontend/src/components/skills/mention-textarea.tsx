"use client"

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type KeyboardEvent,
  type ChangeEvent,
} from "react"
import { useTranslations } from "next-intl"
import { Cable, Server, BookOpen, Bot } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import type { ResourceRef, ResourceRefType } from "@/types/skill"

interface MentionTextareaProps {
  id?: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  resourceRefs: ResourceRef[]
}

const TYPE_ICONS: Record<ResourceRefType, React.ReactNode> = {
  connector: <Cable className="h-3.5 w-3.5" />,
  mcp_server: <Server className="h-3.5 w-3.5" />,
  knowledge_base: <BookOpen className="h-3.5 w-3.5" />,
  agent: <Bot className="h-3.5 w-3.5" />,
}

/**
 * A textarea that shows a dropdown of resource aliases when the user types `@`.
 * This is a simple autocomplete -- not a rich text editor.
 */
export function MentionTextarea({
  id,
  value,
  onChange,
  placeholder,
  className,
  resourceRefs,
}: MentionTextareaProps) {
  const t = useTranslations("skills")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const [showDropdown, setShowDropdown] = useState(false)
  const [mentionQuery, setMentionQuery] = useState("")
  const [mentionStart, setMentionStart] = useState(-1)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 })

  // Compute filtered suggestions
  const suggestions = resourceRefs.filter((ref) => {
    if (!mentionQuery) return true
    const q = mentionQuery.toLowerCase()
    return (
      ref.alias.toLowerCase().includes(q) ||
      ref.name.toLowerCase().includes(q)
    )
  })

  // Calculate caret position for dropdown placement
  const updateDropdownPosition = useCallback(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    // Create a hidden mirror element to measure caret position
    const mirror = document.createElement("div")
    const style = window.getComputedStyle(textarea)
    const properties = [
      "fontFamily", "fontSize", "fontWeight", "lineHeight", "letterSpacing",
      "wordSpacing", "textIndent", "whiteSpace", "wordWrap", "overflowWrap",
      "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
      "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth",
    ] as const

    mirror.style.position = "absolute"
    mirror.style.visibility = "hidden"
    mirror.style.width = `${textarea.clientWidth}px`
    mirror.style.height = "auto"

    for (const prop of properties) {
      mirror.style[prop] = style[prop]
    }

    const textBefore = value.slice(0, textarea.selectionStart)
    mirror.textContent = textBefore

    // Add a span at the caret position
    const span = document.createElement("span")
    span.textContent = "|"
    mirror.appendChild(span)

    document.body.appendChild(mirror)
    const rect = textarea.getBoundingClientRect()
    const spanRect = span.getBoundingClientRect()
    const mirrorRect = mirror.getBoundingClientRect()

    const relativeTop = spanRect.top - mirrorRect.top
    const relativeLeft = spanRect.left - mirrorRect.left

    setDropdownPosition({
      top: relativeTop + parseInt(style.lineHeight || "20") + 4 - textarea.scrollTop,
      left: Math.min(relativeLeft, rect.width - 240),
    })

    document.body.removeChild(mirror)
  }, [value])

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value
      onChange(newValue)

      const cursorPos = e.target.selectionStart
      // Look backward from cursor for an "@" that starts a mention
      const textBefore = newValue.slice(0, cursorPos)
      const lastAt = textBefore.lastIndexOf("@")

      if (lastAt >= 0) {
        // Check that @ is at start of line, start of text, or preceded by whitespace
        const charBefore = lastAt > 0 ? textBefore[lastAt - 1] : " "
        if (charBefore === " " || charBefore === "\n" || charBefore === "\t" || lastAt === 0) {
          const query = textBefore.slice(lastAt + 1)
          // Only show dropdown if the query has no whitespace (still typing the alias)
          if (!/\s/.test(query) && query.length <= 30) {
            setMentionStart(lastAt)
            setMentionQuery(query)
            setShowDropdown(true)
            setSelectedIndex(0)
            return
          }
        }
      }

      setShowDropdown(false)
    },
    [onChange],
  )

  // Update dropdown position when it appears
  useEffect(() => {
    if (showDropdown) {
      updateDropdownPosition()
    }
  }, [showDropdown, updateDropdownPosition])

  const insertMention = useCallback(
    (ref: ResourceRef) => {
      const textarea = textareaRef.current
      if (!textarea || mentionStart < 0) return

      const before = value.slice(0, mentionStart)
      const cursorPos = textarea.selectionStart
      const after = value.slice(cursorPos)

      const aliasText = ref.alias + " "
      const newValue = before + aliasText + after
      onChange(newValue)
      setShowDropdown(false)

      // Restore cursor position after the inserted alias
      requestAnimationFrame(() => {
        const newPos = mentionStart + aliasText.length
        textarea.focus()
        textarea.setSelectionRange(newPos, newPos)
      })
    },
    [value, mentionStart, onChange],
  )

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (!showDropdown || suggestions.length === 0) return

      if (e.key === "ArrowDown") {
        e.preventDefault()
        setSelectedIndex((prev) => (prev + 1) % suggestions.length)
      } else if (e.key === "ArrowUp") {
        e.preventDefault()
        setSelectedIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length)
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault()
        insertMention(suggestions[selectedIndex])
      } else if (e.key === "Escape") {
        e.preventDefault()
        setShowDropdown(false)
      }
    },
    [showDropdown, suggestions, selectedIndex, insertMention],
  )

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!showDropdown) return
    const handler = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [showDropdown])

  return (
    <div className="relative">
      <Textarea
        ref={textareaRef}
        id={id}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={className}
      />

      {/* Hint text */}
      {resourceRefs.length > 0 && (
        <p className="text-[11px] text-muted-foreground mt-1">
          {t("mentionHint")}
        </p>
      )}

      {/* Mention dropdown */}
      {showDropdown && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-60 rounded-md border border-border/60 bg-popover/95 backdrop-blur-md shadow-lg overflow-hidden"
          style={{
            top: dropdownPosition.top,
            left: Math.max(0, dropdownPosition.left),
          }}
        >
          <div className="max-h-[180px] overflow-y-auto py-1">
            {suggestions.map((ref, index) => (
              <button
                key={`${ref.type}:${ref.id}`}
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault() // Prevent textarea blur
                  insertMention(ref)
                }}
                onMouseEnter={() => setSelectedIndex(index)}
                className={`flex items-center gap-2 w-full px-2.5 py-1.5 text-sm text-left transition-colors ${
                  index === selectedIndex
                    ? "bg-accent text-accent-foreground"
                    : "text-popover-foreground hover:bg-accent/50"
                }`}
              >
                <span className="text-muted-foreground shrink-0">
                  {TYPE_ICONS[ref.type]}
                </span>
                <span className="font-mono text-primary font-medium shrink-0 text-xs">
                  {ref.alias}
                </span>
                <span className="text-muted-foreground truncate text-xs">
                  {ref.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
