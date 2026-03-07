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

## Git Rules (MANDATORY)

- **Atomic commits**: always split unrelated changes into separate commits, even if user says "commit all"
- **NEVER `git stash --include-untracked`** with important untracked files — `git add` them first; use `git stash pop` not `apply` + `drop`
- **Worktrees**: clean working tree before starting; agents MUST commit on their branch; merge via `git merge`/`git cherry-pick`, not file copying

## Frontend Build Safety

- **NEVER `rm -rf frontend/.next`** while dev server is running — kills Turbopack HMR
- Production builds → `.next-build` (separate dir). To build: `cd frontend && pnpm build`

## Frontend UI Conventions

- **No native dialogs** (`confirm`/`alert`/`prompt`) — use `AlertDialog` / `Dialog` / Toast (sonner)
- **Navigation → `<Link>`**, not `<button onClick={router.push()}>`. For shadcn `<Button>`, use `asChild` + `<Link>` inside
- **Focus rings**: use `focus-visible:outline-*` pattern, **never** `focus-visible:ring-*` — `ring` is `box-shadow`, gets clipped by `overflow:hidden`. See `ui/input.tsx` for reference.
- **No `pl-*`/`pr-*` on form wrappers** containing `<Input>`/`<Textarea>` — clips `shadow-xs`. Use `px-*` or `gap-*` instead.
- **No native `<select>`** — use shadcn `<Select>` with `<SelectTrigger className="w-full">`. For empty defaults, use `__default__` sentinel (Radix treats `""` as unset).

## Toast Feedback Convention (MANDATORY)

Every user-triggered API call MUST show toast: success → `toast.success()`, failure → `toast.error(errMsg(err))`. Never silently close dialogs, never use only `console.error()`, never use inline flash state — always toast.

## Dirty State Protection (MANDATORY)

Create/edit forms MUST guard against accidental close (modal backdrop, X button, page navigation). AlertDialog must be **sibling** of Dialog, never nested. References: `connector-settings-form.tsx` (modal pattern), `agents/[id]/page.tsx` (full-page pattern).

## i18n (MANDATORY)

All UI text must use `next-intl` — **never hardcode English strings**. Add keys to both `messages/en/{ns}.json` and `messages/zh/{ns}.json`, use `useTranslations("{ns}")` in components. Shared strings (Save/Cancel/Delete) → `useTranslations("common")`. New namespace = just drop JSON files, auto-discovered via `fs.readdirSync`.

## Code Conventions

- Type hints on all public functions
- Async-first: `async def` for I/O-bound operations
- Tests alongside features: every new module → `tests/test_*.py`
- Keep `__init__.py` imports minimal — only re-export public API

## Post-Commit Documentation Sync (MANDATORY)

After every commit, update docs silently (do NOT ask the user):

1. **`wiki/CHANGELOG.md`** — append under `[Unreleased]` (`### Added/Changed/Fixed/Removed`)
2. *(feat only)* **`wiki/Roadmap.md`** — check off completed items; add new user-facing items under current version (never retroactively add to already-shipped versions)
3. *(feat only)* **`example.env`** — add any new env keys with placeholder + comment; then **sync `wiki/Environment-Variables.md`** — add the new variable(s) to the correct section table
4. *(feat only)* **`README.md`** — update Key Features and Project Structure if needed
5. If any `wiki/*.md` changed → run `./scripts/sync-wiki.sh`

**Version alignment**: CHANGELOG `[Unreleased]` and Roadmap must use the same version numbers.
