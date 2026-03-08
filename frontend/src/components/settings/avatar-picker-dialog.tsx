"use client"

import { useRef, useState, useEffect } from "react"
import { useTranslations } from "next-intl"
import { Upload, Trash2, Check, Shuffle } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { AVATAR_ICONS, AVATAR_COLORS, parseBuiltinAvatar, UserAvatar } from "@/components/shared/user-avatar"
import { authApi } from "@/lib/api"
import { useAuth } from "@/contexts/auth-context"
import { toast } from "sonner"

const AVATAR_MAX_SIZE = 5 * 1024 * 1024
const AVATAR_ALLOWED_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
]

interface AvatarPickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function AvatarPickerDialog({
  open,
  onOpenChange,
}: AvatarPickerDialogProps) {
  const { user, updateUser } = useAuth()
  const t = useTranslations("settings.general")
  const tc = useTranslations("common")
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [saving, setSaving] = useState(false)
  const [uploadError, setUploadError] = useState("")

  const currentAvatar = user?.avatar
  const currentParsed = currentAvatar ? parseBuiltinAvatar(currentAvatar) : null

  const [selectedColor, setSelectedColor] = useState(currentParsed?.colorId || "blue")
  const [selectedIcon, setSelectedIcon] = useState<string | null>(currentParsed?.iconId || null)

  // Sync local state when dialog opens with a different avatar
  useEffect(() => {
    if (open) {
      const parsed = currentAvatar ? parseBuiltinAvatar(currentAvatar) : null
      setSelectedColor(parsed?.colorId || "blue")
      setSelectedIcon(parsed?.iconId || null)
      setUploadError("")
    }
  }, [open, currentAvatar])

  const hasBuiltinSelection = !!selectedIcon
  const builtinValue = selectedIcon ? `builtin:${selectedIcon}:${selectedColor}` : null
  const isDirty = hasBuiltinSelection && builtinValue !== currentAvatar

  const handleSaveBuiltin = async () => {
    if (!selectedIcon || !isDirty) return
    setSaving(true)
    try {
      const updated = await authApi.updateProfile({ avatar: builtinValue })
      updateUser(updated)
      toast.success(t("avatarUpdated"))
      onOpenChange(false)
    } catch {
      toast.error(t("avatarUpdateFailed"))
    } finally {
      setSaving(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    e.target.value = ""
    setUploadError("")

    if (!AVATAR_ALLOWED_TYPES.includes(file.type)) {
      setUploadError(t("invalidImageFormat"))
      return
    }
    if (file.size > AVATAR_MAX_SIZE) {
      setUploadError(t("imageTooLarge"))
      return
    }

    setSaving(true)
    try {
      const updated = await authApi.uploadAvatar(file)
      updateUser(updated)
      toast.success(t("avatarUpdated"))
      onOpenChange(false)
    } catch {
      toast.error(t("avatarUpdateFailed"))
    } finally {
      setSaving(false)
    }
  }

  const handleRemove = async () => {
    setSaving(true)
    try {
      const updated = await authApi.removeAvatar()
      updateUser(updated)
      toast.success(t("avatarRemoved"))
      onOpenChange(false)
    } catch {
      toast.error(t("avatarRemoveFailed"))
    } finally {
      setSaving(false)
    }
  }

  const handleRandom = () => {
    const randColor = AVATAR_COLORS[Math.floor(Math.random() * AVATAR_COLORS.length)]
    const randIcon = AVATAR_ICONS[Math.floor(Math.random() * AVATAR_ICONS.length)]
    setSelectedColor(randColor.id)
    setSelectedIcon(randIcon.id)
  }

  const colorCfg = AVATAR_COLORS.find((c) => c.id === selectedColor) || AVATAR_COLORS[0]
  const previewIconCfg = selectedIcon ? AVATAR_ICONS.find((i) => i.id === selectedIcon) : null
  const displayName = user?.display_name || user?.email || ""
  const userFallback = (displayName || "U").charAt(0).toUpperCase()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("chooseAvatar")}</DialogTitle>
          <DialogDescription>
            {t("chooseAvatarDescription")}
          </DialogDescription>
        </DialogHeader>

        {/* Live preview + random */}
        <div className="flex items-center gap-4 py-1">
          <div className="relative">
            {previewIconCfg ? (() => {
              const Icon = previewIconCfg.icon
              return (
                <div className={cn("flex h-16 w-16 items-center justify-center rounded-full", colorCfg.bg)}>
                  <Icon className="h-8 w-8 text-white" />
                </div>
              )
            })() : (
              <UserAvatar avatar={currentAvatar} userId={user?.id} fallback={userFallback} className="h-16 w-16" iconClassName="h-8 w-8" />
            )}
          </div>
          <div className="flex flex-1 flex-col gap-1.5">
            <p className="text-sm font-medium">{displayName}</p>
            <p className="text-xs text-muted-foreground">{t("avatarPreviewHint")}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRandom}
              disabled={saving}
              className="w-fit"
            >
              <Shuffle className="h-3.5 w-3.5" />
              {t("avatarRandom")}
            </Button>
          </div>
        </div>

        {/* Color palette */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">{t("avatarColorLabel")}</p>
          <div className="flex flex-wrap gap-2">
            {AVATAR_COLORS.map((color) => {
              const isSelected = selectedColor === color.id
              return (
                <button
                  key={color.id}
                  onClick={() => setSelectedColor(color.id)}
                  disabled={saving}
                  className={cn(
                    "relative h-7 w-7 rounded-full transition-all outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                    color.bg,
                    isSelected
                      ? "outline-2 outline-offset-2 outline-primary"
                      : "hover:outline-2 hover:outline-offset-2 hover:outline-muted-foreground/40",
                  )}
                  aria-label={color.id}
                >
                  {isSelected && (
                    <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50">
                      <Check className="h-3.5 w-3.5 text-white stroke-[2.5]" />
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Icon grid — rendered in selected color */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-muted-foreground">{t("avatarIconLabel")}</p>
          <div className="grid grid-cols-8 gap-2">
            {AVATAR_ICONS.map((ic) => {
              const isSelected = selectedIcon === ic.id
              const Icon = ic.icon
              return (
                <button
                  key={ic.id}
                  onClick={() => setSelectedIcon(ic.id)}
                  disabled={saving}
                  className={cn(
                    "rounded-full transition-all outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                    isSelected
                      ? "outline-2 outline-offset-2 outline-primary"
                      : "hover:outline-2 hover:outline-offset-2 hover:outline-muted-foreground/40",
                  )}
                >
                  <div
                    className={cn(
                      "relative flex h-9 w-9 items-center justify-center rounded-full",
                      colorCfg.bg,
                    )}
                  >
                    <Icon className="h-4.5 w-4.5 text-white" />
                    {isSelected && (
                      <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50">
                        <Check className="h-4.5 w-4.5 text-white stroke-[2.5]" />
                      </div>
                    )}
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Save built-in selection */}
        {isDirty && (
          <Button
            size="sm"
            onClick={handleSaveBuiltin}
            disabled={saving}
            className="w-full"
          >
            {tc("save")}
          </Button>
        )}

        <Separator />

        {/* Upload and Remove actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={saving}
            className="flex-1"
          >
            <Upload className="h-4 w-4" />
            {t("uploadAvatar")}
          </Button>
          {currentAvatar && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRemove}
              disabled={saving}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
              {t("removeAvatar")}
            </Button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={handleUpload}
            className="hidden"
          />
        </div>
        {uploadError && (
          <p className="text-sm text-destructive">{uploadError}</p>
        )}
      </DialogContent>
    </Dialog>
  )
}
