"use client"

import { useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_KEY } from "@/lib/constants"
import { Loader2 } from "lucide-react"

function CallbackHandler() {
  const searchParams = useSearchParams()

  useEffect(() => {
    const accessToken = searchParams.get("access_token")
    const refreshToken = searchParams.get("refresh_token")
    const userJson = searchParams.get("user")
    const error = searchParams.get("error")

    if (error) {
      window.location.href = `/login?error=${encodeURIComponent(error)}`
      return
    }

    if (accessToken && refreshToken && userJson) {
      try {
        // Validate user JSON is parseable
        const user = JSON.parse(userJson)
        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
        localStorage.setItem(USER_KEY, JSON.stringify(user))
        // Full page reload to re-initialize AuthProvider
        window.location.href = "/"
      } catch {
        window.location.href = "/login?error=oauth_failed"
      }
    } else {
      window.location.href = "/login?error=oauth_failed"
    }
  }, [searchParams])

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  )
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-background">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  )
}
