"use client"

import { useState, useEffect, useCallback, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useTranslations, useLocale } from "next-intl"
import { useAuth } from "@/contexts/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { InputOTP, InputOTPGroup, InputOTPSlot, InputOTPSeparator } from "@/components/ui/input-otp"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Globe, Sun, Moon } from "lucide-react"
import { APP_NAME, getApiBaseUrl, getApiDirectUrl } from "@/lib/constants"
import { authApi } from "@/lib/api"
import { getErrorMessage } from "@/lib/error-utils"
import { toast } from "sonner"
import { AnimatedLogo } from "@/components/layout/animated-logo"
import { useTheme } from "next-themes"

function LoginPageInner() {
  const t = useTranslations("auth")
  const tc = useTranslations("common")
  const tError = useTranslations("errors")
  const locale = useLocale()
  const { user, isLoading: authLoading, login, loginWithCode, register } = useAuth()
  const { resolvedTheme, setTheme } = useTheme()
  const router = useRouter()
  const searchParams = useSearchParams()

  // Login form state
  const [loginEmail, setLoginEmail] = useState("")
  const [loginPassword, setLoginPassword] = useState("")
  const [loginError, setLoginError] = useState("")
  const [loginLoading, setLoginLoading] = useState(false)

  // OTP login state
  const [otpLoginMode, setOtpLoginMode] = useState(false)
  const [otpEmail, setOtpEmail] = useState("")
  const [otpStep, setOtpStep] = useState<"email" | "code">("email")
  const [otpCode, setOtpCode] = useState("")
  const [otpSending, setOtpSending] = useState(false)
  const [otpVerifying, setOtpVerifying] = useState(false)
  const [otpResendCountdown, setOtpResendCountdown] = useState(0)
  const [smtpConfigured, setSmtpConfigured] = useState(false)

  // Forgot password state
  const [forgotMode, setForgotMode] = useState(false)
  const [forgotStep, setForgotStep] = useState<"email" | "code" | "password">("email")
  const [forgotEmail, setForgotEmail] = useState("")
  const [forgotCode, setForgotCode] = useState("")
  const [forgotNewPassword, setForgotNewPassword] = useState("")
  const [forgotConfirmPassword, setForgotConfirmPassword] = useState("")
  const [forgotSending, setForgotSending] = useState(false)
  const [forgotSubmitting, setForgotSubmitting] = useState(false)
  const [forgotResendCountdown, setForgotResendCountdown] = useState(0)

  // Register form state
  const [regEmail, setRegEmail] = useState("")
  const [regPassword, setRegPassword] = useState("")
  const [regConfirm, setRegConfirm] = useState("")
  const [regInviteCode, setRegInviteCode] = useState("")
  const [regError, setRegError] = useState("")
  const [regLoading, setRegLoading] = useState(false)

  // Email verification state
  const [emailVerificationEnabled, setEmailVerificationEnabled] = useState(false)
  const [verificationStep, setVerificationStep] = useState(false)
  const [verificationCode, setVerificationCode] = useState("")
  const [sendingCode, setSendingCode] = useState(false)
  const [resendCountdown, setResendCountdown] = useState(0)

  // Setup status check
  const [setupChecking, setSetupChecking] = useState(true)

  // Registration status
  const [registrationEnabled, setRegistrationEnabled] = useState(true)
  const [registrationMode, setRegistrationMode] = useState<"open" | "invite" | "disabled">("open")

  // OAuth state
  const [oauthProviders, setOauthProviders] = useState<string[]>([])
  const [oauthError, setOauthError] = useState("")

  // Redirect if already logged in (also fires after login/register when user state updates)
  useEffect(() => {
    if (!authLoading && user) {
      if (!user.onboarding_completed) {
        router.replace("/onboarding")
      } else {
        router.replace("/")
      }
    }
  }, [authLoading, user, router])

  // Check if system needs first-time setup, and fetch registration status
  useEffect(() => {
    authApi
      .setupStatus()
      .then((res) => {
        if (!res.initialized) {
          router.replace("/setup")
        } else {
          setSetupChecking(false)
          // Fetch registration status after confirming system is initialized
          fetch(`${getApiBaseUrl()}/api/auth/registration-status`)
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
              if (data) {
                if (typeof data.registration_enabled === "boolean") {
                  setRegistrationEnabled(data.registration_enabled)
                }
                if (data.registration_mode) {
                  setRegistrationMode(data.registration_mode as "open" | "invite" | "disabled")
                }
                if (typeof data.email_verification_enabled === "boolean") {
                  setEmailVerificationEnabled(data.email_verification_enabled)
                }
                if (typeof data.smtp_configured === "boolean") {
                  setSmtpConfigured(data.smtp_configured)
                }
              }
            })
            .catch(() => {
              // Silently ignore — default to showing registration
            })
        }
      })
      .catch(() => {
        // If API call fails (old backend, network error), stay on login for backward compatibility
        setSetupChecking(false)
      })
  }, [router])

  // Check for OAuth error in URL params
  useEffect(() => {
    const error = searchParams.get("error")
    if (error) {
      if (error === "oauth_failed") {
        setOauthError(t("oauthFailed"))
      } else if (error === "registration_disabled") {
        setOauthError(t("oauthRegistrationDisabled"))
      } else {
        setOauthError(error)
      }
    }
  }, [searchParams, t])

  // Fetch available OAuth providers
  useEffect(() => {
    fetch(`${getApiBaseUrl()}/api/auth/oauth/providers`)
      .then((res) => {
        if (res.ok) return res.json()
        return { providers: [] }
      })
      .then((data) => {
        if (Array.isArray(data.providers)) {
          setOauthProviders(data.providers)
        }
      })
      .catch(() => {
        // Silently ignore — OAuth buttons simply won't appear
      })
  }, [])

  // Resend countdown timer (registration)
  useEffect(() => {
    if (resendCountdown <= 0) return
    const timer = setTimeout(() => setResendCountdown(resendCountdown - 1), 1000)
    return () => clearTimeout(timer)
  }, [resendCountdown])

  // Resend countdown timer (OTP login)
  useEffect(() => {
    if (otpResendCountdown <= 0) return
    const timer = setTimeout(() => setOtpResendCountdown(otpResendCountdown - 1), 1000)
    return () => clearTimeout(timer)
  }, [otpResendCountdown])

  // Resend countdown timer (forgot password)
  useEffect(() => {
    if (forgotResendCountdown <= 0) return
    const timer = setTimeout(() => setForgotResendCountdown(forgotResendCountdown - 1), 1000)
    return () => clearTimeout(timer)
  }, [forgotResendCountdown])

  const handleSendCode = async () => {
    setRegError("")
    if (!regEmail.trim()) {
      setRegError(t("emailRequired"))
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(regEmail)) {
      setRegError(t("emailInvalid"))
      return
    }
    setSendingCode(true)
    try {
      await authApi.sendVerificationCode(regEmail, locale)
      setVerificationStep(true)
      setResendCountdown(60)
      setVerificationCode("")
    } catch (err) {
      toast.error(getErrorMessage(err, tError))
    } finally {
      setSendingCode(false)
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError("")
    setLoginLoading(true)
    try {
      await login({ email: loginEmail, password: loginPassword })
      // Redirect is handled by the useEffect that watches user state
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : t("loginFailed"))
    } finally {
      setLoginLoading(false)
    }
  }

  const handleSendLoginCode = async () => {
    if (!otpEmail.trim()) return
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(otpEmail)) return
    setOtpSending(true)
    try {
      await authApi.sendLoginCode(otpEmail, locale)
      setOtpStep("code")
      setOtpResendCountdown(60)
      setOtpCode("")
    } catch (err) {
      toast.error(getErrorMessage(err, tError))
    } finally {
      setOtpSending(false)
    }
  }

  const doLoginWithCode = useCallback(async (codeOverride?: string) => {
    setOtpVerifying(true)
    try {
      await loginWithCode({ email: otpEmail, code: codeOverride || otpCode })
      // Redirect is handled by the useEffect that watches user state
    } catch (err) {
      toast.error(getErrorMessage(err, tError))
      setOtpCode("")
    } finally {
      setOtpVerifying(false)
    }
  }, [loginWithCode, otpEmail, otpCode, tError])

  // Accept optional codeOverride for auto-submit from OTP onComplete
  const doRegister = useCallback(async (codeOverride?: string) => {
    setRegError("")
    setRegLoading(true)
    try {
      await register({
        password: regPassword,
        email: regEmail,
        invite_code: regInviteCode.trim() || undefined,
        verification_code: codeOverride || verificationCode.trim() || undefined,
      })
      // Redirect is handled by the useEffect that watches user state
    } catch (err) {
      toast.error(getErrorMessage(err, tError))
      // Clear OTP so user can re-enter
      setVerificationCode("")
    } finally {
      setRegLoading(false)
    }
  }, [register, regPassword, regEmail, regInviteCode, verificationCode, tError])

  const handleSendForgotCode = async () => {
    if (!forgotEmail.trim()) return
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(forgotEmail)) return
    setForgotSending(true)
    try {
      await authApi.sendForgotCode(forgotEmail, locale)
      setForgotStep("code")
      setForgotResendCountdown(60)
      setForgotCode("")
    } catch (err) {
      toast.error(getErrorMessage(err, tError))
    } finally {
      setForgotSending(false)
    }
  }

  const handleForgotCodeComplete = (code: string) => {
    setForgotCode(code)
    setForgotStep("password")
  }

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (forgotNewPassword.length < 8 || forgotNewPassword !== forgotConfirmPassword) return
    setForgotSubmitting(true)
    try {
      await authApi.forgotPassword({
        email: forgotEmail,
        code: forgotCode,
        new_password: forgotNewPassword,
      })
      toast.success(t("passwordResetSuccess"))
      // Return to login form
      setForgotMode(false)
      setForgotStep("email")
      setForgotCode("")
      setForgotNewPassword("")
      setForgotConfirmPassword("")
      setForgotEmail("")
    } catch (err) {
      toast.error(getErrorMessage(err, tError))
      const apiErr = err as import("@/lib/api").ApiError
      if (apiErr.errorCode === "verification_code_invalid" || apiErr.errorCode === "verification_code_expired" || apiErr.errorCode === "verification_code_too_many_attempts") {
        setForgotStep("code")
        setForgotCode("")
      }
    } finally {
      setForgotSubmitting(false)
    }
  }

  const handleCancelForgot = () => {
    setForgotMode(false)
    setForgotStep("email")
    setForgotEmail("")
    setForgotCode("")
    setForgotNewPassword("")
    setForgotConfirmPassword("")
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setRegError("")

    // Validate fields
    if (!regEmail.trim()) {
      setRegError(t("emailRequired"))
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(regEmail)) {
      setRegError(t("emailInvalid"))
      return
    }
    if (regPassword !== regConfirm) {
      setRegError(t("passwordsDoNotMatch"))
      return
    }
    if (regPassword.length < 6) {
      setRegError(t("passwordMinLength"))
      return
    }

    // If email verification is enabled and we haven't sent code yet, send it first
    if (emailVerificationEnabled && !verificationStep) {
      await handleSendCode()
      return
    }

    await doRegister()
  }

  const handleLanguageSwitch = (lang: string) => {
    const cookieValue = lang === "auto" ? "" : lang
    document.cookie = cookieValue
      ? `NEXT_LOCALE=${cookieValue}; path=/; max-age=${60 * 60 * 24 * 365}`
      : "NEXT_LOCALE=; path=/; max-age=0"
    router.refresh()
  }

  if (authLoading || setupChecking) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (user) return null // Will redirect

  return (
    <div className="flex min-h-screen bg-background">
      {/* Left panel — brand / hero, always dark, hidden on mobile */}
      <div className="login-brand-panel hidden lg:flex w-[45%] shrink-0 flex-col justify-between px-14 py-10 text-white">
        {/* Mesh gradient background */}
        <div className="login-mesh-bg" aria-hidden="true">
          <div className="mesh-orb" />
        </div>

        {/* Top — logo */}
        <AnimatedLogo appName={APP_NAME} />

        {/* Middle-lower — tagline */}
        <div className="relative z-10 -mt-8">
          <h1
            className="text-[2.75rem] font-bold leading-[1.1] tracking-tight text-white whitespace-pre-line"
            style={{ fontFamily: 'var(--font-cabinet), sans-serif' }}
          >
            {t("brandTagline")}
          </h1>
          <p className="mt-4 text-base leading-relaxed text-white/55">
            {t("brandLine1")}
            <br />
            {t("brandLine2")}
            <br />
            {t("brandLine3")}
          </p>
        </div>

        {/* Bottom — copyright */}
        <div className="relative z-10">
          <p className="text-xs text-white/35">&copy; {new Date().getFullYear()} {APP_NAME}</p>
        </div>
      </div>

      {/* Right panel — form, follows light/dark theme */}
      <div className="relative flex flex-1 flex-col items-center justify-center bg-background px-6 py-12">
        {/* Theme & Language switcher */}
        <div className="absolute top-4 right-4 flex items-center gap-1">
          <button
            type="button"
            className="flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          >
            {resolvedTheme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            onClick={() => handleLanguageSwitch(locale === "zh" ? "en" : "zh")}
          >
            <Globe className="h-3.5 w-3.5" />
            {locale === "zh" ? "English" : "中文"}
          </button>
        </div>

        <div className="w-full max-w-sm">
          {/* Mobile-only logo (< lg) */}
          <div className="mb-8 flex items-center justify-center gap-2 lg:hidden">
            <img src="/fim-mark-light.svg" alt="FIM" className="h-8 w-auto dark:hidden" />
            <img src="/fim-mark.svg" alt="FIM" className="h-8 w-auto hidden dark:block" />
            <span
              className="text-lg font-bold"
              style={{ fontFamily: 'var(--font-cabinet), sans-serif' }}
            >
              {APP_NAME}
            </span>
          </div>

          {/* Heading */}
          <div className="mb-6 text-center lg:text-left">
            <h2 className="text-xl font-semibold tracking-tight">{t("loginWelcome")}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("loginSubtitle")}
            </p>
          </div>

          {/* OAuth Error */}
          {oauthError && (
            <p className="text-sm text-destructive text-center mb-4">{oauthError}</p>
          )}

          {/* OAuth Buttons — only in open registration mode; invite/disabled hides them to prevent bypassing invite codes */}
          {oauthProviders.length > 0 && registrationMode === "open" && (
            <>
              <div className="space-y-2">
                {oauthProviders.includes("github") && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      window.location.href = `${getApiDirectUrl()}/api/auth/oauth/github/authorize`
                    }}
                  >
                    <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                    </svg>
                    {t("continueWithGithub")}
                  </Button>
                )}
                {oauthProviders.includes("google") && (
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      window.location.href = `${getApiDirectUrl()}/api/auth/oauth/google/authorize`
                    }}
                  >
                    <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                    </svg>
                    {t("continueWithGoogle")}
                  </Button>
                )}
              </div>

              {/* Separator */}
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">{t("orDivider")}</span>
                </div>
              </div>
            </>
          )}

          <Tabs defaultValue="login" className="w-full">
            <TabsList className={`grid w-full ${registrationEnabled ? "grid-cols-2" : "grid-cols-1"}`}>
              <TabsTrigger value="login">{tc("login")}</TabsTrigger>
              {registrationEnabled && <TabsTrigger value="register">{tc("register")}</TabsTrigger>}
            </TabsList>
            <TabsContent value="login">
              {forgotMode ? (
                forgotStep === "email" ? (
                  <div className="space-y-4 pt-4">
                    <p className="text-sm text-muted-foreground">
                      {t("forgotPasswordSubtitle")}
                    </p>
                    <Input
                      type="email"
                      placeholder={t("emailPlaceholder")}
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      autoFocus
                      autoComplete="email"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault()
                          handleSendForgotCode()
                        }
                      }}
                    />
                    <Button
                      type="button"
                      className="w-full"
                      disabled={forgotSending || !forgotEmail.trim()}
                      onClick={handleSendForgotCode}
                    >
                      {forgotSending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {t("sendResetCode")}
                    </Button>
                    <div className="text-center">
                      <button
                        type="button"
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                        onClick={handleCancelForgot}
                      >
                        {t("backToLogin")}
                      </button>
                    </div>
                  </div>
                ) : forgotStep === "code" ? (
                  <div className="space-y-4 pt-4">
                    <p className="text-sm text-muted-foreground">
                      {t("resetCodeSent", { email: forgotEmail })}
                    </p>
                    <div className="flex justify-center">
                      <InputOTP
                        maxLength={6}
                        value={forgotCode}
                        onChange={setForgotCode}
                        onComplete={handleForgotCodeComplete}
                        autoFocus
                      >
                        <InputOTPGroup>
                          <InputOTPSlot index={0} />
                          <InputOTPSlot index={1} />
                          <InputOTPSlot index={2} />
                        </InputOTPGroup>
                        <InputOTPSeparator />
                        <InputOTPGroup>
                          <InputOTPSlot index={3} />
                          <InputOTPSlot index={4} />
                          <InputOTPSlot index={5} />
                        </InputOTPGroup>
                      </InputOTP>
                    </div>
                    <div className="flex items-center justify-between">
                      <button
                        type="button"
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                        onClick={handleCancelForgot}
                      >
                        {t("backToLogin")}
                      </button>
                      <button
                        type="button"
                        className="text-sm text-primary hover:text-primary/80 transition-colors disabled:text-muted-foreground disabled:cursor-not-allowed"
                        disabled={forgotResendCountdown > 0 || forgotSending}
                        onClick={handleSendForgotCode}
                      >
                        {forgotSending
                          ? t("sendingCode")
                          : forgotResendCountdown > 0
                            ? t("resendCodeIn", { seconds: forgotResendCountdown })
                            : t("resendCode")}
                      </button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleForgotPasswordSubmit} className="space-y-4 pt-4">
                    <p className="text-sm text-muted-foreground">
                      {t("resetCodeSent", { email: forgotEmail })}
                    </p>
                    <div className="space-y-2">
                      <Input
                        type="password"
                        placeholder={t("newPasswordPlaceholder")}
                        value={forgotNewPassword}
                        onChange={(e) => setForgotNewPassword(e.target.value)}
                        autoFocus
                        autoComplete="new-password"
                      />
                      <Input
                        type="password"
                        placeholder={t("confirmNewPasswordPlaceholder")}
                        value={forgotConfirmPassword}
                        onChange={(e) => setForgotConfirmPassword(e.target.value)}
                        autoComplete="new-password"
                      />
                    </div>
                    {forgotConfirmPassword.length > 0 && forgotNewPassword !== forgotConfirmPassword && (
                      <p className="text-sm text-destructive">{t("passwordsMustMatch")}</p>
                    )}
                    <Button
                      type="submit"
                      className="w-full"
                      disabled={
                        forgotSubmitting ||
                        forgotNewPassword.length < 8 ||
                        forgotNewPassword !== forgotConfirmPassword
                      }
                    >
                      {forgotSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {forgotSubmitting ? t("resettingPassword") : t("resetPassword")}
                    </Button>
                    <div className="text-center">
                      <button
                        type="button"
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                        onClick={handleCancelForgot}
                      >
                        {t("backToLogin")}
                      </button>
                    </div>
                  </form>
                )
              ) : !otpLoginMode ? (
                /* Password login mode */
                <form onSubmit={handleLogin} className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Input
                      type="email"
                      placeholder={t("emailPlaceholder")}
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      required
                      autoFocus
                      autoComplete="email"
                    />
                    <Input
                      type="password"
                      placeholder={t("passwordPlaceholder")}
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                    />
                  </div>
                  {loginError && (
                    <p className="text-sm text-destructive">{loginError}</p>
                  )}
                  <Button type="submit" className="w-full" disabled={loginLoading}>
                    {loginLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {t("signIn")}
                  </Button>
                  {smtpConfigured && (
                    <div className="flex items-center justify-between">
                      <button
                        type="button"
                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => {
                          setForgotMode(true)
                          setForgotStep("email")
                          if (loginEmail.trim()) setForgotEmail(loginEmail.trim())
                        }}
                      >
                        {t("forgotPassword")}
                      </button>
                      <button
                        type="button"
                        className="text-sm text-primary hover:text-primary/80 transition-colors"
                        onClick={() => setOtpLoginMode(true)}
                      >
                        {t("loginWithEmailCode")}
                      </button>
                    </div>
                  )}
                </form>
              ) : otpStep === "email" ? (
                /* OTP login — email step */
                <div className="space-y-4 pt-4">
                  <p className="text-sm text-muted-foreground">
                    {t("otpLoginSubtitle")}
                  </p>
                  <Input
                    type="email"
                    placeholder={t("emailPlaceholder")}
                    value={otpEmail}
                    onChange={(e) => setOtpEmail(e.target.value)}
                    autoFocus
                    autoComplete="email"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault()
                        handleSendLoginCode()
                      }
                    }}
                  />
                  <Button
                    type="button"
                    className="w-full"
                    disabled={otpSending || !otpEmail.trim()}
                    onClick={handleSendLoginCode}
                  >
                    {otpSending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {t("sendLoginCode")}
                  </Button>
                  <div className="text-center">
                    <button
                      type="button"
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => {
                        setOtpLoginMode(false)
                        setOtpStep("email")
                        setOtpCode("")
                        setOtpEmail("")
                      }}
                    >
                      {t("backToPasswordLogin")}
                    </button>
                  </div>
                </div>
              ) : (
                /* OTP login — code step */
                <div className="space-y-4 pt-4">
                  <p className="text-sm text-muted-foreground">
                    {t("loginCodeSent", { email: otpEmail })}
                  </p>
                  <div className="flex justify-center">
                    <InputOTP
                      maxLength={6}
                      value={otpCode}
                      onChange={setOtpCode}
                      onComplete={(code) => doLoginWithCode(code)}
                      disabled={otpVerifying}
                      autoFocus
                    >
                      <InputOTPGroup>
                        <InputOTPSlot index={0} />
                        <InputOTPSlot index={1} />
                        <InputOTPSlot index={2} />
                      </InputOTPGroup>
                      <InputOTPSeparator />
                      <InputOTPGroup>
                        <InputOTPSlot index={3} />
                        <InputOTPSlot index={4} />
                        <InputOTPSlot index={5} />
                      </InputOTPGroup>
                    </InputOTP>
                  </div>
                  {otpVerifying && (
                    <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      {t("signingIn")}
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <button
                      type="button"
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => {
                        setOtpStep("email")
                        setOtpCode("")
                      }}
                    >
                      {t("changeEmail")}
                    </button>
                    <button
                      type="button"
                      className="text-sm text-primary hover:text-primary/80 transition-colors disabled:text-muted-foreground disabled:cursor-not-allowed"
                      disabled={otpResendCountdown > 0 || otpSending}
                      onClick={handleSendLoginCode}
                    >
                      {otpSending
                        ? t("sendingCode")
                        : otpResendCountdown > 0
                          ? t("resendCodeIn", { seconds: otpResendCountdown })
                          : t("resendCode")}
                    </button>
                  </div>
                  <div className="text-center">
                    <button
                      type="button"
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                      onClick={() => {
                        setOtpLoginMode(false)
                        setOtpStep("email")
                        setOtpCode("")
                        setOtpEmail("")
                      }}
                    >
                      {t("backToPasswordLogin")}
                    </button>
                  </div>
                </div>
              )}
            </TabsContent>
            {registrationEnabled && <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4 pt-4">
                {!verificationStep ? (
                  <>
                    <div className="space-y-2">
                      <Input
                        type="email"
                        placeholder={t("emailPlaceholder")}
                        value={regEmail}
                        onChange={(e) => setRegEmail(e.target.value)}
                        required
                        autoComplete="email"
                      />
                      <Input
                        type="password"
                        placeholder={t("passwordMinLengthPlaceholder")}
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        required
                        minLength={6}
                        autoComplete="new-password"
                      />
                      <Input
                        type="password"
                        placeholder={t("confirmPasswordPlaceholder")}
                        value={regConfirm}
                        onChange={(e) => setRegConfirm(e.target.value)}
                        required
                        autoComplete="new-password"
                      />
                      {registrationMode === "invite" && (
                        <Input
                          placeholder={t("inviteCodePlaceholder")}
                          value={regInviteCode}
                          onChange={(e) => setRegInviteCode(e.target.value)}
                          autoComplete="off"
                          required
                        />
                      )}
                    </div>
                    {regError && (
                      <p className="text-sm text-destructive">{regError}</p>
                    )}
                    <Button type="submit" className="w-full" disabled={regLoading || sendingCode}>
                      {(regLoading || sendingCode) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {emailVerificationEnabled && !sendingCode ? t("verifyEmail") : sendingCode ? t("sendingCode") : t("createAccount")}
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="space-y-4">
                      <p className="text-sm text-muted-foreground">
                        {t("verificationCodeSent", { email: regEmail })}
                      </p>
                      <div className="flex justify-center">
                        <InputOTP
                          maxLength={6}
                          value={verificationCode}
                          onChange={setVerificationCode}
                          onComplete={(code) => doRegister(code)}
                          disabled={regLoading}
                          autoFocus
                        >
                          <InputOTPGroup>
                            <InputOTPSlot index={0} />
                            <InputOTPSlot index={1} />
                            <InputOTPSlot index={2} />
                          </InputOTPGroup>
                          <InputOTPSeparator />
                          <InputOTPGroup>
                            <InputOTPSlot index={3} />
                            <InputOTPSlot index={4} />
                            <InputOTPSlot index={5} />
                          </InputOTPGroup>
                        </InputOTP>
                      </div>
                      {regLoading && (
                        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          {t("verifying")}
                        </div>
                      )}
                      <div className="flex items-center justify-between">
                        <button
                          type="button"
                          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => {
                            setVerificationStep(false)
                            setVerificationCode("")
                            setRegError("")
                          }}
                        >
                          {t("changeEmail")}
                        </button>
                        <button
                          type="button"
                          className="text-sm text-primary hover:text-primary/80 transition-colors disabled:text-muted-foreground disabled:cursor-not-allowed"
                          disabled={resendCountdown > 0 || sendingCode}
                          onClick={handleSendCode}
                        >
                          {sendingCode
                            ? t("sendingCode")
                            : resendCountdown > 0
                              ? t("resendCodeIn", { seconds: resendCountdown })
                              : t("resendCode")}
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </form>
            </TabsContent>}
          </Tabs>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-background">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <LoginPageInner />
    </Suspense>
  )
}
