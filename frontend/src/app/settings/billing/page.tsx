import { redirect } from "next/navigation"

/**
 * Backward-compatibility redirect.
 *
 * The billing UI was originally a standalone route at `/settings/billing`
 * (P3) so it could ship server-rendered metadata. We've since folded it
 * back into `/settings?tab=billing` to keep the sidebar persistent — but
 * old bookmarks, Stripe Checkout return URLs from earlier deploys, and
 * documentation links may still hit this path. Redirect them in-place
 * rather than 404.
 */
export default function BillingRedirectPage() {
  redirect("/settings?tab=billing")
}
