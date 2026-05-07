/**
 * Lightweight client-side accessor for the ``billing_enabled`` flag.
 *
 * The flag lives in ``system_settings`` on the backend; the user-facing
 * way to read it is the public ``/api/version`` envelope, which already
 * round-trips on every page load. Admins also see it on
 * ``/api/admin/settings`` — but we don't want to gate the user
 * sidebar on an admin-only call.
 *
 * Strategy: piggy-back on the ``/api/version`` endpoint (which
 * historically returned ``{version}``) by adding the flag there. The
 * frontend treats a missing key as ``false`` for backward compat.
 */

import { apiFetch, ApiError } from "@/lib/api"

interface VersionEnvelope {
  version?: string
  billing_enabled?: boolean
}

/**
 * Resolve the billing-enabled flag once. Returns ``false`` on any
 * failure (fail-closed): a private deployment without the version
 * endpoint shouldn't accidentally surface payment UX.
 */
export async function fetchBillingEnabled(): Promise<boolean> {
  try {
    const env = await apiFetch<VersionEnvelope>("/api/version")
    return env.billing_enabled === true
  } catch (err) {
    // Anything goes wrong — auth, network, parse — assume off.
    if (err instanceof ApiError && err.status === 401) {
      // 401 means the user isn't authenticated yet; nothing to surface.
      return false
    }
    return false
  }
}

/**
 * Admin-only: switch the flag.
 *
 * - ``setBillingEnabled(true)`` invokes the activation endpoint, which
 *   seeds plans + backfills user plan bindings the first time it
 *   runs and is a no-op on subsequent calls.
 * - ``setBillingEnabled(false)`` is a pure flag flip.
 */
export async function setBillingEnabled(
  enabled: boolean,
): Promise<{
  plans_seeded: number
  users_backfilled: number
  default_plan_id: number | null
  billing_enabled: boolean
}> {
  return apiFetch<{
    plans_seeded: number
    users_backfilled: number
    default_plan_id: number | null
    billing_enabled: boolean
  }>("/api/admin/system/billing/toggle", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  })
}
