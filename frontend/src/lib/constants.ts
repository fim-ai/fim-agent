export const APP_NAME = "FIM Agent"
export const APP_VERSION = "0.4.0"
/** All fetch() calls use empty base (same-origin), proxied by Next.js rewrites */
export function getApiBaseUrl() {
  return ""
}

/** Direct browser navigation (OAuth redirects) needs the real backend URL */
export function getApiDirectUrl() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }
  return "http://localhost:8000"
}

export const ACCESS_TOKEN_KEY = "fim_access_token"
export const REFRESH_TOKEN_KEY = "fim_refresh_token"
export const USER_KEY = "fim_user"
