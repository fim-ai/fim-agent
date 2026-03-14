import { useCallback } from "react"
import { useLocalStorage } from "./use-local-storage"
import type { WorkflowNodeType } from "@/types/workflow"

const STORAGE_KEY = "fim-workflow-recent-nodes"
const MAX_RECENT = 5

export function useRecentNodes() {
  const [recentNodes, setRecentNodes] = useLocalStorage<WorkflowNodeType[]>(
    STORAGE_KEY,
    [],
  )

  const addRecentNode = useCallback(
    (nodeType: WorkflowNodeType) => {
      setRecentNodes((prev) => {
        const filtered = prev.filter((t) => t !== nodeType)
        return [nodeType, ...filtered].slice(0, MAX_RECENT)
      })
    },
    [setRecentNodes],
  )

  return { recentNodes, addRecentNode }
}
