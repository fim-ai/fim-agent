"use client"

import { useState, useEffect, useCallback } from "react"
import { useTranslations } from "next-intl"
import {
  Building2,
  MoreHorizontal,
  Plus,
  Settings,
  Trash2,
  LogOut,
  Users,
  UserMinus,
  Shield,
  ClipboardCheck,
  Check,
  X,
  ShieldCheck,
} from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAuth } from "@/contexts/auth-context"
import { orgApi, type UserOrg, type OrgMember, type ReviewItem } from "@/lib/api"
import { EmojiPickerPopover } from "@/components/ui/emoji-picker-popover"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------


function roleBadgeClass(role: "owner" | "admin" | "member"): string {
  switch (role) {
    case "owner":
      return "border-purple-400 text-purple-600 dark:text-purple-400"
    case "admin":
      return "border-blue-400 text-blue-600 dark:text-blue-400"
    default:
      return "border-muted-foreground/40 text-muted-foreground"
  }
}

function resourceTypeLabel(type: string, t: (key: string) => string): string {
  switch (type) {
    case "agent": return t("resourceTypeAgent")
    case "connector": return t("resourceTypeConnector")
    case "knowledge_base": return t("resourceTypeKb")
    case "mcp_server": return t("resourceTypeMcpServer")
    default: return type
  }
}

// ---------------------------------------------------------------------------
// OrgFormDialog -- create / edit
// ---------------------------------------------------------------------------

interface OrgFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initial?: UserOrg | null
  onSaved: (org: UserOrg) => void
}

function OrgFormDialog({ open, onOpenChange, initial, onSaved }: OrgFormDialogProps) {
  const t = useTranslations("organizations")
  const tc = useTranslations("common")

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [icon, setIcon] = useState<string | null>(null)
  const [requireReview, setRequireReview] = useState(false)
  const [saving, setSaving] = useState(false)
  const [nameError, setNameError] = useState("")
  const [dirty, setDirty] = useState(false)
  const [discardOpen, setDiscardOpen] = useState(false)

  // Reset form when dialog opens / initial changes
  useEffect(() => {
    if (open) {
      setName(initial?.name ?? "")
      setDescription(initial?.description ?? "")
      setIcon(initial?.icon ?? null)
      setRequireReview(initial?.require_publish_review ?? false)
      setNameError("")
      setDirty(false)
    }
  }, [open, initial])

  const handleNameChange = (val: string) => {
    setName(val)
    setDirty(true)
    setNameError("")
  }

  const handleClose = () => {
    if (dirty) {
      setDiscardOpen(true)
    } else {
      onOpenChange(false)
    }
  }

  const handleSubmit = async () => {
    if (!name.trim()) {
      setNameError(t("nameRequired"))
      return
    }
    setSaving(true)
    try {
      let saved: UserOrg
      if (initial) {
        saved = await orgApi.update(initial.id, {
          name: name.trim(),
          description: description.trim() || null,
          icon: icon || null,
          require_publish_review: requireReview,
        })
        toast.success(t("orgUpdated"))
      } else {
        saved = await orgApi.create({
          name: name.trim(),
          description: description.trim() || null,
          icon: icon || null,
        })
        toast.success(t("orgCreated", { name: saved.name }))
      }
      onSaved(saved)
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message ?? ""
      toast.error(initial ? t("updateFailed") : t("createFailed") + (msg ? `: ${msg}` : ""))
    } finally {
      setSaving(false)
    }
  }

  const isEdit = !!initial

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={(v) => {
          if (!v) handleClose()
          else onOpenChange(true)
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {isEdit ? t("editDialogTitle") : t("createDialogTitle")}
            </DialogTitle>
            <DialogDescription className="sr-only">
              {isEdit ? t("editDialogTitle") : t("createDialogTitle")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* Name */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                {t("nameLabel")} <span className="text-destructive">*</span>
              </label>
              <Input
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder={t("namePlaceholder")}
                aria-invalid={!!nameError}
              />
              {nameError && (
                <p className="text-sm text-destructive">{nameError}</p>
              )}
            </div>

            {/* Icon + Description row */}
            <div className="flex items-start gap-3">
              <div className="space-y-1.5 shrink-0">
                <label className="text-sm font-medium">{t("iconLabel")}</label>
                <EmojiPickerPopover
                  value={icon}
                  onChange={(val) => { setIcon(val); setDirty(true) }}
                  fallbackIcon={<Building2 className="h-5 w-5" />}
                />
              </div>
              <div className="space-y-1.5 flex-1 min-w-0">
                <label className="text-sm font-medium">{t("descriptionLabel")}</label>
                <Textarea
                  value={description}
                  onChange={(e) => { setDescription(e.target.value); setDirty(true) }}
                  placeholder={t("descriptionPlaceholder")}
                  rows={3}
                  className="resize-none"
                />
              </div>
            </div>

            {/* Publish review toggle -- only when editing */}
            {isEdit && (
              <>
                <Separator />
                <div className="flex items-center justify-between gap-4">
                  <div className="space-y-0.5">
                    <label className="text-sm font-medium">{t("requirePublishReview")}</label>
                    <p className="text-xs text-muted-foreground">{t("requirePublishReviewDescription")}</p>
                  </div>
                  <Switch
                    checked={requireReview}
                    onCheckedChange={(v) => { setRequireReview(v); setDirty(true) }}
                  />
                </div>
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose} disabled={saving}>
              {tc("cancel")}
            </Button>
            <Button onClick={handleSubmit} disabled={saving}>
              {saving ? tc("saving") : isEdit ? tc("save") : tc("create")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Discard confirmation -- sibling, never nested */}
      <AlertDialog open={discardOpen} onOpenChange={setDiscardOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("discardTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{t("discardDescription")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setDiscardOpen(false)
                onOpenChange(false)
              }}
            >
              {t("discardConfirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

// ---------------------------------------------------------------------------
// MembersSheet
// ---------------------------------------------------------------------------

interface MembersSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  org: UserOrg
  currentUserId: string
}

function MembersSheet({ open, onOpenChange, org, currentUserId }: MembersSheetProps) {
  const t = useTranslations("organizations")
  const tc = useTranslations("common")

  const [members, setMembers] = useState<OrgMember[]>([])
  const [loading, setLoading] = useState(false)
  const [usernameOrEmail, setUsernameOrEmail] = useState("")
  const [addRole, setAddRole] = useState<string>("member")
  const [addError, setAddError] = useState("")
  const [adding, setAdding] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<OrgMember | null>(null)

  const myRole = org.role
  const canManage = myRole === "owner" || myRole === "admin"

  const loadMembers = useCallback(async () => {
    setLoading(true)
    try {
      const data = await orgApi.listMembers(org.id)
      setMembers(data)
    } catch {
      toast.error(t("membersLoadFailed"))
    } finally {
      setLoading(false)
    }
  }, [org.id, t])

  useEffect(() => {
    if (open) {
      loadMembers()
      setUsernameOrEmail("")
      setAddError("")
      setAddRole("member")
    }
  }, [open, loadMembers])

  const handleAdd = async () => {
    if (!usernameOrEmail.trim()) {
      setAddError(t("usernameOrEmailRequired"))
      return
    }
    setAdding(true)
    try {
      await orgApi.addMember(org.id, {
        username_or_email: usernameOrEmail.trim(),
        role: addRole,
      })
      toast.success(t("memberAdded"))
      setUsernameOrEmail("")
      setAddRole("member")
      setAddError("")
      await loadMembers()
    } catch (err: unknown) {
      const msg = (err as { message?: string })?.message ?? t("addMemberFailed")
      toast.error(msg)
    } finally {
      setAdding(false)
    }
  }

  const handleChangeRole = async (member: OrgMember, newRole: string) => {
    try {
      const updated = await orgApi.changeRole(org.id, member.user_id, newRole)
      setMembers((prev) =>
        prev.map((m) => (m.user_id === member.user_id ? { ...m, role: updated.role } : m)),
      )
      toast.success(t("roleChanged"))
    } catch {
      toast.error(t("changeRoleFailed"))
    }
  }

  const handleRemove = async () => {
    if (!removeTarget) return
    try {
      await orgApi.removeMember(org.id, removeTarget.user_id)
      setMembers((prev) => prev.filter((m) => m.user_id !== removeTarget.user_id))
      toast.success(t("memberRemoved"))
    } catch {
      toast.error(t("removeMemberFailed"))
    } finally {
      setRemoveTarget(null)
    }
  }

  // Determine which roles the current user can assign to a specific member
  const assignableRoles = (targetRole: "owner" | "admin" | "member"): string[] => {
    if (myRole === "owner") {
      // Owner can set admin or member (cannot set owner via this UI)
      return ["admin", "member"].filter((r) => r !== targetRole)
    }
    if (myRole === "admin") {
      // Admin can only set member (cannot touch owner or other admins)
      return targetRole !== "member" && targetRole !== "owner" ? ["member"] : []
    }
    return []
  }

  const displayName = (m: OrgMember) =>
    m.display_name ?? m.username ?? m.email ?? m.user_id

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-full sm:max-w-lg flex flex-col">
          <SheetHeader className="shrink-0">
            <SheetTitle>{t("membersSheetTitle", { name: org.name })}</SheetTitle>
            <SheetDescription>{t("membersSheetDescription")}</SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto space-y-4 mt-4">
            {/* Add member form */}
            {canManage && (
              <div className="space-y-2">
                <p className="text-sm font-medium">{t("addMemberTitle")}</p>
                <div className="flex gap-2">
                  <div className="flex-1 space-y-1">
                    <Input
                      value={usernameOrEmail}
                      onChange={(e) => {
                        setUsernameOrEmail(e.target.value)
                        setAddError("")
                      }}
                      placeholder={t("usernameOrEmailPlaceholder")}
                      aria-invalid={!!addError}
                    />
                    {addError && (
                      <p className="text-sm text-destructive">{addError}</p>
                    )}
                  </div>
                  <Select value={addRole} onValueChange={setAddRole}>
                    <SelectTrigger className="w-[110px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">{t("roleAdmin")}</SelectItem>
                      <SelectItem value="member">{t("roleMember")}</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button onClick={handleAdd} disabled={adding} size="sm">
                    {adding ? t("adding") : t("addMemberButton")}
                  </Button>
                </div>
                <Separator className="mt-2" />
              </div>
            )}

            {/* Member list */}
            {loading ? (
              <p className="text-sm text-muted-foreground py-4 text-center">{tc("loading")}</p>
            ) : members.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">{t("noMembers")}</p>
            ) : (
              <div className="space-y-2">
                {members.map((member) => {
                  const isSelf = member.user_id === currentUserId
                  const rolesCanAssign = assignableRoles(member.role)
                  const canRemove = canManage && !isSelf && member.role !== "owner"
                  const canChangeRole = canManage && !isSelf && rolesCanAssign.length > 0 && member.role !== "owner"

                  return (
                    <div
                      key={member.user_id}
                      className="flex items-center justify-between py-2 px-1 rounded-md hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium shrink-0">
                          {displayName(member).charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">
                            {displayName(member)}
                            {isSelf && (
                              <span className="ml-1 text-xs text-muted-foreground">(you)</span>
                            )}
                          </p>
                          {member.email && (
                            <p className="text-xs text-muted-foreground truncate">{member.email}</p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="outline" className={roleBadgeClass(member.role)}>
                          {t(`role${member.role.charAt(0).toUpperCase()}${member.role.slice(1)}` as "roleOwner" | "roleAdmin" | "roleMember")}
                        </Badge>

                        {(canChangeRole || canRemove) && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 p-0"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                                <span className="sr-only">{tc("actions")}</span>
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              {canChangeRole &&
                                rolesCanAssign.map((r) => (
                                  <DropdownMenuItem
                                    key={r}
                                    onClick={() => handleChangeRole(member, r)}
                                  >
                                    <Shield className="mr-2 h-4 w-4" />
                                    {t("changeRole")}: {t(`role${r.charAt(0).toUpperCase()}${r.slice(1)}` as "roleOwner" | "roleAdmin" | "roleMember")}
                                  </DropdownMenuItem>
                                ))}
                              {canChangeRole && canRemove && <DropdownMenuSeparator />}
                              {canRemove && (
                                <DropdownMenuItem
                                  variant="destructive"
                                  onClick={() => setRemoveTarget(member)}
                                >
                                  <UserMinus className="mr-2 h-4 w-4" />
                                  {t("removeMember")}
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* Remove member confirmation */}
      <AlertDialog open={!!removeTarget} onOpenChange={(v) => { if (!v) setRemoveTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("removeMemberTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {removeTarget
                ? t("removeMemberDescription", {
                    username: displayName(removeTarget),
                  })
                : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleRemove}>
              {t("removeMemberConfirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}

// ---------------------------------------------------------------------------
// ReviewsSheet -- admin/owner review management
// ---------------------------------------------------------------------------

interface ReviewsSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  org: UserOrg
}

function ReviewsSheet({ open, onOpenChange, org }: ReviewsSheetProps) {
  const t = useTranslations("organizations")
  const tc = useTranslations("common")

  const [reviews, setReviews] = useState<ReviewItem[]>([])
  const [loading, setLoading] = useState(false)
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string>("__default__")
  const [statusFilter, setStatusFilter] = useState<string>("pending_review")

  // Reject dialog state
  const [rejectTarget, setRejectTarget] = useState<ReviewItem | null>(null)
  const [rejectNote, setRejectNote] = useState("")

  const loadReviews = useCallback(async () => {
    setLoading(true)
    try {
      const params: { resource_type?: string; status?: string } = {}
      if (resourceTypeFilter !== "__default__") params.resource_type = resourceTypeFilter
      if (statusFilter !== "__default__") params.status = statusFilter
      const data = await orgApi.listReviews(org.id, params)
      setReviews(data)
    } catch {
      toast.error(t("reviewLoadFailed"))
    } finally {
      setLoading(false)
    }
  }, [org.id, resourceTypeFilter, statusFilter, t])

  useEffect(() => {
    if (open) {
      loadReviews()
    }
  }, [open, loadReviews])

  const handleApprove = async (item: ReviewItem) => {
    try {
      await orgApi.approveReview(org.id, {
        resource_type: item.resource_type,
        resource_id: item.resource_id,
      })
      toast.success(t("reviewApproved"))
      setReviews((prev) => prev.filter((r) => r.resource_id !== item.resource_id))
    } catch {
      toast.error(t("reviewApproveFailed"))
    }
  }

  const handleReject = async () => {
    if (!rejectTarget) return
    try {
      await orgApi.rejectReview(org.id, {
        resource_type: rejectTarget.resource_type,
        resource_id: rejectTarget.resource_id,
        note: rejectNote.trim() || undefined,
      })
      toast.success(t("reviewRejected"))
      setReviews((prev) => prev.filter((r) => r.resource_id !== rejectTarget.resource_id))
    } catch {
      toast.error(t("reviewRejectFailed"))
    } finally {
      setRejectTarget(null)
      setRejectNote("")
    }
  }

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-full sm:max-w-lg flex flex-col">
          <SheetHeader className="shrink-0">
            <SheetTitle>{t("reviewManagement")}</SheetTitle>
            <SheetDescription>{t("reviewsSheetDescription")}</SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto space-y-4 mt-4">
            {/* Filters */}
            <div className="flex gap-2">
              <Select value={resourceTypeFilter} onValueChange={setResourceTypeFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__default__">{t("filterAll")}</SelectItem>
                  <SelectItem value="agent">{t("filterAgents")}</SelectItem>
                  <SelectItem value="connector">{t("filterConnectors")}</SelectItem>
                  <SelectItem value="knowledge_base">{t("filterKBs")}</SelectItem>
                  <SelectItem value="mcp_server">{t("filterMcpServers")}</SelectItem>
                </SelectContent>
              </Select>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[130px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__default__">{t("filterAll")}</SelectItem>
                  <SelectItem value="pending_review">{t("filterPending")}</SelectItem>
                  <SelectItem value="rejected">{t("filterRejected")}</SelectItem>
                  <SelectItem value="approved">{t("filterApproved")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Separator />

            {/* Review list */}
            {loading ? (
              <p className="text-sm text-muted-foreground py-4 text-center">{tc("loading")}</p>
            ) : reviews.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">{t("noReviewsPending")}</p>
            ) : (
              <div className="space-y-2">
                {reviews.map((item) => (
                  <div
                    key={`${item.resource_type}-${item.resource_id}`}
                    className="rounded-md border border-border p-3 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="h-8 w-8 rounded-md bg-muted flex items-center justify-center text-sm shrink-0">
                          {item.resource_icon ?? <Building2 className="h-4 w-4 text-muted-foreground" />}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{item.resource_name}</p>
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                              {resourceTypeLabel(item.resource_type, t)}
                            </Badge>
                            {item.owner_username && (
                              <span>{t("submittedBy", { owner: item.owner_username })}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Status badge */}
                      {item.publish_status === "pending_review" && (
                        <Badge variant="outline" className="border-amber-400 text-amber-600 dark:text-amber-400 shrink-0">
                          {t("pendingReview")}
                        </Badge>
                      )}
                      {item.publish_status === "approved" && (
                        <Badge variant="outline" className="border-emerald-400 text-emerald-600 dark:text-emerald-400 shrink-0">
                          {t("approved")}
                        </Badge>
                      )}
                      {item.publish_status === "rejected" && (
                        <Badge variant="outline" className="border-destructive text-destructive shrink-0">
                          {t("rejected")}
                        </Badge>
                      )}
                    </div>

                    {/* Review note for rejected items */}
                    {item.publish_status === "rejected" && item.review_note && (
                      <p className="text-xs text-muted-foreground bg-muted/50 rounded px-2 py-1">
                        {t("rejectedNote", { note: item.review_note })}
                      </p>
                    )}

                    {/* Action buttons -- only for pending items */}
                    {item.publish_status === "pending_review" && (
                      <div className="flex items-center gap-2 pt-1">
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs gap-1 text-emerald-600 dark:text-emerald-400 border-emerald-400/40 hover:bg-emerald-500/10"
                          onClick={() => handleApprove(item)}
                        >
                          <Check className="h-3.5 w-3.5" />
                          {t("approveResource")}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs gap-1 text-destructive border-destructive/40 hover:bg-destructive/10"
                          onClick={() => { setRejectTarget(item); setRejectNote("") }}
                        >
                          <X className="h-3.5 w-3.5" />
                          {t("rejectResource")}
                        </Button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* Reject confirmation dialog -- sibling */}
      <Dialog open={!!rejectTarget} onOpenChange={(v) => { if (!v) { setRejectTarget(null); setRejectNote("") } }}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{t("rejectDialogTitle")}</DialogTitle>
            <DialogDescription>{t("rejectDialogDescription")}</DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              placeholder={t("rejectReasonPlaceholder")}
              rows={3}
              className="resize-none"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setRejectTarget(null); setRejectNote("") }}>
              {tc("cancel")}
            </Button>
            <Button variant="destructive" onClick={handleReject}>
              {t("rejectResource")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ---------------------------------------------------------------------------
// OrgCard
// ---------------------------------------------------------------------------

interface OrgCardProps {
  org: UserOrg
  currentUserId: string
  onEdit: (org: UserOrg) => void
  onDelete: (org: UserOrg) => void
  onLeave: (org: UserOrg) => void
  onManageMembers: (org: UserOrg) => void
  onManageReviews: (org: UserOrg) => void
}

function OrgCard({ org, currentUserId, onEdit, onDelete, onLeave, onManageMembers, onManageReviews }: OrgCardProps) {
  const t = useTranslations("organizations")
  const tc = useTranslations("common")

  const isOwner = org.role === "owner"
  const isAdminOrOwner = org.role === "owner" || org.role === "admin"
  const canLeave = !isOwner

  return (
    <div className="rounded-lg border border-border bg-card p-4 flex items-start justify-between gap-3">
      <div className="flex items-start gap-3 min-w-0">
        {/* Icon */}
        <div className="h-10 w-10 rounded-md bg-muted flex items-center justify-center text-lg shrink-0">
          {org.icon ?? <Building2 className="h-5 w-5 text-muted-foreground" />}
        </div>

        {/* Info */}
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold truncate">{org.name}</p>
            <Badge variant="outline" className={roleBadgeClass(org.role)}>
              {t(`role${org.role.charAt(0).toUpperCase()}${org.role.slice(1)}` as "roleOwner" | "roleAdmin" | "roleMember")}
            </Badge>
            {org.require_publish_review && (
              <Badge variant="outline" className="border-amber-400/40 text-amber-600 dark:text-amber-400 text-[10px] px-1.5 py-0 h-5">
                <ShieldCheck className="h-3 w-3 mr-0.5" />
                {t("reviewEnabled")}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">/{org.slug}</p>
          {org.description && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{org.description}</p>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            {t(
              (org.member_count ?? 0) === 1 ? "memberCountOne" : "memberCount",
              { count: org.member_count ?? 0 }
            )}
          </p>
        </div>
      </div>

      {/* Actions */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-7 w-7 p-0 shrink-0">
            <MoreHorizontal className="h-4 w-4" />
            <span className="sr-only">{tc("actions")}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {isAdminOrOwner && (
            <DropdownMenuItem onClick={() => onManageMembers(org)}>
              <Users className="mr-2 h-4 w-4" />
              {t("manageMembers")}
            </DropdownMenuItem>
          )}
          {isAdminOrOwner && org.require_publish_review && (
            <DropdownMenuItem onClick={() => onManageReviews(org)}>
              <ClipboardCheck className="mr-2 h-4 w-4" />
              {t("reviewManagement")}
            </DropdownMenuItem>
          )}
          {isAdminOrOwner && (
            <DropdownMenuItem onClick={() => onEdit(org)}>
              <Settings className="mr-2 h-4 w-4" />
              {tc("edit")}
            </DropdownMenuItem>
          )}
          {canLeave && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onClick={() => onLeave(org)}
              >
                <LogOut className="mr-2 h-4 w-4" />
                {t("leaveOrganization")}
              </DropdownMenuItem>
            </>
          )}
          {isOwner && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onClick={() => onDelete(org)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {tc("delete")}
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

// ---------------------------------------------------------------------------
// OrganizationSettings (main export)
// ---------------------------------------------------------------------------

export function OrganizationSettings() {
  const t = useTranslations("organizations")
  const tc = useTranslations("common")
  const { user } = useAuth()

  const [orgs, setOrgs] = useState<UserOrg[]>([])
  const [loading, setLoading] = useState(true)

  // Dialogs / Sheets
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<UserOrg | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<UserOrg | null>(null)
  const [leaveTarget, setLeaveTarget] = useState<UserOrg | null>(null)
  const [membersTarget, setMembersTarget] = useState<UserOrg | null>(null)
  const [membersOpen, setMembersOpen] = useState(false)
  const [reviewsTarget, setReviewsTarget] = useState<UserOrg | null>(null)
  const [reviewsOpen, setReviewsOpen] = useState(false)

  const loadOrgs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await orgApi.list()
      setOrgs(data)
    } catch {
      toast.error(t("loadFailed"))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    loadOrgs()
  }, [loadOrgs])

  const handleCreated = (org: UserOrg) => {
    setOrgs((prev) => [org, ...prev])
  }

  const handleEdited = (updated: UserOrg) => {
    setOrgs((prev) => prev.map((o) => (o.id === updated.id ? updated : o)))
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await orgApi.delete(deleteTarget.id)
      toast.success(t("orgDeleted", { name: deleteTarget.name }))
      setOrgs((prev) => prev.filter((o) => o.id !== deleteTarget.id))
    } catch {
      toast.error(t("deleteFailed"))
    } finally {
      setDeleteTarget(null)
    }
  }

  const handleLeave = async () => {
    if (!leaveTarget || !user) return
    try {
      await orgApi.removeMember(leaveTarget.id, user.id)
      toast.success(t("leftOrganization", { name: leaveTarget.name }))
      setOrgs((prev) => prev.filter((o) => o.id !== leaveTarget.id))
    } catch {
      toast.error(t("leaveFailed"))
    } finally {
      setLeaveTarget(null)
    }
  }

  const handleManageMembers = (org: UserOrg) => {
    setMembersTarget(org)
    setMembersOpen(true)
  }

  const handleManageReviews = (org: UserOrg) => {
    setReviewsTarget(org)
    setReviewsOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-medium">{t("myOrganizations")}</h3>
          <p className="text-sm text-muted-foreground">{t("description")}</p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("createOrganization")}
        </Button>
      </div>

      {/* List */}
      {loading ? (
        <p className="text-sm text-muted-foreground py-8 text-center">{tc("loading")}</p>
      ) : orgs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <Building2 className="h-12 w-12 text-muted-foreground/40" />
          <p className="text-sm font-medium">{t("noOrganizations")}</p>
          <p className="text-xs text-muted-foreground max-w-xs">{t("noOrganizationsHint")}</p>
          <Button size="sm" variant="outline" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t("createOrganization")}
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {orgs.map((org) => (
            <OrgCard
              key={org.id}
              org={org}
              currentUserId={user?.id ?? ""}
              onEdit={(o) => { setEditTarget(o); setEditOpen(true) }}
              onDelete={(o) => setDeleteTarget(o)}
              onLeave={(o) => setLeaveTarget(o)}
              onManageMembers={handleManageMembers}
              onManageReviews={handleManageReviews}
            />
          ))}
        </div>
      )}

      {/* Create dialog */}
      <OrgFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        initial={null}
        onSaved={handleCreated}
      />

      {/* Edit dialog */}
      <OrgFormDialog
        open={editOpen}
        onOpenChange={(v) => { setEditOpen(v); if (!v) setEditTarget(null) }}
        initial={editTarget}
        onSaved={handleEdited}
      />

      {/* Delete confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteOrgTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget ? t("deleteOrgDescription", { name: deleteTarget.name }) : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>
              {t("deleteOrgConfirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Leave confirmation */}
      <AlertDialog open={!!leaveTarget} onOpenChange={(v) => { if (!v) setLeaveTarget(null) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("leaveOrgTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {leaveTarget ? t("leaveOrgDescription", { name: leaveTarget.name }) : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleLeave}>
              {t("leaveOrgConfirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Members sheet */}
      {membersTarget && (
        <MembersSheet
          open={membersOpen}
          onOpenChange={(v) => { setMembersOpen(v); if (!v) setMembersTarget(null) }}
          org={membersTarget}
          currentUserId={user?.id ?? ""}
        />
      )}

      {/* Reviews sheet */}
      {reviewsTarget && (
        <ReviewsSheet
          open={reviewsOpen}
          onOpenChange={(v) => { setReviewsOpen(v); if (!v) setReviewsTarget(null) }}
          org={reviewsTarget}
        />
      )}
    </div>
  )
}
