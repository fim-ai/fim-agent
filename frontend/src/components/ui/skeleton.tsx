import { cn } from "@/lib/utils"
import { Card, CardContent } from "@/components/ui/card"

// ── Primitive ──────────────────────────────────────────────────────────
function SkeletonPrimitive({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />
  )
}

// ── StatCard — dashboard watermark stat card ────────────────────────────
function SkeletonStatCard() {
  return (
    <Card className="overflow-hidden relative py-3 gap-0">
      <CardContent className="px-5 space-y-1.5 relative z-10">
        <SkeletonPrimitive className="h-3 w-20" />
        <SkeletonPrimitive className="h-7 w-16 mt-1" />
        <SkeletonPrimitive className="h-3 w-24" />
      </CardContent>
      <SkeletonPrimitive className="absolute -bottom-3 -right-3 h-20 w-20 rounded-full opacity-30" />
    </Card>
  )
}

// ── ChartBars — animated bar columns, no card wrapper ──────────────────
function SkeletonChartBars({ count = 14, height = 200 }: { count?: number; height?: number }) {
  return (
    <div className="flex items-end gap-2" style={{ height }}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonPrimitive
          key={i}
          className="flex-1 rounded-sm"
          style={{ height: `${20 + Math.sin(i * 0.9) * 40 + 40}px` }}
        />
      ))}
    </div>
  )
}

// ── ListRow — icon + text + timestamp
//   twoLines=true: left side shows name + sub-label (e.g. connector rows)
//   twoLines=false (default): single text line (e.g. conversation rows) ──
function SkeletonListRow({ twoLines = false }: { twoLines?: boolean }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2">
      <SkeletonPrimitive className="h-8 w-8 shrink-0 rounded-lg" />
      {twoLines ? (
        <div className="flex-1 space-y-1">
          <SkeletonPrimitive className="h-4 w-2/3" />
          <SkeletonPrimitive className="h-3 w-1/3" />
        </div>
      ) : (
        <SkeletonPrimitive className="h-4 flex-1" />
      )}
      <SkeletonPrimitive className="h-3 w-14 shrink-0" />
    </div>
  )
}

// ── AgentCard — bordered grid card with icon + name + badge line ────────
function SkeletonAgentCard() {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border p-3">
      <SkeletonPrimitive className="h-8 w-8 shrink-0 rounded-lg" />
      <div className="flex-1 space-y-1.5">
        <SkeletonPrimitive className="h-4 w-3/4" />
        <SkeletonPrimitive className="h-3 w-1/2" />
      </div>
    </div>
  )
}

// ── KbCard — bordered grid card with name + two badge pills ─────────────
function SkeletonKbCard() {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
      <SkeletonPrimitive className="h-4 w-3/4" />
      <div className="flex gap-2">
        <SkeletonPrimitive className="h-4 w-16 rounded-full" />
        <SkeletonPrimitive className="h-4 w-16 rounded-full" />
      </div>
    </div>
  )
}

// ── ConnectorCard — same structure as AgentCard, icon(rounded-lg) + name + type ─
function SkeletonConnectorCard() {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-border p-4">
      <SkeletonPrimitive className="h-8 w-8 shrink-0 rounded-lg" />
      <div className="flex-1 space-y-1.5">
        <SkeletonPrimitive className="h-4 w-2/3" />
        <SkeletonPrimitive className="h-3 w-1/3" />
      </div>
    </div>
  )
}

// ── ArtifactCard — square thumbnail area + filename + meta ───────────────────
function SkeletonArtifactCard() {
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <SkeletonPrimitive className="aspect-square w-full rounded-none" />
      <div className="px-3 py-2 space-y-1">
        <SkeletonPrimitive className="h-4 w-3/4" />
        <SkeletonPrimitive className="h-3 w-1/3" />
      </div>
    </div>
  )
}

// ── TableRow — checkbox + filename + type badge + status badge + date ─────────
function SkeletonTableRow() {
  return (
    <div className="flex items-center gap-4 px-4 py-3 border-b last:border-b-0">
      <SkeletonPrimitive className="h-4 w-4 shrink-0 rounded" />
      <SkeletonPrimitive className="h-4 flex-1" />
      <SkeletonPrimitive className="h-4 w-16 shrink-0" />
      <SkeletonPrimitive className="h-5 w-14 shrink-0 rounded-full" />
      <SkeletonPrimitive className="h-4 w-20 shrink-0" />
    </div>
  )
}

// ── WorkflowCard — bordered grid card with icon + name + badge line ─────
function SkeletonWorkflowCard() {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-4">
      <div className="flex items-center gap-2">
        <SkeletonPrimitive className="h-4 w-4 shrink-0 rounded" />
        <SkeletonPrimitive className="h-4 w-3/4" />
      </div>
      <div className="flex gap-2">
        <SkeletonPrimitive className="h-4 w-14 rounded-full" />
        <SkeletonPrimitive className="h-4 w-16 rounded-full" />
      </div>
      <SkeletonPrimitive className="h-3 w-full" />
      <SkeletonPrimitive className="h-3 w-2/3" />
      <SkeletonPrimitive className="h-7 w-full mt-2 rounded-md" />
    </div>
  )
}

// ── Export ─────────────────────────────────────────────────────────────
const Skeleton = Object.assign(SkeletonPrimitive, {
  StatCard: SkeletonStatCard,
  ChartBars: SkeletonChartBars,
  ListRow: SkeletonListRow,
  AgentCard: SkeletonAgentCard,
  KbCard: SkeletonKbCard,
  ConnectorCard: SkeletonConnectorCard,
  ArtifactCard: SkeletonArtifactCard,
  TableRow: SkeletonTableRow,
  WorkflowCard: SkeletonWorkflowCard,
})

export { Skeleton }
