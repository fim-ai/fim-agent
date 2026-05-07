import { getTranslations } from "next-intl/server"

import { BillingPage } from "@/components/settings/billing-page"
import { APP_NAME } from "@/lib/constants"

export async function generateMetadata() {
  const t = await getTranslations("billing")
  const tSettings = await getTranslations("settings")
  return {
    title: `${tSettings("title")} · ${t("page.title")} — ${APP_NAME}`,
    description: t("page.description"),
  }
}

export default function Page() {
  return <BillingPage />
}
