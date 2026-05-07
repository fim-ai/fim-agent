import { getTranslations } from "next-intl/server"

import { BillingPage } from "@/components/settings/billing-page"

/**
 * SEO / browser-tab metadata for the user-facing billing page.
 *
 * The Server Component layer is intentionally tiny: we only emit the
 * `<title>` for SEO/keyboard-tab purposes. All interactive logic
 * (subscription fetch, checkout redirect, Stripe portal handoff) lives
 * in the `BillingPage` Client Component below — this preserves SSR
 * metadata while keeping `useState` / `useEffect` hooks legal.
 */
export async function generateMetadata() {
  const t = await getTranslations("billing")
  const tSettings = await getTranslations("settings")
  return {
    // "Billing — Settings" reads cleanly in the browser tab and matches
    // how the rest of the app composes its titles.
    title: `${t("page.title")} — ${tSettings("title")}`,
    description: t("page.description"),
  }
}

export default function Page() {
  return <BillingPage />
}
