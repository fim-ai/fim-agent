# FIM Agent — Claude Code Instructions

## Project Overview

FIM Agent is an AI-powered Connector Hub. Python async framework, provider-agnostic, protocol-first.

- **Package manager**: `uv` (not pip)
- **Frontend**: Next.js + pnpm (in `frontend/`)
- **Tests**: `uv run pytest`
- **Launcher**: `./start.sh [portal|api]`

## Architecture

```
src/fim_agent/
├── core/
│   ├── agent/       # ReActAgent (JSON mode + native function calling)
│   ├── model/       # BaseLLM, OpenAICompatibleLLM, ModelRegistry, retry, rate limiting, usage tracking
│   ├── planner/     # DAGPlanner → DAGExecutor → PlanAnalyzer
│   ├── memory/      # WindowMemory, SummaryMemory
│   └── tools/       # Tool base classes, ConnectorToolAdapter
├── web/             # FastAPI backend API (agents, connectors, KB, chat)
frontend/            # Next.js portal (shadcn/ui)
```

## Git Commit Rules (MANDATORY)

### Atomic Commits

- **Always split unrelated changes into separate commits**, even if the user says "commit all"
- Group by feature/fix/refactor — one logical change per commit
- This applies to both user-requested commits and post-work commits
- Example: markitdown integration + sidebar fix + interrupt UI = 3 separate commits
- Makes `git log`, `git bisect`, and code review much easier

## Git Safety Rules (MANDATORY)

These rules exist because of a real data loss incident. **Do not skip them.**

### Stash

- **NEVER use `git stash --include-untracked`** when there are important untracked files
- Before any stash: run `git status` and review untracked files
- Important untracked files must be `git add`-ed or committed to a temp branch first
- Use `git stash pop` instead of `git stash apply` + `git stash drop`
- Before `git stash drop`: always confirm all content has been restored

### Parallel Development (Worktrees)

Before starting parallel worktree development:
1. Commit ALL important untracked files (or at least `git add` them)
2. Ensure `.gitignore` covers `node_modules/` and other large generated dirs
3. Working tree must be clean (`git status` shows nothing important)
4. Worktree agents MUST commit their changes on their branch (not leave uncommitted changes)
5. Merge via `git merge` / `git cherry-pick`, not manual file copying

## Frontend Build Safety

- **NEVER run `rm -rf frontend/.next`** while the dev server is running — this kills Turbopack HMR
- Production builds use a separate dir: `.next-build` (configured via `distDir` in `next.config.ts`)
- To build: just run `cd frontend && pnpm build` — the build script handles cleaning `.next-build`
- **NEVER run `rm -rf .next && next build`** — use `pnpm build` which only cleans `.next-build`

## Frontend UI Conventions

- **NEVER use native browser dialogs** (`window.confirm()`, `window.alert()`, `window.prompt()`). Always use shadcn/ui components instead:
  - Confirmations → `AlertDialog` (`@/components/ui/alert-dialog`)
  - Notifications → Toast or inline feedback
  - Input prompts → `Dialog` (`@/components/ui/dialog`)

- **Navigation elements MUST use `<Link>` instead of `<button onClick={router.push()}>`**. If clicking something navigates to a URL, it must be a semantic `<a>` tag (Next.js `<Link>`) so users can middle-click / Cmd+Click to open in a new tab. Side effects (e.g. `selectConversation()`) go in the `onClick` handler — they run for normal clicks but are safely skipped for new-tab opens since the URL drives initial state.
  - Plain elements: `<Link href={url} onClick={sideEffect}>`
  - shadcn `<Button>`: use `asChild` + `<Link>` inside

## Toast Feedback Convention (MANDATORY)

- **Every modal/dialog/drawer/sheet with a submit action MUST show toast feedback** for both success and failure.
  - Success → `toast.success("Action completed")` (use sonner)
  - Failure → `toast.error(errMsg(err))` or `toast.error("Failed to ...")` (use sonner)
- This applies to: create, update, delete, upload, publish/unpublish, reset password, toggle operations — any API call triggered from a modal/drawer.
- **NEVER silently close a dialog** after an API call — the user must see confirmation.
- **NEVER use only `console.error()`** for user-facing errors — always show `toast.error()`.
- Inline error display (e.g. `setError(msg)`) is acceptable in addition to toast, but toast is the minimum.

## Dirty State Protection Convention

Modal/drawer forms with meaningful user input MUST protect against accidental close.

**Applies to**:
- Modal/Drawer/Sheet forms: create, edit, upload, write
- Full-page editor forms (e.g. agent settings page) — intercept navigation instead of backdrop

**Does NOT apply to**: Read-only drawers, search dialogs, inline panels (ActionManager, ChunkDrawer, IterationDetailDrawer).

### Standard implementation pattern

```typescript
// 1. isDirty — truthy when user has entered something worth protecting
const isDirty = name.trim().length > 0 || /* other fields */

// 2. Confirm state
const [showCloseConfirm, setShowCloseConfirm] = useState(false)

// 3. Unified close handler (X button + Cancel button both call this)
const handleClose = (open: boolean) => {
  if (!open && isDirty) { setShowCloseConfirm(true); return }
  onOpenChange(open)
}

// 4. DialogContent — use onInteractOutside only (covers pointer + focus)
//    When dirty: prevent auto-close AND show the same confirm dialog
//    When not dirty: do nothing → Dialog closes normally
<DialogContent
  onInteractOutside={(e) => {
    if (isDirty) { e.preventDefault(); setShowCloseConfirm(true) }
  }}
>

// 5. AlertDialog placed OUTSIDE (sibling, not nested) the Dialog
<AlertDialog open={showCloseConfirm} onOpenChange={setShowCloseConfirm}>
  <AlertDialogTitle>Discard unsaved changes?</AlertDialogTitle>
  <AlertDialogCancel>Keep editing</AlertDialogCancel>
  <AlertDialogAction
    onClick={() => onOpenChange(false)}
    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
  >
    Discard & close
  </AlertDialogAction>
</AlertDialog>
```

**Key rules for Modal/Drawer**:
- Empty form (not dirty) → backdrop click closes directly, no confirmation
- Dirty form → backdrop click shows the same AlertDialog as X button (consistent UX)
- **NEVER silently block backdrop clicks** — always show the confirm dialog when dirty
- Use `onInteractOutside` only, not `onPointerDownOutside` (avoids duplicate triggers)
- AlertDialog must be a sibling of Dialog, never nested inside DialogContent

### Full-page form pattern

For full-page editor pages (e.g. `/agents/[id]`), there is no backdrop — instead intercept navigation:

```typescript
// 1. Track dirty state via onDirtyChange prop from child form
const [formDirty, setFormDirty] = useState(false)
const [showLeaveDialog, setShowLeaveDialog] = useState(false)

// 2. Warn on browser refresh / tab close
useEffect(() => {
  if (!formDirty) return
  const handler = (e: BeforeUnloadEvent) => { e.preventDefault() }
  window.addEventListener("beforeunload", handler)
  return () => window.removeEventListener("beforeunload", handler)
}, [formDirty])

// 3. Back button — swap Link for button when dirty
{formDirty ? (
  <Button onClick={() => setShowLeaveDialog(true)}><ArrowLeft /></Button>
) : (
  <Button asChild><Link href="/parent"><ArrowLeft /></Link></Button>
)}

// 4. AlertDialog for leave confirmation
<AlertDialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
  <AlertDialogTitle>Unsaved changes</AlertDialogTitle>
  <AlertDialogDescription>Leaving this page will discard them.</AlertDialogDescription>
  <AlertDialogCancel>Stay</AlertDialogCancel>
  <AlertDialogAction onClick={() => router.push("/parent")}
    className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
    Discard & Leave
  </AlertDialogAction>
</AlertDialog>
```

**Key difference from modal**: Full-page forms use `beforeunload` + navigation interception (not `onInteractOutside`). The child form component exposes an `onDirtyChange` callback to propagate dirty state up to the page.

## Code Conventions

- Type hints on all public functions
- Async-first: use `async def` for I/O-bound operations
- Tests alongside features: every new module gets a corresponding `tests/test_*.py`
- Keep imports in `__init__.py` minimal — only re-export public API

## Post-Commit Documentation Sync (MANDATORY)

After every commit, you MUST update documentation before moving on. Do NOT ask the user — just do it silently.

### Every commit (feat / fix / refactor / all types)

1. **`wiki/CHANGELOG.md`** — append the change under `[Unreleased]` in the correct section (`### Added` / `### Changed` / `### Fixed` / `### Removed`). Follow [Keep a Changelog](https://keepachangelog.com/) format.

### Additionally after `feat:` commits

2. **`wiki/Roadmap.md`** — check off `[ ]` items that this feature completes. If the feature has no matching entry **and is user-facing**, insert a new item under the **current version** section and mark it done. Never retroactively add to already-shipped older versions.
3. **`example.env`** — compare with `.env`, any new key must be added with placeholder and comment.
4. **`README.md` Key Features** — add entry if this is a new user-facing capability.
5. **`README.md` Project Structure** — update if new modules/directories were added under `src/`.
6. **`wiki/` pages** — update if architecture, execution modes, or competitive positioning changed.

### Always at the end

7. **Wiki sync** — if any `wiki/*.md` file was modified, run `./scripts/sync-wiki.sh`

### Version Alignment Rules

- **CHANGELOG and Roadmap versions must be strictly aligned.** Both use the same version numbers (e.g., v0.6.1).
- The current development version = the latest shipped Roadmap version (e.g., if v0.6.1 is shipped, `[Unreleased]` in CHANGELOG will become v0.6.2 or remain under the current version when shipped).
- When a Roadmap version is marked as shipped, move CHANGELOG `[Unreleased]` items into a new versioned section matching that Roadmap version.
- Never place new features under already-shipped Roadmap versions retroactively.
