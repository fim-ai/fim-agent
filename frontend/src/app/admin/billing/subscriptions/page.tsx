"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth-context"
import { AdminBillingSubscriptions } from "@/components/admin/admin-billing-subscriptions"

/**
 * Standalone route for the admin billing subscriptions table.
 *
 * Mirrors ``/admin/billing/plans/page.tsx`` — exists for deep-linking only;
 * the tabbed shell at ``/admin?tab=billingSubscriptions`` is the canonical
 * entry-point.
 */
export default function AdminBillingSubscriptionsPage() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      router.replace("/login")
      return
    }
    if (!user.is_admin) {
      router.replace("/")
    }
  }, [authLoading, user, router])

  if (authLoading || !user || !user.is_admin) return null

  return (
    <div className="p-6">
      <AdminBillingSubscriptions />
    </div>
  )
}
