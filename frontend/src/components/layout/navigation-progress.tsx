"use client"

import { usePathname } from "next/navigation"
import { useEffect, useRef, useState } from "react"

export function NavigationProgress() {
  const pathname = usePathname()
  const [phase, setPhase] = useState<"idle" | "loading" | "done">("idle")
  const prevPathname = useRef(pathname)
  const doneTimer = useRef<ReturnType<typeof setTimeout>>()
  const safetyTimer = useRef<ReturnType<typeof setTimeout>>()

  // Detect link clicks to start the bar immediately
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const anchor = (e.target as Element).closest("a[href]")
      if (!anchor) return
      const href = anchor.getAttribute("href") ?? ""
      // Skip external, hash, protocol, download, and same-page links
      if (
        !href ||
        href.startsWith("http") ||
        href.startsWith("//") ||
        href.startsWith("#") ||
        href.startsWith("mailto:") ||
        href.startsWith("javascript:") ||
        href.startsWith("blob:") ||
        href.startsWith("data:") ||
        anchor.hasAttribute("download")
      ) return
      const targetPath = href.split("?")[0].split("#")[0]
      if (targetPath === window.location.pathname) return

      clearTimeout(safetyTimer.current)
      setPhase("loading")
      // Safety: auto-cancel if navigation takes too long
      safetyTimer.current = setTimeout(() => setPhase("idle"), 10000)
    }

    document.addEventListener("click", handleClick, true)
    return () => document.removeEventListener("click", handleClick, true)
  }, [])

  // Detect navigation completion via pathname change
  useEffect(() => {
    if (pathname === prevPathname.current) return
    prevPathname.current = pathname

    clearTimeout(safetyTimer.current)
    clearTimeout(doneTimer.current)
    setPhase("done")
    doneTimer.current = setTimeout(() => setPhase("idle"), 500)
  }, [pathname])

  if (phase === "idle") return null

  return (
    <div className="fixed top-0 left-0 right-0 z-[9999] h-[2px] pointer-events-none">
      <div className={phase === "loading" ? "nav-bar-loading" : "nav-bar-done"} />
    </div>
  )
}
