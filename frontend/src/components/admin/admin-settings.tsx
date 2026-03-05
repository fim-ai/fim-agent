"use client"

import { useState, useEffect, useCallback } from "react"
import { Loader2, ShieldOff, ShieldCheck, Megaphone, Wrench, LogOut, AlertTriangle, Zap, Plus, Ticket, Copy, X, Eye } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { apiFetch, adminApi } from "@/lib/api"
import { toast } from "sonner"
import type { InviteCode } from "@/types/admin"

interface SystemSettings {
  registration_enabled: boolean
  registration_mode: string
  maintenance_mode: boolean
  announcement_enabled: boolean
  announcement_text: string
  default_token_quota: number
}

export function AdminSettings() {
  const [settings, setSettings] = useState<SystemSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [announcementDraft, setAnnouncementDraft] = useState("")
  const [quotaDraft, setQuotaDraft] = useState("")
  const [forceLogoutOpen, setForceLogoutOpen] = useState(false)
  const [isForcing, setIsForcing] = useState(false)

  useEffect(() => {
    apiFetch<SystemSettings>("/api/admin/settings")
      .then((data) => {
        setSettings(data)
        setAnnouncementDraft(data.announcement_text)
        setQuotaDraft(data.default_token_quota ? String(data.default_token_quota) : "0")
      })
      .catch((err) =>
        toast.error(err instanceof Error ? err.message : "Failed to load settings"),
      )
      .finally(() => setIsLoading(false))
  }, [])

  const patch = async (updates: Partial<SystemSettings>) => {
    if (!settings) return
    setIsSaving(true)
    try {
      const updated = await apiFetch<SystemSettings>("/api/admin/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      })
      setSettings(updated)
      setAnnouncementDraft(updated.announcement_text)
      return updated
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update settings")
    } finally {
      setIsSaving(false)
    }
  }

  const handleForceLogout = async () => {
    setIsForcing(true)
    try {
      const res = await apiFetch<{ invalidated: number }>("/api/admin/actions/force-logout-all", {
        method: "POST",
      })
      toast.success(`Logged out ${res.invalidated} active session${res.invalidated !== 1 ? "s" : ""}`)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to force logout")
    } finally {
      setIsForcing(false)
      setForceLogoutOpen(false)
    }
  }

  // Derive registration mode from settings
  const registrationMode = settings?.registration_mode ?? (settings?.registration_enabled ? "open" : "disabled")

  const handleRegistrationModeChange = async (value: string) => {
    await patch({ registration_mode: value } as Partial<SystemSettings>)
    toast.success(
      value === "open"
        ? "Registration open to everyone"
        : value === "invite"
        ? "Registration set to invite-only"
        : "Registration disabled"
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading settings...
      </div>
    )
  }

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h2 className="text-base font-semibold">Settings</h2>
        <p className="text-sm text-muted-foreground">
          Global configuration that affects all users.
        </p>
      </div>

      <Separator />

      {/* -- Registration -- */}
      <SettingSection
        icon={registrationMode === "open" ? ShieldCheck : ShieldOff}
        iconColor={registrationMode === "open" ? "text-green-500" : registrationMode === "invite" ? "text-amber-500" : "text-destructive"}
        title="User Registration"
        description="Control how new users can join the system."
      >
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-sm font-medium">Registration Mode</Label>
            <Select value={registrationMode} onValueChange={handleRegistrationModeChange} disabled={isSaving}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="open">Open (anyone can register)</SelectItem>
                <SelectItem value="invite">Invite Only</SelectItem>
                <SelectItem value="disabled">Disabled</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-0.5">
              {registrationMode === "open"
                ? "Anyone can create an account from the login page."
                : registrationMode === "invite"
                ? "Users need a valid invite code to register."
                : "Only admins can create accounts via the Users tab."}
            </p>
          </div>
          {registrationMode === "invite" && <InviteCodeManager />}
        </div>
      </SettingSection>

      <Separator />

      {/* -- Default Token Quota -- */}
      <SettingSection
        icon={Zap}
        iconColor="text-blue-500"
        title="Default Monthly Token Quota"
        description="Applied to users without a personal quota. 0 means unlimited."
      >
        <div className="flex items-center gap-3">
          <Input
            type="number"
            min={0}
            className="max-w-[200px]"
            value={quotaDraft}
            onChange={(e) => setQuotaDraft(e.target.value)}
          />
          <Button
            size="sm"
            variant="outline"
            disabled={isSaving || quotaDraft === String(settings?.default_token_quota ?? 0)}
            onClick={async () => {
              const val = parseInt(quotaDraft, 10) || 0
              await patch({ default_token_quota: val })
              toast.success("Default token quota saved")
            }}
          >
            {isSaving && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
            Save
          </Button>
        </div>
      </SettingSection>

      <Separator />

      {/* -- System Announcement -- */}
      <SettingSection
        icon={Megaphone}
        iconColor="text-amber-500"
        title="System Announcement"
        description="Show a banner message to all users at the top of every page."
      >
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label htmlFor="announcement-toggle" className="text-sm font-medium cursor-pointer">
              Show announcement banner
            </Label>
            <Switch
              id="announcement-toggle"
              checked={settings?.announcement_enabled ?? false}
              onCheckedChange={async (v) => {
                await patch({ announcement_enabled: v })
                toast.success(v ? "Announcement banner enabled" : "Announcement banner disabled")
              }}
              disabled={isSaving}
            />
          </div>
          <Textarea
            placeholder="Write your announcement here..."
            value={announcementDraft}
            onChange={(e) => setAnnouncementDraft(e.target.value)}
            className="resize-none text-sm"
            rows={3}
          />
          <Button
            size="sm"
            variant="outline"
            disabled={isSaving || announcementDraft === settings?.announcement_text}
            onClick={async () => {
              await patch({ announcement_text: announcementDraft })
              toast.success("Announcement text saved")
            }}
          >
            {isSaving && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
            Save Text
          </Button>
        </div>
      </SettingSection>

      <Separator />

      {/* -- Maintenance Mode -- */}
      <SettingSection
        icon={Wrench}
        iconColor={settings?.maintenance_mode ? "text-orange-500" : "text-muted-foreground"}
        title="Maintenance Mode"
        description="Block all non-admin access. Admins can still log in and manage the system."
      >
        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="maintenance-toggle" className="text-sm font-medium cursor-pointer">
              Enable maintenance mode
            </Label>
            <p className="text-xs text-muted-foreground mt-0.5">
              {settings?.maintenance_mode
                ? "System is in maintenance. Non-admin requests receive 503."
                : "System is operating normally."}
            </p>
          </div>
          <Switch
            id="maintenance-toggle"
            checked={settings?.maintenance_mode ?? false}
            onCheckedChange={async (v) => {
              await patch({ maintenance_mode: v })
              toast.success(v ? "Maintenance mode ON -- users are blocked" : "Maintenance mode OFF -- system restored")
            }}
            disabled={isSaving}
          />
        </div>
      </SettingSection>

      <Separator />

      {/* -- Danger Zone -- */}
      <div className="space-y-4">
        <div>
          <h4 className="text-sm font-medium text-destructive flex items-center gap-1.5">
            <AlertTriangle className="h-4 w-4" />
            Danger Zone
          </h4>
          <p className="text-sm text-muted-foreground">
            Irreversible or high-impact actions.
          </p>
        </div>

        <div className="flex items-start gap-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4">
          <LogOut className="h-5 w-5 text-destructive mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium">Force logout all users</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Invalidates every active refresh token. All users (except you) will be signed out immediately.
            </p>
          </div>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setForceLogoutOpen(true)}
          >
            Force Logout All
          </Button>
        </div>
      </div>

      {/* Confirm dialog */}
      <AlertDialog open={forceLogoutOpen} onOpenChange={setForceLogoutOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Force logout all users?</AlertDialogTitle>
            <AlertDialogDescription>
              This will immediately invalidate all active sessions. Every user will be signed out and
              must log in again. Your own session will not be affected.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive hover:bg-destructive/90"
              onClick={handleForceLogout}
              disabled={isForcing}
            >
              {isForcing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Yes, Force Logout
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

/* ── Invite Code Manager ── */

function InviteCodeManager() {
  const [codes, setCodes] = useState<InviteCode[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [revokeTarget, setRevokeTarget] = useState<InviteCode | null>(null)
  const [showInactive, setShowInactive] = useState(false)

  // Create form
  const [note, setNote] = useState("")
  const [maxUses, setMaxUses] = useState("1")
  const [expiresAt, setExpiresAt] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  const errMsg = (err: unknown) =>
    err instanceof Error ? err.message : "Operation failed"

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await adminApi.listInviteCodes()
      setCodes(data)
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async () => {
    setIsSaving(true)
    try {
      await adminApi.createInviteCode({
        note: note.trim() || undefined,
        max_uses: parseInt(maxUses, 10) || 1,
        expires_at: expiresAt || undefined,
      })
      toast.success("Invite code generated")
      setCreateOpen(false)
      setNote("")
      setMaxUses("1")
      setExpiresAt("")
      load()
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setIsSaving(false)
    }
  }

  const handleRevoke = async () => {
    if (!revokeTarget) return
    try {
      await adminApi.revokeInviteCode(revokeTarget.id)
      toast.success("Invite code revoked")
      setRevokeTarget(null)
      load()
    } catch (err) {
      toast.error(errMsg(err))
    }
  }

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code)
    toast.success("Code copied to clipboard")
  }

  const inactiveCount = codes.filter((c) => !c.is_active || c.use_count >= c.max_uses).length
  const visibleCodes = showInactive ? codes : codes.filter((c) => c.is_active && c.use_count < c.max_uses)

  return (
    <div className="space-y-3 pt-2">
      <div className="flex items-center justify-between">
        <h5 className="text-sm font-medium flex items-center gap-1.5">
          <Ticket className="h-3.5 w-3.5" />
          Invite Codes
        </h5>
        <div className="flex items-center gap-2">
          {inactiveCount > 0 && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowInactive((v) => !v)}
              className="h-7 gap-1 text-xs text-muted-foreground"
            >
              <Eye className="h-3 w-3" />
              {showInactive ? "Hide inactive" : `${inactiveCount} inactive`}
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => setCreateOpen(true)} className="h-7 gap-1 text-xs">
            <Plus className="h-3 w-3" />
            Generate Code
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-muted-foreground text-xs py-2">
          <Loader2 className="h-3 w-3 animate-spin" />
          Loading...
        </div>
      ) : visibleCodes.length === 0 ? (
        <p className="text-xs text-muted-foreground py-2">
          {codes.length === 0 ? "No invite codes yet." : "No active invite codes."}
        </p>
      ) : (
        <div className="divide-y divide-border rounded-md border border-border text-sm">
          {visibleCodes.map((c) => (
            <div key={c.id} className="flex items-center justify-between px-3 py-2">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">{c.code}</code>
                <button onClick={() => copyCode(c.code)} className="text-muted-foreground hover:text-foreground shrink-0">
                  <Copy className="h-3 w-3" />
                </button>
                {c.note && <span className="text-xs text-muted-foreground truncate">{c.note}</span>}
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-2">
                <Badge variant="outline" className="text-xs">
                  {c.use_count}/{c.max_uses}
                </Badge>
                {c.expires_at && (
                  <span className="text-xs text-muted-foreground">
                    exp {new Date(c.expires_at).toLocaleDateString()}
                  </span>
                )}
                {!c.is_active ? (
                  <Badge variant="secondary" className="text-xs">Revoked</Badge>
                ) : c.use_count >= c.max_uses ? (
                  <Badge variant="secondary" className="text-xs">Exhausted</Badge>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 text-destructive"
                    onClick={() => setRevokeTarget(c)}
                  >
                    <X className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Invite Code</DialogTitle>
            <DialogDescription>
              Create a new invite code for user registration.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label className="text-sm font-medium">Note (optional)</Label>
              <Input
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="e.g. For team onboarding"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Max Uses</Label>
              <Input
                type="number"
                min={1}
                value={maxUses}
                onChange={(e) => setMaxUses(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-sm font-medium">Expires At (optional)</Label>
              <Input
                type="date"
                value={expiresAt}
                onChange={(e) => setExpiresAt(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={isSaving}>
              {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke AlertDialog */}
      <AlertDialog open={!!revokeTarget} onOpenChange={(open) => !open && setRevokeTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke invite code?</AlertDialogTitle>
            <AlertDialogDescription>
              Code &quot;{revokeTarget?.code}&quot; will be deactivated. Users with this code will no longer be able to register.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRevoke} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function SettingSection({
  icon: Icon,
  iconColor,
  title,
  description,
  children,
}: {
  icon: React.ElementType
  iconColor: string
  title: string
  description: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium flex items-center gap-1.5">
          <Icon className={`h-4 w-4 ${iconColor}`} />
          {title}
        </h4>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="rounded-lg border border-border bg-card p-4">
        {children}
      </div>
    </div>
  )
}
