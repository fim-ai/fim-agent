"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth-context"
import { AdminBillingPlans } from "@/components/admin/admin-billing-plans"

/**
 * Standalone route for the admin billing plans table.
 *
 * The primary admin entry-point lives at ``/admin?tab=billingPlans`` (the
 * tabbed shell). This page exists for direct deep-links and bookmarks; it
 * mirrors the same auth gating + content while keeping the chrome optional.
 */
export default function AdminBillingPlansPage() {
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
      <AdminBillingPlans />
    </div>
  )
}
