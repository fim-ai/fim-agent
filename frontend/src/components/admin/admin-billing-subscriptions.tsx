"use client"

import { useState, useEffect, useCallback, useRef, Suspense } from "react"
import { useTranslations } from "next-intl"
import { useRouter, useSearchParams } from "next/navigation"
import { toast } from "sonner"
import {
  Loader2,
  Search,
  MoreHorizontal,
  Eye,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { adminApi } from "@/lib/api"
import { getErrorMessage } from "@/lib/error-utils"
import { useDateFormatter } from "@/hooks/use-date-formatter"
import type { AdminBillingPlan, AdminBillingSubscription } from "@/types/admin"

// Sentinel value because Radix `<Select>` interprets "" as unset.
const ANY = "__default__"

const PAGE_SIZE = 50

// Stripe lifecycle states (subset we expect to surface in admin UI).
const KNOWN_STATUSES = [
  "active",
  "trialing",
  "past_due",
  "canceled",
  "incomplete",
  "incomplete_expired",
  "unpaid",
] as const

function statusVariant(status: string): { className: string } {
  if (status === "active" || status === "trialing") {
    return { className: "border-green-500/40 text-green-600 dark:text-green-400" }
  }
  if (status === "past_due" || status === "incomplete") {
    return { className: "border-amber-500/40 text-amber-600 dark:text-amber-400" }
  }
  return { className: "border-red-500/40 text-red-600 dark:text-red-400" }
}

function truncate(value: string, max = 16): string {
  if (value.length <= max) return value
  return value.slice(0, 6) + "…" + value.slice(-6)
}

function AdminBillingSubscriptionsContent() {
  const t = useTranslations("admin.billing.subscriptions")
  const tc = useTranslations("common")
  const tError = useTranslations("errors")
  const { formatDate } = useDateFormatter()

  const router = useRouter()
  const searchParams = useSearchParams()

  const initialStatus = searchParams.get("status") ?? ""
  const initialPlan = searchParams.get("plan") ?? ""
  const initialSearch = searchParams.get("search") ?? ""

  const [status, setStatus] = useState(initialStatus)
  const [planSlug, setPlanSlug] = useState(initialPlan)
  const [search, setSearch] = useState(initialSearch)
  const [searchInput, setSearchInput] = useState(initialSearch)

  const [items, setItems] = useState<AdminBillingSubscription[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [plans, setPlans] = useState<AdminBillingPlan[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [viewTarget, setViewTarget] = useState<AdminBillingSubscription | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ----- URL sync -----
  const syncUrl = useCallback(
    (next: { status?: string; plan?: string; search?: string }) => {
      const sp = new URLSearchParams()
      if (next.status) sp.set("status", next.status)
      if (next.plan) sp.set("plan", next.plan)
      if (next.search) sp.set("search", next.search)
      const qs = sp.toString()
      router.replace(qs ? `/admin?tab=billingSubscriptions&${qs}` : "/admin?tab=billingSubscriptions")
    },
    [router],
  )

  // ----- Debounce search input -> search state -----
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      if (searchInput !== search) {
        setSearch(searchInput)
        setOffset(0)
        syncUrl({ status, plan: planSlug, search: searchInput })
      }
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput])

  // ----- Load plan list (for filter dropdown) -----
  useEffect(() => {
    adminApi
      .listBillingPlans()
      .then(setPlans)
      .catch((err: unknown) => toast.error(getErrorMessage(err, tError)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ----- Load subscriptions -----
  const load = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await adminApi.listBillingSubscriptions({
        status: status || undefined,
        plan_slug: planSlug || undefined,
        search: search || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      setItems(data.items)
      setTotal(data.total)
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, tError))
    } finally {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, planSlug, search, offset])

  useEffect(() => {
    load()
  }, [load])

  // ----- Filter handlers -----
  const handleStatusChange = (value: string) => {
    const next = value === ANY ? "" : value
    setStatus(next)
    setOffset(0)
    syncUrl({ status: next, plan: planSlug, search })
  }

  const handlePlanChange = (value: string) => {
    const next = value === ANY ? "" : value
    setPlanSlug(next)
    setOffset(0)
    syncUrl({ status, plan: next, search })
  }

  // ----- Render -----
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold">{t("title")}</h2>
          <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="w-44">
          <Select
            value={status === "" ? ANY : status}
            onValueChange={handleStatusChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={t("filters.status")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANY}>{t("filters.allStatuses")}</SelectItem>
              {KNOWN_STATUSES.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-44">
          <Select
            value={planSlug === "" ? ANY : planSlug}
            onValueChange={handlePlanChange}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={t("filters.plan")} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANY}>{t("filters.allPlans")}</SelectItem>
              {plans.map((p) => (
                <SelectItem key={p.slug} value={p.slug}>{p.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("filters.search")}
            className="pl-9"
          />
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-md border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          {t("noSubsFound")}
        </div>
      ) : (
        <div className="rounded-md border border-border overflow-x-auto">
          <table className="w-full min-w-max text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("columns.userEmail")}</th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("columns.plan")}</th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("columns.status")}</th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("columns.periodEnd")}</th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">{t("columns.stripeSubId")}</th>
                <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">{tc("actions")}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map((s) => {
                const variant = statusVariant(s.status)
                return (
                  <tr key={s.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3 font-medium text-foreground">
                      {s.user_email ?? <span className="text-muted-foreground/60">{s.user_username ?? s.user_id}</span>}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      <span className="font-mono text-xs">{s.plan_slug}</span>
                      <span className="ml-1.5 text-muted-foreground/70">{s.plan_name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline" className={variant.className}>{s.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                      {formatDate(s.current_period_end, "--")}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                      {truncate(s.stripe_subscription_id)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setViewTarget(s)}>
                            <Eye className="mr-2 h-4 w-4" />
                            {t("actions.view")}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination + count */}
      {!isLoading && total > 0 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{t("totalCount", { count: total })}</span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
            >
              {tc("previous")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset((o) => o + PAGE_SIZE)}
            >
              {tc("next")}
            </Button>
          </div>
        </div>
      )}

      {/* --- Detail Sheet --- */}
      <Sheet open={viewTarget !== null} onOpenChange={(open) => { if (!open) setViewTarget(null) }}>
        <SheetContent className="w-full sm:max-w-xl px-6">
          <SheetHeader>
            <SheetTitle>{t("details.title")}</SheetTitle>
            <SheetDescription>
              {viewTarget?.user_email ?? viewTarget?.user_id}
            </SheetDescription>
          </SheetHeader>
          {viewTarget && (
            <div className="space-y-3 py-4 text-sm">
              <DetailRow label={t("details.user")} value={viewTarget.user_email ?? viewTarget.user_username ?? viewTarget.user_id} />
              <DetailRow label={t("details.plan")} value={`${viewTarget.plan_name} (${viewTarget.plan_slug})`} />
              <DetailRow
                label={t("details.status")}
                value={<Badge variant="outline" className={statusVariant(viewTarget.status).className}>{viewTarget.status}</Badge>}
              />
              <DetailRow
                label={t("details.stripeSubscriptionId")}
                value={<span className="font-mono text-xs break-all">{viewTarget.stripe_subscription_id}</span>}
              />
              <DetailRow
                label={t("details.stripePriceId")}
                value={<span className="font-mono text-xs break-all">{viewTarget.stripe_price_id}</span>}
              />
              <DetailRow
                label={t("details.currentPeriodStart")}
                value={formatDate(viewTarget.current_period_start, "--")}
              />
              <DetailRow
                label={t("details.currentPeriodEnd")}
                value={formatDate(viewTarget.current_period_end, "--")}
              />
              <DetailRow
                label={t("details.cancelAtPeriodEnd")}
                value={viewTarget.cancel_at_period_end ? t("details.yes") : t("details.no")}
              />
              <DetailRow
                label={t("details.canceledAt")}
                value={viewTarget.canceled_at ? formatDate(viewTarget.canceled_at, "--") : t("details.notCanceled")}
              />
              <DetailRow label={t("details.createdAt")} value={formatDate(viewTarget.created_at, "--")} />
              <DetailRow label={t("details.updatedAt")} value={formatDate(viewTarget.updated_at, "--")} />
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-3 items-start">
      <div className="text-muted-foreground">{label}</div>
      <div className="col-span-2 break-words">{value}</div>
    </div>
  )
}

export function AdminBillingSubscriptions() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    }>
      <AdminBillingSubscriptionsContent />
    </Suspense>
  )
}
