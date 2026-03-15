"use client"

import { createContext, useContext, type ReactNode } from "react"
import type { ParsedSource } from "@/lib/evidence-utils"

const EvidenceContext = createContext<ParsedSource[]>([])

export function EvidenceProvider({ sources, children }: { sources: ParsedSource[]; children: ReactNode }) {
  return <EvidenceContext.Provider value={sources}>{children}</EvidenceContext.Provider>
}

export function useEvidenceSources(): ParsedSource[] {
  return useContext(EvidenceContext)
}
