"use client"

import { useTheme } from "next-themes"
import { Toaster } from "sonner"

export function ThemedToaster() {
  const { resolvedTheme } = useTheme()
  return (
    <Toaster
      theme={(resolvedTheme as "light" | "dark" | undefined) ?? "system"}
      position="top-center"
      richColors
    />
  )
}
